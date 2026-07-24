import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  act,
  renderHook,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  getActiveGenerationRun,
  getGenerationRun,
  startGenerationRun,
} from "../api/client";
import type {
  GenerationRun,
  GenerationRunStatus,
} from "../api/types";
import { useGenerationRun } from "./useGenerationRun";

vi.mock("../api/client", () => ({
  getActiveGenerationRun: vi.fn(),
  getGenerationRun: vi.fn(),
  startGenerationRun: vi.fn(),
}));

const getActiveGenerationRunMock = vi.mocked(
  getActiveGenerationRun,
);
const getGenerationRunMock = vi.mocked(
  getGenerationRun,
);
const startGenerationRunMock = vi.mocked(
  startGenerationRun,
);

function generationRun(
  status: GenerationRunStatus,
  overrides: Partial<GenerationRun> = {},
): GenerationRun {
  return {
    id: 17,
    experiment_id: 3,
    status,
    generation_number: 2,
    game_id: status === "completed" ? 41 : null,
    error_message: null,
    created_at: "2026-07-24T10:00:00Z",
    started_at:
      status === "queued"
        ? null
        : "2026-07-24T10:00:01Z",
    completed_at:
      status === "completed" || status === "failed"
        ? "2026-07-24T10:00:05Z"
        : null,
    ...overrides,
  };
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: {
        retry: false,
      },
      queries: {
        retry: false,
      },
    },
  });

  function Wrapper({
    children,
  }: {
    children: ReactNode;
  }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return Wrapper;
}

beforeEach(() => {
  vi.clearAllMocks();
  getActiveGenerationRunMock.mockResolvedValue(null);
});

describe("useGenerationRun", () => {
  it("starts a run and exposes its queued state", async () => {
    const queuedRun = generationRun("queued");
    startGenerationRunMock.mockResolvedValue(queuedRun);
    getGenerationRunMock.mockResolvedValue(queuedRun);

    const { result } = renderHook(
      () =>
        useGenerationRun({
          experimentId: 3,
          onCompleted: vi.fn(),
          onFailed: vi.fn(),
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(
        getActiveGenerationRunMock,
      ).toHaveBeenCalledWith(3);
    });

    await act(async () => {
      await result.current.start();
    });

    expect(
      startGenerationRunMock,
    ).toHaveBeenCalledOnce();
    expect(
      startGenerationRunMock,
    ).toHaveBeenCalledWith(3);
    expect(result.current.run).toEqual(queuedRun);
    expect(result.current.isRunning).toBe(true);
  });

  it(
    "polls an active run, handles completion once, and stops polling",
    async () => {
      const onCompleted = vi.fn();
      const queuedRun = generationRun("queued");
      const runningRun = generationRun("running");
      const completedRun = generationRun("completed");

      startGenerationRunMock.mockResolvedValue(
        queuedRun,
      );
      getGenerationRunMock
        .mockResolvedValueOnce(runningRun)
        .mockResolvedValue(completedRun);

      const { result } = renderHook(
        () =>
          useGenerationRun({
            experimentId: 3,
            onCompleted,
            onFailed: vi.fn(),
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(
          getActiveGenerationRunMock,
        ).toHaveBeenCalledOnce();
      });

      await act(async () => {
        await result.current.start();
      });

      await waitFor(() => {
        expect(getGenerationRunMock).toHaveBeenCalled();
      });

      await waitFor(
        () => {
          expect(onCompleted).toHaveBeenCalledWith(41);
        },
        { timeout: 2_500 },
      );

      const requestCount =
        getGenerationRunMock.mock.calls.length;

      await new Promise((resolve) => {
        window.setTimeout(resolve, 1_200);
      });

      expect(
        getGenerationRunMock,
      ).toHaveBeenCalledTimes(requestCount);
      expect(onCompleted).toHaveBeenCalledOnce();
    },
  );

  it("reports a failed recovered run", async () => {
    const onFailed = vi.fn();
    const runningRun = generationRun("running");
    const failedRun = generationRun("failed", {
      error_message: "Provider quota exhausted.",
    });

    getActiveGenerationRunMock.mockResolvedValue(
      runningRun,
    );
    getGenerationRunMock.mockResolvedValue(failedRun);

    renderHook(
      () =>
        useGenerationRun({
          experimentId: 3,
          onCompleted: vi.fn(),
          onFailed,
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(onFailed).toHaveBeenCalledWith(
        "Provider quota exhausted.",
      );
    });
  });

  it(
    "resumes an active run after refresh and reports its game",
    async () => {
      const onCompleted = vi.fn();
      const runningRun = generationRun("running");
      const completedRun = generationRun("completed");

      getActiveGenerationRunMock.mockResolvedValue(
        runningRun,
      );
      getGenerationRunMock.mockResolvedValue(
        completedRun,
      );

      renderHook(
        () =>
          useGenerationRun({
            experimentId: 3,
            onCompleted,
            onFailed: vi.fn(),
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(getGenerationRunMock).toHaveBeenCalledWith(
          runningRun.id,
        );
      });

      await waitFor(() => {
        expect(onCompleted).toHaveBeenCalledWith(41);
      });

      expect(
        startGenerationRunMock,
      ).not.toHaveBeenCalled();
    },
  );

  it(
    "does not start a second run while one is active",
    async () => {
      const runningRun = generationRun("running");
      getActiveGenerationRunMock.mockResolvedValue(
        runningRun,
      );
      getGenerationRunMock.mockResolvedValue(
        runningRun,
      );

      const { result } = renderHook(
        () =>
          useGenerationRun({
            experimentId: 3,
            onCompleted: vi.fn(),
            onFailed: vi.fn(),
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isRunning).toBe(true);
      });

      await expect(
        result.current.start(),
      ).rejects.toThrow(
        "A generation is already active "
        + "for this experiment.",
      );

      expect(
        startGenerationRunMock,
      ).not.toHaveBeenCalled();
    },
  );
});
