"use client";

import {
  api,
  ApiError,
  type CurrentUser,
  type Guardian,
  type GuardianListItem,
  type GuardianWritePayload,
  type StudentListItem,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const RELATIONSHIP_OPTIONS: { value: string; label: string }[] = [
  { value: "father", label: "Father" },
  { value: "mother", label: "Mother" },
  { value: "guardian", label: "Guardian" },
  { value: "other", label: "Other" },
];

export default function GuardiansPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [guardians, setGuardians] = useState<GuardianListItem[]>([]);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [form, setForm] = useState<GuardianWritePayload>({ name: "", phone: "", email: "", relationship: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Guardian | null>(null);
  const [linkStudentId, setLinkStudentId] = useState("");
  const [linkPrimary, setLinkPrimary] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);

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

  async function load(overrides?: { search?: string }) {
    setLoading(true);
    setListError(null);
    try {
      const [guardiansPage, studentsPage] = await Promise.all([
        api.guardians.list({ search: overrides?.search ?? search }),
        api.students.list({}),
      ]);
      setGuardians(guardiansPage.results);
      setStudents(studentsPage.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load guardians.");
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
        const [guardiansPage, studentsPage] = await Promise.all([api.guardians.list({}), api.students.list({})]);
        if (!cancelled) {
          setGuardians(guardiansPage.results);
          setStudents(studentsPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load guardians.");
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

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.guardians.create(form);
      setForm({ name: "", phone: "", email: "", relationship: "" });
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create this guardian.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(guardian: GuardianListItem) {
    if (!window.confirm(`Delete guardian "${guardian.name}"?`)) return;
    try {
      await api.guardians.remove(guardian.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this guardian.");
    }
  }

  async function toggleExpand(guardianId: number) {
    if (expandedId === guardianId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(guardianId);
    setLinkError(null);
    try {
      const full = await api.guardians.retrieve(guardianId);
      setDetail(full);
    } catch (err) {
      setLinkError(err instanceof ApiError ? err.message : "Could not load this guardian.");
    }
  }

  async function handleLinkStudent(e: React.FormEvent) {
    e.preventDefault();
    if (!detail || !linkStudentId) return;
    setLinking(true);
    setLinkError(null);
    try {
      await api.studentGuardians.create({ student: Number(linkStudentId), guardian: detail.id, is_primary_contact: linkPrimary });
      setLinkStudentId("");
      setLinkPrimary(false);
      const full = await api.guardians.retrieve(detail.id);
      setDetail(full);
      await load();
    } catch (err) {
      setLinkError(err instanceof ApiError ? err.message : "Could not link this student.");
    } finally {
      setLinking(false);
    }
  }

  async function handleUnlink(linkId: number) {
    if (!detail) return;
    setLinkError(null);
    try {
      await api.studentGuardians.remove(linkId);
      const full = await api.guardians.retrieve(detail.id);
      setDetail(full);
      await load();
    } catch (err) {
      setLinkError(err instanceof ApiError ? err.message : "Could not unlink this student.");
    }
  }

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission, module_key="guardians"). See
  // docs/permissions.md's "Guardians" row: Admin VCEDX, Principal VEX,
  // Teacher V, Staff VCEX, Student none at all, Parent V (own record) +
  // E (own contact info).
  const canCreate = Boolean(user?.is_superuser || ["Admin", "Staff"].includes(user?.role ?? ""));
  const canDelete = Boolean(user?.is_superuser || user?.role === "Admin");
  const canManageLinks = Boolean(user?.is_superuser || ["Admin", "Staff"].includes(user?.role ?? ""));

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "1040px" }}>
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
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Guardians</h1>
        </div>
      </header>

      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Search (name, phone, email)
          <input value={search} onChange={(e) => setSearch(e.target.value)} style={inputStyle} />
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {canCreate && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <h2 style={{ fontSize: "15px", color: "var(--navy-primary)", marginBottom: "10px" }}>Add guardian</h2>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Field label="Name *" value={form.name} onChange={(v) => setForm((f) => ({ ...f, name: v }))} />
            <Field label="Phone" value={form.phone ?? ""} onChange={(v) => setForm((f) => ({ ...f, phone: v }))} required={false} />
            <Field label="Email" value={form.email ?? ""} onChange={(v) => setForm((f) => ({ ...f, email: v }))} type="email" required={false} />
            <label style={fieldLabelStyle}>
              Relationship
              <select
                value={form.relationship ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, relationship: e.target.value as GuardianWritePayload["relationship"] }))}
                style={inputStyle}
              >
                <option value="">Not specified</option>
                {RELATIONSHIP_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !form.name} style={{ marginTop: "10px" }}>
            {saving ? "Saving…" : "Add guardian"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : guardians.length === 0 ? (
        <Empty text="No guardians yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Phone</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Relationship</th>
              <th style={thStyle}>Children</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {guardians.map((g) => (
              <>
                <tr key={g.id} style={tbodyRowStyle}>
                  <td style={tdStyle}>{g.name}</td>
                  <td style={tdStyle}>{g.phone || "—"}</td>
                  <td style={tdStyle}>{g.email || "—"}</td>
                  <td style={tdStyle}>{g.relationship || "—"}</td>
                  <td style={tdStyle}>{g.child_count}</td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <ActionLink onClick={() => toggleExpand(g.id)}>{expandedId === g.id ? "Close" : "Manage children"}</ActionLink>
                      {canDelete && (
                        <ActionLink onClick={() => handleDelete(g)} danger>
                          Delete
                        </ActionLink>
                      )}
                    </div>
                  </td>
                </tr>
                {expandedId === g.id && detail && (
                  <tr>
                    <td colSpan={6} style={{ padding: "12px 8px", background: "var(--paper)" }}>
                      {detail.student_links.length === 0 ? (
                        <p style={{ fontSize: "13px", opacity: 0.6, marginBottom: "10px" }}>No students linked yet.</p>
                      ) : (
                        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "10px" }}>
                          {detail.student_links.map((link) => (
                            <span
                              key={link.id}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "6px",
                                background: "#fff",
                                border: "1px solid var(--line-strong)",
                                borderRadius: "12px",
                                padding: "3px 10px",
                                fontSize: "12px",
                              }}
                            >
                              {link.student_name} ({link.student_admission_no}){link.is_primary_contact ? " — primary" : ""}
                              {canManageLinks && (
                                <button
                                  onClick={() => handleUnlink(link.id)}
                                  style={{ background: "none", border: "none", cursor: "pointer", color: "var(--red)" }}
                                  aria-label={`Unlink ${link.student_name}`}
                                >
                                  ×
                                </button>
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                      {canManageLinks && (
                        <form onSubmit={handleLinkStudent} style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                          <label style={fieldLabelStyle}>
                            Link student
                            <select value={linkStudentId} onChange={(e) => setLinkStudentId(e.target.value)} style={{ ...inputStyle, minWidth: "220px" }}>
                              <option value="">Select…</option>
                              {students
                                .filter((s) => !detail.student_links.some((link) => link.student === s.id))
                                .map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.full_name} ({s.admission_no})
                                  </option>
                                ))}
                            </select>
                          </label>
                          <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "4px" }}>
                            <input type="checkbox" checked={linkPrimary} onChange={(e) => setLinkPrimary(e.target.checked)} />
                            Primary contact
                          </label>
                          <Button type="submit" disabled={linking || !linkStudentId}>
                            {linking ? "Linking…" : "Link"}
                          </Button>
                        </form>
                      )}
                      {linkError && <ErrorBanner message={linkError} />}
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
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
    <label style={{ ...fieldLabelStyle, flex: "1 1 200px" }}>
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
