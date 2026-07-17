import { FormEvent, useEffect, useId, useState } from "react";
import { Dialog } from "radix-ui";
import { Plus, X } from "lucide-react";

import { errorMessage } from "../lib/format";


interface NewExperimentDialogProps {
  isOpen: boolean;
  isPending: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onCreate: (name: string) => Promise<void>;
}


export function NewExperimentDialog({
  isOpen,
  isPending,
  onOpenChange,
  onCreate,
}: NewExperimentDialogProps) {
  const inputId = useId();
  const errorId = useId();
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setName("");
      setFormError(null);
    }
  }, [isOpen]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = name.trim();

    if (!normalizedName) {
      setFormError("Enter an experiment name.");
      return;
    }

    try {
      setFormError(null);
      await onCreate(normalizedName);
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={isOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <form onSubmit={handleSubmit}>
            <div className="dialog-heading">
              <div>
                <Dialog.Title>New experiment</Dialog.Title>
                <Dialog.Description className="dialog-description">
                  Start from the saved eight-agent baseline.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button
                  aria-label="Close dialog"
                  className="icon-button"
                  disabled={isPending}
                  type="button"
                >
                  <X aria-hidden="true" size={17} />
                </button>
              </Dialog.Close>
            </div>
            <label htmlFor={inputId}>Name</label>
            <input
              aria-describedby={formError ? errorId : undefined}
              autoFocus
              disabled={isPending}
              id={inputId}
              maxLength={200}
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
            <p className="form-error" id={errorId} role="alert">
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
              <button className="primary-button" disabled={isPending} type="submit">
                <Plus aria-hidden="true" size={15} />
                {isPending ? "Creating" : "Create"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
