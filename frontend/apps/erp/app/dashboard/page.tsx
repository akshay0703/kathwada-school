"use client";

import { api, type CurrentUser } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router]);

  async function handleLogout() {
    await api.logout();
    router.replace("/login");
  }

  if (checking) return null; // avoid a flash of protected content before the auth check resolves

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid var(--line)",
          paddingBottom: "16px",
          marginBottom: "24px",
        }}
      >
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px" }}>Kathwada High School — ERP</h1>
        <Button variant="secondary" onClick={handleLogout}>
          Sign out
        </Button>
      </header>

      <p>
        Signed in as <strong>{user?.email}</strong> — role: <strong>{user?.role ?? "(none assigned)"}</strong>
      </p>

      <div style={{ marginTop: "24px", display: "flex", flexWrap: "wrap", gap: "12px" }}>
        <Link
          href="/academic-years"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Academic Years</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Manage the school&apos;s academic year calendar
          </div>
        </Link>

        <Link
          href="/students"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Students</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Search, add, edit, and enroll students
          </div>
        </Link>

        <Link
          href="/report-cards"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Report Cards</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            View and print student marksheets
          </div>
        </Link>

        <Link
          href="/exams"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Exams & Marks</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Manage exams and enter subject-wise marks
          </div>
        </Link>

        <Link
          href="/attendance"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Attendance</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Mark and view attendance by class-section and date
          </div>
        </Link>

        <Link
          href="/teachers"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>Teachers</div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Manage teacher profiles and class/subject assignments
          </div>
        </Link>

        <Link
          href="/classes-sections"
          style={{
            display: "block",
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px 20px",
            textDecoration: "none",
            minWidth: "200px",
          }}
        >
          <div style={{ color: "var(--navy-primary)", fontWeight: 600, fontSize: "15px" }}>
            Classes / Sections / Subjects
          </div>
          <div style={{ color: "var(--ink)", opacity: 0.65, fontSize: "13px", marginTop: "4px" }}>
            Manage classes, sections, subjects, and per-year offerings
          </div>
        </Link>
      </div>

      <p style={{ color: "var(--ink)", opacity: 0.7, fontSize: "14px", marginTop: "24px" }}>
        This is the Phase 1 dashboard shell. Students, Marks, Attendance, Fees, Library, and Report Card
        modules are built in later Phase 1 increments per the approved architecture.
      </p>
    </main>
  );
}
