import type {
  CandidateScore,
  GenerationDetail,
  Personality,
} from "../api/types";

export type ArenaScene =
  | {
      id: string;
      type: "generation-intro";
      generationNumber: number;
      title: string;
    }
  | {
      id: string;
      type: "round-intro";
      roundNumber: number;
      question: string;
    }
  | {
      id: string;
      type: "candidate";
      roundNumber: number;
      candidateId: string;
      content: string;
      attemptCount: number;
    }
  | {
      id: string;
      type: "vote";
      roundNumber: number;
      voterAgentId: string;
      selectedCandidateId: string;
    }
  | {
      id: string;
      type: "round-result";
      roundNumber: number;
      scores: CandidateScore[];
    }
  | {
      id: string;
      type: "elimination";
      eliminatedAgentId: string;
    }
  | {
      id: string;
      type: "replacement";
      replacementAgentId: string;
      replacementAgentName: string;
      personality: Personality;
    }
  | {
      id: string;
      type: "generation-complete";
      generationNumber: number;
    };

export function createArenaScenes(
  generation: GenerationDetail,
): ArenaScene[] {
  const scenes: ArenaScene[] = [
    {
      id: `generation:${generation.game_id}:intro`,
      type: "generation-intro",
      generationNumber: generation.generation_number,
      title: `Generation ${generation.generation_number} enters the arena`,
    },
  ];

  for (const round of generation.rounds) {
    scenes.push({
      id: `round:${round.round_id}:intro`,
      type: "round-intro",
      roundNumber: round.round_number,
      question: round.question,
    });

    for (const answer of round.answers) {
      scenes.push({
        id: `round:${round.round_id}:candidate:${answer.candidate_id}`,
        type: "candidate",
        roundNumber: round.round_number,
        candidateId: answer.candidate_id,
        content: answer.content,
        attemptCount: answer.attempt_count,
      });
    }

    for (const vote of round.votes) {
      scenes.push({
        id: `round:${round.round_id}:vote:${vote.voter_agent_id}`,
        type: "vote",
        roundNumber: round.round_number,
        voterAgentId: vote.voter_agent_id,
        selectedCandidateId: vote.selected_candidate_id,
      });
    }

    scenes.push({
      id: `round:${round.round_id}:result`,
      type: "round-result",
      roundNumber: round.round_number,
      scores: [...round.scores].sort(
        (first, second) => second.score - first.score,
      ),
    });
  }

  scenes.push(
    {
      id: `generation:${generation.game_id}:elimination`,
      type: "elimination",
      eliminatedAgentId: generation.eliminated_agent_id,
    },
    {
      id: `generation:${generation.game_id}:replacement`,
      type: "replacement",
      replacementAgentId: generation.replacement_agent.agent_id,
      replacementAgentName: generation.replacement_agent.agent_name,
      personality: generation.replacement_agent.personality,
    },
    {
      id: `generation:${generation.game_id}:complete`,
      type: "generation-complete",
      generationNumber: generation.generation_number,
    },
  );

  return scenes;
}

export function sceneLabel(scene: ArenaScene): string {
  switch (scene.type) {
    case "generation-intro":
      return "Generation begins";
    case "round-intro":
      return `Round ${scene.roundNumber}: question`;
    case "candidate":
      return `Round ${scene.roundNumber}: anonymous answer`;
    case "vote":
      return `Round ${scene.roundNumber}: vote`;
    case "round-result":
      return `Round ${scene.roundNumber}: result`;
    case "elimination":
      return "Elimination";
    case "replacement":
      return "New challenger";
    case "generation-complete":
      return "Generation complete";
  }
}

export function sceneDelayMilliseconds(scene: ArenaScene): number {
  switch (scene.type) {
    case "candidate":
      return 7_000;
    case "round-intro":
      return 4_500;
    case "round-result":
    case "elimination":
    case "replacement":
      return 5_000;
    default:
      return 3_000;
  }
}
