import { useState } from "react";
import { api, ApiError } from "../api";
import { Alert, Card, Pill } from "../components/ui";

interface SessionResponse {
  username: string | null;
  fixture_mode: boolean;
}

/**
 * Authentication screen: sign in, create account, and (in fixture mode)
 * one-click demo access. Mirrors _render_auth() from the old app.py.
 */
export default function AuthPage({ onAuthed }: { onAuthed: (s: SessionResponse) => void }) {
  const [tab, setTab] = useState<"login" | "signup">("login");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [loginUser, setLoginUser] = useState("");
  const [loginPass, setLoginPass] = useState("");

  const [signUser, setSignUser] = useState("");
  const [signPass, setSignPass] = useState("");
  const [signConfirm, setSignConfirm] = useState("");

  async function finish(fn: () => Promise<SessionResponse>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const session = await fn();
      onAuthed(session);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const signIn = () => {
    if (!loginUser.trim() || !loginPass) {
      setError("Please enter both username and password.");
      return;
    }
    return finish(() =>
      api.post<SessionResponse>("/auth/login", {
        username: loginUser.trim(),
        password: loginPass,
      }),
    );
  };

  const signUp = () => {
    if (!signUser.trim()) {
      setError("Please choose a username.");
      return;
    }
    if (signPass.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    if (signPass !== signConfirm) {
      setError("Passwords do not match.");
      return;
    }
    return finish(() =>
      api.post<SessionResponse>("/auth/signup", {
        username: signUser.trim(),
        password: signPass,
      }),
    );
  };

  const demo = () => finish(() => api.post<SessionResponse>("/auth/demo"));

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1>SkillForce: Career Accelerator</h1>
      <p className="sf-muted mt-1">
        Sign in or create an account to build your personalized career roadmap.
      </p>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-bold">Welcome to SkillForce</h2>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed">
              <li>
                <strong>Create your account</strong> and sign in securely.
              </li>
              <li>
                <strong>Complete your profile</strong> with skills, experience, and target role.
              </li>
              <li>
                <strong>Generate your personalized roadmap</strong> and track progress with
                assessments.
              </li>
            </ol>
            <div className="mt-4">
              <Alert kind="info">Your profile and progress are saved to your account.</Alert>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-2">
              <Pill>Demo access</Pill>
            </div>
            <p className="sf-muted mt-2">
              Use the demo account to explore the app quickly with sample data.
            </p>
            <button
              className="sf-btn mt-3 w-full"
              onClick={demo}
              disabled={busy}
              data-testid="demo-login"
            >
              Continue with demo account
            </button>
          </Card>
        </div>

        <Card className="p-6">
          <div className="flex gap-2 border-b border-[var(--sf-border)] pb-3">
            {(["login", "signup"] as const).map((t) => (
              <button
                key={t}
                onClick={() => {
                  setTab(t);
                  setError(null);
                }}
                className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                  tab === t
                    ? "bg-[var(--sf-pill-bg)] text-[var(--sf-tab-active)]"
                    : "text-[var(--sf-muted)] hover:text-[var(--sf-text)]"
                }`}
              >
                {t === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <div className="mt-5 space-y-4">
            {error && <Alert kind="error">{error}</Alert>}
            {notice && <Alert kind="success">{notice}</Alert>}

            {tab === "login" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void signIn();
                }}
                className="space-y-4"
              >
                <div>
                  <label className="sf-label">Username</label>
                  <input
                    className="sf-input"
                    placeholder="e.g. aarav"
                    value={loginUser}
                    onChange={(e) => setLoginUser(e.target.value)}
                    autoComplete="username"
                  />
                </div>
                <div>
                  <label className="sf-label">Password</label>
                  <input
                    className="sf-input"
                    type="password"
                    value={loginPass}
                    onChange={(e) => setLoginPass(e.target.value)}
                    autoComplete="current-password"
                  />
                </div>
                <button className="sf-btn sf-btn-primary w-full" disabled={busy} type="submit">
                  {busy ? "Signing in…" : "Sign in"}
                </button>
              </form>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void signUp();
                }}
                className="space-y-4"
              >
                <div>
                  <label className="sf-label">Username</label>
                  <input
                    className="sf-input"
                    placeholder="Choose a username"
                    value={signUser}
                    onChange={(e) => setSignUser(e.target.value)}
                    autoComplete="username"
                  />
                </div>
                <div>
                  <label className="sf-label">Password</label>
                  <input
                    className="sf-input"
                    type="password"
                    value={signPass}
                    onChange={(e) => setSignPass(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
                <div>
                  <label className="sf-label">Confirm password</label>
                  <input
                    className="sf-input"
                    type="password"
                    value={signConfirm}
                    onChange={(e) => setSignConfirm(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
                <button className="sf-btn sf-btn-primary w-full" disabled={busy} type="submit">
                  {busy ? "Creating account…" : "Create account"}
                </button>
              </form>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
