import type { LlmClient } from '../llm/types.js';

export class PersonalityService {
  public constructor(private readonly llm: LlmClient) {}

  public async generate(
    eliminatedName: string,
    remainingNames: string[],
  ): Promise<{ name: string; trait: string }> {
    return this.llm.generatePersonality(eliminatedName, remainingNames);
  }
}
