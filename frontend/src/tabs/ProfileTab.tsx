import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { AppState, MetaResponse, MutationResponse } from "../types";
import { Alert, Card } from "../components/ui";
import { MultiSelect, Select } from "../components/inputs";

interface Props {
  state: AppState;
  userId: string;
  onDone: (resp: MutationResponse) => void;
  clearFlash: () => void;
}

function isFreshProfile(state: AppState, userId: string): boolean {
  const p = state.profile;
  const name = (p.name ?? "").trim();
  const hasData = Boolean(
    p.skills.length ||
      p.certs.length ||
      p.projects.length ||
      (p.target_role ?? "").trim() ||
      p.target_company ||
      state.requirements ||
      state.gap ||
      state.roadmap ||
      state.scores.length,
  );
  return !hasData && (!name || name === userId);
}

/**
 * Learner profile form. The dictionaries (skills/certs/roles/companies) come
 * from /api/meta; the form is hydrated from AppState once, then edits are
 * local until Save Profile posts everything back to /api/profile/save.
 */
export default function ProfileTab({ state, userId, onDone, clearFlash }: Props) {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillLevels, setSkillLevels] = useState<Record<string, number>>({});
  const [customSkills, setCustomSkills] = useState("");
  const [selectedCerts, setSelectedCerts] = useState<string[]>([]);
  const [customCerts, setCustomCerts] = useState("");
  const [projects, setProjects] = useState("");
  const [role, setRole] = useState("");
  const [companyChoice, setCompanyChoice] = useState("");
  const [customCompany, setCustomCompany] = useState("");
  const [customCompanyActive, setCustomCompanyActive] = useState(false);

  // Load dropdown dictionaries once, then hydrate the form from AppState.
  useEffect(() => {
    let cancelled = false;
    api
      .get<MetaResponse>("/meta")
      .then((m) => {
        if (cancelled) return;
        setMeta(m);
        if (!isFreshProfile(state, userId)) {
          const knownSkills = new Set(m.known_skills.map((s) => s.trim().toLowerCase()));
          const knownCerts = new Set(m.known_certs);
          const existing = state.profile.skills;

          setSelectedSkills(
            existing
              .filter((s) => knownSkills.has(s.name.trim().toLowerCase()))
              .map((s) => s.name),
          );
          setSkillLevels(
            Object.fromEntries(existing.map((s) => [s.name.trim().toLowerCase(), s.level])),
          );
          setCustomSkills(
            existing
              .filter((s) => !knownSkills.has(s.name.trim().toLowerCase()))
              .map((s) => `${s.name}: ${s.level}`)
              .join("\n"),
          );
          setSelectedCerts(state.profile.certs.filter((c) => knownCerts.has(c)));
          setCustomCerts(state.profile.certs.filter((c) => !knownCerts.has(c)).join("\n"));
          setProjects((state.profile.projects ?? []).join("\n"));
          setName(state.profile.name ?? "");
          setRole(state.profile.target_role ?? "");

          const stored = state.profile.target_company;
          if (stored) {
            if (m.companies.includes(stored)) {
              setCompanyChoice(stored);
            } else {
              setCompanyChoice("Other...");
              setCustomCompanyActive(true);
              setCustomCompany(stored);
            }
          }
        }
        setHydrated(true);
      })
      .catch((e) => {
        if (!cancelled) {
          setLocalError(e instanceof ApiError ? e.message : "Failed to load options.");
          setHydrated(true);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!meta || !hydrated) {
    return <p className="sf-muted">Loading profile options…</p>;
  }

  const companyOptions = [...meta.companies, "Other..."];
  const finalCompany =
    companyChoice === "Other..." ? customCompany.trim() || null : companyChoice || null;

  const submit = async () => {
    clearFlash();
    setLocalError(null);
    if (!name.trim()) {
      setLocalError("Please enter your full name.");
      return;
    }
    if (!role.trim()) {
      setLocalError("Please select a target role to generate your personalized roadmap.");
      return;
    }
    const payloadSkills = selectedSkills.map((skillName) => ({
      name: skillName,
      level: skillLevels[skillName.trim().toLowerCase()] ?? 3,
    }));
    if (payloadSkills.length === 0 && !customSkills.trim()) {
      setLocalError("Please select or add at least one skill so we can personalize your roadmap.");
      return;
    }

    setSaving(true);
    try {
      const resp = await api.post<MutationResponse>("/profile/save", {
        name,
        selected_skills: payloadSkills,
        custom_skills_text: customSkills,
        selected_certs: selectedCerts,
        custom_certs_text: customCerts,
        projects_text: projects,
        target_role: role,
        target_company: finalCompany,
      });
      onDone(resp);
    } catch (e) {
      setLocalError(e instanceof ApiError ? e.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="sf-animate max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl">Learner Profile</h2>
        <p className="sf-muted">
          Fill in your details to generate a personalized roadmap tailored to your goals.
        </p>
      </div>

      {localError && <Alert kind="error">{localError}</Alert>}

      <Card className="p-5">
        <h3 className="text-base font-bold">Personal Details</h3>
        <div className="mt-3">
          <label className="sf-label">Full Name</label>
          <input
            className="sf-input"
            placeholder="Enter your full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-base font-bold">Skills &amp; Experience</h3>
        <p className="sf-muted mt-1 text-sm">
          Select skills and proficiency levels from the dictionary, and add any custom skills if
          needed.
        </p>

        <div className="mt-4">
          <label className="sf-label">Select skills</label>
          <MultiSelect
            values={selectedSkills}
            onChange={setSelectedSkills}
            options={meta.known_skills}
            placeholder="Choose skills from the list"
            searchable
          />
        </div>

        {selectedSkills.length > 0 && (
          <div className="mt-4">
            <p className="font-semibold">Skill levels</p>
            <div className="mt-2 grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
              {selectedSkills.map((skillName) => {
                const key = skillName.trim().toLowerCase();
                const level = skillLevels[key] ?? 3;
                return (
                  <div key={skillName} className="flex items-center gap-3">
                    <span className="min-w-0 flex-1 truncate text-sm">{skillName}</span>
                    <select
                      className="sf-select w-40"
                      value={String(level)}
                      aria-label={`${skillName} level`}
                      onChange={(e) =>
                        setSkillLevels((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                      }
                    >
                      {[0, 1, 2, 3, 4, 5].map((n) => (
                        <option key={n} value={n}>
                          {n}
                          {n === 0 ? " (none)" : n === 5 ? " (expert)" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-4">
          <label className="sf-label">Additional/custom skills</label>
          <textarea
            className="sf-textarea"
            rows={4}
            placeholder={"Figma: 2\nPublic Speaking: 4"}
            value={customSkills}
            onChange={(e) => setCustomSkills(e.target.value)}
          />
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="sf-label">Select certifications</label>
            <MultiSelect
              values={selectedCerts}
              onChange={setSelectedCerts}
              options={meta.known_certs}
              placeholder="Choose certifications from the list"
              searchable
            />
            <label className="sf-label mt-3">Additional/custom certifications</label>
            <textarea
              className="sf-textarea"
              rows={3}
              placeholder={"Scrum Master (CSM)\nCompany-specific certification"}
              value={customCerts}
              onChange={(e) => setCustomCerts(e.target.value)}
            />
          </div>
          <div>
            <label className="sf-label">Key Projects</label>
            <textarea
              className="sf-textarea h-[228px]"
              placeholder={"Personal portfolio website\nSales dashboard in Excel"}
              value={projects}
              onChange={(e) => setProjects(e.target.value)}
            />
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="text-base font-bold">Career Target</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="sf-label">Target Role</label>
            <Select
              value={role}
              onChange={setRole}
              options={meta.roles}
              placeholder="Select a target role"
              ariaLabel="Target Role"
            />
          </div>
          <div>
            <label className="sf-label">Target Company</label>
            <Select
              value={companyChoice}
              onChange={(v) => {
                setCompanyChoice(v);
                setCustomCompanyActive(v === "Other...");
              }}
              options={companyOptions}
              placeholder="Select a target company"
              ariaLabel="Target Company"
            />
            {customCompanyActive && (
              <div className="mt-3">
                <label className="sf-label">Specify Company Name</label>
                <input
                  className="sf-input"
                  placeholder="e.g. Acme Corp"
                  value={customCompany}
                  onChange={(e) => setCustomCompany(e.target.value)}
                />
              </div>
            )}
          </div>
        </div>
        {!role && (
          <p className="mt-3 text-sm font-medium text-amber-500">
            ⚠ Select a target role to generate your personalized roadmap.
          </p>
        )}
      </Card>

      <button
        className="sf-btn sf-btn-primary w-full"
        disabled={saving}
        onClick={() => void submit()}
      >
        {saving ? "Saving profile and generating your personalized roadmap…" : "Save Profile"}
      </button>
    </div>
  );
}
