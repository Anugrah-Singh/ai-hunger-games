import type { ExperimentAnalysis, GenerationSummary } from "../api/types";
import { formatNumber, formatPercent } from "../lib/format";
import { MetricCard, Placeholder } from "./common";


interface LineageTabProps {
  analysis: ExperimentAnalysis;
  agentName: (agentId: string) => string;
  generations: GenerationSummary[];
}


export function LineageTab({
  analysis,
  agentName,
  generations,
}: LineageTabProps) {
  const diversity = analysis.personality_diversity;
  const personalityPerformance = [...analysis.personality_performance].sort(
    (first, second) => second.total_points - first.total_points,
  );

  return (
    <section className="view-panel">
      <section className="section-block">
        <SectionHeading eyebrow="Personality succession" title="Replacement lineage" />
        <div className="lineage-list">
          {generations.length === 0 ? (
            <Placeholder>No replacements have been generated.</Placeholder>
          ) : (
            generations.map((generation) => (
              <div className="lineage-row" key={generation.game_id}>
                <strong className="ledger-generation">
                  Gen {generation.generation_number}
                </strong>
                <span>
                  <strong>{agentName(generation.eliminated_agent_id)}</strong>
                  eliminated
                </span>
                <span className="lineage-arrow">to</span>
                <span>
                  <strong>{generation.replacement_agent.agent_name}</strong>
                  {generation.replacement_agent.personality.name}
                </span>
              </div>
            ))
          )}
        </div>
      </section>

      <div className="section-grid">
        <section className="section-block">
          <SectionHeading eyebrow="Generated personalities" title="Diversity" />
          <div className="metric-grid compact-metrics">
            <MetricCard
              detail="Replacement records"
              label="Generated"
              value={diversity.generated_personality_count}
            />
            <MetricCard
              detail={formatPercent(diversity.distinct_name_rate)}
              label="Distinct names"
              value={diversity.distinct_name_count}
            />
            <MetricCard
              detail={formatPercent(diversity.distinct_instruction_rate)}
              label="Distinct instructions"
              value={diversity.distinct_instruction_count}
            />
          </div>
        </section>
        <section className="section-block">
          <SectionHeading
            eyebrow="Replacement observations"
            title="Outcomes"
          />
          <div className="indicator-list">
            {analysis.replacement_outcomes.length === 0 ? (
              <Placeholder>No replacement outcomes yet.</Placeholder>
            ) : (
              analysis.replacement_outcomes.map((outcome) => (
                <div
                  className="indicator-row"
                  key={`${outcome.replacement_agent_id}:${outcome.created_in_generation}`}
                >
                  <span>
                    <strong>{outcome.personality.name}</strong>
                    created in generation {formatNumber(outcome.created_in_generation, 0)}
                  </span>
                  <span>{outcome.status}</span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="section-block">
        <SectionHeading
          eyebrow="Across recorded generations"
          title="Personality performance"
        />
        <div className="indicator-list">
          {personalityPerformance.length === 0 ? (
            <Placeholder>No personality performance has been recorded.</Placeholder>
          ) : (
            personalityPerformance.map((performance) => (
              <div
                className="indicator-row indicator-row-stacked"
                key={performance.personality.name}
              >
                <span>
                  <strong>{performance.personality.name}</strong>
                  {formatNumber(performance.generation_participations, 0)}
                  {" "}participating generations, {formatNumber(
                    performance.generation_survivals,
                    0,
                  )}{" "}
                  survivals
                </span>
                <p>
                  {formatNumber(performance.total_points, 0)} points;{" "}
                  {formatNumber(performance.average_points_per_round)} average per
                  round; replacement success{" "}
                  {formatPercent(performance.replacement_success_rate)}
                </p>
              </div>
            ))
          )}
        </div>
      </section>
    </section>
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
