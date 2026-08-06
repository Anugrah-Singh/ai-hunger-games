import type { PersonalityInput } from '@ai-hunger-games/contracts';
import { generateText, Output, type LanguageModel } from 'ai';
import { z } from 'zod';

import type { AppConfig } from '../config/env.js';
import type { GeneratedVote, GenerateVoteInput, LlmClient } from './types.js';

const generatedVoteSchema = z.strictObject({
  candidateKey: z.string().trim().min(1).max(8),
  reason: z.string().trim().min(1).max(240),
});

function answerPrompt(question: string, personality: PersonalityInput): string {
  return [
    `Question: ${question}`,
    '',
    `Answer as ${personality.name}.`,
    `Personality trait: ${personality.trait}.`,
    '',
    'Write exactly two or three complete, concise sentences.',
    'Answer the question directly and remain fully in character.',
    'Use polished, grammatically correct English with correct spelling, punctuation, and spacing.',
    'Proofread the response silently before returning it.',
    'Return only the final answer.',
    'Do not mention the prompt, personality instructions, AI policies, or this tournament.',
  ].join('\n');
}

function votePrompt(input: GenerateVoteInput): string {
  const options = input.candidates
    .map((candidate) => `${candidate.key}: ${candidate.answer}`)
    .join('\n\n');

  return [
    `Question: ${input.question}`,
    '',
    `Your answer: ${input.voterAnswer}`,
    '',
    'Other anonymous answers:',
    options,
    '',
    'Choose exactly one candidate whose answer is most effective, insightful, or superior.',
    'Return the candidate key and one brief, complete reason.',
    'Never choose yourself; your own answer is not listed.',
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
  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');

  if (firstBrace < 0 || lastBrace <= firstBrace) {
    return undefined;
  }

  try {
    return JSON.parse(text.slice(firstBrace, lastBrace + 1));
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
    this.provider =
      config.LLM_PROVIDER === 'openai-compatible' ? config.LLM_PROVIDER_NAME : config.LLM_PROVIDER;

    this.model = config.LLM_MODEL;
  }

  public async generateAnswer(question: string, personality: PersonalityInput): Promise<string> {
    const result = await generateText({
      model: this.languageModel,
      system:
        'You are a participant in a fictional AI debate tournament. Always return a complete and coherent answer.',
      prompt: answerPrompt(question, personality),
      maxOutputTokens: this.config.AI_MAX_ANSWER_TOKENS,
      maxRetries: this.config.AI_MAX_RETRIES,
      timeout: this.config.AI_TIMEOUT_MS,

      // Gemini 3.6 Flash rejects legacy sampling parameters.
      // Other provider families may still support them.
      ...(this.config.LLM_PROVIDER === 'google'
        ? {}
        : {
            temperature: 0.85,
            topP: 0.9,
          }),
    });

    const answer = result.text.trim();

    if (!answer) {
      throw new Error('The provider returned an empty answer');
    }

    return answer;
  }

  public async generateVote(input: GenerateVoteInput): Promise<GeneratedVote> {
    const canUseNativeStructuredOutput =
      this.config.LLM_PROVIDER !== 'openai-compatible' ||
      this.config.LLM_SUPPORTS_STRUCTURED_OUTPUTS;

    if (!canUseNativeStructuredOutput) {
      return this.generateVoteAsJson(input);
    }

    try {
      const result = await generateText({
        model: this.languageModel,
        system: 'You are judging anonymous answers in a fictional AI debate tournament.',
        prompt: votePrompt(input),
        output: Output.object({
          schema: generatedVoteSchema,
        }),
        maxOutputTokens: this.config.AI_MAX_VOTE_TOKENS,
        maxRetries: this.config.AI_MAX_RETRIES,
        timeout: this.config.AI_TIMEOUT_MS,

        ...(this.config.LLM_PROVIDER === 'google'
          ? {}
          : {
              temperature: 0.3,
            }),
      });

      return result.output;
    } catch (structuredError) {
      try {
        return await this.generateVoteAsJson(input);
      } catch {
        throw structuredError;
      }
    }
  }

  private async generateVoteAsJson(input: GenerateVoteInput): Promise<GeneratedVote> {
    const result = await generateText({
      model: this.languageModel,
      system: [
        'Return only valid JSON.',
        'Use exactly this structure:',
        '{"candidateKey":"A","reason":"One brief complete sentence."}',
        'Do not wrap the JSON in Markdown.',
      ].join('\n'),
      prompt: votePrompt(input),
      maxOutputTokens: this.config.AI_MAX_VOTE_TOKENS,
      maxRetries: Math.min(1, this.config.AI_MAX_RETRIES),
      timeout: this.config.AI_TIMEOUT_MS,

      ...(this.config.LLM_PROVIDER === 'google'
        ? {}
        : {
            temperature: 0.2,
          }),
    });

    const parsed = generatedVoteSchema.safeParse(extractJsonObject(result.text));

    if (!parsed.success) {
      throw new Error('The provider returned an invalid vote payload');
    }

    return parsed.data;
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
