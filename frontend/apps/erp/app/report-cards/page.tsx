"use client";

import {
  api,
  ApiError,
  type AcademicYear,
  type ClassMarksheetRow,
  type ClassSection,
  type CurrentUser,
  type ExamListItem,
  type Marksheet,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ReportCardsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [classSections, setClassSections] = useState<ClassSection[]>([]);

  const [academicYearId, setAcademicYearId] = useState("");
  const [examId, setExamId] = useState("");
  const [classSectionId, setClassSectionId] = useState("");

  const [classSummary, setClassSummary] = useState<ClassMarksheetRow[] | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const [marksheet, setMarksheet] = useState<Marksheet | null>(null);
  const [loadingMarksheet, setLoadingMarksheet] = useState(false);
  const [marksheetError, setMarksheetError] = useState<string | null>(null);

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
        const [yearsPage, examsPage, csPage] = await Promise.all([
          api.academicYears.list(),
          api.exams.list(),
          api.classSections.list(),
        ]);
        if (!cancelled) {
          setAcademicYears(yearsPage.results);
          setExams(examsPage.results);
          setClassSections(csPage.results);
        }
      } catch (err) {
        if (!cancelled) setSummaryError(err instanceof ApiError ? err.message : "Could not load filters.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking]);

  const filteredExams = academicYearId ? exams.filter((e) => e.academic_year === Number(academicYearId)) : exams;
  const filteredClassSections = academicYearId
    ? classSections.filter((cs) => cs.academic_year === Number(academicYearId))
    : classSections;

  useEffect(() => {
    if (checking || !examId || !classSectionId) return;
    let cancelled = false;
    async function run() {
      setLoadingSummary(true);
      setSummaryError(null);
      setSelectedStudentId(null);
      setMarksheet(null);
      try {
        const rows = await api.marks.classMarksheet({ class_section: Number(classSectionId), exam: Number(examId) });
        if (!cancelled) setClassSummary(rows);
      } catch (err) {
        if (!cancelled) setSummaryError(err instanceof ApiError ? err.message : "Could not load the class summary.");
      } finally {
        if (!cancelled) setLoadingSummary(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking, examId, classSectionId]);

  async function viewStudent(studentId: number) {
    if (!examId) return;
    setSelectedStudentId(studentId);
    setLoadingMarksheet(true);
    setMarksheetError(null);
    try {
      const result = await api.marks.marksheet({ student: studentId, exam: Number(examId) });
      setMarksheet(result);
    } catch (err) {
      setMarksheetError(err instanceof ApiError ? err.message : "Could not load this marksheet.");
    } finally {
      setLoadingMarksheet(false);
    }
  }

  function handlePrint() {
    window.print();
  }

  const canViewClassSummary = Boolean(
    user?.is_superuser || ["Admin", "Principal", "Teacher"].includes(user?.role ?? "")
  );

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "900px" }}>
      <style>{"@media print { .no-print { display: none !important; } body { padding: 0; } }"}</style>

      <header className="no-print" style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Report Cards / Marksheets</h1>
      </header>

      <div className="no-print" style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Academic Year
          <select
            value={academicYearId}
            onChange={(e) => {
              setAcademicYearId(e.target.value);
              setExamId("");
              setClassSectionId("");
            }}
            style={{ ...inputStyle, minWidth: "160px" }}
          >
            <option value="">All</option>
            {academicYears.map((y) => (
              <option key={y.id} value={y.id}>
                {y.label}
              </option>
            ))}
          </select>
        </label>
        <label style={fieldLabelStyle}>
          Exam
          <select value={examId} onChange={(e) => setExamId(e.target.value)} style={{ ...inputStyle, minWidth: "180px" }}>
            <option value="">Select…</option>
            {filteredExams.map((ex) => (
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
            {filteredClassSections.map((cs) => (
              <option key={cs.id} value={cs.id}>
                {cs.school_class_name}-{cs.section_name} ({cs.academic_year_label})
              </option>
            ))}
          </select>
        </label>
      </div>

      {summaryError && <ErrorBanner message={summaryError} />}

      {!(examId && classSectionId) ? (
        <p className="no-print" style={{ fontSize: "14px", opacity: 0.6 }}>
          Choose an exam and class-section to view marksheets.
        </p>
      ) : !canViewClassSummary && !selectedStudentId ? (
        <p className="no-print" style={{ fontSize: "14px", opacity: 0.6 }}>
          You do not have permission to view the class summary. If you are a student, use the marksheet link shared with you.
        </p>
      ) : (
        canViewClassSummary && (
          <div className="no-print">
            {loadingSummary ? (
              <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading class summary…</p>
            ) : classSummary && classSummary.length > 0 ? (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "24px" }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                    <th style={thStyle}>Student</th>
                    <th style={thStyle}>Admission No</th>
                    <th style={thStyle}>Total</th>
                    <th style={thStyle}>%</th>
                    <th style={thStyle}>Result</th>
                    <th style={thStyle}></th>
                  </tr>
                </thead>
                <tbody>
                  {classSummary.map((row) => (
                    <tr key={row.student.id} style={{ borderBottom: "1px solid var(--line)" }}>
                      <td style={tdStyle}>{row.student.full_name}</td>
                      <td style={tdStyle}>{row.student.admission_no}</td>
                      <td style={tdStyle}>
                        {row.total_obtained} / {row.total_max}
                      </td>
                      <td style={tdStyle}>{row.percentage != null ? `${row.percentage}%` : "—"}</td>
                      <td style={tdStyle}>
                        <ResultBadge result={row.overall_result} incomplete={!row.all_marks_entered} />
                      </td>
                      <td style={tdStyle}>
                        <button
                          onClick={() => viewStudent(row.student.id)}
                          style={{
                            background: "none",
                            border: "none",
                            color: "var(--navy-primary)",
                            cursor: "pointer",
                            fontSize: "13px",
                            textDecoration: "underline",
                          }}
                        >
                          View marksheet
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ fontSize: "14px", opacity: 0.6 }}>No actively enrolled students in this class-section.</p>
            )}
          </div>
        )
      )}

      {marksheetError && <ErrorBanner message={marksheetError} />}

      {loadingMarksheet && (
        <p className="no-print" style={{ fontSize: "14px", opacity: 0.6 }}>
          Loading marksheet…
        </p>
      )}

      {marksheet && (
        <section style={{ border: "1px solid var(--line-strong)", borderRadius: "8px", padding: "24px", marginTop: "12px" }}>
          <div className="no-print" style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px" }}>
            <Button type="button" variant="secondary" onClick={handlePrint}>
              Print marksheet
            </Button>
          </div>

          <div style={{ textAlign: "center", marginBottom: "16px" }}>
            <h2 style={{ color: "var(--navy-primary)", fontSize: "18px", margin: 0 }}>Kathwada High School</h2>
            <p style={{ fontSize: "13px", opacity: 0.7, margin: "4px 0 0" }}>
              {marksheet.exam.name} — {marksheet.academic_year_label}
            </p>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", marginBottom: "16px" }}>
            <div>
              <strong>{marksheet.student.full_name}</strong>
              <div style={{ opacity: 0.7 }}>Admission No: {marksheet.student.admission_no}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div>{marksheet.class_section_label}</div>
              <div style={{ opacity: 0.7 }}>Roll No: {marksheet.roll_no}</div>
            </div>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px", marginBottom: "16px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                <th style={thStyle}>Subject</th>
                <th style={thStyle}>Max Marks</th>
                <th style={thStyle}>Passing Marks</th>
                <th style={thStyle}>Marks Obtained</th>
                <th style={thStyle}>Result</th>
              </tr>
            </thead>
            <tbody>
              {marksheet.subjects.map((row) => (
                <tr key={row.exam_subject} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={tdStyle}>
                    {row.subject_name} ({row.subject_code})
                  </td>
                  <td style={tdStyle}>{row.max_marks}</td>
                  <td style={tdStyle}>{row.passing_marks ?? "—"}</td>
                  <td style={tdStyle}>{row.marks_obtained ?? "Not entered"}</td>
                  <td style={tdStyle}>
                    {row.passed === null ? (
                      "—"
                    ) : row.passed ? (
                      <span style={{ color: "green" }}>Pass</span>
                    ) : (
                      <span style={{ color: "var(--red)" }}>Fail</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "15px",
              fontWeight: 600,
              borderTop: "2px solid var(--line-strong)",
              paddingTop: "12px",
            }}
          >
            <span>
              Total: {marksheet.total_obtained} / {marksheet.total_max}
            </span>
            <span>Percentage: {marksheet.percentage != null ? `${marksheet.percentage}%` : "—"}</span>
            <span>
              Overall: <ResultBadge result={marksheet.overall_result} incomplete={!marksheet.all_marks_entered} />
            </span>
          </div>
          {!marksheet.all_marks_entered && (
            <p style={{ fontSize: "12px", opacity: 0.6, marginTop: "8px" }}>Note: not all subjects have marks entered yet.</p>
          )}
        </section>
      )}
    </main>
  );
}

function ResultBadge({ result, incomplete }: { result: "pass" | "fail" | null; incomplete: boolean }) {
  if (result === "pass") return <span style={{ color: "green", fontWeight: 600 }}>Pass</span>;
  if (result === "fail") return <span style={{ color: "var(--red)", fontWeight: 600 }}>Fail</span>;
  return <span style={{ opacity: 0.6 }}>{incomplete ? "Incomplete" : "—"}</span>;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="no-print"
      style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px" }}
    >
      {message}
    </p>
  );
}

const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
