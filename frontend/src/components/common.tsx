import type { ButtonHTMLAttributes, ReactNode } from "react";
import { LoaderCircle, Sparkles } from "lucide-react";
import { Tooltip } from "radix-ui";

interface MetricCardProps {
  label: string;
  value: string | number;
  detail: string;
  icon?: ReactNode;
}

export function MetricCard({ label, value, detail, icon }: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-card-header">
        <p className="metric-label">{label}</p>
        {icon !== undefined && <span className="metric-icon">{icon}</span>}
      </div>
      <p className="metric-value">{value}</p>
      <p className="metric-detail">{detail}</p>
    </article>
  );
}

export function Surface({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`surface ${className}`.trim()}>{children}</section>;
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {description !== undefined && <p className="section-description">{description}</p>}
      </div>
      {action !== undefined && <div className="section-action">{action}</div>}
    </div>
  );
}

export function Placeholder({ children }: { children: ReactNode }) {
  return (
    <div className="placeholder-row">
      <Sparkles aria-hidden="true" size={16} />
      <span>{children}</span>
    </div>
  );
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
        <Tooltip.Content className="tooltip-content" sideOffset={8}>
          {label}
          <Tooltip.Arrow className="tooltip-arrow" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export function LoadingState({ label = "Loading experiment data" }: { label?: string }) {
  return (
    <section className="center-state" aria-live="polite">
      <span className="uiverse-loader" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <p className="loading-label">{label}</p>
    </section>
  );
}

export function RunProgress() {
  return (
    <div className="run-progress" role="status" aria-live="polite">
      <LoaderCircle aria-hidden="true" className="spin" size={18} />
      <div>
        <strong>Generation is running</strong>
        <span>Answers, voting, replacement, and persistence are executing on the backend.</span>
      </div>
    </div>
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
    <section className="center-state" role="alert">
      <div className="error-orb" aria-hidden="true">!</div>
      <h1>Unable to load the experiment</h1>
      <p className="metadata">{message}</p>
      <button className="secondary-button" onClick={onRetry} type="button">
        Try again
      </button>
    </section>
  );
}
