import { createOpenRouter } from "@openrouter/ai-sdk-provider";
import { generateText } from "ai";

const modelsStr = "google/gemini-3.6-flash,mistralai/ministral-8b-2512,meta-llama/llama-4-scout";
const models = modelsStr.split(',').map((m) => m.trim());
const primaryModel = models[0];

console.log("Primary model is:", primaryModel);
console.log("Fallback models array is:", models);

const provider = createOpenRouter({
  apiKey: "dummy",
  extraBody: { models }
});

const model = provider.chat(primaryModel);

try {
  await generateText({
    model,
    prompt: "Hello"
  });
} catch (e) {
  console.log("Error generated:", e.message);
  console.log("Error details:", JSON.stringify(e, null, 2));
}
