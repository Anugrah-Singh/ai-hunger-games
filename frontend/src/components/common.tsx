import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Tooltip } from "radix-ui";


interface MetricCardProps {
  label: string;
  value: string | number;
  detail: string;
}


export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <article className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-detail">{detail}</p>
    </article>
  );
}


export function Placeholder({ children }: { children: ReactNode }) {
  return <div className="placeholder-row">{children}</div>;
}


interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  children: ReactNode;
}


export function IconButton({
  label,
  children,
  className = "",
  ...props
}: IconButtonProps) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          aria-label={label}
          className={`icon-button ${className}`.trim()}
          type="button"
          {...props}
        >
          {children}
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tooltip-content" sideOffset={6}>
          {label}
          <Tooltip.Arrow className="tooltip-arrow" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}


export function LoadingState() {
  return (
    <section className="empty-state" aria-live="polite">
      <p className="loading-label">Loading experiment data</p>
    </section>
  );
}


export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <section className="empty-state" role="alert">
      <p className="loading-label">Unable to load the experiment</p>
      <p className="metadata">{message}</p>
      <button className="secondary-button" onClick={onRetry} type="button">
        Try again
      </button>
    </section>
  );
}
