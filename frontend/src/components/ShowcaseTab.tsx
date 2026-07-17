import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Callout,
  Card,
  DataList,
  Theme,
} from "@radix-ui/themes";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Database,
  Gauge,
  GitBranch,
  Info,
  MessageSquare,
  RefreshCcw,
  ShieldCheck,
  Users,
  Vote,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { domAnimation, LazyMotion, MotionConfig } from "motion/react";
import * as m from "motion/react-m";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";
import Tilt from "react-parallax-tilt";

import type {
  ExperimentAnalysis,
  ExperimentDetail,
  GenerationSummary,
} from "../api/types";


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
  "Python",
  "Async orchestration",
  "FastAPI",
  "React + TypeScript",
  "SQLAlchemy",
  "Alembic",
  "Automated tests",
];


const stages: ExperimentStage[] = [
  {
    description: "Distinct prompt instructions form a competing population.",
    icon: Users,
    title: "Personalities",
  },
  {
    description: "Agents answer concurrently with timeouts and retry ownership.",
    icon: MessageSquare,
    title: "Answers",
  },
  {
    description: "Answers become shuffled candidates with no author identity exposed.",
    icon: ShieldCheck,
    title: "Anonymous set",
  },
  {
    description: "Eligible voters choose sequentially to respect constrained provider limits.",
    icon: Vote,
    title: "Votes",
  },
  {
    description: "Scores and complete historical snapshots commit atomically.",
    icon: Database,
    title: "History",
  },
  {
    description: "The lowest scorer leaves and a generated personality joins next time.",
    icon: RefreshCcw,
    title: "Replacement",
  },
];


const decisions = [
  {
    detail:
      "Vote providers receive candidate IDs and answer text, never an answer author ID. The UI follows that same constraint.",
    icon: ShieldCheck,
    title: "Anonymous evaluation",
  },
  {
    detail:
      "The engine owns timeouts, exponential backoff, and provider retry-after delays so retries remain observable and predictable.",
    icon: Gauge,
    title: "Explicit reliability boundaries",
  },
  {
    detail:
      "A generation is saved as one transaction with agent, round, vote, score, and replacement snapshots for reproducible analysis.",
    icon: Database,
    title: "Durable experimental history",
  },
  {
    detail:
      "Relationship metrics compare observed votes with eligibility and random baselines; they are indicators, not proof of coordination.",
    icon: GitBranch,
    title: "Measured claims",
  },
];


export function ShowcaseTab({
  agentName,
  analysis,
  experiment,
  generations,
  onTabChange,
}: ShowcaseTabProps) {
  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const latestGeneration = generations.at(-1);
  const persistedRounds = generations.reduce(
    (total, generation) => total + generation.round_count,
    0,
  );
  const caution = analysis.cautions.at(0)
    ?? "A completed generation demonstrates the workflow, not a durable behavioral pattern.";

  return (
    <Theme
      accentColor="teal"
      appearance="light"
      grayColor="sage"
      hasBackground={false}
      radius="small"
      scaling="100%"
    >
      <LazyMotion features={domAnimation} strict>
        <MotionConfig reducedMotion="user">
          <section className="recruiter-overview" aria-labelledby="showcase-title">
            <Theme appearance="dark" accentColor="cyan" grayColor="slate" hasBackground={false} asChild>
              <m.section
                className="showcase-hero"
                animate={{ opacity: 1, y: 0 }}
                initial={{ opacity: 1, y: 6 }}
                transition={{ duration: 0.34, ease: "easeOut" }}
                style={{ position: 'relative', overflow: 'hidden' }}
              >
              {init && (
                <Particles
                  id="tsparticles"
                  options={{
                    fullScreen: { enable: false, zIndex: 0 },
                    background: { color: { value: "transparent" } },
                    fpsLimit: 120,
                    interactivity: {
                      events: {
                        onHover: { enable: true, mode: "repulse" },
                      },
                      modes: { repulse: { distance: 100, duration: 0.4 } },
                    },
                    particles: {
                      color: { value: "#0ea5e9" },
                      links: {
                        color: "#0ea5e9",
                        distance: 150,
                        enable: true,
                        opacity: 0.2,
                        width: 1,
                      },
                      move: {
                        direction: "none",
                        enable: true,
                        outModes: { default: "bounce" },
                        random: false,
                        speed: 1,
                        straight: false,
                      },
                      number: {
                        density: { enable: true, width: 800, height: 800 },
                        value: 80,
                      },
                      opacity: { value: 0.4 },
                      shape: { type: "circle" },
                      size: { value: { min: 1, max: 3 } },
                    },
                    detectRetina: true,
                  }}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    zIndex: 0,
                  }}
                />
              )}
              <img
                alt=""
                aria-hidden="true"
                className="showcase-hero-mark"
                src="/static/arena-mark.png"
                style={{ zIndex: 1 }}
              />
              <div className="showcase-hero-content" style={{ position: 'relative', zIndex: 1 }}>
                <Badge color="cyan" size="2" variant="surface">
                  Portfolio case study
                </Badge>
                <p className="showcase-kicker">Multi-agent experiment platform</p>
                <h1 id="showcase-title">AI Hunger Games</h1>
                <p className="showcase-lede">
                  A durable experiment for testing how LLM-driven personalities
                  answer, vote, compete, and change across persisted generations.
                </p>
                <div className="showcase-hero-actions">
                  <Button onClick={() => onTabChange("overview")} size="3">
                    Explore live experiment
                    <ArrowRight aria-hidden="true" size={16} />
                  </Button>
                  <Button
                    asChild
                    color="gray"
                    size="3"
                    variant="surface"
                  >
                    <a
                      href="https://github.com/Anugrah-Singh/ai-hunger-games"
                      rel="noreferrer"
                      target="_blank"
                    >
                      View source
                      <ArrowUpRight aria-hidden="true" size={16} />
                    </a>
                  </Button>
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
            </m.section>
            </Theme>

            <m.section
              className="showcase-section showcase-proof"
              animate={{ opacity: 1, y: 0 }}
              initial={{ opacity: 1, y: 6 }}
              transition={{ duration: 0.34, ease: "easeOut", delay: 0.04 }}
            >
              <div className="showcase-section-heading">
                <div>
                  <p className="eyebrow">Evidence of scope</p>
                  <h2>Built as an experiment, not a scripted demo</h2>
                </div>
                <Workflow aria-hidden="true" size={22} />
              </div>
              <ul className="showcase-proof-rail" aria-label="Technology and practice evidence">
                {proofLabels.map((label) => (
                  <li key={label}>
                    <Badge color="teal" size="2" variant="surface">
                      {label}
                    </Badge>
                  </li>
                ))}
              </ul>
            </m.section>

            <m.section
              className="showcase-section showcase-flow-section"
              animate={{ opacity: 1, y: 0 }}
              initial={{ opacity: 1, y: 6 }}
              transition={{ duration: 0.34, ease: "easeOut", delay: 0.08 }}
            >
              <div className="showcase-section-heading">
                <div>
                  <p className="eyebrow">Generation loop</p>
                  <h2>One traceable system, six deliberate stages</h2>
                </div>
              </div>
              <ol className="showcase-flow">
                {stages.map((stage, index) => {
                  const Icon = stage.icon;

                  return (
                    <li key={stage.title}>
                      <span className="showcase-stage-number">0{index + 1}</span>
                      <span className="showcase-stage-icon">
                        <Icon aria-hidden="true" size={18} />
                      </span>
                      <div>
                        <h3>{stage.title}</h3>
                        <p>{stage.description}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </m.section>

            <section className="showcase-outcome-grid">
              <Tilt tiltMaxAngleX={5} tiltMaxAngleY={5} perspective={1000} scale={1.02} transitionSpeed={2500} className="showcase-tilt-wrapper">
                <Card className="showcase-outcome-card" size="3" variant="surface">
                <div className="showcase-section-heading">
                  <div>
                    <p className="eyebrow">Latest persisted outcome</p>
                    <h2>Inspectable, not simulated</h2>
                  </div>
                  <BarChart3 aria-hidden="true" size={22} />
                </div>
                <DataList.Root className="showcase-data-list" orientation="horizontal">
                  <DataList.Item>
                    <DataList.Label minWidth="132px">Generation</DataList.Label>
                    <DataList.Value>
                      {latestGeneration
                        ? `Generation ${latestGeneration.generation_number}`
                        : "No completed generation"}
                    </DataList.Value>
                  </DataList.Item>
                  <DataList.Item>
                    <DataList.Label minWidth="132px">Eliminated</DataList.Label>
                    <DataList.Value>
                      {latestGeneration
                        ? agentName(latestGeneration.eliminated_agent_id)
                        : "Not available"}
                    </DataList.Value>
                  </DataList.Item>
                  <DataList.Item>
                    <DataList.Label minWidth="132px">Replacement</DataList.Label>
                    <DataList.Value>
                      {latestGeneration
                        ? `${latestGeneration.replacement_agent.agent_name} (${latestGeneration.replacement_agent.personality.name})`
                        : "Not available"}
                    </DataList.Value>
                  </DataList.Item>
                  <DataList.Item>
                    <DataList.Label minWidth="132px">Population</DataList.Label>
                    <DataList.Value>
                      {experiment.current_population.length} active agents
                    </DataList.Value>
                  </DataList.Item>
                </DataList.Root>
              </Card>
            </Tilt>

              <Callout.Root className="showcase-caution" color="amber" size="2" variant="surface">
                <Callout.Icon>
                  <Info aria-hidden="true" size={18} />
                </Callout.Icon>
                <Callout.Text>
                  <strong>Evidence boundary. </strong>
                  {caution}
                </Callout.Text>
              </Callout.Root>
            </section>

            <section className="showcase-section showcase-decisions" id="architecture">
              <div className="showcase-section-heading">
                <div>
                  <p className="eyebrow">Engineering decisions</p>
                  <h2>Design choices with visible consequences</h2>
                </div>
              </div>
              <div className="showcase-decision-grid">
                {decisions.map((decision) => {
                  const Icon = decision.icon;

                  return (
                    <article className="showcase-decision" key={decision.title}>
                      <span className="showcase-decision-icon">
                        <Icon aria-hidden="true" size={19} />
                      </span>
                      <div>
                        <h3>{decision.title}</h3>
                        <p>{decision.detail}</p>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>

            <section className="showcase-section showcase-next-steps">
              <div className="showcase-section-heading">
                <div>
                  <p className="eyebrow">Inspect the evidence</p>
                  <h2>Move from the case study into the live record</h2>
                </div>
              </div>
              <div className="showcase-paths">
                <Button
                  color="gray"
                  onClick={() => onTabChange("rounds")}
                  variant="surface"
                >
                  Inspect anonymous rounds
                  <ArrowRight aria-hidden="true" size={15} />
                </Button>
                <Button
                  color="gray"
                  onClick={() => onTabChange("relationships")}
                  variant="surface"
                >
                  Compare voting signals
                  <ArrowRight aria-hidden="true" size={15} />
                </Button>
                <Button
                  color="gray"
                  onClick={() => onTabChange("lineage")}
                  variant="surface"
                >
                  Trace replacement lineage
                  <ArrowRight aria-hidden="true" size={15} />
                </Button>
              </div>
            </section>
          </section>
        </MotionConfig>
      </LazyMotion>
    </Theme>
  );
}
