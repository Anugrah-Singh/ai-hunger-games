export interface CounterStatus {
  trackingEnabled: boolean;
  requestsUsed: number;
  requestLimit: number;
  remaining: number;
  disabled: boolean;
}

export interface CounterDecision extends CounterStatus {
  allowed: boolean;
}

export interface RequestCounter {
  consume(): Promise<CounterDecision>;
  status(): Promise<CounterStatus>;
  reset(): Promise<void>;
  close(): Promise<void>;
}

export class RequestCounterUnavailableError extends Error {
  public constructor(cause?: unknown) {
    super('Request tracking is temporarily unavailable', { cause });
    this.name = 'RequestCounterUnavailableError';
  }
}
