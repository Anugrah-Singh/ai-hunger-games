import { useEffect, useRef, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getActiveGenerationRun,
  getGenerationRun,
  startGenerationRun,
} from "../api/client";
import type { GenerationRun } from "../api/types";

const activeStatuses = new Set<GenerationRun["status"]>([
  "queued",
  "running",
]);

interface UseGenerationRunOptions {
  experimentId: number | null;
  onCompleted: (gameId: number) => void;
  onFailed: (message: string) => void;
}

export function useGenerationRun({
  experimentId,
  onCompleted,
  onFailed,
}: UseGenerationRunOptions) {
  const queryClient = useQueryClient();

  const [runId, setRunId] =
    useState<number | null>(null);

  const handledRunIds = useRef(
    new Set<number>(),
  );

  const onCompletedRef = useRef(onCompleted);
  const onFailedRef = useRef(onFailed);

  useEffect(() => {
    onCompletedRef.current = onCompleted;
  }, [onCompleted]);

  useEffect(() => {
    onFailedRef.current = onFailed;
  }, [onFailed]);

  useEffect(() => {
    setRunId(null);
    handledRunIds.current.clear();
  }, [experimentId]);

  const activeRunQuery = useQuery({
    enabled: experimentId !== null,
    queryFn: () =>
      getActiveGenerationRun(experimentId!),
    queryKey: [
      "active-generation-run",
      experimentId,
    ],
    refetchInterval: 2_000,
  });

  useEffect(() => {
    const activeRun = activeRunQuery.data;

    if (
      activeRun !== null
      && activeRun !== undefined
    ) {
      setRunId(activeRun.id);
    }
  }, [activeRunQuery.data]);

  const runQuery = useQuery({
    enabled: runId !== null,
    queryFn: () => getGenerationRun(runId!),
    queryKey: ["generation-run", runId],
    refetchInterval: (query) => {
      const run = query.state.data;

      return (
        run !== undefined
        && activeStatuses.has(run.status)
      )
        ? 1_000
        : false;
    },
  });

  useEffect(() => {
    const run = runQuery.data;

    if (
      run === undefined
      || activeStatuses.has(run.status)
      || handledRunIds.current.has(run.id)
    ) {
      return;
    }

    handledRunIds.current.add(run.id);

    async function finishRun(
      terminalRun: GenerationRun,
    ) {
      if (experimentId !== null) {
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: ["experiments"],
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "experiment",
              experimentId,
            ],
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "generations",
              experimentId,
            ],
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "analysis",
              experimentId,
            ],
          }),
          queryClient.invalidateQueries({
            queryKey: [
              "active-generation-run",
              experimentId,
            ],
          }),
        ]);
      }

      if (
        terminalRun.status === "completed"
        && terminalRun.game_id !== null
      ) {
        await queryClient.invalidateQueries({
          queryKey: [
            "generation",
            terminalRun.game_id,
          ],
        });

        onCompletedRef.current(
          terminalRun.game_id,
        );
      } else {
        onFailedRef.current(
          terminalRun.error_message
          ?? (
            "Generation did not complete; "
            + "no generation was saved."
          ),
        );
      }

      setRunId(null);
    }

    void finishRun(run);
  }, [
    experimentId,
    queryClient,
    runQuery.data,
  ]);

  const startMutation = useMutation({
    mutationFn: async () => {
      if (experimentId === null) {
        throw new Error(
          "Select an experiment before "
          + "starting a generation.",
        );
      }

      return startGenerationRun(experimentId);
    },

    onSuccess: (run) => {
      handledRunIds.current.delete(run.id);
      setRunId(run.id);

      queryClient.setQueryData(
        ["generation-run", run.id],
        run,
      );

      queryClient.setQueryData(
        [
          "active-generation-run",
          run.experiment_id,
        ],
        run,
      );
    },

    retry: false,
  });

  const run =
    runQuery.data
    ?? activeRunQuery.data
    ?? null;

  const isRunning =
    startMutation.isPending
    || (
      run !== null
      && activeStatuses.has(run.status)
    );

  return {
    isRunning,
    run,
    start: startMutation.mutateAsync,
  };
}