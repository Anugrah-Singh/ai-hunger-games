import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";

import { getGeneration } from "../api/client";
import type { GenerationSummary, Round } from "../api/types";
import {
  candidateLabel,
  errorMessage,
  formatNumber,
} from "../lib/format";
import { Placeholder } from "./common";


interface RoundsTabProps {
  agentName: (agentId: string) => string;
  generations: GenerationSummary[];
  onSelectedGenerationChange: (gameId: number | null) => void;
  selectedGenerationId: number | null;
}


export function RoundsTab({
  agentName,
  generations,
  onSelectedGenerationChange,
  selectedGenerationId,
}: RoundsTabProps) {
  const generationQuery = useQuery({
    enabled: selectedGenerationId !== null,
    queryFn: () => getGeneration(selectedGenerationId!),
    queryKey: ["generation", selectedGenerationId],
  });
  const [selectedRoundNumber, setSelectedRoundNumber] = useState<number | null>(
    null,
  );
  const generation = generationQuery.data;

  useEffect(() => {
    if (generation === undefined) {
      setSelectedRoundNumber(null);
      return;
    }

    setSelectedRoundNumber((currentRoundNumber) => {
      const roundStillExists = generation.rounds.some(
        (round) => round.round_number === currentRoundNumber,
      );
      return roundStillExists
        ? currentRoundNumber
        : generation.rounds[0]?.round_number ?? null;
    });
  }, [generation]);

  const selectedRound = generation?.rounds.find(
    (round) => round.round_number === selectedRoundNumber,
  );

  return (
    <section className="view-panel">
      <section className="section-block">
        <div className="section-title-row round-heading">
          <div>
            <p className="eyebrow">Anonymized voting record</p>
            <h2>Round explorer</h2>
          </div>
          <div className="round-selectors">
            <label htmlFor="generation-select">Generation</label>
            <select
              disabled={generations.length === 0}
              id="generation-select"
              onChange={(event) =>
                onSelectedGenerationChange(Number(event.target.value))
              }
              value={selectedGenerationId ?? ""}
            >
              {generations.length === 0 ? (
                <option value="">No saved generations</option>
              ) : (
                generations.map((generationSummary) => (
                  <option
                    key={generationSummary.game_id}
                    value={generationSummary.game_id}
                  >
                    Generation {generationSummary.generation_number}
                  </option>
                ))
              )}
            </select>
            <label htmlFor="round-select">Round</label>
            <select
              disabled={generation === undefined || generationQuery.isFetching}
              id="round-select"
              onChange={(event) => setSelectedRoundNumber(Number(event.target.value))}
              value={selectedRoundNumber ?? ""}
            >
              {generation?.rounds.map((round) => (
                <option key={round.round_id} value={round.round_number}>
                  Round {round.round_number}
                </option>
              ))}
            </select>
          </div>
        </div>

        {generationQuery.isPending ? (
          <LoadingRound />
        ) : generationQuery.isError ? (
          <Placeholder>{errorMessage(generationQuery.error)}</Placeholder>
        ) : selectedRound === undefined ? (
          <Placeholder>No completed rounds.</Placeholder>
        ) : (
          <RoundDetail agentName={agentName} round={selectedRound} />
        )}
      </section>
    </section>
  );
}


function LoadingRound() {
  return (
    <div className="round-loading" aria-live="polite">
      <LoaderCircle aria-hidden="true" className="spin" size={18} />
      Loading anonymized round data
    </div>
  );
}


function RoundDetail({
  agentName,
  round,
}: {
  agentName: (agentId: string) => string;
  round: Round;
}) {
  const attempts = round.answers.reduce(
    (total, answer) => total + answer.attempt_count,
    0,
  );
  const retries = Math.max(0, attempts - round.answers.length);

  return (
    <>
      <p className="question">{round.question}</p>
      <div className="execution-summary">
        <ExecutionMetric label="Successful answers" value={round.answers.length} />
        <ExecutionMetric label="Answer attempts" value={attempts} />
        <ExecutionMetric label="Retries" value={retries} />
        <ExecutionMetric label="Exhausted requests" value={round.failures.length} />
      </div>
      {round.failures.length > 0 && (
        <div className="failure-list">
          {round.failures.map((failure) => (
            <div className="failure-row" key={`${failure.agent_id}:${failure.error_type}`}>
              <span>
                <strong>{agentName(failure.agent_id)}</strong>
                {failure.error_type} after {formatNumber(failure.attempt_count, 0)}
                {" "}attempts
              </span>
              <span>{formatRetryAfter(failure.retry_after_seconds)}</span>
              <p>{failure.message}</p>
            </div>
          ))}
        </div>
      )}
      <div className="round-grid">
        <div>
          <h3>Candidate answers</h3>
          <div className="candidate-list">
            {round.answers.map((answer) => (
              <article className="candidate-answer" key={answer.candidate_id}>
                <strong>{candidateLabel(answer.candidate_id)}</strong>
                <p>{answer.content}</p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <h3>Votes</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Voter</th>
                  <th>Selected candidate</th>
                </tr>
              </thead>
              <tbody>
                {round.votes.map((vote) => (
                  <tr key={`${vote.voter_agent_id}:${vote.selected_candidate_id}`}>
                    <td>{agentName(vote.voter_agent_id)}</td>
                    <td>{candidateLabel(vote.selected_candidate_id)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3 className="round-score-title">Candidate scores</h3>
          <div className="score-list">
            {[...round.scores]
              .sort((first, second) => second.score - first.score)
              .map((score) => (
                <div className="score-row" key={score.candidate_id}>
                  <span>{candidateLabel(score.candidate_id)}</span>
                  <strong>{formatNumber(score.score, 0)}</strong>
                </div>
              ))}
          </div>
        </div>
      </div>
    </>
  );
}


function ExecutionMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="execution-metric">
      <span>{label}</span>
      <strong>{formatNumber(value, 0)}</strong>
    </div>
  );
}


function formatRetryAfter(retryAfterSeconds: number | null): string {
  return retryAfterSeconds === null
    ? "No provider retry delay"
    : `Provider retry delay ${formatNumber(retryAfterSeconds)} s`;
}
