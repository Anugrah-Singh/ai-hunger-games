import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Play, Plus, RefreshCw, Wifi } from "lucide-react";
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
import { ExperimentSidebar } from "./components/ExperimentSidebar";
import { NewExperimentDialog } from "./components/NewExperimentDialog";
import {
  ErrorState,
  IconButton,
  LoadingState,
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


const viewTabs = [
  { label: "Overview", value: "overview" },
  { label: "Rounds", value: "rounds" },
  { label: "Relationships", value: "relationships" },
  { label: "Lineage", value: "lineage" },
] as const;

type ViewTab = (typeof viewTabs)[number]["value"];


interface ToastState {
  isError: boolean;
  message: string;
}


export function App() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ViewTab>("overview");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | null>(
    null,
  );
  const [selectedGenerationId, setSelectedGenerationId] = useState<number | null>(
    null,
  );
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
      setDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["experiments"] });
      setToast({ isError: false, message: "Experiment created." });
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
        queryClient.invalidateQueries({
          queryKey: ["experiment", selectedExperimentId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["generations", selectedExperimentId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["analysis", selectedExperimentId],
        }),
      ]);
      setToast({ isError: false, message: "Generation completed and saved." });
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
    setActiveTab("overview");
  }

  return (
    <Tooltip.Provider delayDuration={250}>
      <div className="app-shell">
        <header className="topbar">
          <a className="brand" href="/" aria-label="AI Hunger Games dashboard">
            <img alt="Abstract eight-seat arena" src="/static/arena-mark.png" />
            <span>
              <span className="eyebrow">Multi-agent experiment</span>
              <strong>AI Hunger Games</strong>
            </span>
          </a>
          <div className="topbar-actions">
            <span className={`connection-state ${connection.className}`.trim()}>
              <Wifi aria-hidden="true" size={13} strokeWidth={2} />
              {connection.label}
            </span>
            <IconButton
              disabled={isBusy}
              label="Refresh experiment data"
              onClick={() => void refresh()}
            >
              <RefreshCw
                aria-hidden="true"
                className={connection.isFetching ? "spin" : undefined}
                size={17}
              />
            </IconButton>
            <button
              className="primary-button"
              disabled={isBusy}
              onClick={() => setDialogOpen(true)}
              type="button"
            >
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
              <EmptyState
                isBusy={isBusy}
                onNewExperiment={() => setDialogOpen(true)}
              />
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
                activeTab={activeTab}
                agentName={(agentId) => agentNames.get(agentId) ?? agentId}
                analysis={analysis}
                experiment={experiment}
                generations={generations}
                isRunning={runMutation.isPending}
                onRun={() => void handleRun()}
                onTabChange={setActiveTab}
                onSelectedGenerationChange={setSelectedGenerationId}
                selectedGenerationId={selectedGenerationId}
              />
            )}
          </main>
        </div>
        {toast !== null && (
          <div
            className={`toast${toast.isError ? " is-error" : ""}`}
            role="status"
          >
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
  activeTab,
  agentName,
  analysis,
  experiment,
  generations,
  isRunning,
  onRun,
  onSelectedGenerationChange,
  onTabChange,
  selectedGenerationId,
}: {
  activeTab: ViewTab;
  agentName: (agentId: string) => string;
  analysis: ExperimentAnalysis;
  experiment: ExperimentDetail;
  generations: GenerationSummary[];
  isRunning: boolean;
  onRun: () => void;
  onSelectedGenerationChange: (gameId: number | null) => void;
  onTabChange: (view: ViewTab) => void;
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
          <p className="eyebrow">Selected experiment</p>
          <h1 id="experiment-name">{experiment.name}</h1>
          <p className="metadata">{metadata.join(" | ")}</p>
        </div>
        <div className="run-controls">
          <span className="run-count">1 generation</span>
          <button
            className="primary-button"
            disabled={isRunning || !experiment.can_run}
            onClick={onRun}
            type="button"
          >
            <Play aria-hidden="true" size={15} />
            {isRunning ? "Running" : "Run"}
          </button>
        </div>
      </section>

      <Tabs.Root
        onValueChange={(value) => {
          if (isViewTab(value)) {
            onTabChange(value);
          }
        }}
        value={activeTab}
      >
        <Tabs.List aria-label="Experiment views" className="view-tabs">
          {viewTabs.map((tab) => (
            <Tabs.Trigger className="view-tab" key={tab.value} value={tab.value}>
              {tab.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        <Tabs.Content value="overview">
          <Suspense fallback={<TabLoading />}>
            <OverviewTab
              agentName={agentName}
              analysis={analysis}
              experiment={experiment}
              generations={generations}
            />
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
            <LineageTab
              agentName={agentName}
              analysis={analysis}
              generations={generations}
            />
          </Suspense>
        </Tabs.Content>
      </Tabs.Root>
    </>
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
    <section className="empty-state">
      <h1>No experiment selected</h1>
      <button
        className="primary-button"
        disabled={isBusy}
        onClick={onNewExperiment}
        type="button"
      >
        <Plus aria-hidden="true" size={15} />
        New experiment
      </button>
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


function isViewTab(value: string): value is ViewTab {
  return viewTabs.some((tab) => tab.value === value);
}
