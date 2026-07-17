import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  Agent,
  AgentPerformance,
  ExperimentAnalysis,
  ExperimentDetail,
  GenerationSummary,
} from "../api/types";
import { formatNumber, formatSeeds } from "../lib/format";
import { MetricCard, Placeholder } from "./common";


interface OverviewTabProps {
  analysis: ExperimentAnalysis;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  agentName: (agentId: string) => string;
}


const chartColors = [
  "#087d76",
  "#c65248",
  "#39699d",
  "#a96f13",
  "#5d4c9b",
  "#287255",
  "#a14678",
  "#58694f",
];


export function OverviewTab({
  analysis,
  experiment,
  generations,
  agentName,
}: OverviewTabProps) {
  const totalPoints = analysis.agent_performance.reduce(
    (total, agent) => total + agent.total_points,
    0,
  );
  const latestGeneration = generations.at(-1);

  return (
    <section className="view-panel">
      <div className="metric-grid">
        <MetricCard
          detail={
            latestGeneration
              ? `Latest: ${latestGeneration.generation_number}`
              : "No completed games"
          }
          label="Generations"
          value={experiment.generation_count}
        />
        <MetricCard
          detail="Final population"
          label="Active agents"
          value={experiment.current_population.length}
        />
        <MetricCard
          detail="Across persisted rounds"
          label="Recorded points"
          value={totalPoints}
        />
        <MetricCard
          detail="Interpret before inference"
          label="Evidence notes"
          value={analysis.cautions.length}
        />
      </div>

      <div className="section-grid">
        <PopulationGrid
          canRun={experiment.can_run}
          population={experiment.current_population}
          runBlockReason={experiment.run_block_reason}
        />
        <Leaderboard agents={analysis.agent_performance} />
      </div>

      <ScoreTrendChart agents={analysis.agent_performance} />

      <section className="section-block">
        <div className="section-title-row">
          <div>
            <p className="eyebrow">Generation ledger</p>
            <h2>Eliminations and replacements</h2>
          </div>
        </div>
        <div className="generation-ledger">
          {generations.length === 0 ? (
            <Placeholder>No completed generation.</Placeholder>
          ) : (
            generations.map((generation) => (
              <div className="ledger-row" key={generation.game_id}>
                <strong className="ledger-generation">
                  Gen {generation.generation_number}
                </strong>
                <span>
                  <strong>{agentName(generation.eliminated_agent_id)}</strong>
                  eliminated
                </span>
                <span>
                  <strong>{generation.replacement_agent.agent_name}</strong>
                  {generation.replacement_agent.personality.name} entered
                </span>
                <span className="ledger-seeds">{formatSeeds(generation.seeds)}</span>
              </div>
            ))
          )}
        </div>
      </section>
    </section>
  );
}


function PopulationGrid({
  canRun,
  population,
  runBlockReason,
}: {
  canRun: boolean;
  population: Agent[];
  runBlockReason: string | null;
}) {
  const emptyMessage = canRun
    ? "Run a generation to establish a population."
    : runBlockReason ?? "No population snapshot is available.";

  return (
    <section className="section-block">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Active population</p>
          <h2>Current personalities</h2>
        </div>
      </div>
      <div className="population-grid">
        {population.length === 0 ? (
          <Placeholder>{emptyMessage}</Placeholder>
        ) : (
          population.map((agent) => (
            <article className="agent-tile" key={agent.agent_id}>
              <h3>{agent.agent_name}</h3>
              <span className="agent-id">{agent.personality.name}</span>
              <p>{agent.personality.description}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}


function Leaderboard({ agents }: { agents: AgentPerformance[] }) {
  const rankedAgents = [...agents].sort(
    (first, second) => second.total_points - first.total_points,
  );
  const maximumSlope = Math.max(
    0.01,
    ...rankedAgents.map((agent) => Math.abs(agent.score_slope_per_generation ?? 0)),
  );

  return (
    <section className="section-block">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Accumulated outcomes</p>
          <h2>Leaderboard</h2>
        </div>
      </div>
      <div className="table-scroll">
        <table className="data-table leaderboard-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th className="numeric">Points</th>
              <th className="numeric">Avg / round</th>
              <th className="numeric">Survived</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {rankedAgents.length === 0 ? (
              <tr>
                <td className="metadata" colSpan={5}>
                  No completed generation.
                </td>
              </tr>
            ) : (
              rankedAgents.map((agent) => {
                const slope = agent.score_slope_per_generation ?? 0;
                const width = Math.round((Math.abs(slope) / maximumSlope) * 100);
                return (
                  <tr key={agent.agent_id}>
                    <td>
                      <strong>{agent.agent_name}</strong>
                      <br />
                      <span className="metadata">{agent.personality.name}</span>
                    </td>
                    <td className="numeric">{formatNumber(agent.total_points, 0)}</td>
                    <td className="numeric">
                      {formatNumber(agent.average_points_per_round)}
                    </td>
                    <td className="numeric">
                      {formatNumber(agent.survival_count, 0)}
                    </td>
                    <td>
                      <span
                        className={`trend-bar${slope < 0 ? " is-down" : ""}`}
                        title={`Score trend ${formatNumber(slope)}`}
                      >
                        <span style={{ width: `${width}%` }} />
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}


function ScoreTrendChart({ agents }: { agents: AgentPerformance[] }) {
  const generationNumbers = [...new Set(
    agents.flatMap((agent) =>
      agent.generation_scores.map((score) => score.generation_number),
    ),
  )].sort((first, second) => first - second);

  const data = generationNumbers.map((generationNumber) => {
    const point: Record<string, string | number> = {
      generation: `Gen ${generationNumber}`,
    };

    for (const agent of agents) {
      point[agent.agent_id] =
        agent.generation_scores.find(
          (score) => score.generation_number === generationNumber,
        )?.total_score ?? 0;
    }

    return point;
  });

  return (
    <section className="section-block">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Persisted score history</p>
          <h2>Generation score trends</h2>
        </div>
      </div>
      {data.length === 0 ? (
        <Placeholder>Complete a generation to chart score history.</Placeholder>
      ) : (
        <div className="chart-shell">
          <ResponsiveContainer height="100%" width="100%">
            <LineChart data={data} margin={{ top: 8, right: 20, left: -16, bottom: 4 }}>
              <CartesianGrid stroke="#cbd3cd" strokeDasharray="3 3" />
              <XAxis dataKey="generation" tick={{ fill: "#68736c", fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fill: "#68736c", fontSize: 11 }} />
              <RechartsTooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {agents.map((agent, index) => (
                <Line
                  activeDot={{ r: 4 }}
                  dataKey={agent.agent_id}
                  dot={{ r: 3 }}
                  key={agent.agent_id}
                  name={agent.agent_name}
                  stroke={chartColors[index % chartColors.length]}
                  strokeWidth={2}
                  type="monotone"
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
