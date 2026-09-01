"use client";

import { api, ApiError, type CurrentUser, type TeacherListItem } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function TeachersPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [teachers, setTeachers] = useState<TeacherListItem[]>([]);
  const [count, setCount] = useState(0);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [prevUrl, setPrevUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [search, setSearch] = useState("");

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
      setLoading(true);
      setListError(null);
      try {
        const page = await api.teachers.list({});
        if (!cancelled) {
          setTeachers(page.results);
          setCount(page.count);
          setNextUrl(page.next);
          setPrevUrl(page.previous);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load teachers.");
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
    setLoading(true);
    setListError(null);
    try {
      const page = await api.teachers.list({ search });
      setTeachers(page.results);
      setCount(page.count);
      setNextUrl(page.next);
      setPrevUrl(page.previous);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load teachers.");
    } finally {
      setLoading(false);
    }
  }

  async function followPage(url: string | null) {
    if (!url) return;
    setLoading(true);
    setListError(null);
    try {
      const page = await api.teachers.listPage(url);
      setTeachers(page.results);
      setCount(page.count);
      setNextUrl(page.next);
      setPrevUrl(page.previous);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load teachers.");
    } finally {
      setLoading(false);
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="teachers").
  // See docs/prototype-analysis.md's "Teachers" row: Admin VCEDX,
  // Principal VEX (no Create), Teacher V(own)+E(own), Staff V only.
  const canCreate = Boolean(user?.is_superuser || user?.role === "Admin");

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
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Teachers</h1>
        </div>
        {canCreate && (
          <Link href="/teachers/new" style={{ textDecoration: "none" }}>
            <Button type="button">+ Add teacher</Button>
          </Link>
        )}
      </header>

      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px", flex: "1 1 280px" }}>
          Search (name, phone, email)
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="e.g. Meera Joshi"
            style={{ padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px" }}
          />
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {loading ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading…</p>
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : teachers.length === 0 ? (
        <p style={{ fontSize: "14px", opacity: 0.6 }}>No teachers found.</p>
      ) : (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
                <th style={thStyle}>Name</th>
                <th style={thStyle}>Phone</th>
                <th style={thStyle}>Email</th>
                <th style={thStyle}>Joined</th>
                <th style={thStyle}>Assignments</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {teachers.map((t) => (
                <tr key={t.id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={tdStyle}>{t.full_name}</td>
                  <td style={tdStyle}>{t.phone || "—"}</td>
                  <td style={tdStyle}>{t.email || "—"}</td>
                  <td style={tdStyle}>{t.joined_date ?? "—"}</td>
                  <td style={tdStyle}>{t.assignment_count}</td>
                  <td style={tdStyle}>
                    <Link href={`/teachers/detail?id=${t.id}`} style={{ fontSize: "13px", color: "var(--navy-primary)" }}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px" }}>
            <span style={{ fontSize: "13px", opacity: 0.6 }}>{count} teacher{count === 1 ? "" : "s"} total</span>
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
