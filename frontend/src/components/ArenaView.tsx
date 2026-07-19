import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  CirclePlay,
  FastForward,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Trophy,
  Vote as VoteIcon,
  Volume2,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { getGeneration } from "../api/client";
import type {
  Agent,
  ExperimentDetail,
  GenerationDetail,
  GenerationSummary,
  Participant,
} from "../api/types";
import { candidateLabel, errorMessage, formatNumber } from "../lib/format";
import {
  createArenaScenes,
  type ArenaScene,
  sceneDelayMilliseconds,
  sceneLabel,
} from "../lib/arenaTimeline";
import { LoadingState, Placeholder } from "./common";

export type ArenaMode = "watch" | "replay";

interface ArenaViewProps {
  agentName: (agentId: string) => string;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  isRunning: boolean;
  mode: ArenaMode;
  onRun: () => void;
  onSelectedGenerationChange: (gameId: number | null) => void;
  selectedGenerationId: number | null;
}

const playbackSpeeds = [0.75, 1, 1.5, 2] as const;

export function ArenaView({
  agentName,
  experiment,
  generations,
  isRunning,
  mode,
  onRun,
  onSelectedGenerationChange,
  selectedGenerationId,
}: ArenaViewProps) {
  const generationQuery = useQuery({
    enabled: selectedGenerationId !== null,
    queryFn: () => getGeneration(selectedGenerationId!),
    queryKey: ["generation", selectedGenerationId],
  });
  const generation = generationQuery.data;
  const scenes = useMemo(
    () => (generation === undefined ? [] : createArenaScenes(generation)),
    [generation],
  );
  const [sceneIndex, setSceneIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(mode === "watch");
  const [playbackSpeed, setPlaybackSpeed] = useState<(typeof playbackSpeeds)[number]>(1);

  useEffect(() => {
    setSceneIndex(0);
    setIsPlaying(mode === "watch");
  }, [mode, selectedGenerationId]);

  useEffect(() => {
    if (!isPlaying || scenes.length === 0) {
      return undefined;
    }

    if (sceneIndex >= scenes.length - 1) {
      setIsPlaying(false);
      return undefined;
    }

    const delay = sceneDelayMilliseconds(scenes[sceneIndex]) / playbackSpeed;
    const timeout = window.setTimeout(
      () => setSceneIndex((current) => Math.min(current + 1, scenes.length - 1)),
      delay,
    );

    return () => window.clearTimeout(timeout);
  }, [isPlaying, playbackSpeed, sceneIndex, scenes]);

  if (generations.length === 0 || selectedGenerationId === null) {
    return (
      <ArenaEmptyState
        canRun={experiment.can_run}
        isRunning={isRunning}
        onRun={onRun}
        reason={experiment.run_block_reason}
      />
    );
  }

  if (generationQuery.isPending) {
    return <LoadingState label="Preparing the arena replay" />;
  }

  if (generationQuery.isError) {
    return (
      <section className="arena-error" role="alert">
        <strong>The arena record could not be loaded.</strong>
        <span>{errorMessage(generationQuery.error)}</span>
      </section>
    );
  }

  if (generation === undefined || scenes.length === 0) {
    return <Placeholder>No replayable generation data is available.</Placeholder>;
  }

  const currentScene = scenes[sceneIndex];

  return (
    <section className="arena-page" aria-labelledby="arena-heading">
      <ArenaHeader
        generation={generation}
        generations={generations}
        isPlaying={isPlaying}
        mode={mode}
        onSelectedGenerationChange={onSelectedGenerationChange}
        selectedGenerationId={selectedGenerationId}
      />

      <div className="arena-layout">
        <div className="arena-main-column">
          <ArenaStage
            agentName={agentName}
            generation={generation}
            scene={currentScene}
          />
          <PlaybackControls
            isPlaying={isPlaying}
            onFirst={() => setSceneIndex(0)}
            onNext={() => setSceneIndex((current) => Math.min(current + 1, scenes.length - 1))}
            onPlayChange={setIsPlaying}
            onPrevious={() => setSceneIndex((current) => Math.max(current - 1, 0))}
            onSpeedChange={setPlaybackSpeed}
            playbackSpeed={playbackSpeed}
            sceneCount={scenes.length}
            sceneIndex={sceneIndex}
          />
        </div>

        <aside className="arena-story-panel">
          <GenerationScoreboard generation={generation} />
          <Transcript
            agentName={agentName}
            currentSceneIndex={sceneIndex}
            scenes={scenes}
          />
        </aside>
      </div>
    </section>
  );
}

function ArenaHeader({
  generation,
  generations,
  isPlaying,
  mode,
  onSelectedGenerationChange,
  selectedGenerationId,
}: {
  generation: GenerationDetail;
  generations: GenerationSummary[];
  isPlaying: boolean;
  mode: ArenaMode;
  onSelectedGenerationChange: (gameId: number | null) => void;
  selectedGenerationId: number;
}) {
  return (
    <header className="arena-page-header">
      <div>
        <span className="arena-live-pill">
          <span className={isPlaying ? "arena-live-dot" : "arena-live-dot is-paused"} />
          {isPlaying ? "Playing" : "Paused"}
        </span>
        <p className="eyebrow">{mode === "watch" ? "Watch mode" : "Replay mode"}</p>
        <h1 id="arena-heading">Generation {generation.generation_number} arena</h1>
        <p className="arena-header-copy">
          Anonymous answers take the centre stage. Named agents speak only when
          their persisted votes are revealed.
        </p>
      </div>
      <label className="arena-generation-picker">
        <span>Generation</span>
        <select
          onChange={(event) => onSelectedGenerationChange(Number(event.target.value))}
          value={selectedGenerationId}
        >
          {generations.map((generationSummary) => (
            <option key={generationSummary.game_id} value={generationSummary.game_id}>
              Generation {generationSummary.generation_number}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}

function ArenaStage({
  agentName,
  generation,
  scene,
}: {
  agentName: (agentId: string) => string;
  generation: GenerationDetail;
  scene: ArenaScene;
}) {
  const prefersReducedMotion = useReducedMotion();
  const agents = generation.starting_agents;
  const activeVoterId = scene.type === "vote" ? scene.voterAgentId : null;
  const activeVoterPosition = agents.findIndex(
    (agent) => agent.agent_id === activeVoterId,
  );
  const activeSeat = activeVoterPosition >= 0
    ? seatPosition(activeVoterPosition, agents.length)
    : null;

  return (
    <div className="arena-stage-shell">
      <div className="arena-stage" aria-label="AI agent arena">
        <div className="arena-grid-floor" aria-hidden="true" />
        <div className="arena-ring arena-ring-outer" aria-hidden="true" />
        <div className="arena-ring arena-ring-inner" aria-hidden="true" />

        {activeSeat !== null && scene.type === "vote" && (
          <svg className="vote-beam-layer" aria-hidden="true" viewBox="0 0 100 100">
            <motion.line
              animate={{ opacity: 1, pathLength: 1 }}
              initial={{ opacity: 0, pathLength: 0 }}
              key={scene.id}
              stroke="url(#vote-gradient)"
              strokeLinecap="round"
              strokeWidth="1.1"
              transition={{ duration: prefersReducedMotion ? 0 : 0.7 }}
              x1={activeSeat.x}
              x2="50"
              y1={activeSeat.y}
              y2="50"
            />
            <defs>
              <linearGradient id="vote-gradient" x1="0" x2="1">
                <stop offset="0%" stopColor="#5eead4" />
                <stop offset="100%" stopColor="#fbbf24" />
              </linearGradient>
            </defs>
          </svg>
        )}

        {agents.map((agent, index) => (
          <ArenaAgent
            agent={agent}
            eliminated={
              scene.type === "elimination"
              && scene.eliminatedAgentId === agent.agent_id
            }
            isActive={activeVoterId === agent.agent_id}
            key={agent.agent_id}
            position={seatPosition(index, agents.length)}
            status={agentStatus(scene, agent.agent_id)}
          />
        ))}

        <AnimatePresence mode="wait">
          <motion.div
            animate={{ opacity: 1, scale: 1, x: "-50%", y: "-50%" }}
            className="arena-centre-stage"
            exit={{ opacity: 0, scale: 0.97, x: "-50%", y: "calc(-50% - 8px)" }}
            initial={{ opacity: 0, scale: 0.97, x: "-50%", y: "calc(-50% + 10px)" }}
            key={scene.id}
            transition={{ duration: prefersReducedMotion ? 0 : 0.28 }}
          >
            <ArenaSceneCard agentName={agentName} generation={generation} scene={scene} />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function ArenaAgent({
  agent,
  eliminated,
  isActive,
  position,
  status,
}: {
  agent: Participant;
  eliminated: boolean;
  isActive: boolean;
  position: { x: number; y: number };
  status: string;
}) {
  return (
    <motion.article
      animate={{
        opacity: eliminated ? 0.34 : 1,
        scale: isActive ? 1.08 : 1,
        x: "-50%",
        y: isActive ? "calc(-50% - 5px)" : "-50%",
      }}
      className={`arena-agent${isActive ? " is-active" : ""}${eliminated ? " is-eliminated" : ""}`}
      layout
      style={{ left: `${position.x}%`, top: `${position.y}%` }}
      transition={{ type: "spring", stiffness: 280, damping: 24 }}
    >
      <div className="arena-agent-platform" aria-hidden="true" />
      <div className="arena-avatar">
        <span>{initials(agent.agent_name)}</span>
      </div>
      <div className="arena-agent-copy">
        <strong>{agent.agent_name}</strong>
        <span>{agent.personality.name}</span>
        <small>{status}</small>
      </div>
      {isActive && (
        <span className="arena-speaking-indicator" aria-label={`${agent.agent_name} is voting`}>
          <Volume2 aria-hidden="true" size={13} />
        </span>
      )}
    </motion.article>
  );
}

function ArenaSceneCard({
  agentName,
  generation,
  scene,
}: {
  agentName: (agentId: string) => string;
  generation: GenerationDetail;
  scene: ArenaScene;
}) {
  switch (scene.type) {
    case "generation-intro":
      return (
        <div className="arena-scene-card arena-scene-intro">
          <Sparkles aria-hidden="true" size={24} />
          <span className="arena-scene-kicker">The arena opens</span>
          <h2>{scene.title}</h2>
          <p>{generation.starting_agents.length} personalities. {generation.round_count} rounds. One elimination.</p>
        </div>
      );
    case "round-intro":
      return (
        <div className="arena-scene-card">
          <span className="arena-round-chip">Round {scene.roundNumber}</span>
          <span className="arena-scene-kicker">Question</span>
          <h2>{scene.question}</h2>
          <p>Every personality answers independently before candidates are anonymized.</p>
        </div>
      );
    case "candidate":
      return (
        <div className="arena-scene-card arena-candidate-card">
          <span className="arena-anonymous-badge">
            <ShieldCheck aria-hidden="true" size={14} />
            Anonymous voice
          </span>
          <span className="arena-scene-kicker">{candidateLabel(scene.candidateId)}</span>
          <blockquote>{scene.content}</blockquote>
          <small>{scene.attemptCount > 1 ? `${scene.attemptCount} attempts` : "Generated on first attempt"}</small>
        </div>
      );
    case "vote":
      return (
        <div className="arena-scene-card arena-vote-card">
          <span className="arena-round-chip">Round {scene.roundNumber}</span>
          <VoteIcon aria-hidden="true" size={26} />
          <span className="arena-scene-kicker">{agentName(scene.voterAgentId)} speaks</span>
          <h2>“My vote goes to {candidateLabel(scene.selectedCandidateId)}.”</h2>
          <p>The voter never received the candidate author’s identity.</p>
        </div>
      );
    case "round-result":
      return (
        <div className="arena-scene-card">
          <Trophy aria-hidden="true" size={25} />
          <span className="arena-scene-kicker">Round {scene.roundNumber} result</span>
          <h2>{scene.scores[0] === undefined ? "No scored candidates" : `${candidateLabel(scene.scores[0].candidate_id)} leads`}</h2>
          <div className="arena-candidate-scoreboard">
            {scene.scores.map((score) => (
              <div key={score.candidate_id}>
                <span>{candidateLabel(score.candidate_id)}</span>
                <strong>{score.score}</strong>
              </div>
            ))}
          </div>
        </div>
      );
    case "elimination": {
      const eliminated = generation.starting_agents.find(
        (agent) => agent.agent_id === scene.eliminatedAgentId,
      );
      return (
        <div className="arena-scene-card arena-elimination-card">
          <span className="arena-danger-chip">Elimination</span>
          <h2>{eliminated?.agent_name ?? agentName(scene.eliminatedAgentId)} leaves the arena</h2>
          <p>{eliminated?.personality.name ?? "The lowest-scoring personality"} finished with the lowest generation total.</p>
        </div>
      );
    }
    case "replacement":
      return (
        <div className="arena-scene-card arena-replacement-card">
          <Sparkles aria-hidden="true" size={26} />
          <span className="arena-scene-kicker">New challenger</span>
          <h2>{scene.replacementAgentName}</h2>
          <strong>{scene.personality.name}</strong>
          <p>{scene.personality.description}</p>
        </div>
      );
    case "generation-complete":
      return (
        <div className="arena-scene-card arena-complete-card">
          <Trophy aria-hidden="true" size={26} />
          <span className="arena-scene-kicker">Generation complete</span>
          <h2>The next population is ready.</h2>
          <p>The complete record is persisted for replay and analysis.</p>
        </div>
      );
  }
}

function PlaybackControls({
  isPlaying,
  onFirst,
  onNext,
  onPlayChange,
  onPrevious,
  onSpeedChange,
  playbackSpeed,
  sceneCount,
  sceneIndex,
}: {
  isPlaying: boolean;
  onFirst: () => void;
  onNext: () => void;
  onPlayChange: (isPlaying: boolean) => void;
  onPrevious: () => void;
  onSpeedChange: (speed: (typeof playbackSpeeds)[number]) => void;
  playbackSpeed: (typeof playbackSpeeds)[number];
  sceneCount: number;
  sceneIndex: number;
}) {
  const progress = sceneCount <= 1 ? 100 : (sceneIndex / (sceneCount - 1)) * 100;

  return (
    <div className="arena-controls" aria-label="Replay controls">
      <div className="arena-progress-track" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className="arena-control-row">
        <div className="arena-control-buttons">
          <button aria-label="Restart replay" className="arena-icon-button" onClick={onFirst} type="button">
            <RotateCcw aria-hidden="true" size={17} />
          </button>
          <button aria-label="Previous scene" className="arena-icon-button" disabled={sceneIndex === 0} onClick={onPrevious} type="button">
            <ChevronLeft aria-hidden="true" size={19} />
          </button>
          <button
            aria-label={isPlaying ? "Pause replay" : "Play replay"}
            className="arena-play-button"
            onClick={() => onPlayChange(!isPlaying)}
            type="button"
          >
            {isPlaying ? <Pause aria-hidden="true" size={19} /> : <Play aria-hidden="true" size={19} />}
          </button>
          <button aria-label="Next scene" className="arena-icon-button" disabled={sceneIndex >= sceneCount - 1} onClick={onNext} type="button">
            <ChevronRight aria-hidden="true" size={19} />
          </button>
        </div>
        <span className="arena-scene-counter">Scene {sceneIndex + 1} / {sceneCount}</span>
        <label className="arena-speed-control">
          <FastForward aria-hidden="true" size={15} />
          <span>Speed</span>
          <select
            onChange={(event) => onSpeedChange(Number(event.target.value) as (typeof playbackSpeeds)[number])}
            value={playbackSpeed}
          >
            {playbackSpeeds.map((speed) => <option key={speed} value={speed}>{speed}×</option>)}
          </select>
        </label>
      </div>
    </div>
  );
}

function GenerationScoreboard({ generation }: { generation: GenerationDetail }) {
  const rankedAgents = [...generation.starting_agents].sort(
    (first, second) => second.total_score - first.total_score,
  );

  return (
    <section className="arena-side-card">
      <div className="arena-side-card-header">
        <div>
          <p className="eyebrow">Generation record</p>
          <h2>Final scoreboard</h2>
        </div>
        <Trophy aria-hidden="true" size={18} />
      </div>
      <ol className="arena-score-list">
        {rankedAgents.map((agent, index) => (
          <li className={agent.was_eliminated ? "is-eliminated" : ""} key={agent.agent_id}>
            <span>{index + 1}</span>
            <div><strong>{agent.agent_name}</strong><small>{agent.personality.name}</small></div>
            <b>{formatNumber(agent.total_score, 0)}</b>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Transcript({
  agentName,
  currentSceneIndex,
  scenes,
}: {
  agentName: (agentId: string) => string;
  currentSceneIndex: number;
  scenes: ArenaScene[];
}) {
  const visibleScenes = scenes.slice(0, currentSceneIndex + 1).slice(-8);

  return (
    <section className="arena-side-card arena-transcript-card">
      <div className="arena-side-card-header">
        <div>
          <p className="eyebrow">Live story</p>
          <h2>Event transcript</h2>
        </div>
        <CirclePlay aria-hidden="true" size={18} />
      </div>
      <div className="arena-transcript" aria-live="polite">
        {visibleScenes.map((scene) => (
          <article key={scene.id}>
            <span>{sceneLabel(scene)}</span>
            <p>{describeScene(scene, agentName)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ArenaEmptyState({
  canRun,
  isRunning,
  onRun,
  reason,
}: {
  canRun: boolean;
  isRunning: boolean;
  onRun: () => void;
  reason: string | null;
}) {
  return (
    <section className="arena-empty-state">
      <div className="arena-empty-orbit" aria-hidden="true">
        {Array.from({ length: 8 }, (_, index) => (
          <span key={index} style={{ transform: `rotate(${index * 45}deg) translateY(-104px)` }} />
        ))}
      </div>
      <span className="hero-badge"><Sparkles aria-hidden="true" size={14} />Arena ready</span>
      <h1>Run the first generation to start the show.</h1>
      <p>
        The backend will create anonymous answers, collect peer votes, save the
        result, and unlock a complete animated replay.
      </p>
      <button className="primary-button" disabled={!canRun || isRunning} onClick={onRun} type="button">
        <Play aria-hidden="true" size={16} />
        {isRunning ? "Generation running" : "Run first generation"}
      </button>
      {!canRun && reason !== null && <small>{reason}</small>}
    </section>
  );
}

function seatPosition(index: number, total: number): { x: number; y: number } {
  const angle =
    -Math.PI / 2 + (index / Math.max(total, 1)) * Math.PI * 2;

  return {
    x: 50 + Math.cos(angle) * 35,
    y: 50 + Math.sin(angle) * 36,
  };
}

function agentStatus(scene: ArenaScene, agentId: string): string {
  if (scene.type === "vote" && scene.voterAgentId === agentId) {
    return "Casting vote";
  }
  if (scene.type === "candidate") {
    return "Evaluating";
  }
  if (scene.type === "round-intro") {
    return "Preparing";
  }
  if (scene.type === "round-result") {
    return "Awaiting scores";
  }
  if (scene.type === "elimination" && scene.eliminatedAgentId === agentId) {
    return "Eliminated";
  }
  return "Watching";
}

function describeScene(
  scene: ArenaScene,
  agentName: (agentId: string) => string,
): string {
  switch (scene.type) {
    case "generation-intro":
      return scene.title;
    case "round-intro":
      return scene.question;
    case "candidate":
      return `${candidateLabel(scene.candidateId)} presented an anonymous answer.`;
    case "vote":
      return `${agentName(scene.voterAgentId)} voted for ${candidateLabel(scene.selectedCandidateId)}.`;
    case "round-result":
      return scene.scores[0] === undefined
        ? `Round ${scene.roundNumber} ended without a scored candidate.`
        : `${candidateLabel(scene.scores[0].candidate_id)} led Round ${scene.roundNumber} with ${scene.scores[0].score} votes.`;
    case "elimination":
      return `${agentName(scene.eliminatedAgentId)} was eliminated.`;
    case "replacement":
      return `${scene.replacementAgentName} entered as ${scene.personality.name}.`;
    case "generation-complete":
      return `Generation ${scene.generationNumber} was saved.`;
  }
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
