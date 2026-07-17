import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/dom";
import { describe, expect, it, vi } from "vitest";

import { getGeneration } from "../api/client";
import type { GenerationDetail, GenerationSummary } from "../api/types";
import { RoundsTab } from "./RoundsTab";


vi.mock("../api/client", () => ({
  getGeneration: vi.fn(),
}));


const generationSummary: GenerationSummary = {
  game_id: 42,
  generation_number: 3,
  provider_name: "Simulated providers",
  created_at: "2026-07-18T00:00:00Z",
  round_count: 1,
  seeds: {
    candidate_order_seed: 1,
    voting_seed: 2,
    elimination_seed: 3,
    replacement_seed: 4,
  },
  eliminated_agent_id: "agent_1",
  replacement_agent: {
    agent_id: "agent_9",
    agent_name: "Replacement",
    personality: {
      name: "Replacement personality",
      description: "A test replacement.",
      answer_template: "Answer {question}",
    },
  },
};


const generationDetail: GenerationDetail = {
  ...generationSummary,
  final_agents: [],
  starting_agents: [],
  rounds: [
    {
      round_id: 7,
      round_number: 1,
      question: "Which plan is strongest?",
      answers: [
        {
          candidate_id: "candidate_1",
          content: "An anonymous answer.",
          attempt_count: 1,
        },
        {
          candidate_id: "candidate_2",
          content: "Another anonymous answer.",
          attempt_count: 2,
        },
      ],
      votes: [
        {
          voter_agent_id: "agent_1",
          selected_candidate_id: "candidate_2",
        },
      ],
      scores: [
        { candidate_id: "candidate_1", score: 0 },
        { candidate_id: "candidate_2", score: 1 },
      ],
      failures: [],
    },
  ],
};


describe("RoundsTab", () => {
  it("renders candidates and scores without an author mapping", async () => {
    vi.mocked(getGeneration).mockResolvedValue(generationDetail);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RoundsTab
          agentName={(agentId) =>
            agentId === "agent_1" ? "Known voter" : agentId
          }
          generations={[generationSummary]}
          onSelectedGenerationChange={vi.fn()}
          selectedGenerationId={generationSummary.game_id}
        />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Which plan is strongest?")).toBeVisible();
    expect(screen.getAllByText("Candidate 1")).toHaveLength(2);
    expect(screen.getAllByText("Candidate 2")).toHaveLength(3);
    expect(screen.getByText("An anonymous answer.")).toBeVisible();
    expect(screen.getByText("Known voter")).toBeVisible();
    expect(screen.queryByText("agent_1")).not.toBeInTheDocument();
  });
});
