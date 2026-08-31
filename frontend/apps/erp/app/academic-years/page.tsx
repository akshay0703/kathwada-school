"use client";

import { api, ApiError, type AcademicYear, type CurrentUser } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type FormState = { label: string; start_date: string; end_date: string };
const EMPTY_FORM: FormState = { label: "", start_date: "", end_date: "" };

export default function AcademicYearsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [years, setYears] = useState<AcademicYear[]>([]);
  const [loadingYears, setLoadingYears] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState<FormState>(EMPTY_FORM);
  const [createError, setCreateError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<FormState>(EMPTY_FORM);
  const [editError, setEditError] = useState<string | null>(null);

  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router]);

  async function loadYears() {
    setLoadingYears(true);
    setListError(null);
    try {
      const page = await api.academicYears.list();
      setYears(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load academic years.");
    } finally {
      setLoadingYears(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function run() {
      setLoadingYears(true);
      setListError(null);
      try {
        const page = await api.academicYears.list();
        if (!cancelled) setYears(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load academic years.");
      } finally {
        if (!cancelled) setLoadingYears(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user]);

  // UI-only convenience — the real access control is entirely server-side
  // (HasModulePermission + the RolePermission table). Hiding buttons here
  // just avoids showing a Teacher/Student/Parent a control that would 403;
  // it grants nothing on its own. See docs/permissions.md.
  const canWrite = Boolean(user?.is_superuser || user?.role === "Admin" || user?.role === "Principal");
  const canDelete = Boolean(user?.is_superuser || user?.role === "Admin");

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setSaving(true);
    try {
      await api.academicYears.create(createForm);
      setCreateForm(EMPTY_FORM);
      setShowCreateForm(false);
      await loadYears();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Could not create academic year.");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(year: AcademicYear) {
    setEditingId(year.id);
    setEditForm({ label: year.label, start_date: year.start_date, end_date: year.end_date });
    setEditError(null);
  }

  async function handleEditSave(id: number) {
    setEditError(null);
    setSaving(true);
    try {
      await api.academicYears.update(id, editForm);
      setEditingId(null);
      await loadYears();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkCurrent(id: number) {
    setActionError(null);
    try {
      await api.academicYears.markCurrent(id);
      await loadYears();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not mark this year as current.");
    }
  }

  async function handleDelete(year: AcademicYear) {
    if (!window.confirm(`Delete academic year "${year.label}"? This can be restored later if needed.`)) return;
    setActionError(null);
    try {
      await api.academicYears.remove(year.id);
      await loadYears();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not delete this academic year.");
    }
  }

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "860px" }}>
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
        <div>
          <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
            ← Dashboard
          </Link>
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Academic Years</h1>
        </div>
        {canWrite && (
          <Button onClick={() => setShowCreateForm((v) => !v)}>{showCreateForm ? "Cancel" : "+ New Academic Year"}</Button>
        )}
      </header>

      {!canWrite && (
        <p style={{ fontSize: "13px", color: "var(--ink)", opacity: 0.65, marginBottom: "16px" }}>
          You have view-only access to this module.
        </p>
      )}

      {actionError && <ErrorBanner message={actionError} />}

      {showCreateForm && canWrite && (
        <form
          onSubmit={handleCreate}
          style={{
            border: "1px solid var(--line)",
            borderRadius: "8px",
            padding: "16px",
            marginBottom: "20px",
            background: "var(--paper)",
          }}
        >
          <YearFields form={createForm} setForm={setCreateForm} />
          {createError && <ErrorBanner message={createError} />}
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Create"}
          </Button>
        </form>
      )}

      {loadingYears ? (
        <p style={{ fontSize: "14px", color: "var(--ink)", opacity: 0.6 }}>Loading…</p>
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : years.length === 0 ? (
        <p style={{ fontSize: "14px", color: "var(--ink)", opacity: 0.6 }}>No academic years yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid var(--line-strong)" }}>
              <th style={thStyle}>Label</th>
              <th style={thStyle}>Start</th>
              <th style={thStyle}>End</th>
              <th style={thStyle}>Status</th>
              {canWrite && <th style={thStyle}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {years.map((year) =>
              editingId === year.id ? (
                <tr key={year.id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td colSpan={canWrite ? 5 : 4} style={{ padding: "10px 8px" }}>
                    <YearFields form={editForm} setForm={setEditForm} inline />
                    {editError && <ErrorBanner message={editError} />}
                    <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                      <Button onClick={() => handleEditSave(year.id)} disabled={saving}>
                        {saving ? "Saving…" : "Save"}
                      </Button>
                      <Button variant="secondary" onClick={() => setEditingId(null)}>
                        Cancel
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={year.id} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={tdStyle}>{year.label}</td>
                  <td style={tdStyle}>{year.start_date}</td>
                  <td style={tdStyle}>{year.end_date}</td>
                  <td style={tdStyle}>
                    {year.is_current ? (
                      <span
                        style={{
                          background: "var(--gold)",
                          color: "var(--navy-dark)",
                          fontSize: "12px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "10px",
                        }}
                      >
                        Current
                      </span>
                    ) : (
                      <span style={{ fontSize: "12px", color: "var(--ink)", opacity: 0.5 }}>—</span>
                    )}
                  </td>
                  {canWrite && (
                    <td style={tdStyle}>
                      <div style={{ display: "flex", gap: "10px" }}>
                        <ActionLink onClick={() => startEdit(year)}>Edit</ActionLink>
                        {!year.is_current && (
                          <ActionLink onClick={() => handleMarkCurrent(year.id)}>Mark current</ActionLink>
                        )}
                        {canDelete && (
                          <ActionLink onClick={() => handleDelete(year)} danger>
                            Delete
                          </ActionLink>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              )
            )}
          </tbody>
        </table>
      )}
    </main>
  );
}

function YearFields({
  form,
  setForm,
  inline = false,
}: {
  form: FormState;
  setForm: (f: FormState) => void;
  inline?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: inline ? 0 : "12px" }}>
      <Field label="Label (e.g. 2026-27)" value={form.label} onChange={(v) => setForm({ ...form, label: v })} />
      <Field
        label="Start date"
        type="date"
        value={form.start_date}
        onChange={(v) => setForm({ ...form, start_date: v })}
      />
      <Field label="End date" type="date" value={form.end_date} onChange={(v) => setForm({ ...form, end_date: v })} />
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
      {label}
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "7px 9px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px" }}
      />
    </label>
  );
}

function ActionLink({
  children,
  onClick,
  danger = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: "none",
        border: "none",
        padding: 0,
        fontSize: "13px",
        color: danger ? "var(--red)" : "var(--navy-primary)",
        cursor: "pointer",
        textDecoration: "underline",
      }}
    >
      {children}
    </button>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p
      role="alert"
      style={{
        background: "#fdecea",
        color: "var(--red)",
        padding: "8px 12px",
        borderRadius: "6px",
        fontSize: "13px",
        margin: "8px 0",
      }}
    >
      {message}
    </p>
  );
}

const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
