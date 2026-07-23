import { screen } from "@testing-library/dom";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { NewExperimentDialog } from "./NewExperimentDialog";

describe("NewExperimentDialog", () => {
  it(
    "submits a trimmed name with the quick demo preset by default",
    async () => {
      const user = userEvent.setup();
      const onCreate =
        vi.fn().mockResolvedValue(undefined);

      render(
        <NewExperimentDialog
          isOpen
          isPending={false}
          onCreate={onCreate}
          onOpenChange={vi.fn()}
        />,
      );

      await user.type(
        screen.getByLabelText("Name"),
        "  Fresh baseline  ",
      );

      await user.click(
        screen.getByRole("button", {
          name: "Create",
        }),
      );

      expect(onCreate).toHaveBeenCalledWith({
        name: "Fresh baseline",
        preset: "quick_demo",
      });
    },
  );

  it(
    "submits the full tournament preset when selected",
    async () => {
      const user = userEvent.setup();
      const onCreate =
        vi.fn().mockResolvedValue(undefined);

      render(
        <NewExperimentDialog
          isOpen
          isPending={false}
          onCreate={onCreate}
          onOpenChange={vi.fn()}
        />,
      );

      await user.type(
        screen.getByLabelText("Name"),
        "Full benchmark",
      );

      await user.click(
        screen.getByRole("radio", {
          name: /Full Tournament/i,
        }),
      );

      await user.click(
        screen.getByRole("button", {
          name: "Create",
        }),
      );

      expect(onCreate).toHaveBeenCalledWith({
        name: "Full benchmark",
        preset: "full_tournament",
      });
    },
  );

  it(
    "shows a local validation error without making a request",
    async () => {
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

      await user.click(
        screen.getByRole("button", {
          name: "Create",
        }),
      );

      expect(
        await screen.findByRole("alert"),
      ).toHaveTextContent(
        "Enter an experiment name.",
      );

      expect(onCreate).not.toHaveBeenCalled();
    },
  );
});