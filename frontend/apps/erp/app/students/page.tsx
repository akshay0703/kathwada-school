"use client";

import { api, ApiError, type CurrentUser, type StudentListItem } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function StudentsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [count, setCount] = useState(0);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [prevUrl, setPrevUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [genderFilter, setGenderFilter] = useState("");

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

  async function load(overrides?: { search?: string; gender?: string }) {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.students.list({
        search: overrides?.search ?? search,
        gender: overrides?.gender ?? genderFilter,
      });
      setStudents(page.results);
      setCount(page.count);
      setNextUrl(page.next);
      setPrevUrl(page.previous);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load students.");
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
        const page = await api.students.list({});
        if (!cancelled) {
          setStudents(page.results);
          setCount(page.count);
          setNextUrl(page.next);
          setPrevUrl(page.previous);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load students.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [checking]);

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    await load();
  }

  async function handleGenderChange(value: string) {
    setGenderFilter(value);
    await load({ gender: value });
  }

  async function followPage(url: string | null) {
    if (!url) return;
    setLoading(true);
    setListError(null);
    try {
      const page = await api.students.listPage(url);
      setStudents(page.results);
      setCount(page.count);
      setNextUrl(page.next);
      setPrevUrl(page.previous);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load students.");
    } finally {
      setLoading(false);
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="students").
  // See docs/permissions.md's "Students" row: Admin VCEDX, Principal VCEX,
  // Staff VCEX, Teacher/Student/Parent view-only.
  const canCreate = Boolean(user?.is_superuser || ["Admin", "Principal", "Staff"].includes(user?.role ?? ""));

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "1100px" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid var(--line)",
          paddingBottom: "16px",
          marginBottom: "20px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
            ← Dashboard
          </Link>
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Students</h1>
        </div>
        {canCreate && (
          <Link href="/students/new" style={{ textDecoration: "none" }}>
            <Button type="button">+ Add student</Button>
          </Link>
        )}
      </header>

      <form
        onSubmit={handleSearchSubmit}
        style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}
      >
        <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px", flex: "1 1 240px" }}>
          Search (name, admission no, phone)
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="e.g. Aarav or KHS-2026-0001"
            style={{ padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px" }}
          />
        </label>
        <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
          Gender
          <select
            value={genderFilter}
            onChange={(e) => handleGenderChange(e.target.value)}
            style={{ padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px" }}
          >
            <option value="">All</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {loading ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading…</p>
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : students.length === 0 ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>No students found.</p>
      ) : (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                <th style={thStyle}>Admission No</th>
                <th style={thStyle}>Name</th>
                <th style={thStyle}>Gender</th>
                <th style={thStyle}>DOB</th>
                <th style={thStyle}>Class-Section</th>
                <th style={thStyle}>Roll No</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={tdStyle}>{s.admission_no}</td>
                  <td style={tdStyle}>{s.full_name}</td>
                  <td style={tdStyle}>{s.gender || "—"}</td>
                  <td style={tdStyle}>{s.dob}</td>
                  <td style={tdStyle}>{s.current_class_section?.label ?? <span style={{ opacity: 0.5 }}>Unassigned</span>}</td>
                  <td style={tdStyle}>{s.current_class_section?.roll_no ?? "—"}</td>
                  <td style={tdStyle}>
                    <Link href={`/students/detail?id=${s.id}`} style={{ fontSize: "13px", color: "var(--navy-primary)" }}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px" }}>
            <span style={{ fontSize: "13px", opacity: 0.6 }}>{count} student{count === 1 ? "" : "s"} total</span>
            <div style={{ display: "flex", gap: "8px" }}>
              <Button type="button" variant="secondary" onClick={() => followPage(prevUrl)} disabled={!prevUrl}>
                ← Previous
              </Button>
              <Button type="button" variant="secondary" onClick={() => followPage(nextUrl)} disabled={!nextUrl}>
                Next →
              </Button>
            </div>
          </div>
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

const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
