import { FlaskConical } from "lucide-react";

import type { ExperimentSummary } from "../api/types";
import { formatDate } from "../lib/format";
import { Placeholder } from "./common";


interface ExperimentSidebarProps {
  experiments: ExperimentSummary[];
  isBusy: boolean;
  selectedExperimentId: number | null;
  onSelect: (experimentId: number) => void;
}


export function ExperimentSidebar({
  experiments,
  isBusy,
  selectedExperimentId,
  onSelect,
}: ExperimentSidebarProps) {
  return (
    <aside className="experiment-sidebar" aria-label="Experiments">
      <div className="sidebar-heading">
        <h2>Experiments</h2>
        <span className="count-badge">{experiments.length}</span>
      </div>
      <div className="experiment-list">
        {experiments.length === 0 ? (
          <Placeholder>No experiments</Placeholder>
        ) : (
          experiments.map((experiment) => {
            const isActive = experiment.id === selectedExperimentId;
            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className={`experiment-item${isActive ? " is-active" : ""}`}
                disabled={isBusy}
                key={experiment.id}
                onClick={() => onSelect(experiment.id)}
                type="button"
              >
                <span className="experiment-number">
                  {String(experiment.id).padStart(2, "0")}
                </span>
                <span>
                  <strong>{experiment.name}</strong>
                  <span>{formatDate(experiment.created_at)}</span>
                </span>
              </button>
            );
          })
        )}
      </div>
      <div className="sidebar-footer" aria-hidden="true">
        <FlaskConical size={15} strokeWidth={1.8} />
        <span>Persisted experiment history</span>
      </div>
    </aside>
  );
}
