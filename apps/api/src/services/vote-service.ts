import type { Answer, PersonalityInput, Vote } from '@ai-hunger-games/contracts';
import type { LlmClient, VoteCandidate } from '../llm/types.js';
import { normalizeReason } from '../utilities/text.js';

const CANDIDATE_KEYS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

function buildCandidates(responses: Answer[], voterId: number): VoteCandidate[] {
  return responses
    .filter((response) => response.id !== voterId)
    .map((response, index) => ({
      key: CANDIDATE_KEYS[index] ?? String(index + 1),
      id: response.id,
      answer: response.answer,
    }));
}

export class VoteService {
  public constructor(
    private readonly llm: LlmClient,
    private readonly concurrency: number, // left for backwards compatibility if needed
  ) {}

  public async generate(question: string, responses: Answer[]): Promise<Vote[]> {
    if (responses.length === 0) return [];

    const votersInput = responses.map((voter) => ({
      voterId: voter.id,
      voterAnswer: voter.answer,
    }));

    // Pass all possible answers as candidates
    const candidates = responses.map((response, index) => ({
      key: CANDIDATE_KEYS[index] ?? String(index + 1),
      id: response.id,
      answer: response.answer,
    }));

    const generatedVotes = await this.llm.generateVotes({
      question,
      voters: votersInput,
      candidates,
    });

    return generatedVotes.map((gv) => {
      const selected = candidates.find((c) => c.key === gv.candidateKey);
      if (!selected) {
        throw new Error(`The provider selected an unknown candidate key: ${gv.candidateKey}`);
      }
      return {
        voter: gv.voterId,
        votedFor: selected.id,
        reason: normalizeReason(gv.reason),
      };
    });
  }

  public async generateSingle(
    question: string,
    voterId: number,
    responses: Answer[],
    voterPersonality?: PersonalityInput,
    _voterIndex: number = 0,
  ): Promise<Vote> {
    const voter = responses.find((r) => r.id === voterId);
    if (!voter) throw new Error('Voter not found in responses');

    const candidates = buildCandidates(responses, voter.id);

    const generatedVotes = await this.llm.generateVotes({
      question,
      voters: [
        {
          voterId: voter.id,
          voterAnswer: voter.answer,
          ...(voterPersonality ? { voterPersonality } : {}),
        },
      ],
      candidates,
    });

    const generated = generatedVotes[0];
    if (!generated) {
      throw new Error('Provider returned no votes for single generation');
    }

    const selected = candidates.find((candidate) => candidate.key === generated.candidateKey);
    if (!selected) {
      throw new Error(`The provider selected an unknown candidate key: ${generated.candidateKey}`);
    }

    return {
      voter: voter.id,
      votedFor: selected.id,
      reason: normalizeReason(generated.reason),
    };
  }
}
