import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  ExperimentAnalysis,
  ExperimentDetail,
  GenerationSummary,
} from "../api/types";
import { ShowcaseTab } from "./ShowcaseTab";


const experiment: ExperimentDetail = {
  can_run: true,
  created_at: "2026-07-18T00:00:00Z",
  current_population: [
    {
      agent_id: "agent_2",
      agent_name: "Scientist",
      personality: {
        answer_template: "Answer {question}",
        description: "Tests evidence before claiming a result.",
        name: "Evidence-driven scientist",
      },
    },
  ],
  generation_count: 3,
  id: 8,
  name: "Recruiter review",
  provider_name: "Simulated providers",
  run_block_reason: null,
};


const generations: GenerationSummary[] = [
  {
    created_at: "2026-07-18T00:00:00Z",
    eliminated_agent_id: "agent_1",
    game_id: 42,
    generation_number: 3,
    provider_name: "Simulated providers",
    replacement_agent: {
      agent_id: "agent_9",
      agent_name: "Replacement",
      personality: {
        answer_template: "Answer {question}",
        description: "Tests alternate strategies.",
        name: "First-principles engineer",
      },
    },
    round_count: 4,
    seeds: {
      candidate_order_seed: 1,
      elimination_seed: 3,
      replacement_seed: 4,
      voting_seed: 2,
    },
  },
];


const analysis: ExperimentAnalysis = {
  agent_performance: [],
  cautions: [
    "The current data is descriptive and does not establish a durable voting bloc.",
  ],
  entry_adjacent_changes: [],
  experiment_id: experiment.id,
  experiment_name: experiment.name,
  generation_count: experiment.generation_count,
  personality_diversity: {
    distinct_instruction_count: 1,
    distinct_instruction_rate: 1,
    distinct_name_count: 1,
    distinct_name_rate: 1,
    generated_personality_count: 1,
  },
  personality_performance: [],
  possible_voting_bloc_indicators: [],
  reciprocal_vote_indicators: [],
  replacement_outcomes: [],
  vote_relationships: [],
};


describe("ShowcaseTab", () => {
  it("presents persisted evidence and routes into the live dashboard", async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();

    render(
      <ShowcaseTab
        agentName={(agentId) => (agentId === "agent_1" ? "Auditor" : agentId)}
        analysis={analysis}
        experiment={experiment}
        generations={generations}
        onTabChange={onTabChange}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "AI Hunger Games" }),
    ).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("Auditor")).toBeInTheDocument();
    expect(
      screen.getByText("Replacement (First-principles engineer)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "The current data is descriptive and does not establish a durable voting bloc.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("agent_1")).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Explore live experiment" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Inspect anonymous rounds" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Compare voting signals" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Trace replacement lineage" }),
    );

    expect(onTabChange).toHaveBeenNthCalledWith(1, "overview");
    expect(onTabChange).toHaveBeenNthCalledWith(2, "rounds");
    expect(onTabChange).toHaveBeenNthCalledWith(3, "relationships");
    expect(onTabChange).toHaveBeenNthCalledWith(4, "lineage");
  });
});
