import type { AppConfig } from '../config/env.js';
import { DisabledRequestCounter } from './disabled-counter.js';
import { MemoryRequestCounter } from './memory-counter.js';
import { RedisRequestCounter } from './redis-counter.js';
import type { RequestCounter } from './types.js';

export async function createRequestCounter(config: AppConfig): Promise<RequestCounter> {
  switch (config.REQUEST_TRACKING_MODE) {
    case 'disabled':
      return new DisabledRequestCounter(config.REQUEST_LIMIT);
    case 'memory':
      return new MemoryRequestCounter(config.REQUEST_LIMIT);
    case 'redis':
      return RedisRequestCounter.connect(config);
    default:
      throw new Error('Unsupported request tracking mode');
  }
}
