import { useEffect, useState } from 'react';

export function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return undefined;
    }

    setSeconds(0);
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - startedAt) / 1_000));
    }, 250);

    return () => window.clearInterval(timer);
  }, [active]);

  return seconds;
}
