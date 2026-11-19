import { useState } from "react";
import type { AppState, StepStatus } from "../types";
import { Alert, Card, Metric } from "../components/ui";
import { ProgressBar } from "../components/inputs";

const STATUS_BADGES: Record<StepStatus, string> = {
  todo: "⏳ To Do",
  doing: "🚀 In Progress",
  done: "✅ Completed",
  revision: "⚠️ Needs Revision",
};

export default function RoadmapTab({ state }: { state: AppState }) {
  const roadmap = state.roadmap;

  // Practice-task checkboxes are UI-local (they never persisted in Streamlit either).
  const [checks, setChecks] = useState<Record<string, boolean>>({});

  if (!roadmap || roadmap.steps.length === 0) {
    return (
      <Alert kind="info">
        No learning roadmap generated yet. Complete your profile to build your plan.
      </Alert>
    );
  }

  const steps = [...roadmap.steps].sort((a, b) => a.order - b.order);
  const doneSteps = steps.filter((s) => s.status === "done").length;

  const badgeStyle = (status: StepStatus) => {
    switch (status) {
      case "revision":
        return "bg-red-500/15 text-red-500 border border-red-500/40";
      case "done":
        return "bg-emerald-500/15 text-emerald-500 border border-emerald-500/40";
      case "doing":
        return "bg-[var(--sf-pill-bg)] text-[var(--sf-tab-active)] border border-[var(--sf-border)]";
      default:
        return "text-[var(--sf-muted)]";
    }
  };

  return (
    <div className="sf-animate max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl">Learning Roadmap</h2>
        {roadmap.est_hours > 0 && (
          <p className="sf-muted mt-1">
            ⏱️ <strong>Total Estimated Time:</strong> ~{roadmap.est_hours} hours to job readiness
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric label="Steps" value={String(steps.length)} />
        <Metric label="Completed" value={`${doneSteps}/${steps.length}`} />
        <div className="col-span-2 flex flex-col justify-center sm:col-span-1">
          <p className="sf-muted mb-1 text-xs font-semibold">Progress</p>
          <ProgressBar value={(doneSteps / steps.length) * 100} />
        </div>
      </div>

      <div className="space-y-4">
        {steps.map((step) => {
          const isRevision = step.status === "revision";
          return (
            <Card key={step.order} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h3 className="text-base font-bold">
                  Step {step.order}: {step.skill}{" "}
                  <span className="text-sm font-normal text-[var(--sf-muted)]">
                    (Target: Level {step.target_level}/5)
                  </span>
                </h3>
                <span
                  className={`rounded-lg px-2.5 py-1 text-xs font-bold ${badgeStyle(step.status)}`}
                >
                  {STATUS_BADGES[step.status] ?? step.status.toUpperCase()}
                </span>
              </div>

              {isRevision && (
                <div className="mt-3">
                  <Alert kind="error">
                    ⚠️ <strong>Revision Required:</strong> Assessment results flagged this skill
                    for review. Review foundational concepts and complete the practice tasks
                    before retaking.
                  </Alert>
                </div>
              )}

              {step.mini_project && (
                <p className="mt-3 text-sm">
                  🛠️ <strong>Mini-Project:</strong> {step.mini_project}
                </p>
              )}

              {step.practice_tasks.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-semibold">Practice Tasks:</p>
                  <div className="mt-1.5 space-y-1.5">
                    {step.practice_tasks.map((task, idx) => {
                      const key = `${step.order}_${idx}`;
                      return (
                        <label
                          key={key}
                          className="flex cursor-pointer items-start gap-2 text-sm"
                        >
                          <input
                            type="checkbox"
                            className="mt-0.5"
                            checked={checks[key] ?? false}
                            onChange={(e) =>
                              setChecks((prev) => ({ ...prev, [key]: e.target.checked }))
                            }
                          />
                          <span
                            className={
                              checks[key] ? "text-[var(--sf-muted)] line-through" : ""
                            }
                          >
                            {task}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              {step.resources.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-semibold">Learning Resources:</p>
                  <ul className="mt-1 space-y-1 text-sm">
                    {step.resources.map((res) => (
                      <li key={res.url}>
                        •{" "}
                        <a
                          href={res.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[var(--sf-accent)] underline hover:text-[var(--sf-accent-2)]"
                        >
                          {res.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
