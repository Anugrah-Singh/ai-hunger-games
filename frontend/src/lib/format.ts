import type { GenerationSeeds } from "../api/types";


export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


export function formatNumber(
  value: number | null | undefined,
  maximumFractionDigits = 1,
): string {
  if (value === null || value === undefined) {
    return "-";
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits,
  }).format(value);
}


export function formatPercent(
  value: number | null | undefined,
): string {
  if (value === null || value === undefined) {
    return "-";
  }

  return `${formatNumber(value * 100)}%`;
}


export function candidateLabel(candidateId: string): string {
  const suffix = /(\d+)$/.exec(candidateId)?.[1];
  return suffix === undefined
    ? `Candidate ${candidateId}`
    : `Candidate ${Number(suffix)}`;
}


export function formatSeeds(seeds: GenerationSeeds): string {
  const entries: [string, number | null][] = [
    ["candidate", seeds.candidate_order_seed],
    ["vote", seeds.voting_seed],
    ["elimination", seeds.elimination_seed],
    ["replacement", seeds.replacement_seed],
  ];
  const rendered = entries
    .filter(([, value]) => value !== null)
    .map(([label, value]) => `${label}: ${value}`);

  return rendered.join(" | ") || "Seeds unavailable";
}


export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "An unexpected error occurred.";
}
