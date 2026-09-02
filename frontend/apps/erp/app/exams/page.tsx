"use client";

import { api, ApiError, type AcademicYear, type CurrentUser, type ExamListItem, type ExamWritePayload } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const emptyForm: ExamWritePayload = {
  academic_year: 0,
  code: "",
  name: "",
  start_date: "",
  end_date: "",
  sequence_order: 0,
};

export default function ExamsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ExamWritePayload>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

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

  async function loadAll() {
    setLoading(true);
    setListError(null);
    try {
      const [examsPage, yearsPage] = await Promise.all([api.exams.list(), api.academicYears.list()]);
      setExams(examsPage.results);
      setAcademicYears(yearsPage.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load exams.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checking) return;
    let cancelled = false;
    async function run() {
      setLoading(true);
      setListError(null);
      try {
        const [examsPage, yearsPage] = await Promise.all([api.exams.list(), api.academicYears.list()]);
        if (!cancelled) {
          setExams(examsPage.results);
          setAcademicYears(yearsPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load exams.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking]);

  function startEdit(exam: ExamListItem) {
    setEditingId(exam.id);
    setForm({
      academic_year: exam.academic_year,
      code: exam.code,
      name: exam.name,
      start_date: exam.start_date,
      end_date: exam.end_date,
      sequence_order: exam.sequence_order,
    });
    setFormError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
    setFormError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      if (editingId) {
        await api.exams.update(editingId, form);
      } else {
        await api.exams.create(form);
      }
      cancelEdit();
      await loadAll();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not save this exam.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(exam: ExamListItem) {
    if (!window.confirm(`Delete exam "${exam.name}"?`)) return;
    try {
      await api.exams.remove(exam.id);
      await loadAll();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this exam.");
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="exams").
  const canWrite = Boolean(user?.is_superuser || ["Admin", "Principal"].includes(user?.role ?? ""));

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "900px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Exams</h1>
      </header>

      <div style={{ marginBottom: "20px" }}>
        <Link href="/exams/marks-entry" style={{ textDecoration: "none" }}>
          <Button type="button" variant="secondary">
            Go to marks entry →
          </Button>
        </Link>
      </div>

      {canWrite && (
        <form onSubmit={handleSubmit} style={panelStyle}>
          <h2 style={{ fontSize: "15px", color: "var(--navy-primary)", marginBottom: "10px" }}>
            {editingId ? "Edit exam" : "Add exam"}
          </h2>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <label style={fieldLabelStyle}>
              Academic Year
              <select
                value={form.academic_year || ""}
                onChange={(e) => setForm((f) => ({ ...f, academic_year: Number(e.target.value) }))}
                style={{ ...inputStyle, minWidth: "160px" }}
              >
                <option value="">Select…</option>
                {academicYears.map((y) => (
                  <option key={y.id} value={y.id}>
                    {y.label}
                  </option>
                ))}
              </select>
            </label>
            <Field label="Code (e.g. UT1)" value={form.code} onChange={(v) => setForm((f) => ({ ...f, code: v }))} />
            <Field label="Name (e.g. Unit Test 1)" value={form.name} onChange={(v) => setForm((f) => ({ ...f, name: v }))} />
          </div>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "12px" }}>
            <Field label="Start date" value={form.start_date} onChange={(v) => setForm((f) => ({ ...f, start_date: v }))} type="date" />
            <Field label="End date" value={form.end_date} onChange={(v) => setForm((f) => ({ ...f, end_date: v }))} type="date" />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
            <Button type="submit" disabled={saving || !form.academic_year || !form.code || !form.name || !form.start_date || !form.end_date}>
              {saving ? "Saving…" : editingId ? "Save changes" : "Add exam"}
            </Button>
            {editingId && (
              <Button type="button" variant="secondary" onClick={cancelEdit}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      )}

      {loading ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading…</p>
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : exams.length === 0 ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>No exams yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
              <th style={thStyle}>Code</th>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Academic Year</th>
              <th style={thStyle}>Dates</th>
              <th style={thStyle}>Subjects configured</th>
              {canWrite && <th style={thStyle}></th>}
            </tr>
          </thead>
          <tbody>
            {exams.map((exam) => (
              <tr key={exam.id} style={{ borderBottom: "1px solid var(--line)" }}>
                <td style={tdStyle}>{exam.code}</td>
                <td style={tdStyle}>{exam.name}</td>
                <td style={tdStyle}>{exam.academic_year_label}</td>
                <td style={tdStyle}>
                  {exam.start_date} – {exam.end_date}
                </td>
                <td style={tdStyle}>{exam.subject_count}</td>
                {canWrite && (
                  <td style={tdStyle}>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <ActionLink onClick={() => startEdit(exam)}>Edit</ActionLink>
                      <ActionLink onClick={() => handleDelete(exam)} danger>
                        Delete
                      </ActionLink>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label style={fieldLabelStyle}>
      {label}
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px" }}>
      {message}
    </p>
  );
}

function ActionLink({ children, onClick, danger = false }: { children: React.ReactNode; onClick: () => void; danger?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{ background: "none", border: "none", padding: 0, fontSize: "13px", color: danger ? "var(--red)" : "var(--navy-primary)", cursor: "pointer", textDecoration: "underline" }}
    >
      {children}
    </button>
  );
}

const panelStyle: React.CSSProperties = { border: "1px solid var(--line)", borderRadius: "8px", padding: "16px", marginBottom: "20px", background: "var(--paper)" };
const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
