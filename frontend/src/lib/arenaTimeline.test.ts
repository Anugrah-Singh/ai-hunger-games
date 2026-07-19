import { describe, expect, it } from "vitest";

import type { GenerationDetail } from "../api/types";
import { createArenaScenes } from "./arenaTimeline";

const generation: GenerationDetail = {
  game_id: 42,
  generation_number: 2,
  provider_name: "Simulated providers",
  created_at: "2026-07-19T00:00:00Z",
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
    agent_name: "Systems Critic",
    personality: {
      name: "Systems Critic",
      description: "Looks for hidden feedback loops.",
      answer_template: "Analyze {question}",
    },
  },
  starting_agents: [],
  final_agents: [],
  rounds: [
    {
      round_id: 7,
      round_number: 1,
      question: "What makes a team resilient?",
      answers: [
        {
          candidate_id: "candidate_1",
          content: "An anonymous answer.",
          attempt_count: 1,
        },
      ],
      votes: [
        {
          voter_agent_id: "agent_2",
          selected_candidate_id: "candidate_1",
        },
      ],
      scores: [{ candidate_id: "candidate_1", score: 1 }],
      failures: [],
    },
  ],
};

describe("createArenaScenes", () => {
  it("creates an honest replay without attaching authors to anonymous answers", () => {
    const scenes = createArenaScenes(generation);
    const candidateScene = scenes.find((scene) => scene.type === "candidate");

    expect(candidateScene).toEqual(
      expect.objectContaining({
        candidateId: "candidate_1",
        content: "An anonymous answer.",
      }),
    );
    expect(candidateScene).not.toHaveProperty("agentId");
    expect(scenes.map((scene) => scene.type)).toEqual([
      "generation-intro",
      "round-intro",
      "candidate",
      "vote",
      "round-result",
      "elimination",
      "replacement",
      "generation-complete",
    ]);
  });
});
