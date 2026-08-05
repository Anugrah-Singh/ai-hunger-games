import type { CounterDecision, CounterStatus, RequestCounter } from './types.js';

export class MemoryRequestCounter implements RequestCounter {
  private used = 0;

  public constructor(private readonly limit: number) {}

  public async consume(): Promise<CounterDecision> {
    if (this.used >= this.limit) {
      return { ...this.snapshot(), allowed: false };
    }

    this.used += 1;
    return { ...this.snapshot(), allowed: true };
  }

  public async status(): Promise<CounterStatus> {
    return this.snapshot();
  }

  public async reset(): Promise<void> {
    this.used = 0;
  }

  public async close(): Promise<void> {}

  private snapshot(): CounterStatus {
    return {
      trackingEnabled: true,
      requestsUsed: this.used,
      requestLimit: this.limit,
      remaining: Math.max(0, this.limit - this.used),
      disabled: this.used >= this.limit,
    };
  }
}
