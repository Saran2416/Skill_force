import { useMemo, useState } from "react";
import { api, ApiError } from "../api";
import type { AppState, Quiz, ScoreResponse, ScoreResult } from "../types";
import { Alert, Card, Metric } from "../components/ui";
import { Select } from "../components/inputs";

interface Props {
  state: AppState;
  explanation: string;
  onDone: (resp: ScoreResponse) => void;
  clearFlash: () => void;
}

export default function AssessmentTab({ state, explanation, onDone, clearFlash }: Props) {
  const candidateSkills = useMemo(() => {
    const names: string[] = [];
    state.profile.skills.forEach((s) => names.push(s.name));
    state.requirements?.requirements.forEach((r) => names.push(r.skill));
    state.roadmap?.steps.forEach((s) => names.push(s.skill));
    const unique = [...new Set(names.map((s) => s.trim()).filter(Boolean))];
    return unique.length > 0 ? unique : ["Python", "SQL", "JavaScript", "HTML"];
  }, [state]);

  const [skill, setSkill] = useState(candidateSkills[0]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [quizSkill, setQuizSkill] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [simScore, setSimScore] = useState(75);
  const [lastResult, setLastResult] = useState<ScoreResult | null>(null);
  const [busy, setBusy] = useState<"quiz" | "sim" | "submit" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentLevel = (() => {
    const target = skill.trim().toLowerCase();
    return state.profile.skills.find((s) => s.name.trim().toLowerCase() === target)?.level ?? 0;
  })();

  const quizMatchesSelection =
    quiz !== null &&
    quiz.questions.length > 0 &&
    (!quizSkill || quizSkill.trim().toLowerCase() === skill.trim().toLowerCase());

  const flash = (msg: string | null) => {
    clearFlash();
    setError(msg);
  };

  const generateQuiz = async () => {
    flash(null);
    setBusy("quiz");
    try {
      const resp = await api.post<{ quiz: Quiz }>("/assessment/quiz/generate", { skill });
      setQuiz(resp.quiz);
      setQuizSkill(skill);
      setAnswers({});
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to generate quiz.");
    } finally {
      setBusy(null);
    }
  };

  const submitSimulated = async () => {
    flash(null);
    setBusy("sim");
    try {
      const resp = await api.post<ScoreResponse>("/assessment/simulate", {
        skill,
        percent: simScore,
      });
      setLastResult(resp.result);
      onDone(resp);
      if (resp.error) setError(resp.error);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to simulate score.");
    } finally {
      setBusy(null);
    }
  };

  const submitQuiz = async () => {
    if (!quiz) return;
    flash(null);
    setBusy("submit");
    try {
      const ordered = quiz.questions.map((q) => answers[q.id] ?? 0);
      const resp = await api.post<ScoreResponse>("/assessment/quiz/submit", {
        quiz,
        answers: ordered,
      });
      setLastResult(resp.result);
      onDone(resp);
      setQuiz(null);
      setQuizSkill(null);
      setAnswers({});
      if (resp.error) setError(resp.error);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to submit quiz.");
    } finally {
      setBusy(null);
    }
  };

  const showFeedback = lastResult !== null || Boolean(explanation);

  return (
    <div className="sf-animate max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl">Skill Assessment &amp; Verification</h2>
        <p className="sf-muted">
          Validate your proficiency with quizzes or simulations and update your learning plan.
        </p>
      </div>

      {error && <Alert kind="error">{error}</Alert>}

      <div className="grid items-end gap-4 md:grid-cols-[2fr_1fr]">
        <div>
          <label className="sf-label">Select Skill to Assess</label>
          <Select
            value={skill}
            onChange={(v) => {
              setSkill(v);
              flash(null);
            }}
            options={candidateSkills}
            ariaLabel="Select Skill to Assess"
          />
        </div>
        <Metric label="Current Level" value={`${currentLevel}/5`} />
      </div>

      <hr className="border-[var(--sf-border)]" />

      <div className="grid gap-6 md:grid-cols-2">
        {/* --- quiz --- */}
        <Card className="p-5">
          <h3 className="text-lg">📝 Take Live Quiz</h3>
          <p className="sf-muted mt-1 text-sm">
            Generate a tailored 5-question multiple choice assessment.
          </p>
          <button
            className="sf-btn mt-3 w-full"
            disabled={busy !== null}
            onClick={() => void generateQuiz()}
          >
            {busy === "quiz" ? "Generating quiz…" : "Generate Quiz"}
          </button>
          {quiz && (
            <button
              className="sf-btn mt-2 w-full"
              onClick={() => {
                setQuiz(null);
                setQuizSkill(null);
                setAnswers({});
                flash(null);
              }}
            >
              Clear Active Quiz
            </button>
          )}
        </Card>

        {/* --- simulation --- */}
        <Card className="p-5">
          <h3 className="text-lg">🎚️ Simulate Score</h3>
          <p className="sf-muted mt-1 text-sm">
            Simulate an assessment outcome to test roadmap and gap impact.
          </p>
          <div className="mt-4">
            <div className="flex items-center justify-between">
              <label className="sf-label mb-0" htmlFor="sim-score">
                Simulated Score %
              </label>
              <span className="text-sm font-bold">{simScore}%</span>
            </div>
            <input
              id="sim-score"
              type="range"
              min={0}
              max={100}
              step={5}
              value={simScore}
              onChange={(e) => setSimScore(Number(e.target.value))}
              className="mt-2 w-full accent-[var(--sf-accent)]"
            />
          </div>
          <button
            className="sf-btn sf-btn-primary mt-4 w-full"
            disabled={busy !== null}
            onClick={() => void submitSimulated()}
          >
            {busy === "sim" ? "Calculating…" : "Submit Simulated Score"}
          </button>
        </Card>
      </div>

      {/* active quiz */}
      {quiz && !quizMatchesSelection && quizSkill && (
        <Alert kind="info">
          An active quiz for <strong>{quizSkill}</strong> is available. Select that skill to
          continue, or clear the active quiz.
        </Alert>
      )}

      {quiz && quizMatchesSelection && (
        <Card className="p-5">
          <h3 className="text-lg">
            Assessment for <strong>{quiz.skill}</strong>
          </h3>
          <div className="mt-4 space-y-5">
            {quiz.questions.map((q, idx) => (
              <div key={q.id}>
                <p className="text-sm font-semibold">
                  Question {idx + 1}: {q.q}
                </p>
                <div className="mt-2 space-y-1.5">
                  {q.options.map((opt, i) => (
                    <label
                      key={i}
                      className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
                        answers[q.id] === i
                          ? "border-[var(--sf-accent)] bg-[var(--sf-pill-bg)]"
                          : "border-[var(--sf-border)] hover:border-[var(--sf-accent)]/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name={q.id}
                        checked={answers[q.id] === i}
                        onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: i }))}
                      />
                      <span>{opt}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button
              className="sf-btn sf-btn-primary w-full"
              disabled={busy !== null}
              onClick={() => void submitQuiz()}
            >
              {busy === "submit" ? "Scoring answers…" : "Submit Quiz Answers"}
            </button>
          </div>
        </Card>
      )}

      {/* latest feedback */}
      {showFeedback && (
        <>
          <hr className="border-[var(--sf-border)]" />
          <div>
            <h3 className="text-lg">Latest Assessment Feedback</h3>
            {lastResult && (
              <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <Metric label="Score" value={`${Number(lastResult.score_percent).toLocaleString()}%`} />
                <Metric label="Updated Skill Level" value={`${lastResult.new_level}/5`} />
                <Metric
                  label="Status"
                  value={lastResult.weak ? "⚠️ Weak (Needs Revision)" : "✅ Proficient"}
                />
              </div>
            )}
            {explanation && (
              <div className="mt-4">
                <Alert kind="info">
                  <strong>Mentor Insights &amp; System Changes:</strong>
                  <p className="mt-1.5 whitespace-pre-wrap">{explanation}</p>
                </Alert>
              </div>
            )}
          </div>
        </>
      )}

      {/* history */}
      {state.scores.length > 0 && (
        <>
          <hr className="border-[var(--sf-border)]" />
          <div>
            <h3 className="text-lg">Assessment History</h3>
            <Card className="mt-2 overflow-x-auto p-4">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-[var(--sf-border)] text-left">
                    <th className="py-1.5 pr-3">Skill</th>
                    <th className="py-1.5 px-3">Score %</th>
                    <th className="py-1.5 px-3">Assigned Level</th>
                    <th className="py-1.5 pl-3">Weak Area</th>
                  </tr>
                </thead>
                <tbody>
                  {[...state.scores].reverse().map((score, i) => (
                    <tr key={i} className="border-b border-[var(--sf-border)]/50">
                      <td className="py-1.5 pr-3">{score.skill}</td>
                      <td className="py-1.5 px-3">
                        {Number(score.score_percent).toLocaleString()}%
                      </td>
                      <td className="py-1.5 px-3">{score.new_level}/5</td>
                      <td className="py-1.5 pl-3">{score.weak ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
