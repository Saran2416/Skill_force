import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { SessionResponse, StateResponse, Theme } from "./types";
import AuthPage from "./pages/AuthPage";
import AppShell from "./shell/AppShell";
import { Spinner } from "./components/ui";

function applyTheme(theme: Theme) {
  document.documentElement.classList.remove("theme-dark", "theme-light");
  document.documentElement.classList.add(theme === "Dark" ? "theme-dark" : "theme-light");
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("sf_theme") as Theme | null) ?? "Dark",
  );
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [data, setData] = useState<StateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fatal, setFatal] = useState<string | null>(null);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem("sf_theme", theme);
  }, [theme]);

  const refresh = useCallback(async () => {
    try {
      const next = await api.get<StateResponse>("/state");
      setData(next);
      setFatal(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setSession(null);
        setData(null);
      } else {
        setFatal(e instanceof Error ? e.message : "Failed to load your session.");
      }
    }
  }, []);

  // Bootstrap: is there an existing session (cookie or auto-auth)?
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.get<SessionResponse>("/auth/session");
        if (cancelled) return;
        setSession(s);
        if (s.username) await refresh();
      } catch (e) {
        if (!cancelled) setFatal(e instanceof Error ? e.message : "Cannot reach the API.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const onAuthed = useCallback(
    async (s: SessionResponse) => {
      setSession(s);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* clearing locally is enough */
    }
    setSession(null);
    setData(null);
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Loading SkillForce…" />
      </div>
    );
  }

  if (fatal) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="sf-card max-w-lg p-6 text-center">
          <h2 className="text-lg font-bold">Cannot reach the SkillForce API</h2>
          <p className="sf-muted mt-2">{fatal}</p>
          <p className="sf-muted mt-1">
            Start the backend with <code>uvicorn server.app:app --reload</code>, then refresh.
          </p>
        </div>
      </div>
    );
  }

  if (!session?.username || !data) {
    return <AuthPage onAuthed={onAuthed} />;
  }

  return (
    <AppShell
      data={data}
      theme={theme}
      onThemeChange={setTheme}
      onRefresh={refresh}
      onLogout={logout}
    />
  );
}
