import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div className={`sf-card ${hover ? "sf-card-hover" : ""} ${className}`}>{children}</div>
  );
}

export function Pill({ children }: { children: ReactNode }) {
  return <span className="sf-pill">{children}</span>;
}

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="sf-metric">
      <div className="sf-metric-label">{label}</div>
      <div className="sf-metric-value">{value}</div>
    </div>
  );
}

export function Alert({
  kind = "info",
  children,
}: {
  kind?: "info" | "success" | "error";
  children: ReactNode;
}) {
  const styles: Record<string, string> = {
    info: "border-[var(--sf-accent)]/40 bg-[var(--sf-pill-bg)] text-[var(--sf-pill-text)]",
    success:
      "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
    error: "border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-300",
  };
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm font-medium ${styles[kind]}`}>
      {children}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--sf-muted)]">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[var(--sf-accent)] border-t-transparent" />
      {label ?? "Loading…"}
    </div>
  );
}
