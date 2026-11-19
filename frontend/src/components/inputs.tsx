import { useEffect, useRef, useState } from "react";

/** Styled native select. `value` of "" renders the placeholder option. */
export function Select({
  value,
  onChange,
  options,
  placeholder,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
  ariaLabel?: string;
}) {
  return (
    <select
      className="sf-select"
      value={value}
      aria-label={ariaLabel}
      onChange={(e) => onChange(e.target.value)}
    >
      {placeholder !== undefined && (
        <option value="">{placeholder}</option>
      )}
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}

/**
 * Chip-style multiselect: selected values render as removable pills, options
 * live in a dropdown panel (with an optional search box for long lists).
 */
export function MultiSelect({
  values,
  onChange,
  options,
  placeholder,
  searchable = false,
}: {
  values: string[];
  onChange: (values: string[]) => void;
  options: string[];
  placeholder?: string;
  searchable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const lower = query.trim().toLowerCase();
  const visible = options.filter((o) => !lower || o.toLowerCase().includes(lower));

  const toggle = (opt: string) => {
    onChange(
      values.includes(opt) ? values.filter((v) => v !== opt) : [...values, opt],
    );
  };

  return (
    <div ref={rootRef} className="relative">
      <div
        className="sf-input flex min-h-[42px] cursor-pointer flex-wrap items-center gap-1.5"
        onClick={() => setOpen((o) => !o)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        }}
      >
        {values.length === 0 && (
          <span className="text-[var(--sf-muted)]">{placeholder ?? "Select…"}</span>
        )}
        {values.map((v) => (
          <span key={v} className="sf-pill flex items-center gap-1">
            {v}
            <button
              type="button"
              aria-label={`Remove ${v}`}
              className="font-bold hover:text-red-400"
              onClick={(e) => {
                e.stopPropagation();
                toggle(v);
              }}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 max-h-64 overflow-auto rounded-xl border border-[var(--sf-border)] bg-[var(--sf-surface-strong)] p-2 shadow-lg">
          {searchable && (
            <input
              className="sf-input mb-2"
              placeholder="Search…"
              value={query}
              autoFocus
              onChange={(e) => setQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          )}
          {visible.length === 0 && (
            <div className="sf-muted px-2 py-1">No matches</div>
          )}
          {visible.map((opt) => (
            <label
              key={opt}
              className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-[var(--sf-pill-bg)]"
            >
              <input
                type="checkbox"
                checked={values.includes(opt)}
                onChange={() => toggle(opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

/** Horizontal progress bar (replaces st.progress). */
export function ProgressBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--sf-border)]">
      <div
        className="h-full rounded-full bg-[var(--sf-accent)] transition-all duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
