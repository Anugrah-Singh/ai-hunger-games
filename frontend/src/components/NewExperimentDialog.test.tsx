import { render } from "@testing-library/react";
import { screen } from "@testing-library/dom";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NewExperimentDialog } from "./NewExperimentDialog";


describe("NewExperimentDialog", () => {
  it("submits a trimmed experiment name", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(undefined);

    render(
      <NewExperimentDialog
        isOpen
        isPending={false}
        onCreate={onCreate}
        onOpenChange={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("Name"), "  Fresh baseline  ");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(onCreate).toHaveBeenCalledWith("Fresh baseline");
  });

  it("shows a local validation error without making a request", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();

    render(
      <NewExperimentDialog
        isOpen
        isPending={false}
        onCreate={onCreate}
        onOpenChange={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Enter an experiment name.",
    );
    expect(onCreate).not.toHaveBeenCalled();
  });
});
