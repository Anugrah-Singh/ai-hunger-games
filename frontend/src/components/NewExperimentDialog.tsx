import {
  type FormEvent,
  useEffect,
  useId,
  useState,
} from "react";
import {
  Gauge,
  Plus,
  Trophy,
  X,
} from "lucide-react";
import { Dialog } from "radix-ui";

import type {
  CreateExperimentInput,
  ExperimentPreset,
} from "../api/types";
import { errorMessage } from "../lib/format";

interface NewExperimentDialogProps {
  isOpen: boolean;
  isPending: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onCreate: (
    input: CreateExperimentInput,
  ) => Promise<void>;
}

interface PresetOption {
  agentCount: number;
  description: string;
  estimatedTime: string;
  label: string;
  roundCount: number;
  value: ExperimentPreset;
}

const presetOptions: PresetOption[] = [
  {
    agentCount: 4,
    description:
      "Runs the complete tournament loop with fewer model calls. Recommended for live demos.",
    estimatedTime: "About 1–3 minutes",
    label: "Quick Demo",
    roundCount: 3,
    value: "quick_demo",
  },
  {
    agentCount: 8,
    description:
      "Runs the full benchmark configuration with all personalities and questions.",
    estimatedTime: "May take 15–25 minutes",
    label: "Full Tournament",
    roundCount: 8,
    value: "full_tournament",
  },
];

const defaultPreset: ExperimentPreset = "quick_demo";

export function NewExperimentDialog({
  isOpen,
  isPending,
  onOpenChange,
  onCreate,
}: NewExperimentDialogProps) {
  const inputId = useId();
  const errorId = useId();

  const [name, setName] = useState("");
  const [preset, setPreset] =
    useState<ExperimentPreset>(defaultPreset);
  const [formError, setFormError] =
    useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setName("");
      setPreset(defaultPreset);
      setFormError(null);
    }
  }, [isOpen]);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedName = name.trim();

    if (!normalizedName) {
      setFormError("Enter an experiment name.");
      return;
    }

    try {
      setFormError(null);

      await onCreate({
        name: normalizedName,
        preset,
      });
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  return (
    <Dialog.Root
      onOpenChange={onOpenChange}
      open={isOpen}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />

        <Dialog.Content className="dialog-content">
          <form onSubmit={handleSubmit}>
            <div className="dialog-heading">
              <div>
                <Dialog.Title>
                  New experiment
                </Dialog.Title>

                <Dialog.Description className="dialog-description">
                  Choose a fast recruiter demo or the complete
                  benchmark tournament.
                </Dialog.Description>
              </div>

              <Dialog.Close asChild>
                <button
                  aria-label="Close dialog"
                  className="icon-button"
                  disabled={isPending}
                  type="button"
                >
                  <X
                    aria-hidden="true"
                    size={17}
                  />
                </button>
              </Dialog.Close>
            </div>

            <label htmlFor={inputId}>
              Name
            </label>

            <input
              aria-describedby={
                formError ? errorId : undefined
              }
              autoFocus
              disabled={isPending}
              id={inputId}
              maxLength={200}
              onChange={(event) =>
                setName(event.target.value)
              }
              value={name}
            />

            <fieldset
              className="preset-fieldset"
              disabled={isPending}
            >
              <legend>
                Tournament preset
              </legend>

              <div className="preset-options">
                {presetOptions.map((option) => {
                  const isSelected =
                    option.value === preset;

                  const Icon =
                    option.value === "quick_demo"
                      ? Gauge
                      : Trophy;

                  return (
                    <label
                      className={
                        `preset-option${
                          isSelected
                            ? " is-selected"
                            : ""
                        }`
                      }
                      key={option.value}
                    >
                      <input
                        checked={isSelected}
                        name="preset"
                        onChange={() =>
                          setPreset(option.value)
                        }
                        type="radio"
                        value={option.value}
                      />

                      <span className="preset-option-icon">
                        <Icon
                          aria-hidden="true"
                          size={19}
                        />
                      </span>

                      <span className="preset-option-copy">
                        <span className="preset-option-heading">
                          <strong>
                            {option.label}
                          </strong>

                          {option.value ===
                            "quick_demo" && (
                            <span className="recommended-badge">
                              Recommended
                            </span>
                          )}
                        </span>

                        <span>
                          {option.agentCount} agents ·{" "}
                          {option.roundCount} rounds
                        </span>

                        <small>
                          {option.description}
                        </small>

                        <small className="preset-duration">
                          {option.estimatedTime}
                        </small>
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <p
              className="form-error"
              id={errorId}
              role="alert"
            >
              {formError}
            </p>

            <div className="dialog-actions">
              <Dialog.Close asChild>
                <button
                  className="secondary-button"
                  disabled={isPending}
                  type="button"
                >
                  Cancel
                </button>
              </Dialog.Close>

              <button
                className="primary-button"
                disabled={isPending}
                type="submit"
              >
                <Plus
                  aria-hidden="true"
                  size={15}
                />

                {isPending
                  ? "Creating"
                  : "Create"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}