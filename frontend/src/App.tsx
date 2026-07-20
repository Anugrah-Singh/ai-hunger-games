import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Clapperboard,
  Eye,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Wifi,
} from "lucide-react";
import { Tabs, Tooltip } from "radix-ui";

import {
  createExperiment,
  getExperiment,
  getExperimentAnalysis,
  getExperiments,
  getGenerations,
  runGeneration,
} from "./api/client";
import type {
  ExperimentAnalysis,
  ExperimentDetail,
  GenerationSummary,
} from "./api/types";
import { ArenaView, type ArenaMode } from "./components/ArenaView";
import { ExperimentSidebar } from "./components/ExperimentSidebar";
import { NewExperimentDialog } from "./components/NewExperimentDialog";
import {
  ErrorState,
  IconButton,
  LoadingState,
  RunProgress,
} from "./components/common";
import { errorMessage, formatDate } from "./lib/format";
import { defaultExperimentId } from "./lib/selection";

const OverviewTab = lazy(async () => ({
  default: (await import("./components/OverviewTab")).OverviewTab,
}));
const RoundsTab = lazy(async () => ({
  default: (await import("./components/RoundsTab")).RoundsTab,
}));
const RelationshipsTab = lazy(async () => ({
  default: (await import("./components/RelationshipsTab")).RelationshipsTab,
}));
const LineageTab = lazy(async () => ({
  default: (await import("./components/LineageTab")).LineageTab,
}));
const ShowcaseTab = lazy(async () => ({
  default: (await import("./components/ShowcaseTab")).ShowcaseTab,
}));

const experienceModes = [
  { icon: Eye, label: "Watch", value: "watch" },
  { icon: Clapperboard, label: "Replay", value: "replay" },
  { icon: BarChart3, label: "Analyze", value: "analyze" },
] as const;

type ExperienceMode = (typeof experienceModes)[number]["value"];

const analysisTabs = [
  { label: "Overview", value: "overview" },
  { label: "Rounds", value: "rounds" },
  { label: "Relationships", value: "relationships" },
  { label: "Lineage", value: "lineage" },
  { label: "About", value: "showcase" },
] as const;

type AnalysisTab = (typeof analysisTabs)[number]["value"];

interface ToastState {
  isError: boolean;
  message: string;
}

export function App() {
  const queryClient = useQueryClient();
  const [experienceMode, setExperienceMode] = useState<ExperienceMode>("watch");
  const [analysisTab, setAnalysisTab] = useState<AnalysisTab>("overview");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | null>(null);
  const [selectedGenerationId, setSelectedGenerationId] = useState<number | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  const experimentsQuery = useQuery({
    queryFn: getExperiments,
    queryKey: ["experiments"],
  });
  const experimentQuery = useQuery({
    enabled: selectedExperimentId !== null,
    queryFn: () => getExperiment(selectedExperimentId!),
    queryKey: ["experiment", selectedExperimentId],
  });
  const generationsQuery = useQuery({
    enabled: selectedExperimentId !== null,
    queryFn: () => getGenerations(selectedExperimentId!),
    queryKey: ["generations", selectedExperimentId],
  });
  const analysisQuery = useQuery({
    enabled: selectedExperimentId !== null,
    queryFn: () => getExperimentAnalysis(selectedExperimentId!),
    queryKey: ["analysis", selectedExperimentId],
  });

  useEffect(() => {
    const experiments = experimentsQuery.data;
    if (experiments === undefined) {
      return;
    }

    if (
      selectedExperimentId !== null
      && experiments.some((experiment) => experiment.id === selectedExperimentId)
    ) {
      return;
    }

    setSelectedExperimentId(defaultExperimentId(experiments));
    setSelectedGenerationId(null);
  }, [experimentsQuery.data, selectedExperimentId]);

  useEffect(() => {
    const generations = generationsQuery.data;
    if (generations === undefined) {
      return;
    }

    if (
      selectedGenerationId !== null
      && generations.some((generation) => generation.game_id === selectedGenerationId)
    ) {
      return;
    }

    setSelectedGenerationId(generations.at(-1)?.game_id ?? null);
  }, [generationsQuery.data, selectedGenerationId]);

  useEffect(() => {
    if (toast === null) {
      return undefined;
    }

    const timeout = window.setTimeout(() => setToast(null), 5_000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const createMutation = useMutation({
    mutationFn: createExperiment,
    onSuccess: async (experiment) => {
      setSelectedExperimentId(experiment.id);
      setSelectedGenerationId(null);
      setExperienceMode("watch");
      setDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["experiments"] });
      setToast({ isError: false, message: "Experiment created. The arena is ready." });
    },
  });

  const runMutation = useMutation({
    mutationFn: (experimentId: number) => runGeneration(experimentId),
    retry: false,
    onSuccess: async (results) => {
      const savedGeneration = results[0];
      if (savedGeneration !== undefined) {
        setSelectedGenerationId(savedGeneration.game_id);
      }

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["experiments"] }),
        queryClient.invalidateQueries({ queryKey: ["experiment", selectedExperimentId] }),
        queryClient.invalidateQueries({ queryKey: ["generations", selectedExperimentId] }),
        queryClient.invalidateQueries({ queryKey: ["analysis", selectedExperimentId] }),
        queryClient.invalidateQueries({ queryKey: ["generation", savedGeneration?.game_id] }),
      ]);
      setExperienceMode("watch");
      setToast({ isError: false, message: "Generation completed. Starting the arena replay." });
    },
  });

  const experiment = experimentQuery.data;
  const analysis = analysisQuery.data;
  const generations = generationsQuery.data ?? [];
  const agentNames = useAgentNames(experiment, analysis?.agent_performance);
  const isBusy = createMutation.isPending || runMutation.isPending;
  const hasLoadError =
    experimentsQuery.isError
    || experimentQuery.isError
    || generationsQuery.isError
    || analysisQuery.isError;
  const connection = getConnectionState({
    hasLoadError,
    isBusy,
    isFetching:
      experimentsQuery.isFetching
      || experimentQuery.isFetching
      || generationsQuery.isFetching
      || analysisQuery.isFetching,
  });

  async function refresh() {
    try {
      await Promise.all([
        experimentsQuery.refetch(),
        experimentQuery.refetch(),
        generationsQuery.refetch(),
        analysisQuery.refetch(),
      ]);
      setToast({ isError: false, message: "Experiment data refreshed." });
    } catch (error) {
      setToast({ isError: true, message: errorMessage(error) });
    }
  }

  async function handleCreate(name: string) {
    await createMutation.mutateAsync(name);
  }

  async function handleRun() {
    if (selectedExperimentId === null) {
      return;
    }

    try {
      await runMutation.mutateAsync(selectedExperimentId);
    } catch (error) {
      setToast({ isError: true, message: errorMessage(error) });
    }
  }

  function selectExperiment(experimentId: number) {
    setSelectedExperimentId(experimentId);
    setSelectedGenerationId(null);
    setExperienceMode("watch");
  }

  return (
    <Tooltip.Provider delayDuration={250}>
      <div className="app-shell">
        <header className="topbar">
          <a className="brand" href="/" aria-label="AI Hunger Games dashboard">
            <span className="brand-mark" aria-hidden="true">
              <span /><span /><span />
            </span>
            <span>
              <span className="eyebrow">Capitol broadcast system</span>
              <strong>AI Hunger Games</strong><small className="brand-motto">Only one model survives</small>
            </span>
          </a>
          <div className="topbar-actions">
            <span className={`connection-state ${connection.className}`.trim()}>
              <Wifi aria-hidden="true" size={13} strokeWidth={2} />
              {connection.label}
            </span>
            <IconButton disabled={isBusy} label="Refresh experiment data" onClick={() => void refresh()}>
              <RefreshCw aria-hidden="true" className={connection.isFetching ? "spin" : undefined} size={17} />
            </IconButton>
            <button className="primary-button" disabled={isBusy} onClick={() => setDialogOpen(true)} type="button">
              <Plus aria-hidden="true" size={15} />
              New experiment
            </button>
          </div>
        </header>

        <div className="workspace">
          <ExperimentSidebar
            experiments={experimentsQuery.data ?? []}
            isBusy={isBusy}
            onSelect={selectExperiment}
            selectedExperimentId={selectedExperimentId}
          />
          <main className="content">
            {experimentsQuery.isPending ? (
              <LoadingState />
            ) : selectedExperimentId === null ? (
              <EmptyState isBusy={isBusy} onNewExperiment={() => setDialogOpen(true)} />
            ) : hasLoadError ? (
              <ErrorState
                message={firstErrorMessage([
                  experimentsQuery.error,
                  experimentQuery.error,
                  generationsQuery.error,
                  analysisQuery.error,
                ])}
                onRetry={() => void refresh()}
              />
            ) : experiment === undefined || analysis === undefined ? (
              <LoadingState />
            ) : (
              <ExperimentView
                agentName={(agentId) => agentNames.get(agentId) ?? agentId}
                analysis={analysis}
                analysisTab={analysisTab}
                experienceMode={experienceMode}
                experiment={experiment}
                generations={generations}
                isRunning={runMutation.isPending}
                onAnalysisTabChange={setAnalysisTab}
                onExperienceModeChange={setExperienceMode}
                onRun={() => void handleRun()}
                onSelectedGenerationChange={setSelectedGenerationId}
                selectedGenerationId={selectedGenerationId}
              />
            )}
          </main>
        </div>

        {toast !== null && (
          <div className={`toast${toast.isError ? " is-error" : ""}`} role="status">
            {toast.message}
          </div>
        )}
        <NewExperimentDialog
          isOpen={dialogOpen}
          isPending={createMutation.isPending}
          onCreate={handleCreate}
          onOpenChange={setDialogOpen}
        />
      </div>
    </Tooltip.Provider>
  );
}

function ExperimentView({
  agentName,
  analysis,
  analysisTab,
  experienceMode,
  experiment,
  generations,
  isRunning,
  onAnalysisTabChange,
  onExperienceModeChange,
  onRun,
  onSelectedGenerationChange,
  selectedGenerationId,
}: {
  agentName: (agentId: string) => string;
  analysis: ExperimentAnalysis;
  analysisTab: AnalysisTab;
  experienceMode: ExperienceMode;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  isRunning: boolean;
  onAnalysisTabChange: (tab: AnalysisTab) => void;
  onExperienceModeChange: (mode: ExperienceMode) => void;
  onRun: () => void;
  onSelectedGenerationChange: (gameId: number | null) => void;
  selectedGenerationId: number | null;
}) {
  const metadata = [
    experiment.provider_name ?? "Provider configuration unavailable",
    `Created ${formatDate(experiment.created_at)}`,
    experiment.run_block_reason,
  ].filter((value): value is string => value !== null);

  return (
    <>
      <section className="experiment-header" aria-labelledby="experiment-name">
        <div>
          <p className="eyebrow">Current season</p>
          <h1 id="experiment-name">{experiment.name}</h1>
          <p className="metadata">{metadata.join(" · ")}</p>
        </div>
        <div className="run-controls">
          <span className="run-count">Next arena: generation {experiment.generation_count + 1}</span>
          <button className="primary-button" disabled={isRunning || !experiment.can_run} onClick={onRun} type="button">
            <Play aria-hidden="true" size={15} />
            {isRunning ? "Broadcasting" : "Begin next arena"}
          </button>
        </div>
      </section>

      {isRunning && <RunProgress />}

      <div className="experience-switcher" role="tablist" aria-label="Experience mode">
        {experienceModes.map((mode) => {
          const Icon = mode.icon;
          const active = experienceMode === mode.value;
          return (
            <button
              aria-selected={active}
              className={`experience-mode${active ? " is-active" : ""}`}
              key={mode.value}
              onClick={() => onExperienceModeChange(mode.value)}
              role="tab"
              type="button"
            >
              <Icon aria-hidden="true" size={17} />
              <span>{mode.label}</span>
            </button>
          );
        })}
      </div>

      {experienceMode === "watch" || experienceMode === "replay" ? (
        <ArenaView
          agentName={agentName}
          experiment={experiment}
          generations={generations}
          isRunning={isRunning}
          mode={experienceMode as ArenaMode}
          onRun={onRun}
          onSelectedGenerationChange={onSelectedGenerationChange}
          selectedGenerationId={selectedGenerationId}
        />
      ) : (
        <AnalyzeView
          agentName={agentName}
          analysis={analysis}
          analysisTab={analysisTab}
          experiment={experiment}
          generations={generations}
          onAnalysisTabChange={onAnalysisTabChange}
          onSelectedGenerationChange={onSelectedGenerationChange}
          selectedGenerationId={selectedGenerationId}
        />
      )}
    </>
  );
}

function AnalyzeView({
  agentName,
  analysis,
  analysisTab,
  experiment,
  generations,
  onAnalysisTabChange,
  onSelectedGenerationChange,
  selectedGenerationId,
}: {
  agentName: (agentId: string) => string;
  analysis: ExperimentAnalysis;
  analysisTab: AnalysisTab;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  onAnalysisTabChange: (tab: AnalysisTab) => void;
  onSelectedGenerationChange: (gameId: number | null) => void;
  selectedGenerationId: number | null;
}) {
  return (
    <Tabs.Root
      onValueChange={(value) => {
        if (isAnalysisTab(value)) {
          onAnalysisTabChange(value);
        }
      }}
      value={analysisTab}
    >
      <Tabs.List aria-label="Analysis views" className="view-tabs">
        {analysisTabs.map((tab) => (
          <Tabs.Trigger className="view-tab" key={tab.value} value={tab.value}>
            {tab.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      <Tabs.Content value="overview">
        <Suspense fallback={<TabLoading />}>
          <OverviewTab agentName={agentName} analysis={analysis} experiment={experiment} generations={generations} />
        </Suspense>
      </Tabs.Content>
      <Tabs.Content value="rounds">
        <Suspense fallback={<TabLoading />}>
          <RoundsTab
            agentName={agentName}
            generations={generations}
            onSelectedGenerationChange={onSelectedGenerationChange}
            selectedGenerationId={selectedGenerationId}
          />
        </Suspense>
      </Tabs.Content>
      <Tabs.Content value="relationships">
        <Suspense fallback={<TabLoading />}>
          <RelationshipsTab agentName={agentName} analysis={analysis} />
        </Suspense>
      </Tabs.Content>
      <Tabs.Content value="lineage">
        <Suspense fallback={<TabLoading />}>
          <LineageTab agentName={agentName} analysis={analysis} generations={generations} />
        </Suspense>
      </Tabs.Content>
      <Tabs.Content value="showcase">
        <Suspense fallback={<TabLoading />}>
          <ShowcaseTab
            agentName={agentName}
            analysis={analysis}
            experiment={experiment}
            generations={generations}
            onTabChange={(destination) => {
              onAnalysisTabChange(destination === "overview" ? "overview" : destination);
            }}
          />
        </Suspense>
      </Tabs.Content>
    </Tabs.Root>
  );
}

function EmptyState({
  isBusy,
  onNewExperiment,
}: {
  isBusy: boolean;
  onNewExperiment: () => void;
}) {
  return (
    <section className="empty-portfolio">
      <div className="empty-portfolio-grid" aria-hidden="true" />
      <span className="hero-badge">Capitol spectator console</span>
      <p className="eyebrow">Ceremonial multi-agent broadcast</p>
      <h1>Enter the arena. Watch intelligence compete.</h1>
      <p>
        Create a local simulated experiment, run one generation, and replay
        anonymous answers, named votes, elimination, and replacement as a visual show.
      </p>
      <div className="empty-actions">
        <button className="primary-button" disabled={isBusy} onClick={onNewExperiment} type="button">
          <Plus aria-hidden="true" size={15} />
          Create experiment
        </button>
        <a className="secondary-button link-button" href="https://github.com/Anugrah-Singh/ai-hunger-games" rel="noreferrer" target="_blank">
          View source
        </a>
      </div>
      <div className="empty-proof-grid">
        <article><Eye aria-hidden="true" size={20} /><strong>Watch</strong><span>Animated arena</span></article>
        <article><RotateCcw aria-hidden="true" size={20} /><strong>Replay</strong><span>Scene controls</span></article>
        <article><BarChart3 aria-hidden="true" size={20} /><strong>Analyze</strong><span>Research dashboard</span></article>
        <article><strong>8 × 8</strong><span>Agents and rounds</span></article>
      </div>
    </section>
  );
}

function TabLoading() {
  return (
    <section className="view-panel" aria-live="polite">
      <p className="loading-label">Loading view</p>
    </section>
  );
}

function useAgentNames(
  experiment: ExperimentDetail | undefined,
  agentPerformance: { agent_id: string; agent_name: string }[] | undefined,
) {
  return useMemo(() => {
    const names = new Map<string, string>();
    for (const agent of agentPerformance ?? []) {
      names.set(agent.agent_id, agent.agent_name);
    }
    for (const agent of experiment?.current_population ?? []) {
      names.set(agent.agent_id, agent.agent_name);
    }
    return names;
  }, [agentPerformance, experiment?.current_population]);
}

function getConnectionState({
  hasLoadError,
  isBusy,
  isFetching,
}: {
  hasLoadError: boolean;
  isBusy: boolean;
  isFetching: boolean;
}) {
  if (isBusy) {
    return { className: "", isFetching: true, label: "Working" };
  }
  if (hasLoadError) {
    return { className: "is-error", isFetching: false, label: "Unavailable" };
  }
  if (isFetching) {
    return { className: "", isFetching: true, label: "Refreshing" };
  }
  return { className: "is-ready", isFetching: false, label: "Connected" };
}

function firstErrorMessage(errors: unknown[]): string {
  const error = errors.find((candidate) => candidate !== null);
  return errorMessage(error);
}

function isAnalysisTab(value: string): value is AnalysisTab {
  return analysisTabs.some((tab) => tab.value === value);
}
