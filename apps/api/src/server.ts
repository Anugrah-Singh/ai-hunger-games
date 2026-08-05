import { buildApp } from './app.js';
import { loadConfig } from './config/env.js';
import { createRequestCounter } from './counter/create-counter.js';
import { createLlmClient } from './llm/create-client.js';

const config = loadConfig();
const llm = createLlmClient(config);
const counter = await createRequestCounter(config);
const app = await buildApp({ config, llm, counter });

const shutdown = async (signal: string): Promise<void> => {
  app.log.info({ signal }, 'Shutting down');
  await app.close();
  process.exit(0);
};

process.once('SIGINT', () => void shutdown('SIGINT'));
process.once('SIGTERM', () => void shutdown('SIGTERM'));

try {
  await app.listen({ host: config.HOST, port: config.PORT });
  app.log.info(
    {
      provider: llm.provider,
      model: llm.model,
      requestTracking: config.REQUEST_TRACKING_MODE,
    },
    'AI Hunger Games API started',
  );
} catch (error) {
  app.log.fatal({ err: error }, 'Failed to start API');
  await app.close();
  process.exit(1);
}
