"use client";

import {
  api,
  ApiError,
  type AttendanceStatus,
  type ClassSection,
  type CurrentUser,
  type Enrollment,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const STATUS_OPTIONS: { value: AttendanceStatus; label: string }[] = [
  { value: "present", label: "Present" },
  { value: "absent", label: "Absent" },
  { value: "late", label: "Late" },
  { value: "excused", label: "Excused" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function AttendancePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [classSections, setClassSections] = useState<ClassSection[]>([]);
  const [classSectionId, setClassSectionId] = useState("");
  const [date, setDate] = useState(todayIso());

  const [roster, setRoster] = useState<{ enrollment: Enrollment; status: AttendanceStatus | "" }[]>([]);
  const [recordIdByStudent, setRecordIdByStudent] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(false);
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
        const page = await api.classSections.list();
        if (!cancelled) setClassSections(page.results);
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not load class-sections.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking]);

  async function loadRoster() {
    if (!classSectionId || !date) return;
    setLoading(true);
    setLoadError(null);
    setSaveSuccess(false);
    try {
      const [enrollmentsPage, attendancePage] = await Promise.all([
        api.enrollments.list({ class_section: Number(classSectionId), status: "active" }),
        api.attendance.list({ class_section: Number(classSectionId), date }),
      ]);
      const statusByStudent: Record<number, AttendanceStatus> = {};
      const idByStudent: Record<number, number> = {};
      attendancePage.results.forEach((r) => {
        statusByStudent[r.student] = r.status;
        idByStudent[r.student] = r.id;
      });
      setRecordIdByStudent(idByStudent);
      setRoster(
        enrollmentsPage.results.map((enrollment) => ({
          enrollment,
          status: statusByStudent[enrollment.student] ?? "",
        }))
      );
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Could not load the roster.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checking || !classSectionId || !date) return;
    let cancelled = false;
    async function run() {
      setLoading(true);
      setLoadError(null);
      setSaveSuccess(false);
      try {
        const [enrollmentsPage, attendancePage] = await Promise.all([
          api.enrollments.list({ class_section: Number(classSectionId), status: "active" }),
          api.attendance.list({ class_section: Number(classSectionId), date }),
        ]);
        if (cancelled) return;
        const statusByStudent: Record<number, AttendanceStatus> = {};
        const idByStudent: Record<number, number> = {};
        attendancePage.results.forEach((r) => {
          statusByStudent[r.student] = r.status;
          idByStudent[r.student] = r.id;
        });
        setRecordIdByStudent(idByStudent);
        setRoster(
          enrollmentsPage.results.map((enrollment) => ({
            enrollment,
            status: statusByStudent[enrollment.student] ?? "",
          }))
        );
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : "Could not load the roster.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking, classSectionId, date]);

  function setStatus(studentId: number, status: AttendanceStatus) {
    setRoster((prev) => prev.map((r) => (r.enrollment.student === studentId ? { ...r, status } : r)));
  }

  function markAll(status: AttendanceStatus) {
    setRoster((prev) => prev.map((r) => ({ ...r, status })));
  }

  async function handleSaveAll() {
    const records = roster.filter((r) => r.status !== "").map((r) => ({ student: r.enrollment.student, status: r.status as AttendanceStatus }));
    if (records.length === 0) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await api.attendance.bulkMark({ class_section: Number(classSectionId), date, records });
      setSaveSuccess(true);
      await loadRoster();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not save attendance.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSingleEdit(studentId: number, status: AttendanceStatus) {
    setStatus(studentId, status);
    const recordId = recordIdByStudent[studentId];
    if (!recordId) return; // no existing record yet — will be created via "Save attendance"
    try {
      await api.attendance.update(recordId, { status });
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Could not update this record.");
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="attendance").
  // See docs/permissions.md's "Attendance" row: Admin VCEDX, Principal VE
  // (no Create — can only edit already-marked records), Teacher VCE (own
  // classes only, enforced server-side via TeacherAssignment), Staff VC.
  const canMark = Boolean(
    user?.is_superuser || ["Admin", "Staff", "Teacher"].includes(user?.role ?? "")
  );
  const canEditExisting = Boolean(canMark || user?.role === "Principal");

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "900px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Attendance</h1>
      </header>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Class-Section
          <select value={classSectionId} onChange={(e) => setClassSectionId(e.target.value)} style={{ ...inputStyle, minWidth: "240px" }}>
            <option value="">Select…</option>
            {classSections.map((cs) => (
              <option key={cs.id} value={cs.id}>
                {cs.school_class_name}-{cs.section_name} ({cs.academic_year_label})
              </option>
            ))}
          </select>
        </label>
        <label style={fieldLabelStyle}>
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={inputStyle} />
        </label>
      </div>

      {loadError && <ErrorBanner message={loadError} />}

      {!classSectionId ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Choose a class-section and date to view or mark attendance.</p>
      ) : loading ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading…</p>
      ) : roster.length === 0 ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>No actively enrolled students in this class-section.</p>
      ) : (
        <>
          {canMark && (
            <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "13px", opacity: 0.6, alignSelf: "center" }}>Mark all as:</span>
              {STATUS_OPTIONS.map((opt) => (
                <Button key={opt.value} type="button" variant="secondary" onClick={() => markAll(opt.value)}>
                  {opt.label}
                </Button>
              ))}
            </div>
          )}

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "16px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                <th style={thStyle}>Roll No</th>
                <th style={thStyle}>Student</th>
                <th style={thStyle}>Admission No</th>
                <th style={thStyle}>Status</th>
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
                      <select
                        value={r.status}
                        onChange={(e) => {
                          const value = e.target.value as AttendanceStatus | "";
                          if (value === "") return;
                          if (canMark) {
                            setStatus(r.enrollment.student, value);
                          } else {
                            void handleSingleEdit(r.enrollment.student, value);
                          }
                        }}
                        style={{ ...inputStyle, padding: "4px 8px" }}
                      >
                        <option value="">Not marked</option>
                        {STATUS_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      STATUS_OPTIONS.find((opt) => opt.value === r.status)?.label ?? "Not marked"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {canMark && (
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <Button type="button" onClick={handleSaveAll} disabled={saving}>
                {saving ? "Saving…" : "Save attendance"}
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

const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
