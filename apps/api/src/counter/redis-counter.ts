import { createClient } from 'redis';

import type { AppConfig } from '../config/env.js';
import type { CounterDecision, CounterStatus, RequestCounter } from './types.js';
import { RequestCounterUnavailableError } from './types.js';

const CONSUME_SCRIPT = `
local countKey = KEYS[1]
local disabledKey = KEYS[2]
local limit = tonumber(ARGV[1])
local current = tonumber(redis.call('GET', countKey) or '0')
local disabled = redis.call('GET', disabledKey) == 'true'

if disabled or current >= limit then
  redis.call('SET', disabledKey, 'true')
  return {0, current}
end

local nextCount = redis.call('INCR', countKey)

if nextCount >= limit then
  redis.call('SET', disabledKey, 'true')
end

return {1, nextCount}
`;

async function createConnectedRedisClient(url: string) {
  const client = createClient({ url });

  client.on('error', () => undefined);

  await client.connect();

  return client;
}

type ConnectedRedisClient = Awaited<ReturnType<typeof createConnectedRedisClient>>;

export class RedisRequestCounter implements RequestCounter {
  private readonly countKey = 'ai-hunger-games:request-count';
  private readonly disabledKey = 'ai-hunger-games:api-disabled';

  private constructor(
    private readonly client: ConnectedRedisClient,
    private readonly limit: number,
    private readonly failureMode: AppConfig['COUNTER_FAILURE_MODE'],
  ) {}

  public static async connect(config: AppConfig): Promise<RedisRequestCounter> {
    if (!config.REDIS_URL) {
      throw new Error('REDIS_URL is required');
    }

    const client = await createConnectedRedisClient(config.REDIS_URL);

    return new RedisRequestCounter(client, config.REQUEST_LIMIT, config.COUNTER_FAILURE_MODE);
  }

  public async consume(): Promise<CounterDecision> {
    try {
      const raw = await this.client.eval(CONSUME_SCRIPT, {
        keys: [this.countKey, this.disabledKey],
        arguments: [String(this.limit)],
      });

      const values = Array.isArray(raw) ? raw.map(Number) : [];
      const allowed = values[0] === 1;
      const used = Number.isFinite(values[1]) ? (values[1] ?? 0) : 0;

      return {
        ...this.snapshot(used, used >= this.limit),
        allowed,
      };
    } catch (error) {
      if (this.failureMode === 'open') {
        return {
          ...this.snapshot(0, false),
          allowed: true,
        };
      }

      throw new RequestCounterUnavailableError(error);
    }
  }

  public async status(): Promise<CounterStatus> {
    try {
      const [countValue, disabledValue] = await this.client.mGet([this.countKey, this.disabledKey]);

      const used = Number(countValue ?? 0);

      return this.snapshot(Number.isFinite(used) ? used : 0, disabledValue === 'true');
    } catch (error) {
      if (this.failureMode === 'open') {
        return this.snapshot(0, false);
      }

      throw new RequestCounterUnavailableError(error);
    }
  }

  public async reset(): Promise<void> {
    try {
      await this.client.mSet({
        [this.countKey]: '0',
        [this.disabledKey]: 'false',
      });
    } catch (error) {
      throw new RequestCounterUnavailableError(error);
    }
  }

  public async close(): Promise<void> {
    if (this.client.isOpen) {
      await this.client.quit();
    }
  }

  private snapshot(used: number, disabled: boolean): CounterStatus {
    return {
      trackingEnabled: true,
      requestsUsed: used,
      requestLimit: this.limit,
      remaining: Math.max(0, this.limit - used),
      disabled,
    };
  }
}
