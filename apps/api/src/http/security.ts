import { createHash, timingSafeEqual } from 'node:crypto';

export function secretsMatch(provided: string | undefined, expected: string | undefined): boolean {
  if (!provided || !expected) return false;
  const providedDigest = createHash('sha256').update(provided).digest();
  const expectedDigest = createHash('sha256').update(expected).digest();
  return timingSafeEqual(providedDigest, expectedDigest);
}
