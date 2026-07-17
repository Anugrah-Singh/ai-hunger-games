import { describe, expect, it } from "vitest";

import type { ExperimentSummary } from "../api/types";
import { defaultExperimentId } from "./selection";


const newestFirstExperiments: ExperimentSummary[] = [
  {
    id: 9,
    name: "Newest",
    created_at: "2026-07-18T00:00:00Z",
    provider_name: "Simulated providers",
  },
  {
    id: 4,
    name: "Older",
    created_at: "2026-07-17T00:00:00Z",
    provider_name: null,
  },
];


describe("defaultExperimentId", () => {
  it("uses the first item from the newest-first API response", () => {
    expect(defaultExperimentId(newestFirstExperiments)).toBe(9);
  });

  it("returns null when no experiments exist", () => {
    expect(defaultExperimentId([])).toBeNull();
  });
});
