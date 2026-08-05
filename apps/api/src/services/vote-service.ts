import type { Answer, Vote } from '@ai-hunger-games/contracts';
import type { GenerateVoteInput, LlmClient, VoteCandidate } from '../llm/types.js';
import { mapWithConcurrency } from '../utilities/concurrency.js';
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

function deterministicFallback(candidates: VoteCandidate[], voterIndex: number): VoteCandidate {
  const candidate = candidates[voterIndex % candidates.length];
  if (!candidate) throw new Error('Voting requires at least one eligible candidate');
  return candidate;
}

export class VoteService {
  public constructor(
    private readonly llm: LlmClient,
    private readonly concurrency: number,
  ) {}

  public async generate(question: string, responses: Answer[]): Promise<Vote[]> {
    return mapWithConcurrency(responses, this.concurrency, async (voter, voterIndex) => {
      const candidates = buildCandidates(responses, voter.id);
      const input: GenerateVoteInput = {
        question,
        voterId: voter.id,
        voterAnswer: voter.answer,
        candidates,
      };

      try {
        const generated = await this.llm.generateVote(input);
        const selected = candidates.find((candidate) => candidate.key === generated.candidateKey);
        if (!selected) throw new Error('The provider selected an unknown candidate');

        return {
          voter: voter.id,
          votedFor: selected.id,
          reason: normalizeReason(generated.reason),
        };
      } catch {
        const selected = deterministicFallback(candidates, voterIndex);
        return {
          voter: voter.id,
          votedFor: selected.id,
          reason: 'This answer is the least aligned with my perspective.',
        };
      }
    });
  }
}
