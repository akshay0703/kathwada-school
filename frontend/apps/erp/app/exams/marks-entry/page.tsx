"use client";

import {
  api,
  ApiError,
  type ClassSection,
  type CurrentUser,
  type Enrollment,
  type ExamListItem,
  type ExamSubject,
  type Subject,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function MarksEntryPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [classSections, setClassSections] = useState<ClassSection[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  const [examId, setExamId] = useState("");
  const [classSectionId, setClassSectionId] = useState("");
  const [subjectId, setSubjectId] = useState("");

  const [examSubject, setExamSubject] = useState<ExamSubject | null>(null);
  const [lookupDone, setLookupDone] = useState(false);
  const [maxMarksInput, setMaxMarksInput] = useState("");
  const [configuring, setConfiguring] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  const [roster, setRoster] = useState<{ enrollment: Enrollment; marksId: number | null; value: string }[]>([]);
  const [loadingRoster, setLoadingRoster] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch(() => router.replace("/login"))
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  useEffect(() => {
    if (checking) return;
    let cancelled = false;
    async function run() {
      try {
        const [examsPage, csPage, subjectsPage] = await Promise.all([
          api.exams.list(),
          api.classSections.list(),
          api.subjects.list(),
        ]);
        if (!cancelled) {
          setExams(examsPage.results);
          setClassSections(csPage.results);
          setSubjects(subjectsPage.results);
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not load filters.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking]);

  useEffect(() => {
    if (checking || !examId || !classSectionId || !subjectId) return;
    let cancelled = false;
    async function run() {
      setLoadError(null);
      setConfigError(null);
      setLookupDone(false);
      setExamSubject(null);
      setRoster([]);
      try {
        const page = await api.examSubjects.list({ exam: Number(examId), class_section: Number(classSectionId) });
        if (cancelled) return;
        const match = page.results.find((es) => es.subject === Number(subjectId)) ?? null;
        setExamSubject(match);
        setLookupDone(true);
        if (match) {
          await loadRoster(match);
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not check exam configuration.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking, examId, classSectionId, subjectId]);

  async function loadRoster(es: ExamSubject) {
    setLoadingRoster(true);
    setSaveSuccess(false);
    try {
      const [enrollmentsPage, marksPage] = await Promise.all([
        api.enrollments.list({ class_section: es.class_section, status: "active" }),
        api.marks.list({ exam_subject: es.id }),
      ]);
      const marksByStudent: Record<number, { id: number; marks_obtained: string }> = {};
      marksPage.results.forEach((m) => {
        marksByStudent[m.student] = { id: m.id, marks_obtained: m.marks_obtained };
      });
      setRoster(
        enrollmentsPage.results.map((enrollment) => ({
          enrollment,
          marksId: marksByStudent[enrollment.student]?.id ?? null,
          value: marksByStudent[enrollment.student]?.marks_obtained ?? "",
        }))
      );
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not load the roster.");
    } finally {
      setLoadingRoster(false);
    }
  }

  async function handleCreateConfig(e: React.FormEvent) {
    e.preventDefault();
    if (!maxMarksInput) return;
    setConfiguring(true);
    setConfigError(null);
    try {
      const created = await api.examSubjects.create({
        exam: Number(examId),
        class_section: Number(classSectionId),
        subject: Number(subjectId),
        max_marks: maxMarksInput,
      });
      setExamSubject(created);
      await loadRoster(created);
    } catch (err) {
      setConfigError(err instanceof ApiError ? err.message : "Could not create this configuration.");
    } finally {
      setConfiguring(false);
    }
  }

  function setValue(studentId: number, value: string) {
    setRoster((prev) => prev.map((r) => (r.enrollment.student === studentId ? { ...r, value } : r)));
  }

  async function handleSaveAll() {
    if (!examSubject) return;
    const records = roster.filter((r) => r.value !== "").map((r) => ({ student: r.enrollment.student, marks_obtained: r.value }));
    if (records.length === 0) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await api.marks.bulkSave({ exam_subject: examSubject.id, records });
      setSaveSuccess(true);
      await loadRoster(examSubject);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save marks.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSingleEdit(studentId: number, value: string) {
    setValue(studentId, value);
    const row = roster.find((r) => r.enrollment.student === studentId);
    if (!row?.marksId || value === "") return;
    try {
      await api.marks.update(row.marksId, { marks_obtained: value });
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not update this mark.");
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="marks"). See
  // docs/permissions.md's "Marks Entry" row: Admin VCEDX, Principal VE (no
  // Create), Teacher VCE (own classes/subjects only, enforced server-side
  // via TeacherAssignment), Staff none at all.
  const canEnterMarks = Boolean(user?.is_superuser || ["Admin", "Teacher"].includes(user?.role ?? ""));
  const canEditExisting = Boolean(canEnterMarks || user?.role === "Principal");

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "900px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/exams" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Exams
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Marks entry</h1>
      </header>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Exam
          <select value={examId} onChange={(e) => setExamId(e.target.value)} style={{ ...inputStyle, minWidth: "180px" }}>
            <option value="">Select…</option>
            {exams.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name} ({ex.academic_year_label})
              </option>
            ))}
          </select>
        </label>
        <label style={fieldLabelStyle}>
          Class-Section
          <select value={classSectionId} onChange={(e) => setClassSectionId(e.target.value)} style={{ ...inputStyle, minWidth: "180px" }}>
            <option value="">Select…</option>
            {classSections.map((cs) => (
              <option key={cs.id} value={cs.id}>
                {cs.school_class_name}-{cs.section_name} ({cs.academic_year_label})
              </option>
            ))}
          </select>
        </label>
        <label style={fieldLabelStyle}>
          Subject
          <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} style={{ ...inputStyle, minWidth: "160px" }}>
            <option value="">Select…</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.code})
              </option>
            ))}
          </select>
        </label>
      </div>

      {loadError && <ErrorBanner message={loadError} />}

      {!(examId && classSectionId && subjectId) ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Choose an exam, class-section, and subject to enter or view marks.</p>
      ) : !lookupDone ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Checking…</p>
      ) : !examSubject ? (
        <div style={panelStyle}>
          <p style={{ fontSize: "14px", marginBottom: "10px" }}>
            This exam hasn&apos;t been configured for this class-section/subject yet.
          </p>
          {canEnterMarks ? (
            <form onSubmit={handleCreateConfig} style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
              <label style={fieldLabelStyle}>
                Maximum marks
                <input
                  type="number"
                  min={1}
                  step="0.5"
                  value={maxMarksInput}
                  onChange={(e) => setMaxMarksInput(e.target.value)}
                  style={{ ...inputStyle, width: "120px" }}
                />
              </label>
              <Button type="submit" disabled={configuring || !maxMarksInput}>
                {configuring ? "Creating…" : "Set up & continue"}
              </Button>
            </form>
          ) : (
            <p style={{ fontSize: "13px", opacity: 0.6 }}>Ask an Admin or Teacher to set this up.</p>
          )}
          {configError && <ErrorBanner message={configError} />}
        </div>
      ) : loadingRoster ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading roster…</p>
      ) : roster.length === 0 ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>No actively enrolled students in this class-section.</p>
      ) : (
        <>
          <p style={{ fontSize: "13px", opacity: 0.7, marginBottom: "10px" }}>Maximum marks: {examSubject.max_marks}</p>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "16px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                <th style={thStyle}>Roll No</th>
                <th style={thStyle}>Student</th>
                <th style={thStyle}>Admission No</th>
                <th style={thStyle}>Marks obtained</th>
              </tr>
            </thead>
            <tbody>
              {roster.map((r) => (
                <tr key={r.enrollment.id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={tdStyle}>{r.enrollment.roll_no}</td>
                  <td style={tdStyle}>{r.enrollment.student_name}</td>
                  <td style={tdStyle}>{r.enrollment.student_admission_no}</td>
                  <td style={tdStyle}>
                    {canEditExisting ? (
                      <input
                        type="number"
                        min={0}
                        max={Number(examSubject.max_marks)}
                        step="0.5"
                        value={r.value}
                        onChange={(e) => (canEnterMarks ? setValue(r.enrollment.student, e.target.value) : void handleSingleEdit(r.enrollment.student, e.target.value))}
                        style={{ ...inputStyle, width: "90px", padding: "4px 8px" }}
                      />
                    ) : (
                      r.value || "Not entered"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {canEnterMarks && (
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <Button type="button" onClick={handleSaveAll} disabled={saving}>
                {saving ? "Saving…" : "Save marks"}
              </Button>
              {saveSuccess && <span style={{ fontSize: "13px", color: "green" }}>Saved.</span>}
            </div>
          )}
          {saveError && <ErrorBanner message={saveError} />}
        </>
      )}
    </main>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px" }}>
      {message}
    </p>
  );
}

const panelStyle: React.CSSProperties = { border: "1px solid var(--line)", borderRadius: "8px", padding: "18px", marginBottom: "20px", background: "var(--paper)" };
const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
