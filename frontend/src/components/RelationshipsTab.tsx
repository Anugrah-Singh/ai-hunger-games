import { Tooltip } from "radix-ui";
import type { CSSProperties } from "react";

import type { ExperimentAnalysis, VoteRelationship } from "../api/types";
import { formatNumber, formatPercent } from "../lib/format";
import { Placeholder } from "./common";


interface RelationshipsTabProps {
  analysis: ExperimentAnalysis;
  agentName: (agentId: string) => string;
}


export function RelationshipsTab({
  analysis,
  agentName,
}: RelationshipsTabProps) {
  const relationships = new Map<string, VoteRelationship>(
    analysis.vote_relationships.map((relationship) => [
      relationshipKey(
        relationship.voter_agent_id,
        relationship.target_agent_id,
      ),
      relationship,
    ]),
  );
  const agents = analysis.agent_performance;

  return (
    <section className="view-panel">
      <section className="section-block">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Observed voter-to-target rates</p>
            <h2>Voting relationship matrix</h2>
          </div>
        </div>
        <div className="heatmap-scroll">
          {agents.length === 0 ? (
            <Placeholder>No voting history.</Placeholder>
          ) : (
            <div
              className="heatmap"
              style={{ "--agent-count": agents.length } as CSSProperties}
            >
              <span className="heatmap-label" />
              {agents.map((target) => (
                <span
                  className="heatmap-label is-column"
                  key={`column:${target.agent_id}`}
                >
                  {target.agent_name}
                </span>
              ))}
              {agents.flatMap((voter) => [
                <span className="heatmap-label" key={`row:${voter.agent_id}`}>
                  {voter.agent_name}
                </span>,
                ...agents.map((target) => (
                  <RelationshipCell
                    key={`${voter.agent_id}:${target.agent_id}`}
                    relationship={relationships.get(
                      relationshipKey(voter.agent_id, target.agent_id),
                    )}
                    isSelf={voter.agent_id === target.agent_id}
                    targetName={target.agent_name}
                    voterName={voter.agent_name}
                  />
                )),
              ])}
            </div>
          )}
        </div>
      </section>

      <div className="section-grid relationship-grid">
        <section className="section-block">
          <SectionHeading
            eyebrow="Reciprocal patterns"
            title="Reciprocity indicators"
          />
          <div className="indicator-list">
            {analysis.reciprocal_vote_indicators.length === 0 ? (
              <Placeholder>
                No reciprocal relationship meets the reporting threshold.
              </Placeholder>
            ) : (
              analysis.reciprocal_vote_indicators.map((indicator) => (
                <div
                  className="indicator-row"
                  key={`${indicator.first_agent_id}:${indicator.second_agent_id}`}
                >
                  <span>
                    <strong>
                      {agentName(indicator.first_agent_id)} and{" "}
                      {agentName(indicator.second_agent_id)}
                    </strong>
                    {formatNumber(indicator.reciprocal_rounds, 0)} reciprocal
                    rounds across {formatNumber(indicator.distinct_generations, 0)}
                    {" "}generations
                  </span>
                  <span>
                    {indicator.meets_history_threshold
                      ? "Threshold met"
                      : "Insufficient history"}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
        <section className="section-block">
          <SectionHeading
            eyebrow="Interpretation boundary"
            title="Evidence notes"
          />
          <ul className="caution-list">
            {analysis.cautions.length === 0 ? (
              <li>No interpretation cautions were generated.</li>
            ) : (
              analysis.cautions.map((caution) => <li key={caution}>{caution}</li>)
            )}
          </ul>
        </section>
      </div>

      <div className="section-grid relationship-grid">
        <section className="section-block">
          <SectionHeading
            eyebrow="Above-baseline clusters"
            title="Possible voting bloc indicators"
          />
          <div className="indicator-list">
            {analysis.possible_voting_bloc_indicators.length === 0 ? (
              <Placeholder>
                No cluster indicator meets the reporting threshold.
              </Placeholder>
            ) : (
              analysis.possible_voting_bloc_indicators.map((indicator) => {
                const agentNames = indicator.agent_ids.map(agentName).join(", ");
                const pairs = indicator.supporting_agent_pairs
                  .map(([firstAgentId, secondAgentId]) =>
                    `${agentName(firstAgentId)} / ${agentName(secondAgentId)}`,
                  )
                  .join("; ");
                return (
                  <div
                    className="indicator-row indicator-row-stacked"
                    key={indicator.agent_ids.join(":")}
                  >
                    <span>
                      <strong>{agentNames}</strong>
                      {pairs}
                    </span>
                    <p>{indicator.caveat}</p>
                  </div>
                );
              })
            )}
          </div>
        </section>
        <section className="section-block">
          <SectionHeading
            eyebrow="After a replacement enters"
            title="Entry-adjacent changes"
          />
          <div className="indicator-list">
            {analysis.entry_adjacent_changes.length === 0 ? (
              <Placeholder>
                No entry-adjacent relationship change is available.
              </Placeholder>
            ) : (
              analysis.entry_adjacent_changes.map((change) => (
                <div
                  className="indicator-row indicator-row-stacked"
                  key={`${change.entrant_agent_id}:${change.voter_agent_id}:${change.target_agent_id}:${change.entry_generation}`}
                >
                  <span>
                    <strong>
                      {agentName(change.voter_agent_id)} to{" "}
                      {agentName(change.target_agent_id)}
                    </strong>
                    Generation {formatNumber(change.entry_generation, 0)}, after{" "}
                    {agentName(change.entrant_agent_id)} entered
                  </span>
                  <p>
                    {formatPercent(change.previous_vote_rate)} to{" "}
                    {formatPercent(change.entry_vote_rate)}; change{" "}
                    {formatPercent(change.rate_change)}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </section>
  );
}


function RelationshipCell({
  isSelf,
  relationship,
  targetName,
  voterName,
}: {
  isSelf: boolean;
  relationship: VoteRelationship | undefined;
  targetName: string;
  voterName: string;
}) {
  if (isSelf) {
    return <span className="heatmap-cell is-self">-</span>;
  }

  if (relationship === undefined) {
    return <span className="heatmap-cell">-</span>;
  }

  const observedRate = relationship.vote_rate ?? 0;
  const randomBaseline = relationship.random_baseline_rate ?? 0;
  const difference = observedRate - randomBaseline;
  const tone =
    difference > 0.08
      ? "is-above"
      : difference < -0.08
        ? "is-below"
        : "is-neutral";
  const description = `${voterName} to ${targetName}: ${formatPercent(
    observedRate,
  )} observed; ${formatPercent(randomBaseline)} random baseline.`;

  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <span
          aria-label={description}
          className={`heatmap-cell ${tone}`}
          tabIndex={0}
        >
          {formatPercent(observedRate)}
        </span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tooltip-content" sideOffset={6}>
          {description}
          <Tooltip.Arrow className="tooltip-arrow" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}


function SectionHeading({
  eyebrow,
  title,
}: {
  eyebrow: string;
  title: string;
}) {
  return (
    <div className="section-title-row">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
    </div>
  );
}


function relationshipKey(voterAgentId: string, targetAgentId: string): string {
  return `${voterAgentId}:${targetAgentId}`;
}
