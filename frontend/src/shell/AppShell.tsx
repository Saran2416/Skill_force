import { useEffect, useMemo, useState } from "react";
import type { AppState, MutationResponse, StateResponse, Theme } from "../types";
import { Alert, Card, Metric, Pill } from "../components/ui";
import { Select } from "../components/inputs";
import DashboardTab from "../tabs/DashboardTab";
import ProfileTab from "../tabs/ProfileTab";
import RequirementsTab from "../tabs/RequirementsTab";
import GapTab from "../tabs/GapTab";
import RoadmapTab from "../tabs/RoadmapTab";
import AssessmentTab from "../tabs/AssessmentTab";
import MentorTab from "../tabs/MentorTab";

const TABS = [
  "Dashboard",
  "Profile",
  "Requirements",
  "Gap",
  "Roadmap",
  "Assessment",
  "Mentor",
] as const;
type Tab = (typeof TABS)[number];

function isProfileComplete(state: AppState): boolean {
  const p = state.profile;
  return Boolean(
    (p.target_role ?? "").trim() && (p.name ?? "").trim() && p.skills.length,
  );
}

export default function AppShell({
  data,
  theme,
  onThemeChange,
  onLogout,
}: {
  data: StateResponse;
  theme: Theme;
  onThemeChange: (t: Theme) => void;
  onRefresh: () => Promise<void>;
  onLogout: () => Promise<void>;
}) {
  const [view, setView] = useState<StateResponse>(data);
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setView(data), [data]);

  const state = view.state;
  const profileReady = view.profile_ready;

  // After any mutation, merge the server's new state into the local view.
  const applyMutation = (resp: MutationResponse) => {
    setView({
      ...view,
      state: resp.state,
      latest_explanation: resp.latest_explanation,
      profile_ready: isProfileComplete(resp.state),
    });
    if (resp.error) {
      setError(resp.error);
      setNotice(null);
    } else {
      setError(null);
    }
  };

  const clearFlash = () => {
    setNotice(null);
    setError(null);
  };

  const profile = state.profile;
  const targetRole = profile.target_role || "Not set";
  const targetCompany = profile.target_company || "Any company";
  const modeLabel = view.fixture_mode ? "Sample fixture" : "Authenticated account";

  const logEntries = useMemo(() => [...state.log].slice(-30).reverse(), [state.log]);

  return (
    <div className="flex min-h-screen">
      {/* ------------------------------------------------ sidebar */}
      <aside className="sticky top-0 flex h-screen w-72 shrink-0 flex-col overflow-y-auto border-r border-[var(--sf-border)] bg-[linear-gradient(180deg,var(--sf-bg-2)_0%,var(--sf-bg)_100%)] px-4 py-5">
        <h1 className="text-xl">🧭 SkillForce</h1>
        <p className="sf-muted mb-4">Agentic Career Acceleration &amp; Upskilling Platform</p>

        <label className="sf-label">Appearance</label>
        <Select
          value={theme}
          onChange={(v) => onThemeChange(v as Theme)}
          options={["Dark", "Light"]}
          ariaLabel="Appearance"
        />

        <div className="mt-4">
          <Pill>{modeLabel}</Pill>
        </div>

        <Card className="mt-4 p-4">
          <div className="text-sm">
            <div className="font-semibold">Learner</div>
            <div className="mb-2 text-[var(--sf-text)]">{profile.name || view.username}</div>
            <div className="font-semibold">Account</div>
            <div className="mb-2 break-all">{view.username}</div>
            <div className="font-semibold">Target</div>
            <div className="break-words">
              {targetRole} · {targetCompany}
            </div>
          </div>
          {state.gap && (
            <div className="mt-3">
              <Metric
                label="Readiness"
                value={`${Number(state.gap.match_percent).toLocaleString()}%`}
              />
            </div>
          )}
        </Card>

        {!view.fixture_mode && (
          <button className="sf-btn mt-4 w-full" onClick={() => void onLogout()}>
            Log out
          </button>
        )}

        <hr className="my-4 border-[var(--sf-border)]" />

        <h2 className="text-base">📋 Agent Activity Log</h2>
        <p className="sf-muted mb-2">Real-time audit log of agent operations (newest first).</p>

        <div className="sf-scroll flex-1 space-y-2 overflow-y-auto pr-1">
          {logEntries.length === 0 && (
            <p className="sf-muted">No agent activity logged yet.</p>
          )}
          {logEntries.map((entry, idx) => (
            <Card key={`${entry.timestamp}-${idx}`} className="p-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <code className="font-bold text-[var(--sf-accent)]">{entry.agent}</code>
                <span className="text-xs text-[var(--sf-muted)]">
                  {entry.timestamp ? entry.timestamp.slice(0, 19).replace("T", " ") : ""}
                </span>
              </div>
              <div className="mt-1 italic text-[var(--sf-muted)]">{entry.action}</div>
              <div className="mt-0.5 break-words">{entry.reason}</div>
            </Card>
          ))}
          {state.log.length > 30 && (
            <p className="sf-muted">Showing latest 30 of {state.log.length} log entries.</p>
          )}
        </div>
      </aside>

      {/* ------------------------------------------------ main */}
      <main className="min-w-0 flex-1 px-8 py-6">
        <h1>SkillForce: Career Accelerator</h1>
        <p className="sf-muted mb-5">
          Analyze your profile, close skill gaps, and adapt your roadmap with confidence.
        </p>

        {notice && (
          <div className="mb-4">
            <Alert kind="success">{notice}</Alert>
          </div>
        )}
        {error && (
          <div className="mb-4">
            <Alert kind="error">{error}</Alert>
          </div>
        )}

        {!profileReady ? (
          <>
            <Alert kind="info">
              Complete your profile first to unlock your personalized dashboard, requirements,
              gap analysis, and roadmap. Add your name, skills, and target role, then click{" "}
              <strong>Save Profile</strong>.
            </Alert>
            <div className="mt-5">
              <ProfileTab
                state={state}
                userId={view.username}
                onDone={(resp) => {
                  applyMutation(resp);
                  setNotice("Profile saved successfully. Your personalized roadmap is ready.");
                  if (isProfileComplete(resp.state)) setTab("Dashboard");
                }}
                clearFlash={clearFlash}
              />
            </div>
          </>
        ) : (
          <>
            <nav className="flex gap-2 border-b border-[var(--sf-border)] pb-1">
              {TABS.map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setTab(t);
                    clearFlash();
                  }}
                  className={`rounded-t-lg px-4 py-2.5 text-sm font-semibold transition ${
                    tab === t
                      ? "border-b-2 border-[var(--sf-tab-active)] text-[var(--sf-tab-active)]"
                      : "text-[var(--sf-muted)] hover:text-[var(--sf-text)]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </nav>

            <div className="mt-5">
              {tab === "Dashboard" && <DashboardTab state={state} />}
              {tab === "Profile" && (
                <ProfileTab
                  state={state}
                  userId={view.username}
                  onDone={(resp) => {
                    applyMutation(resp);
                    setNotice(
                      "Profile saved successfully. Your personalized roadmap is ready.",
                    );
                  }}
                  clearFlash={clearFlash}
                />
              )}
              {tab === "Requirements" && <RequirementsTab state={state} />}
              {tab === "Gap" && <GapTab state={state} />}
              {tab === "Roadmap" && <RoadmapTab state={state} />}
              {tab === "Assessment" && (
                <AssessmentTab
                  state={state}
                  explanation={view.latest_explanation}
                  onDone={(resp) => {
                    applyMutation(resp);
                    setNotice(null);
                  }}
                  clearFlash={clearFlash}
                />
              )}
              {tab === "Mentor" && (
                <MentorTab
                  state={state}
                  explanation={view.latest_explanation}
                  onDone={(resp) => {
                    applyMutation(resp);
                    setNotice(null);
                  }}
                  clearFlash={clearFlash}
                />
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
