"use client";

import {
  api,
  ApiError,
  type AcademicYear,
  type ClassSection,
  type CurrentUser,
  type Student,
  type StudentWritePayload,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

export default function StudentDetailPage() {
  return (
    <Suspense fallback={null}>
      <StudentDetailContent />
    </Suspense>
  );
}

function StudentDetailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const studentId = Number(searchParams.get("id"));

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [student, setStudent] = useState<Student | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [classSections, setClassSections] = useState<ClassSection[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<StudentWritePayload | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [enrollClassSectionId, setEnrollClassSectionId] = useState("");
  const [enrollRollNo, setEnrollRollNo] = useState("");
  const [enrollError, setEnrollError] = useState<string | null>(null);
  const [enrolling, setEnrolling] = useState(false);

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

  async function loadStudent() {
    if (!studentId) {
      setLoadError("No student id given.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const [s, csPage, yearsPage] = await Promise.all([
        api.students.retrieve(studentId),
        api.classSections.list(),
        api.academicYears.list(),
      ]);
      setStudent(s);
      setForm({
        admission_no: s.admission_no,
        first_name: s.first_name,
        last_name: s.last_name,
        dob: s.dob,
        gender: s.gender,
        address: s.address,
        phone: s.phone,
        admission_date: s.admission_date,
      });
      setClassSections(csPage.results);
      setAcademicYears(yearsPage.results);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not load this student.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checking) return;
    let cancelled = false;
    async function run() {
      if (!studentId) {
        setLoadError("No student id given.");
        setLoading(false);
        return;
      }
      setLoading(true);
      setLoadError(null);
      try {
        const [s, csPage, yearsPage] = await Promise.all([
          api.students.retrieve(studentId),
          api.classSections.list(),
          api.academicYears.list(),
        ]);
        if (cancelled) return;
        setStudent(s);
        setForm({
          admission_no: s.admission_no,
          first_name: s.first_name,
          last_name: s.last_name,
          dob: s.dob,
          gender: s.gender,
          address: s.address,
          phone: s.phone,
          admission_date: s.admission_date,
        });
        setClassSections(csPage.results);
        setAcademicYears(yearsPage.results);
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not load this student.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking, studentId]);

  function updateForm<K extends keyof StudentWritePayload>(key: K, value: StudentWritePayload[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form || !student) return;
    setFormError(null);
    setSaving(true);
    try {
      const updated = await api.students.update(student.id, { ...form, admission_date: form.admission_date || null });
      setStudent((prev) => (prev ? { ...prev, ...updated } : updated));
      setEditing(false);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleEnroll(e: React.FormEvent) {
    e.preventDefault();
    if (!student || !enrollClassSectionId || !enrollRollNo) return;
    setEnrollError(null);
    setEnrolling(true);
    try {
      await api.enrollments.create({
        student: student.id,
        class_section: Number(enrollClassSectionId),
        roll_no: Number(enrollRollNo),
      });
      setEnrollClassSectionId("");
      setEnrollRollNo("");
      await loadStudent();
    } catch (err) {
      setEnrollError(err instanceof ApiError ? err.message : "Could not create this enrollment.");
    } finally {
      setEnrolling(false);
    }
  }

  async function handleDeactivate() {
    if (!student) return;
    if (!window.confirm(`Deactivate ${student.full_name} (${student.admission_no})? Their records are preserved and this can be reversed by an administrator if needed.`)) {
      return;
    }
    try {
      await api.students.remove(student.id);
      router.push("/students");
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not deactivate this student.");
    }
  }

  // UI-only convenience — real access control is server-side (module_key="students").
  const canEdit = Boolean(user?.is_superuser || ["Admin", "Principal", "Staff"].includes(user?.role ?? ""));
  const canDeactivate = Boolean(user?.is_superuser || user?.role === "Admin");
  const canEnroll = canEdit;

  if (checking || loading) return <main style={{ padding: "32px" }}>Loading…</main>;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "820px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/students" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Students
        </Link>
        {student && (
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>
            {student.full_name} <span style={{ fontSize: "14px", opacity: 0.6, fontWeight: 400 }}>({student.admission_no})</span>
          </h1>
        )}
      </header>

      {loadError && <ErrorBanner message={loadError} />}

      {student && form && (
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
                  <Field label="Admission No *" value={form.admission_no} onChange={(v) => updateForm("admission_no", v)} />
                  <Field
                    label="Admission date"
                    value={form.admission_date ?? ""}
                    onChange={(v) => updateForm("admission_date", v)}
                    type="date"
                    required={false}
                  />
                </Row>
                <Row>
                  <Field label="First name *" value={form.first_name} onChange={(v) => updateForm("first_name", v)} />
                  <Field label="Last name *" value={form.last_name} onChange={(v) => updateForm("last_name", v)} />
                </Row>
                <Row>
                  <Field label="Date of birth *" value={form.dob} onChange={(v) => updateForm("dob", v)} type="date" />
                  <label style={fieldLabelStyle}>
                    Gender
                    <select
                      value={form.gender}
                      onChange={(e) => updateForm("gender", e.target.value as StudentWritePayload["gender"])}
                      style={inputStyle}
                    >
                      <option value="">Not specified</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </label>
                </Row>
                <Row>
                  <Field label="Phone" value={form.phone ?? ""} onChange={(v) => updateForm("phone", v)} required={false} />
                </Row>
                <label style={fieldLabelStyle}>
                  Address
                  <textarea
                    value={form.address}
                    onChange={(e) => updateForm("address", e.target.value)}
                    rows={3}
                    style={{ ...inputStyle, resize: "vertical" as const }}
                  />
                </label>
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
                        admission_no: student.admission_no,
                        first_name: student.first_name,
                        last_name: student.last_name,
                        dob: student.dob,
                        gender: student.gender,
                        address: student.address,
                        phone: student.phone,
                        admission_date: student.admission_date,
                      });
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <dl style={dlStyle}>
                <ProfileRow label="Admission No" value={student.admission_no} />
                <ProfileRow label="Admission date" value={student.admission_date ?? "—"} />
                <ProfileRow label="Date of birth" value={student.dob} />
                <ProfileRow label="Gender" value={student.gender || "—"} />
                <ProfileRow label="Phone" value={student.phone || "—"} />
                <ProfileRow label="Address" value={student.address || "—"} />
              </dl>
            )}
          </section>

          <section style={panelStyle}>
            <h2 style={{ fontSize: "16px", color: "var(--navy-primary)", marginBottom: "12px" }}>Enrollment history</h2>
            {student.enrollments.length === 0 ? (
              <p style={{ fontSize: "14px", opacity: 0.6 }}>Not enrolled in any class-section yet.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "16px" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                    <th style={thStyle}>Class-Section</th>
                    <th style={thStyle}>Academic Year</th>
                    <th style={thStyle}>Roll No</th>
                    <th style={thStyle}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {student.enrollments.map((en) => (
                    <tr key={en.id} style={{ borderBottom: "1px solid var(--line)" }}>
                      <td style={tdStyle}>
                        {en.school_class_name}-{en.section_name}
                      </td>
                      <td style={tdStyle}>{en.academic_year_label}</td>
                      <td style={tdStyle}>{en.roll_no}</td>
                      <td style={tdStyle}>{en.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {canEnroll && (
              <form onSubmit={handleEnroll} style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
                <label style={fieldLabelStyle}>
                  Class-Section
                  <select
                    value={enrollClassSectionId}
                    onChange={(e) => setEnrollClassSectionId(e.target.value)}
                    style={{ ...inputStyle, minWidth: "220px" }}
                  >
                    <option value="">Select…</option>
                    {classSections.map((cs) => (
                      <option key={cs.id} value={cs.id}>
                        {cs.school_class_name}-{cs.section_name} ({cs.academic_year_label})
                      </option>
                    ))}
                  </select>
                </label>
                <label style={fieldLabelStyle}>
                  Roll No
                  <input
                    type="number"
                    min={1}
                    value={enrollRollNo}
                    onChange={(e) => setEnrollRollNo(e.target.value)}
                    style={{ ...inputStyle, width: "100px" }}
                  />
                </label>
                <Button type="submit" disabled={enrolling || !enrollClassSectionId || !enrollRollNo}>
                  {enrolling ? "Enrolling…" : "Enroll"}
                </Button>
                {classSections.length === 0 && (
                  <span style={{ fontSize: "12px", opacity: 0.6 }}>
                    No class-sections exist yet — create one under Classes / Sections / Subjects first.
                  </span>
                )}
              </form>
            )}
            {enrollError && <ErrorBanner message={enrollError} />}
            {academicYears.length === 0 && (
              <p style={{ fontSize: "12px", opacity: 0.5, marginTop: "8px" }}>No academic years exist yet.</p>
            )}
          </section>

          {canDeactivate && (
            <section style={{ ...panelStyle, borderColor: "var(--red)" }}>
              <h2 style={{ fontSize: "16px", color: "var(--red)", marginBottom: "8px" }}>Danger zone</h2>
              <p style={{ fontSize: "13px", opacity: 0.7, marginBottom: "12px" }}>
                Deactivating a student is a soft delete — their record, enrollment history, and any future
                marks/attendance/fee history are preserved, but they are removed from active lists.
              </p>
              <Button
                type="button"
                onClick={handleDeactivate}
                style={{ background: "var(--red)", borderColor: "var(--red)" }}
              >
                Deactivate student
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
const dlStyle: React.CSSProperties = { margin: 0 };
const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
