import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { generateText } from 'ai';
import * as dotenv from 'dotenv';
dotenv.config();

const provider = createOpenRouter({
  apiKey: process.env.LLM_API_KEY ?? '',
  extraBody: { models: ['mistralai/ministral-8b-2512', 'meta-llama/llama-4-scout'] },
});

const model = provider.chat('google/gemini-3.6-flash');

async function run() {
  try {
    const result = await generateText({
      model,
      prompt: 'Say hi',
    });
    console.log(result.text);
  } catch (err) {
    console.error(err);
  }
}

run();
