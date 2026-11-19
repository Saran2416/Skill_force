import { useEffect, useState } from "react";
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { api } from "../api";
import type { AppState, RadarData } from "../types";
import { Alert, Card, Metric } from "../components/ui";

export default function GapTab({ state }: { state: AppState }) {
  const gap = state.gap;
  const [radar, setRadar] = useState<RadarData | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<RadarData>("/gap/radar")
      .then((d) => {
        if (!cancelled) setRadar(d);
      })
      .catch(() => {
        if (!cancelled) setRadar(null);
      });
    return () => {
      cancelled = true;
    };
  }, [state]);

  if (!gap) {
    return (
      <Card className="p-5 text-sm">
        No skill gap analysis available yet. Save your profile to compute gaps.
      </Card>
    );
  }

  const chartData = (radar?.labels ?? []).map((label, i) => ({
    skill: label,
    current: radar?.current[i] ?? 0,
    required: radar?.required[i] ?? 0,
  }));

  return (
    <div className="sf-animate max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl">Skill Gap &amp; Role Readiness</h2>
        <p className="sf-muted">
          Compare your current proficiency against target requirements and prioritize what to
          learn next.
        </p>
      </div>

      <div className="grid gap-5 md:grid-cols-[220px_1fr]">
        <Card className="p-4">
          <Metric
            label="Role Match"
            value={`${Number(gap.match_percent).toLocaleString()}%`}
          />
        </Card>
        <Alert kind="info">
          Readiness is weighted by priority: <strong>must-have</strong> skills carry 3× weight,{" "}
          <strong>good-to-have</strong> 2×, and <strong>bonus</strong> 1×.
        </Alert>
      </div>

      <div>
        <h3 className="text-lg">Competency Radar (Current vs. Required)</h3>
        {!radar || chartData.length === 0 ? (
          <p className="sf-muted mt-2 text-sm">No radar data available to chart.</p>
        ) : (
          <Card className="mt-2 p-4">
            <div className="h-[420px] w-full">
              <ResponsiveContainer>
                <RadarChart data={chartData} outerRadius="75%">
                  <PolarGrid stroke="rgba(148,163,184,0.25)" />
                  <PolarAngleAxis dataKey="skill" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                  <PolarRadiusAxis
                    domain={[0, 5]}
                    ticks={[0, 1, 2, 3, 4, 5]}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    axisLine={false}
                  />
                  <Radar
                    name="Current Level"
                    dataKey="current"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fill="#2563eb"
                    fillOpacity={0.2}
                  />
                  <Radar
                    name="Required Level"
                    dataKey="required"
                    stroke="#dc2626"
                    strokeWidth={2}
                    strokeDasharray="5 4"
                    fill="#dc2626"
                    fillOpacity={0.15}
                  />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <Card className="p-5">
          <h3 className="text-lg">Identified Gaps</h3>
          {gap.gaps.length > 0 ? (
            <ul className="mt-2 space-y-2 text-sm">
              {gap.gaps.map((item) => (
                <li key={item.skill} className="flex flex-wrap items-center gap-2">
                  <strong>{item.skill}</strong>
                  <span className="text-[var(--sf-muted)]">
                    Current {item.current}/5 → Required {item.required}/5
                  </span>
                  <code className="rounded bg-[var(--sf-border)] px-1.5 py-0.5 text-xs font-bold uppercase">
                    {item.priority}
                  </code>
                  <span className="text-red-400">(Gap: -{item.gap})</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm font-medium text-emerald-500">
              🎉 No skill gaps! You meet or exceed all role requirements.
            </p>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="text-lg">Core Strengths</h3>
          {gap.strengths.length > 0 ? (
            <ul className="mt-2 space-y-1.5 text-sm">
              {gap.strengths.map((s) => (
                <li key={s}>✅ <strong>{s}</strong></li>
              ))}
            </ul>
          ) : (
            <p className="sf-muted mt-2 text-sm">No specific strengths detected yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
