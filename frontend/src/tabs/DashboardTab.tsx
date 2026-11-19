import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type { AppState, DashboardResponse } from "../types";
import { Card, Metric, Spinner } from "../components/ui";
import { ProgressBar } from "../components/inputs";

const STATUS_COLORS: Record<string, string> = {
  met: "#1a7f37",
  gap: "#b7791f",
  missing: "#c0392b",
};

export default function DashboardTab({ state }: { state: AppState }) {
  const [model, setModel] = useState<DashboardResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<DashboardResponse>("/dashboard")
      .then((m) => {
        if (!cancelled) setModel(m);
      })
      .catch(() => {
        if (!cancelled) setModel(null);
      });
    return () => {
      cancelled = true;
    };
  }, [state]);

  const requirements = state.requirements;
  if (!requirements) {
    return (
      <Card className="p-5 text-sm">
        Your dashboard is empty. Complete the <strong>Profile</strong> tab to generate a
        personalised match analysis.
      </Card>
    );
  }

  const profile = state.profile;
  const gap = state.gap;
  const targetRole = (profile.target_role ?? "").trim() || "Not set";
  const company = requirements.company || "Any company";
  const match = gap ? `${Number(gap.match_percent).toLocaleString()}%` : "—";

  if (!model) return <Spinner label="Loading dashboard…" />;

  const prog = model.progress;

  return (
    <div className="sf-animate space-y-6">
      <div>
        <h2 className="text-xl">Dashboard Overview</h2>
        <p className="sf-muted">A snapshot of your target, readiness, and next actions.</p>
      </div>

      {/* top metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Target Role" value={targetRole} />
        <div className="space-y-2">
          <Metric label="Target Company" value={company} />
          <span
            className="inline-block rounded-lg px-2.5 py-0.5 text-xs font-semibold text-white"
            style={{
              background: requirements.confidence === "curated" ? "#1a7f37" : "#b7791f",
            }}
          >
            {requirements.confidence === "curated" ? "Curated" : "AI-estimated"}
          </span>
        </div>
        <Metric label="Match" value={match} />
        <div className="space-y-1">
          <Metric label="Roadmap Progress" value={`${Number(prog.percent).toLocaleString()}%`} />
          {prog.total > 0 && (
            <p className="sf-muted text-xs">
              {prog.done}/{prog.total} steps completed
            </p>
          )}
        </div>
      </div>

      <hr className="border-[var(--sf-border)]" />

      {/* languages + required skills */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-lg">Languages You Know</h2>
          {model.known_languages.length > 0 ? (
            <div className="mt-2 space-y-3">
              <div className="flex flex-wrap gap-2">
                {model.known_languages.map((s) => (
                  <span
                    key={s.name}
                    className="rounded-xl bg-indigo-50 px-2.5 py-1 text-sm text-[#1f2a6b]"
                  >
                    {s.name}
                  </span>
                ))}
              </div>
              {model.known_languages.map((s) => (
                <div key={s.name}>
                  <p className="sf-muted text-xs">
                    {s.name} — level {s.level}/5
                  </p>
                  <ProgressBar value={(s.level / 5) * 100} />
                </div>
              ))}
            </div>
          ) : (
            <p className="sf-muted mt-2 text-sm">
              No programming languages yet. Add skills in the Profile tab.
            </p>
          )}
        </div>

        <div>
          <h2 className="text-lg">Required Skills</h2>
          {model.required_skills.length > 0 ? (
            <table className="mt-2 w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--sf-border)] text-left">
                  <th className="py-1.5 pr-2">Skill</th>
                  <th className="py-1.5 px-2 text-center">Required</th>
                  <th className="py-1.5 px-2 text-center">Current</th>
                  <th className="py-1.5 px-2">Priority</th>
                  <th className="py-1.5 pl-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {model.required_skills.map((row) => (
                  <tr key={row.skill} className="border-b border-[var(--sf-border)]/50">
                    <td className="py-1.5 pr-2">{row.skill}</td>
                    <td className="py-1.5 px-2 text-center">{row.required}</td>
                    <td className="py-1.5 px-2 text-center">{row.current}</td>
                    <td className="py-1.5 px-2">{row.priority}</td>
                    <td
                      className="py-1.5 pl-2 font-semibold"
                      style={{ color: STATUS_COLORS[row.status] ?? "#555" }}
                    >
                      {row.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="sf-muted mt-2 text-sm">No requirements available yet.</p>
          )}
        </div>
      </div>

      <hr className="border-[var(--sf-border)]" />

      {/* advantages / disadvantages */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="text-lg">Strengths &amp; Advantages</h2>
          {model.advantages.length > 0 ? (
            <ul className="mt-2 space-y-1 text-sm" style={{ color: "#1a7f37" }}>
              {model.advantages.map((item, i) => (
                <li key={i}>• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="sf-muted mt-2 text-sm">Save your profile to see personalized strengths.</p>
          )}
        </Card>
        <Card className="p-5">
          <h2 className="text-lg">Gaps &amp; Risks</h2>
          {model.disadvantages.length > 0 ? (
            <ul className="mt-2 space-y-1 text-sm" style={{ color: "#c0392b" }}>
              {model.disadvantages.map((item, i) => (
                <li key={i}>• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="sf-muted mt-2 text-sm">Save your profile to see personalized gaps.</p>
          )}
        </Card>
      </div>

      <hr className="border-[var(--sf-border)]" />

      {/* next step + scores */}
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <div className="sf-glow rounded-[14px]">
          <Card className="h-full p-5">
            <p className="font-semibold">Recommended Next Step</p>
            {prog.next_step ? (
              <p className="mt-2 text-sm">
                Focus on <strong>{prog.next_step}</strong> to move your roadmap forward.
              </p>
            ) : prog.total === 0 ? (
              <p className="sf-muted mt-2 text-sm">
                No roadmap steps yet. Save your profile to generate a plan.
              </p>
            ) : (
              <p className="mt-2 text-sm font-medium text-emerald-500">
                Roadmap complete. Keep validating skills with assessments.
              </p>
            )}
          </Card>
        </div>

        <Card className="h-full p-5">
          <p className="font-semibold">Assessment Scores</p>
          {state.scores.length > 0 ? (
            <div className="mt-3 h-[240px] w-full">
              <ResponsiveContainer>
                <BarChart data={state.scores} margin={{ left: -20, right: 10, top: 10, bottom: 0 }}>
                  <XAxis
                    dataKey="skill"
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    angle={-20}
                    textAnchor="end"
                    height={50}
                    stroke="rgba(148,163,184,0.35)"
                  />
                  <YAxis
                    domain={[0, 110]}
                    tick={{ fill: "#94a3b8", fontSize: 12 }}
                    stroke="rgba(148,163,184,0.35)"
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#111827",
                      border: "1px solid rgba(148,163,184,0.3)",
                      borderRadius: 8,
                      color: "#e5e7eb",
                    }}
                    formatter={(value) => [`${value}%`, "Score"]}
                  />
                  <Bar dataKey="score_percent" radius={[4, 4, 0, 0]}>
                    {state.scores.map((_, i) => (
                      <Cell key={i} fill="#60a5fa" stroke="#3b82f6" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="sf-muted mt-2 text-sm">
              No assessment scores yet. Complete a quiz or simulation to track progress.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
