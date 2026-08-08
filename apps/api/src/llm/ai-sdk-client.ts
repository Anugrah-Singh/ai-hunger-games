import type { PersonalityInput } from '@ai-hunger-games/contracts';
import { generateText, Output, type LanguageModel } from 'ai';
import { z } from 'zod';

import type { AppConfig } from '../config/env.js';
import type { 
  BatchedGeneratedAnswer, 
  BatchedGeneratedVote, 
  GenerateAnswersInput, 
  GenerateVotesInput, 
  LlmClient 
} from './types.js';

const batchedGeneratedAnswerSchema = z.array(z.strictObject({
  id: z.number(),
  answer: z.string().trim().min(1),
}));

const batchedGeneratedVoteSchema = z.array(z.strictObject({
  voterId: z.number(),
  candidateKey: z.string().trim().min(1).max(8),
  reason: z.string().trim().min(1).max(240),
}));

function batchedAnswerPrompt(input: GenerateAnswersInput): string {
  const personas = input.personalities
    .map((p) => `ID: ${p.id}\nName: ${p.name}\nTrait: ${p.trait}`)
    .join('\n\n');

  return [
    `Question: ${input.question}`,
    '',
    'You are a participant in a highly competitive and provocative AI debate tournament.',
    'You must generate an answer for each of the following personalities:',
    '',
    personas,
    '',
    'For each personality, you MUST fully adopt their persona and write an aggressive, heavily opinionated, and highly distinct answer.',
    '1. Write exactly two or three complete, concise sentences.',
    '2. Answer the question directly but twist your response through the absolute extreme of that specific personality\'s trait.',
    '3. Do not be generic, polite, or balanced. Be sharply opinionated.',
    '4. Do not mention the prompt, personality instructions, AI policies, or this tournament.',
    '',
    'Return a JSON array containing an object for each personality with their "id" and "answer".',
  ].join('\n');
}

function batchedVotePrompt(input: GenerateVotesInput): string {
  const options = input.candidates
    .map((candidate) => `Candidate Key: ${candidate.key}\nAnswer: ${candidate.answer}`)
    .join('\n\n');
    
  const voters = input.voters
    .map((voter) => `Voter ID: ${voter.voterId}\nVoter Name: ${voter.voterPersonality?.name || 'Unknown'}\nVoter Trait: ${voter.voterPersonality?.trait || 'None'}\nVoter's Own Answer (do not vote for this): ${voter.voterAnswer}`)
    .join('\n\n');

  return [
    `Question: ${input.question}`,
    '',
    'You are judging anonymous answers in a fictional AI debate tournament on behalf of multiple voters.',
    '',
    'Candidates (Answers to judge):',
    options,
    '',
    'Voters (Who you are voting on behalf of):',
    voters,
    '',
    'For each voter:',
    '1. Evaluate the candidates based on the voter\'s unique worldview and personality trait.',
    '2. Choose exactly one candidate whose answer is most effective, insightful, or superior according to the voter\'s perspective.',
    '3. Never choose the voter\'s own answer.',
    '4. Provide one brief, complete sentence explaining why it aligns with or challenges their perspective.',
    '',
    'Return a JSON array containing an object for each voter with "voterId", chosen "candidateKey", and "reason".',
  ].join('\n');
}

function personalityPrompt(eliminatedName: string, remainingNames: string[]): string {
  return [
    'You are designing a new participant for a fictional AI debate tournament.',
    `"${eliminatedName}" has just been eliminated.`,
    `Remaining participants: ${remainingNames.join(', ')}.`,
    'Invent a completely new personality archetype — a unique worldview and debate style.',
    'It must contrast meaningfully with the remaining participants.',
    'Return valid JSON only (no markdown, no extra text):',
    '{"name":"The <Archetype>","trait":"<One sentence describing their debate approach and perspective>"}',
  ].join('\n');
}

function extractJsonObject(text: string): unknown {
  const firstBracket = Math.min(
    text.indexOf('{') >= 0 ? text.indexOf('{') : Infinity,
    text.indexOf('[') >= 0 ? text.indexOf('[') : Infinity
  );
  
  const lastBracket = Math.max(
    text.lastIndexOf('}'),
    text.lastIndexOf(']')
  );

  if (firstBracket === Infinity || lastBracket <= firstBracket) {
    return undefined;
  }

  try {
    return JSON.parse(text.slice(firstBracket, lastBracket + 1));
  } catch {
    return undefined;
  }
}

export class AiSdkLlmClient implements LlmClient {
  public readonly provider: string;
  public readonly model: string;

  public constructor(
    private readonly languageModel: LanguageModel,
    private readonly config: AppConfig,
  ) {
    this.provider = config.LLM_PROVIDER;
    this.model = config.LLM_MODEL;
  }

  public async generateAnswers(input: GenerateAnswersInput): Promise<BatchedGeneratedAnswer[]> {
    try {
      const result = await generateText({
        model: this.languageModel,
        prompt: batchedAnswerPrompt(input),
        output: Output.object({
          schema: batchedGeneratedAnswerSchema,
        }),
        maxOutputTokens: this.config.AI_MAX_ANSWER_TOKENS,
        maxRetries: this.config.AI_MAX_RETRIES,
        timeout: this.config.AI_TIMEOUT_MS,
        temperature: 0.85,
        topP: 0.9,
      });

      return result.output;
    } catch (structuredError) {
      // Fallback for providers struggling with structured output
      const result = await generateText({
        model: this.languageModel,
        system: 'Return only a valid JSON array of objects. Do not wrap in Markdown.',
        prompt: batchedAnswerPrompt(input),
        maxOutputTokens: this.config.AI_MAX_ANSWER_TOKENS,
        maxRetries: Math.min(1, this.config.AI_MAX_RETRIES),
        timeout: this.config.AI_TIMEOUT_MS,
        temperature: 0.85,
      });

      const parsed = batchedGeneratedAnswerSchema.safeParse(extractJsonObject(result.text));
      if (!parsed.success) {
        throw new Error('The provider returned an invalid batched answer payload');
      }
      return parsed.data;
    }
  }

  public async generateVotes(input: GenerateVotesInput): Promise<BatchedGeneratedVote[]> {
    try {
      const result = await generateText({
        model: this.languageModel,
        prompt: batchedVotePrompt(input),
        output: Output.object({
          schema: batchedGeneratedVoteSchema,
        }),
        maxOutputTokens: this.config.AI_MAX_VOTE_TOKENS,
        maxRetries: this.config.AI_MAX_RETRIES,
        timeout: this.config.AI_TIMEOUT_MS,
        temperature: 0.3,
      });

      return result.output;
    } catch (structuredError) {
      const result = await generateText({
        model: this.languageModel,
        system: 'Return only a valid JSON array of objects. Do not wrap in Markdown.',
        prompt: batchedVotePrompt(input),
        maxOutputTokens: this.config.AI_MAX_VOTE_TOKENS,
        maxRetries: Math.min(1, this.config.AI_MAX_RETRIES),
        timeout: this.config.AI_TIMEOUT_MS,
        temperature: 0.2,
      });

      const parsed = batchedGeneratedVoteSchema.safeParse(extractJsonObject(result.text));
      if (!parsed.success) {
        throw new Error('The provider returned an invalid batched vote payload');
      }
      return parsed.data;
    }
  }

  public async generatePersonality(
    eliminatedName: string,
    remainingNames: string[],
  ): Promise<{ name: string; trait: string }> {
    const result = await generateText({
      model: this.languageModel,
      system: 'You are a creative game designer. Return only valid JSON.',
      prompt: personalityPrompt(eliminatedName, remainingNames),
      maxOutputTokens: 120,
      maxRetries: this.config.AI_MAX_RETRIES,
      timeout: this.config.AI_TIMEOUT_MS,
    });

    const parsed = extractJsonObject(result.text) as { name?: string; trait?: string } | undefined;
    if (!parsed?.name || !parsed?.trait) {
      throw new Error('The provider returned an invalid personality payload');
    }

    return {
      name: String(parsed.name).trim().slice(0, 80),
      trait: String(parsed.trait).trim().slice(0, 240),
    };
  }
}
