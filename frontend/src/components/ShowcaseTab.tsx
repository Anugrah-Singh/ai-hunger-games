import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BrainCircuit,
  Database,
  Gauge,
  GitBranch,
  Layers3,
  MessageSquare,
  RefreshCcw,
  ServerCog,
  ShieldCheck,
  Sparkles,
  Users,
  Vote,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { domAnimation, LazyMotion, MotionConfig } from "motion/react";
import * as m from "motion/react-m";

import type {
  ExperimentAnalysis,
  ExperimentDetail,
  GenerationSummary,
} from "../api/types";
import { SectionHeading } from "./common";

export type ShowcaseDestination =
  | "overview"
  | "rounds"
  | "relationships"
  | "lineage";

interface ShowcaseTabProps {
  agentName: (agentId: string) => string;
  analysis: ExperimentAnalysis;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  onTabChange: (view: ShowcaseDestination) => void;
}

interface ExperimentStage {
  description: string;
  icon: LucideIcon;
  title: string;
}

const proofLabels = [
  "Python 3.14",
  "FastAPI",
  "React 19 + TypeScript",
  "SQLAlchemy + Alembic",
  "Async orchestration",
  "33+ automated tests",
];

const stages: ExperimentStage[] = [
  {
    description: "Eight reasoning profiles enter a reproducible experiment definition.",
    icon: Users,
    title: "Population",
  },
  {
    description: "Providers generate answers concurrently with explicit timeout and retry policies.",
    icon: MessageSquare,
    title: "Generation",
  },
  {
    description: "Candidate IDs replace author identities before any evaluator sees an answer.",
    icon: ShieldCheck,
    title: "Anonymization",
  },
  {
    description: "Eligible agents evaluate the anonymous set without being allowed to self-vote.",
    icon: Vote,
    title: "Evaluation",
  },
  {
    description: "Rounds, scores, retries, and provider failures commit as one durable snapshot.",
    icon: Database,
    title: "Persistence",
  },
  {
    description: "The lowest scorer exits and a generated personality enters the next generation.",
    icon: RefreshCcw,
    title: "Evolution",
  },
];

const decisions = [
  {
    detail:
      "Vote providers receive candidate IDs and answer text, never an answer-author identifier. The browser API preserves the same invariant.",
    icon: ShieldCheck,
    title: "Anonymous by architecture",
  },
  {
    detail:
      "The engine owns timeouts, exponential backoff, and provider retry-after delays so reliability remains visible and testable.",
    icon: Gauge,
    title: "One retry owner",
  },
  {
    detail:
      "Every generation is an atomic historical record with agents, rounds, votes, scores, random seeds, and replacement lineage.",
    icon: Database,
    title: "Reproducible history",
  },
  {
    detail:
      "Relationship metrics compare observed votes with eligibility-aware random baselines and avoid claiming unsupported coordination.",
    icon: GitBranch,
    title: "Evidence before claims",
  },
];

const architectureNodes = [
  { icon: Layers3, label: "React dashboard", note: "Typed, query-driven UI" },
  { icon: ServerCog, label: "FastAPI", note: "Pydantic API boundary" },
  { icon: Workflow, label: "Generation runner", note: "Durable orchestration" },
  { icon: BrainCircuit, label: "Engine + providers", note: "Rules, retries, anonymity" },
  { icon: Database, label: "SQLAlchemy + Alembic", note: "Atomic experiment history" },
  { icon: BarChart3, label: "Analysis", note: "Deterministic metrics" },
];

export function ShowcaseTab({
  agentName,
  analysis,
  experiment,
  generations,
  onTabChange,
}: ShowcaseTabProps) {
  const latestGeneration = generations.at(-1);
  const persistedRounds = generations.reduce(
    (total, generation) => total + generation.round_count,
    0,
  );
  const caution = analysis.cautions.at(0)
    ?? "A completed generation demonstrates the workflow, not a durable behavioral pattern.";

  return (
    <LazyMotion features={domAnimation} strict>
      <MotionConfig reducedMotion="user">
        <section className="recruiter-overview" aria-labelledby="showcase-title">
          <m.section
            className="showcase-hero"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <div className="hero-grid" aria-hidden="true" />
            <div className="hero-orb hero-orb-one" aria-hidden="true" />
            <div className="hero-orb hero-orb-two" aria-hidden="true" />
            <div className="showcase-hero-content">
              <span className="hero-badge">
                <Sparkles aria-hidden="true" size={14} />
                Portfolio-grade AI evaluation platform
              </span>
              <p className="showcase-kicker">Multi-agent experiment system</p>
              <h1 id="showcase-title">AI Hunger Games</h1>
              <p className="showcase-lede">
                Eight LLM-driven personalities answer anonymously, judge peers,
                accumulate evidence, and evolve through persisted generations.
              </p>
              <div className="showcase-hero-actions">
                <button
                  className="hero-primary"
                  onClick={() => onTabChange("overview")}
                  type="button"
                >
                  Explore live experiment
                  <ArrowRight aria-hidden="true" size={17} />
                </button>
                <a
                  className="hero-secondary"
                  href="https://github.com/Anugrah-Singh/ai-hunger-games"
                  rel="noreferrer"
                  target="_blank"
                >
                  View source
                  <ArrowUpRight aria-hidden="true" size={16} />
                </a>
              </div>
              <dl className="showcase-evidence-strip">
                <div>
                  <dt>Latest record</dt>
                  <dd>
                    {latestGeneration
                      ? `Generation ${latestGeneration.generation_number}`
                      : "Awaiting first generation"}
                  </dd>
                </div>
                <div>
                  <dt>Active population</dt>
                  <dd>{experiment.current_population.length} agents</dd>
                </div>
                <div>
                  <dt>Persisted rounds</dt>
                  <dd>{persistedRounds}</dd>
                </div>
                <div>
                  <dt>Provider</dt>
                  <dd>{experiment.provider_name ?? "Configured at runtime"}</dd>
                </div>
              </dl>
            </div>
            <div className="hero-system-card" aria-label="Experiment system summary">
              <div className="system-card-header">
                <span className="status-dot" />
                <span>Experiment pipeline</span>
                <span className="mono-label">LIVE DATA</span>
              </div>
              {stages.map((stage, index) => {
                const Icon = stage.icon;
                return (
                  <div className="system-step" key={stage.title}>
                    <span className="system-step-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="system-step-icon"><Icon aria-hidden="true" size={16} /></span>
                    <span>{stage.title}</span>
                  </div>
                );
              })}
            </div>
          </m.section>

          <section className="showcase-section">
            <SectionHeading
              eyebrow="Evidence of scope"
              title="Built as an experiment platform, not a chat wrapper"
              description="The project combines AI evaluation, durable orchestration, statistical analysis, and a production-style full-stack interface."
            />
            <ul className="proof-cloud" aria-label="Technology and practice evidence">
              {proofLabels.map((label) => <li key={label}>{label}</li>)}
            </ul>
          </section>

          <section className="showcase-section architecture-section" id="architecture">
            <SectionHeading
              eyebrow="System architecture"
              title="One traceable path from interface to evidence"
              description="Each boundary has a narrow responsibility, which keeps provider behavior, game rules, persistence, and analysis independently testable."
            />
            <div className="architecture-flow">
              {architectureNodes.map((node, index) => {
                const Icon = node.icon;
                return (
                  <div className="architecture-node-wrap" key={node.label}>
                    <article className="architecture-node">
                      <span><Icon aria-hidden="true" size={20} /></span>
                      <strong>{node.label}</strong>
                      <p>{node.note}</p>
                    </article>
                    {index < architectureNodes.length - 1 && (
                      <span className="architecture-connector" aria-hidden="true">
                        <ArrowRight size={16} />
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="showcase-section">
            <SectionHeading
              eyebrow="Generation loop"
              title="Six deliberate stages"
              description="The user-visible workflow mirrors the actual engine rather than presenting decorative or invented phases."
            />
            <ol className="showcase-flow">
              {stages.map((stage, index) => {
                const Icon = stage.icon;
                return (
                  <li key={stage.title}>
                    <span className="showcase-stage-number">{String(index + 1).padStart(2, "0")}</span>
                    <span className="showcase-stage-icon"><Icon aria-hidden="true" size={18} /></span>
                    <div>
                      <h3>{stage.title}</h3>
                      <p>{stage.description}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>

          <section className="showcase-outcome-grid">
            <article className="showcase-outcome-card">
              <div className="outcome-card-header">
                <div>
                  <p className="eyebrow">Latest persisted outcome</p>
                  <h2>Inspect real experiment history</h2>
                </div>
                <BarChart3 aria-hidden="true" size={22} />
              </div>
              <dl className="outcome-list">
                <div><dt>Generation</dt><dd>{latestGeneration ? latestGeneration.generation_number : "—"}</dd></div>
                <div><dt>Eliminated</dt><dd>{latestGeneration ? agentName(latestGeneration.eliminated_agent_id) : "Not available"}</dd></div>
                <div><dt>Replacement</dt><dd>{latestGeneration ? `${latestGeneration.replacement_agent.agent_name} (${latestGeneration.replacement_agent.personality.name})` : "Not available"}</dd></div>
                <div><dt>Population</dt><dd>{experiment.current_population.length} active agents</dd></div>
              </dl>
            </article>
            <aside className="evidence-boundary">
              <span><ShieldCheck aria-hidden="true" size={20} /></span>
              <div>
                <p className="eyebrow">Evidence boundary</p>
                <h2>Measured, not sensationalized</h2>
                <p>{caution}</p>
              </div>
            </aside>
          </section>

          <section className="showcase-section">
            <SectionHeading
              eyebrow="Engineering decisions"
              title="Design choices with visible consequences"
            />
            <div className="showcase-decision-grid">
              {decisions.map((decision) => {
                const Icon = decision.icon;
                return (
                  <article className="showcase-decision" key={decision.title}>
                    <span className="showcase-decision-icon"><Icon aria-hidden="true" size={19} /></span>
                    <div><h3>{decision.title}</h3><p>{decision.detail}</p></div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="showcase-section showcase-next-steps">
            <SectionHeading eyebrow="Inspect the evidence" title="Move from the case study into the live record" />
            <div className="showcase-paths">
              <button onClick={() => onTabChange("rounds")} type="button">Inspect anonymous rounds <ArrowRight size={15} /></button>
              <button onClick={() => onTabChange("relationships")} type="button">Compare voting signals <ArrowRight size={15} /></button>
              <button onClick={() => onTabChange("lineage")} type="button">Trace replacement lineage <ArrowRight size={15} /></button>
            </div>
          </section>
        </section>
      </MotionConfig>
    </LazyMotion>
  );
}
