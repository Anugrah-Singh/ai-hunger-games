import type {
  ExperimentAnalysis,
  ExperimentDetail,
  ExperimentSummary,
  GenerationDetail,
  GenerationSummary,
} from "./types";


export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}


async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);

  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    const detail = getErrorDetail(payload);
    throw new ApiError(
      response.status,
      detail ?? `Request failed with status ${response.status}.`,
    );
  }

  return payload as T;
}


function getErrorDetail(payload: unknown): string | null {
  if (
    typeof payload === "object"
    && payload !== null
    && "detail" in payload
    && typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return null;
}


export function getExperiments(): Promise<ExperimentSummary[]> {
  return request<ExperimentSummary[]>("/experiments");
}


export function getExperiment(
  experimentId: number,
): Promise<ExperimentDetail> {
  return request<ExperimentDetail>(`/experiments/${experimentId}`);
}


export function getGenerations(
  experimentId: number,
): Promise<GenerationSummary[]> {
  return request<GenerationSummary[]>(
    `/experiments/${experimentId}/generations`,
  );
}


export function getExperimentAnalysis(
  experimentId: number,
): Promise<ExperimentAnalysis> {
  return request<ExperimentAnalysis>(
    `/experiments/${experimentId}/analysis`,
  );
}


export function getGeneration(
  gameId: number,
): Promise<GenerationDetail> {
  return request<GenerationDetail>(`/generations/${gameId}`);
}


export function createExperiment(
  name: string,
): Promise<ExperimentSummary> {
  return request<ExperimentSummary>("/experiments", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}


export function runGeneration(
  experimentId: number,
): Promise<GenerationSummary[]> {
  return request<GenerationSummary[]>(
    `/experiments/${experimentId}/generations`,
    {
      method: "POST",
      body: JSON.stringify({ generation_count: 1 }),
    },
  );
}
