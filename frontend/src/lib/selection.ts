import type { ExperimentSummary } from "../api/types";


/** The API returns experiments newest-first, so the first item is the default. */
export function defaultExperimentId(
  experiments: ExperimentSummary[],
): number | null {
  return experiments[0]?.id ?? null;
}
