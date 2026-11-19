import type { AppState } from "../types";
import { Alert, Card } from "../components/ui";

function ConfidenceBadge({ confidence }: { confidence: "curated" | "ai_estimated" }) {
  const curated = confidence === "curated";
  return (
    <span
      className="inline-block rounded-xl px-3 py-0.5 text-xs font-semibold text-white"
      style={{ background: curated ? "#1a7f37" : "#b7791f" }}
    >
      {curated ? "Curated" : "AI-estimated"}
    </span>
  );
}

export default function RequirementsTab({ state }: { state: AppState }) {
  const req = state.requirements;
  if (!req) {
    return (
      <Card className="p-5 text-sm">
        No requirements available yet. Complete your profile to load role requirements.
      </Card>
    );
  }

  const recommendations = state.recommendations ?? [];

  return (
    <div className="sf-animate max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl">Target Role Requirements</h2>
        <p className="sf-muted">
          {req.role} · {req.company || "Any Company"}
        </p>
        <div className="mt-2">
          <ConfidenceBadge confidence={req.confidence} />
        </div>
      </div>

      {req.disclaimer && (
        <Alert kind="info">
          <strong>Disclaimer:</strong> {req.disclaimer}
        </Alert>
      )}

      <hr className="border-[var(--sf-border)]" />

      <div>
        <h3 className="text-lg">Skill Requirements</h3>
        {req.requirements.length > 0 ? (
          <Card className="mt-2 overflow-x-auto p-4">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--sf-border)] text-left">
                  <th className="py-1.5 pr-3">Skill</th>
                  <th className="py-1.5 px-3">Required Level</th>
                  <th className="py-1.5 px-3">Priority</th>
                  <th className="py-1.5 pl-3">Note</th>
                </tr>
              </thead>
              <tbody>
                {req.requirements.map((r) => (
                  <tr key={r.skill} className="border-b border-[var(--sf-border)]/50">
                    <td className="py-1.5 pr-3 font-medium">{r.skill}</td>
                    <td className="py-1.5 px-3 text-center">{r.level_required}/5</td>
                    <td className="py-1.5 px-3">
                      <span
                        className="rounded-md px-2 py-0.5 text-xs font-bold uppercase"
                        style={{
                          background:
                            r.priority === "must"
                              ? "rgba(220,38,38,0.15)"
                              : r.priority === "good"
                                ? "rgba(184,121,31,0.15)"
                                : "rgba(148,163,184,0.15)",
                          color:
                            r.priority === "must"
                              ? "#ef4444"
                              : r.priority === "good"
                                ? "#b7791f"
                                : "#94a3b8",
                        }}
                      >
                        {r.priority}
                      </span>
                    </td>
                    <td className="py-1.5 pl-3 text-[var(--sf-muted)]">{r.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        ) : (
          <p className="sf-muted mt-2 text-sm">No specific skills listed for this role.</p>
        )}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <h3 className="text-lg">Required Tools &amp; Technologies</h3>
          {req.tools.length > 0 ? (
            <ul className="mt-2 space-y-1 text-sm">
              {req.tools.map((tool) => (
                <li key={tool} className="font-semibold">
                  • {tool}
                </li>
              ))}
            </ul>
          ) : (
            <p className="sf-muted mt-2 text-sm">No specific tools specified.</p>
          )}
        </div>
        <div>
          <h3 className="text-lg">Recommended Certifications</h3>
          {req.certs.length > 0 ? (
            <ul className="mt-2 space-y-1 text-sm">
              {req.certs.map((cert) => (
                <li key={cert} className="font-semibold">
                  • {cert}
                </li>
              ))}
            </ul>
          ) : (
            <p className="sf-muted mt-2 text-sm">No specific certifications required.</p>
          )}
        </div>
      </div>

      <div>
        <h3 className="text-lg">Interview Process</h3>
        {req.interview_process.length > 0 ? (
          <ol className="mt-2 space-y-2 text-sm">
            {req.interview_process.map((stage, i) => (
              <li key={i}>
                <strong>Step {i + 1}:</strong> {stage}
              </li>
            ))}
          </ol>
        ) : (
          <p className="sf-muted mt-2 text-sm">
            Standard technical and behavioral interview process.
          </p>
        )}
      </div>

      <div>
        <h3 className="text-lg">Additional Recommendations</h3>
        {recommendations.length > 0 ? (
          <div className="mt-2 space-y-3">
            {recommendations.map((rec, i) => (
              <Card key={i} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <strong>{rec.title}</strong>{" "}
                    <code className="ml-1 rounded bg-[var(--sf-pill-bg)] px-1.5 py-0.5 text-xs text-[var(--sf-pill-text)]">
                      {rec.type.replace("_", " ").toLowerCase()}
                    </code>
                  </div>
                  <span className="sf-muted shrink-0 text-xs">
                    ⏱️ Effort: ~{rec.effort_hours}h
                  </span>
                </div>
                <p className="mt-1.5 text-sm text-[var(--sf-muted)]">{rec.why}</p>
              </Card>
            ))}
          </div>
        ) : (
          <p className="sf-muted mt-2 text-sm">No additional recommendations generated yet.</p>
        )}
      </div>
    </div>
  );
}
