"use client";

import { api, ApiError, type Book, type BookIssue, type CurrentUser, type StudentListItem } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Tab = "issues" | "catalog";

export default function LibraryPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>("issues");

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

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="library"). See
  // docs/permissions.md's "Library" row: Admin VCEDX, Principal VX,
  // Teacher V,C (issue/return), Staff VCEDX, Student V, Parent V.
  const canManageCatalog = Boolean(user?.is_superuser || ["Admin", "Staff"].includes(user?.role ?? ""));
  const canIssueReturn = Boolean(user?.is_superuser || ["Admin", "Staff", "Teacher"].includes(user?.role ?? ""));
  const canDelete = Boolean(user?.is_superuser || ["Admin", "Staff"].includes(user?.role ?? ""));

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "1040px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Library</h1>
      </header>

      <nav style={{ display: "flex", gap: "4px", marginBottom: "20px", borderBottom: "1px solid var(--line)" }}>
        <TabButton active={tab === "issues"} onClick={() => setTab("issues")}>
          Issue / Return
        </TabButton>
        <TabButton active={tab === "catalog"} onClick={() => setTab("catalog")}>
          Catalog
        </TabButton>
      </nav>

      {tab === "catalog" && <CatalogTab canWrite={canManageCatalog} canDelete={canDelete} />}
      {tab === "issues" && <IssuesTab canIssue={canIssueReturn} canDelete={canDelete} />}
    </main>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: "none",
        border: "none",
        borderBottom: active ? "2px solid var(--navy-primary)" : "2px solid transparent",
        padding: "10px 14px",
        fontSize: "14px",
        fontWeight: active ? 600 : 400,
        color: active ? "var(--navy-primary)" : "var(--ink)",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

/* ------------------------------ Catalog tab ------------------------------ */

function CatalogTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [category, setCategory] = useState("");
  const [totalCopies, setTotalCopies] = useState("1");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load(overrides?: { search?: string }) {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.books.list({ search: overrides?.search ?? search });
      setBooks(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load books.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setListError(null);
      try {
        const page = await api.books.list({});
        if (!cancelled) setBooks(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load books.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    await load();
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.books.create({ title, author, category, total_copies: Number(totalCopies) || 1 });
      setTitle("");
      setAuthor("");
      setCategory("");
      setTotalCopies("1");
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not add this book.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(book: Book) {
    if (!window.confirm(`Remove "${book.title}" from the catalog?`)) return;
    try {
      await api.books.remove(book.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not remove this book.");
    }
  }

  return (
    <div>
      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Search title
          <input value={search} onChange={(e) => setSearch(e.target.value)} style={inputStyle} />
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <h2 style={{ fontSize: "15px", color: "var(--navy-primary)", marginBottom: "10px" }}>Add book</h2>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Field label="Title *" value={title} onChange={setTitle} />
            <Field label="Author" value={author} onChange={setAuthor} required={false} />
            <Field label="Category" value={category} onChange={setCategory} required={false} />
            <Field label="Total copies" value={totalCopies} onChange={setTotalCopies} type="number" />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !title} style={{ marginTop: "10px" }}>
            {saving ? "Saving…" : "Add book"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : books.length === 0 ? (
        <Empty text="No books in the catalog yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Title</th>
              <th style={thStyle}>Author</th>
              <th style={thStyle}>Category</th>
              <th style={thStyle}>Available / Total</th>
              {canDelete && <th style={thStyle}></th>}
            </tr>
          </thead>
          <tbody>
            {books.map((b) => (
              <tr key={b.id} style={tbodyRowStyle}>
                <td style={tdStyle}>{b.title}</td>
                <td style={tdStyle}>{b.author || "—"}</td>
                <td style={tdStyle}>{b.category || "—"}</td>
                <td style={tdStyle}>
                  {b.available_copies} / {b.total_copies}
                </td>
                {canDelete && (
                  <td style={tdStyle}>
                    <ActionLink onClick={() => handleDelete(b)} danger>
                      Delete
                    </ActionLink>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ------------------------------ Issues tab ------------------------------ */

function IssuesTab({ canIssue, canDelete }: { canIssue: boolean; canDelete: boolean }) {
  const [issues, setIssues] = useState<BookIssue[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [outstandingOnly, setOutstandingOnly] = useState(true);

  const [bookId, setBookId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [issueDate, setIssueDate] = useState(new Date().toISOString().slice(0, 10));
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [returnError, setReturnError] = useState<string | null>(null);

  async function load(overrides?: { outstanding?: boolean }) {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.bookIssues.list({ outstanding: overrides?.outstanding ?? outstandingOnly });
      setIssues(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load issues.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setListError(null);
      try {
        const [issuesPage, booksPage, studentsPage] = await Promise.all([
          api.bookIssues.list({ outstanding: true }),
          api.books.list({}),
          api.students.list({}),
        ]);
        if (!cancelled) {
          setIssues(issuesPage.results);
          setBooks(booksPage.results);
          setStudents(studentsPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load issues.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleToggleOutstanding(value: boolean) {
    setOutstandingOnly(value);
    await load({ outstanding: value });
  }

  async function handleIssue(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.bookIssues.create({ book: Number(bookId), student: Number(studentId), issue_date: issueDate });
      setBookId("");
      setStudentId("");
      await load();
      const booksPage = await api.books.list({});
      setBooks(booksPage.results);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not issue this book.");
    } finally {
      setSaving(false);
    }
  }

  async function handleReturn(issue: BookIssue) {
    setReturnError(null);
    try {
      await api.bookIssues.returnBook(issue.id);
      await load();
      const booksPage = await api.books.list({});
      setBooks(booksPage.results);
    } catch (err) {
      setReturnError(err instanceof ApiError ? err.message : "Could not mark this book returned.");
    }
  }

  async function handleDelete(issue: BookIssue) {
    if (!window.confirm(`Delete this issue record for "${issue.book_title}"?`)) return;
    try {
      await api.bookIssues.remove(issue.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this record.");
    }
  }

  return (
    <div>
      {canIssue && (
        <form onSubmit={handleIssue} style={panelStyle}>
          <h2 style={{ fontSize: "15px", color: "var(--navy-primary)", marginBottom: "10px" }}>Issue a book</h2>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <label style={fieldLabelStyle}>
              Book
              <select value={bookId} onChange={(e) => setBookId(e.target.value)} style={{ ...inputStyle, minWidth: "220px" }}>
                <option value="">Select…</option>
                {books.map((b) => (
                  <option key={b.id} value={b.id} disabled={b.available_copies <= 0}>
                    {b.title} ({b.available_copies} available)
                  </option>
                ))}
              </select>
            </label>
            <label style={fieldLabelStyle}>
              Student
              <select value={studentId} onChange={(e) => setStudentId(e.target.value)} style={{ ...inputStyle, minWidth: "220px" }}>
                <option value="">Select…</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.admission_no})
                  </option>
                ))}
              </select>
            </label>
            <Field label="Issue date" value={issueDate} onChange={setIssueDate} type="date" />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !bookId || !studentId} style={{ marginTop: "10px" }}>
            {saving ? "Issuing…" : "Issue book"}
          </Button>
        </form>
      )}

      <label style={{ ...fieldLabelStyle, flexDirection: "row", alignItems: "center", gap: "6px", marginBottom: "12px" }}>
        <input type="checkbox" checked={outstandingOnly} onChange={(e) => handleToggleOutstanding(e.target.checked)} />
        Show only books currently on loan
      </label>

      {returnError && <ErrorBanner message={returnError} />}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : issues.length === 0 ? (
        <Empty text="No issue records to show." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Book</th>
              <th style={thStyle}>Student</th>
              <th style={thStyle}>Issued</th>
              <th style={thStyle}>Due</th>
              <th style={thStyle}>Returned</th>
              <th style={thStyle}>Fine</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              <tr key={issue.id} style={tbodyRowStyle}>
                <td style={tdStyle}>{issue.book_title}</td>
                <td style={tdStyle}>
                  {issue.student_name} ({issue.student_admission_no})
                </td>
                <td style={tdStyle}>{issue.issue_date}</td>
                <td style={tdStyle}>
                  {issue.due_date}
                  {issue.is_overdue && !issue.return_date && <span style={{ color: "var(--red)", marginLeft: "6px" }}>Overdue</span>}
                </td>
                <td style={tdStyle}>{issue.return_date ?? "—"}</td>
                <td style={tdStyle}>{issue.fine_amount !== "0.00" ? issue.fine_amount : "—"}</td>
                <td style={tdStyle}>
                  <div style={{ display: "flex", gap: "10px" }}>
                    {canIssue && !issue.return_date && <ActionLink onClick={() => handleReturn(issue)}>Mark returned</ActionLink>}
                    {canDelete && (
                      <ActionLink onClick={() => handleDelete(issue)} danger>
                        Delete
                      </ActionLink>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ------------------------------ Shared UI ------------------------------ */

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
    <label style={fieldLabelStyle}>
      {label}
      <input type={type} required={required} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}

function Loading() {
  return <p style={{ fontSize: "14px", opacity: 0.6 }}>Loading…</p>;
}

function Empty({ text }: { text: string }) {
  return <p style={{ fontSize: "14px", opacity: 0.6 }}>{text}</p>;
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
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: "14px" };
const theadRowStyle: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid var(--line-strong)" };
const tbodyRowStyle: React.CSSProperties = { borderBottom: "1px solid var(--line)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
