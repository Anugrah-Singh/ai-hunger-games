import type { CounterDecision, CounterStatus, RequestCounter } from './types.js';

export class DisabledRequestCounter implements RequestCounter {
  public constructor(private readonly limit: number) {}

  public async consume(): Promise<CounterDecision> {
    return { ...this.snapshot(), allowed: true };
  }

  public async status(): Promise<CounterStatus> {
    return this.snapshot();
  }

  public async reset(): Promise<void> {}
  public async close(): Promise<void> {}

  private snapshot(): CounterStatus {
    return {
      trackingEnabled: false,
      requestsUsed: 0,
      requestLimit: this.limit,
      remaining: this.limit,
      disabled: false,
    };
  }
}
