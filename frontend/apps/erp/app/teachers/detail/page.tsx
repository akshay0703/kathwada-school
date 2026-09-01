"use client";

import {
  api,
  ApiError,
  type ClassSection,
  type CurrentUser,
  type Teacher,
  type TeacherWritePayload,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

export default function TeacherDetailPage() {
  return (
    <Suspense fallback={null}>
      <TeacherDetailContent />
    </Suspense>
  );
}

type AssignableOption = { id: number; label: string };

function TeacherDetailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const teacherId = Number(searchParams.get("id"));

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [assignableOptions, setAssignableOptions] = useState<AssignableOption[]>([]);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<TeacherWritePayload | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [assignId, setAssignId] = useState("");
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);

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

  async function loadTeacher() {
    if (!teacherId) {
      setLoadError("No teacher id given.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const [t, csPage] = await Promise.all([api.teachers.retrieve(teacherId), api.classSections.list()]);
      setTeacher(t);
      setForm({
        first_name: t.first_name,
        last_name: t.last_name,
        phone: t.phone,
        email: t.email,
        joined_date: t.joined_date,
      });
      const alreadyAssigned = new Set(t.assignments.map((a) => a.class_section_subject));
      const options: AssignableOption[] = [];
      csPage.results.forEach((cs: ClassSection) => {
        cs.subjects.forEach((s) => {
          if (!alreadyAssigned.has(s.id)) {
            options.push({
              id: s.id,
              label: `${cs.school_class_name}-${cs.section_name} — ${s.subject_name} (${cs.academic_year_label})`,
            });
          }
        });
      });
      setAssignableOptions(options);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not load this teacher.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checking) return;
    let cancelled = false;
    async function run() {
      if (!teacherId) {
        setLoadError("No teacher id given.");
        setLoading(false);
        return;
      }
      setLoading(true);
      setLoadError(null);
      try {
        const [t, csPage] = await Promise.all([api.teachers.retrieve(teacherId), api.classSections.list()]);
        if (cancelled) return;
        setTeacher(t);
        setForm({
          first_name: t.first_name,
          last_name: t.last_name,
          phone: t.phone,
          email: t.email,
          joined_date: t.joined_date,
        });
        const alreadyAssigned = new Set(t.assignments.map((a) => a.class_section_subject));
        const options: AssignableOption[] = [];
        csPage.results.forEach((cs: ClassSection) => {
          cs.subjects.forEach((s) => {
            if (!alreadyAssigned.has(s.id)) {
              options.push({
                id: s.id,
                label: `${cs.school_class_name}-${cs.section_name} — ${s.subject_name} (${cs.academic_year_label})`,
              });
            }
          });
        });
        setAssignableOptions(options);
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not load this teacher.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking, teacherId]);

  function updateForm<K extends keyof TeacherWritePayload>(key: K, value: TeacherWritePayload[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form || !teacher) return;
    setFormError(null);
    setSaving(true);
    try {
      const updated = await api.teachers.update(teacher.id, { ...form, joined_date: form.joined_date || null });
      setTeacher((prev) => (prev ? { ...prev, ...updated } : updated));
      setEditing(false);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!teacher || !assignId) return;
    setAssignError(null);
    setAssigning(true);
    try {
      await api.teacherAssignments.create({ teacher: teacher.id, class_section_subject: Number(assignId) });
      setAssignId("");
      await loadTeacher();
    } catch (err) {
      setAssignError(err instanceof ApiError ? err.message : "Could not create this assignment.");
    } finally {
      setAssigning(false);
    }
  }

  async function handleUnassign(assignmentId: number) {
    setAssignError(null);
    try {
      await api.teacherAssignments.remove(assignmentId);
      await loadTeacher();
    } catch (err) {
      setAssignError(err instanceof ApiError ? err.message : "Could not remove this assignment.");
    }
  }

  async function handleDeactivate() {
    if (!teacher) return;
    if (!window.confirm(`Deactivate ${teacher.full_name}? Their record and assignment history are preserved.`)) {
      return;
    }
    try {
      await api.teachers.remove(teacher.id);
      router.push("/teachers");
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not deactivate this teacher.");
    }
  }

  // UI-only convenience — real access control is server-side (module_key="teachers").
  const isSelf = Boolean(user && teacher && user.id === teacher.user);
  const canEdit = Boolean(user?.is_superuser || user?.role === "Admin" || user?.role === "Principal" || isSelf);
  const canDeactivate = Boolean(user?.is_superuser || user?.role === "Admin");
  const canAssign = Boolean(user?.is_superuser || user?.role === "Admin");

  if (checking || loading) return <main style={{ padding: "32px" }}>Loading…</main>;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "820px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/teachers" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Teachers
        </Link>
        {teacher && (
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>{teacher.full_name}</h1>
        )}
      </header>

      {loadError && <ErrorBanner message={loadError} />}

      {teacher && form && (
        <>
          <section style={panelStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <h2 style={{ fontSize: "16px", color: "var(--navy-primary)" }}>Profile</h2>
              {canEdit && !editing && (
                <Button type="button" variant="secondary" onClick={() => setEditing(true)}>
                  Edit
                </Button>
              )}
            </div>

            {editing ? (
              <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <Row>
                  <Field label="First name *" value={form.first_name} onChange={(v) => updateForm("first_name", v)} />
                  <Field label="Last name *" value={form.last_name} onChange={(v) => updateForm("last_name", v)} />
                </Row>
                <Row>
                  <Field label="Phone" value={form.phone ?? ""} onChange={(v) => updateForm("phone", v)} required={false} />
                  <Field label="Email" value={form.email ?? ""} onChange={(v) => updateForm("email", v)} type="email" required={false} />
                </Row>
                <Row>
                  <Field
                    label="Joined date"
                    value={form.joined_date ?? ""}
                    onChange={(v) => updateForm("joined_date", v)}
                    type="date"
                    required={false}
                  />
                </Row>
                {formError && <ErrorBanner message={formError} />}
                <div style={{ display: "flex", gap: "10px" }}>
                  <Button type="submit" disabled={saving}>
                    {saving ? "Saving…" : "Save changes"}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setEditing(false);
                      setFormError(null);
                      setForm({
                        first_name: teacher.first_name,
                        last_name: teacher.last_name,
                        phone: teacher.phone,
                        email: teacher.email,
                        joined_date: teacher.joined_date,
                      });
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <dl style={{ margin: 0 }}>
                <ProfileRow label="Phone" value={teacher.phone || "—"} />
                <ProfileRow label="Email" value={teacher.email || "—"} />
                <ProfileRow label="Joined date" value={teacher.joined_date ?? "—"} />
              </dl>
            )}
          </section>

          <section style={panelStyle}>
            <h2 style={{ fontSize: "16px", color: "var(--navy-primary)", marginBottom: "12px" }}>Class / subject assignments</h2>
            {teacher.assignments.length === 0 ? (
              <p style={{ fontSize: "14px", opacity: 0.6 }}>Not assigned to any class-section subject yet.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "16px" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                    <th style={thStyle}>Class-Section</th>
                    <th style={thStyle}>Subject</th>
                    <th style={thStyle}>Academic Year</th>
                    {canAssign && <th style={thStyle}></th>}
                  </tr>
                </thead>
                <tbody>
                  {teacher.assignments.map((a) => (
                    <tr key={a.id} style={{ borderBottom: "1px solid var(--line)" }}>
                      <td style={tdStyle}>
                        {a.school_class_name}-{a.section_name}
                      </td>
                      <td style={tdStyle}>
                        {a.subject_name} ({a.subject_code})
                      </td>
                      <td style={tdStyle}>{a.academic_year_label}</td>
                      {canAssign && (
                        <td style={tdStyle}>
                          <button
                            onClick={() => handleUnassign(a.id)}
                            style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: "13px", textDecoration: "underline" }}
                          >
                            Remove
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {canAssign && (
              <form onSubmit={handleAssign} style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
                <label style={fieldLabelStyle}>
                  Assign to class-section subject
                  <select value={assignId} onChange={(e) => setAssignId(e.target.value)} style={{ ...inputStyle, minWidth: "320px" }}>
                    <option value="">Select…</option>
                    {assignableOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
                <Button type="submit" disabled={assigning || !assignId}>
                  {assigning ? "Assigning…" : "Assign"}
                </Button>
                {assignableOptions.length === 0 && (
                  <span style={{ fontSize: "12px", opacity: 0.6 }}>
                    No unassigned class-section subjects available — add subjects to a class-section first.
                  </span>
                )}
              </form>
            )}
            {assignError && <ErrorBanner message={assignError} />}
          </section>

          {canDeactivate && (
            <section style={{ ...panelStyle, borderColor: "var(--red)" }}>
              <h2 style={{ fontSize: "16px", color: "var(--red)", marginBottom: "8px" }}>Danger zone</h2>
              <p style={{ fontSize: "13px", opacity: 0.7, marginBottom: "12px" }}>
                Deactivating a teacher is a soft delete — their record and assignment history are preserved, but
                they are removed from active lists.
              </p>
              <Button type="button" onClick={handleDeactivate} style={{ background: "var(--red)", borderColor: "var(--red)" }}>
                Deactivate teacher
              </Button>
            </section>
          )}
        </>
      )}
    </main>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>{children}</div>;
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = true,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label style={{ ...fieldLabelStyle, flex: "1 1 220px" }}>
      {label}
      <input type={type} required={required} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: "8px", padding: "4px 0" }}>
      <dt style={{ fontSize: "13px", opacity: 0.6, minWidth: "140px" }}>{label}</dt>
      <dd style={{ fontSize: "14px", margin: 0 }}>{value}</dd>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px" }}>
      {message}
    </p>
  );
}

const panelStyle: React.CSSProperties = {
  border: "1px solid var(--line)",
  borderRadius: "8px",
  padding: "18px",
  marginBottom: "20px",
  background: "var(--paper)",
};
const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
