"use client";

import {
  api,
  ApiError,
  type CurrentUser,
  type GuardianListItem,
  type ManagedUser,
  type Role,
  type StudentListItem,
  type TeacherListItem,
  type UserCreatePayload,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type ProfileType = "student" | "teacher" | "guardian";

export default function UsersPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [form, setForm] = useState<UserCreatePayload>({ email: "", password: "", role_id: undefined, is_active: true });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [editRoleId, setEditRoleId] = useState("");
  const [editIsActive, setEditIsActive] = useState(true);
  const [editError, setEditError] = useState<string | null>(null);

  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [settingPassword, setSettingPassword] = useState(false);

  const [profileType, setProfileType] = useState<ProfileType>("student");
  const [unlinkedStudents, setUnlinkedStudents] = useState<StudentListItem[]>([]);
  const [unlinkedTeachers, setUnlinkedTeachers] = useState<TeacherListItem[]>([]);
  const [unlinkedGuardians, setUnlinkedGuardians] = useState<GuardianListItem[]>([]);
  const [profileId, setProfileId] = useState("");
  const [linkError, setLinkError] = useState<string | null>(null);
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        const allowed = u.is_superuser || u.role === "Admin";
        if (!allowed) router.replace("/dashboard");
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
      const [usersPage, rolesPage] = await Promise.all([
        api.users.list({ search: overrides?.search ?? search }),
        api.roles.list(),
      ]);
      setUsers(usersPage.results);
      setRoles(rolesPage.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load users.");
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
        const [usersPage, rolesPage] = await Promise.all([api.users.list({}), api.roles.list()]);
        if (!cancelled) {
          setUsers(usersPage.results);
          setRoles(rolesPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load users.");
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
      await api.users.create(form);
      setForm({ email: "", password: "", role_id: undefined, is_active: true });
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create this user.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleExpand(target: ManagedUser) {
    if (expandedId === target.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(target.id);
    setEditRoleId(target.role_id ? String(target.role_id) : "");
    setEditIsActive(target.is_active);
    setEditError(null);
    setNewPassword("");
    setPasswordError(null);
    setPasswordSuccess(false);
    setProfileType("student");
    setProfileId("");
    setLinkError(null);
    try {
      const [studentsPage, teachersPage, guardiansPage] = await Promise.all([
        api.students.list({ unlinked: true }),
        api.teachers.list({ unlinked: true }),
        api.guardians.list({ unlinked: true }),
      ]);
      setUnlinkedStudents(studentsPage.results);
      setUnlinkedTeachers(teachersPage.results);
      setUnlinkedGuardians(guardiansPage.results);
    } catch (err) {
      setLinkError(err instanceof ApiError ? err.message : "Could not load linkable profiles.");
    }
  }

  async function handleSaveEdit(target: ManagedUser) {
    setEditError(null);
    try {
      await api.users.update(target.id, {
        role_id: editRoleId ? Number(editRoleId) : null,
        is_active: editIsActive,
      });
      await load();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : "Could not save changes.");
    }
  }

  async function handleSetPassword(target: ManagedUser) {
    if (!newPassword) return;
    setSettingPassword(true);
    setPasswordError(null);
    setPasswordSuccess(false);
    try {
      await api.users.setPassword(target.id, newPassword);
      setNewPassword("");
      setPasswordSuccess(true);
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : "Could not set password.");
    } finally {
      setSettingPassword(false);
    }
  }

  async function handleLinkProfile(target: ManagedUser) {
    if (!profileId) return;
    setLinking(true);
    setLinkError(null);
    try {
      if (profileType === "student") {
        await api.students.update(Number(profileId), { user: target.id });
      } else if (profileType === "teacher") {
        await api.teachers.update(Number(profileId), { user: target.id });
      } else {
        await api.guardians.update(Number(profileId), { user: target.id });
      }
      setProfileId("");
      const [studentsPage, teachersPage, guardiansPage] = await Promise.all([
        api.students.list({ unlinked: true }),
        api.teachers.list({ unlinked: true }),
        api.guardians.list({ unlinked: true }),
      ]);
      setUnlinkedStudents(studentsPage.results);
      setUnlinkedTeachers(teachersPage.results);
      setUnlinkedGuardians(guardiansPage.results);
    } catch (err) {
      setLinkError(err instanceof ApiError ? err.message : "Could not link this profile.");
    } finally {
      setLinking(false);
    }
  }

  if (checking) return null;
  if (!user) return null;

  const profileOptions =
    profileType === "student"
      ? unlinkedStudents.map((s) => ({ id: s.id, label: `${s.full_name} (${s.admission_no})` }))
      : profileType === "teacher"
        ? unlinkedTeachers.map((t) => ({ id: t.id, label: t.full_name }))
        : unlinkedGuardians.map((g) => ({ id: g.id, label: g.name }));

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "1040px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>User Management</h1>
      </header>

      <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "20px" }}>
        <label style={fieldLabelStyle}>
          Search email
          <input value={search} onChange={(e) => setSearch(e.target.value)} style={inputStyle} />
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      <form onSubmit={handleCreate} style={panelStyle}>
        <h2 style={{ fontSize: "15px", color: "var(--navy-primary)", marginBottom: "10px" }}>Add user</h2>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <label style={fieldLabelStyle}>
            Email *
            <input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} style={inputStyle} />
          </label>
          <label style={fieldLabelStyle}>
            Password *
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              style={inputStyle}
            />
          </label>
          <label style={fieldLabelStyle}>
            Role
            <select
              value={form.role_id ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, role_id: e.target.value ? Number(e.target.value) : undefined }))}
              style={inputStyle}
            >
              <option value="">Not specified</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {formError && <ErrorBanner message={formError} />}
        <Button type="submit" disabled={saving || !form.email || !form.password} style={{ marginTop: "10px" }}>
          {saving ? "Creating…" : "Create user"}
        </Button>
        <p style={{ fontSize: "12px", opacity: 0.6, marginTop: "8px" }}>
          Passwords must meet Django&apos;s standard strength requirements (length, not too common, not all-numeric).
        </p>
      </form>

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : users.length === 0 ? (
        <Empty text="No users found." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Active</th>
              <th style={thStyle}>Last login</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <>
                <tr key={u.id} style={tbodyRowStyle}>
                  <td style={tdStyle}>
                    {u.email} {u.is_superuser && <span style={{ fontSize: "11px", opacity: 0.6 }}>(superuser)</span>}
                  </td>
                  <td style={tdStyle}>{u.role ?? "—"}</td>
                  <td style={tdStyle}>{u.is_active ? "Yes" : "No"}</td>
                  <td style={tdStyle}>{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "Never"}</td>
                  <td style={tdStyle}>
                    <ActionLink onClick={() => toggleExpand(u)}>{expandedId === u.id ? "Close" : "Manage"}</ActionLink>
                  </td>
                </tr>
                {expandedId === u.id && (
                  <tr>
                    <td colSpan={5} style={{ padding: "14px 8px", background: "var(--paper)" }}>
                      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
                        <div>
                          <h3 style={subheadingStyle}>Role & status</h3>
                          <div style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
                            <label style={fieldLabelStyle}>
                              Role
                              <select value={editRoleId} onChange={(e) => setEditRoleId(e.target.value)} style={inputStyle}>
                                <option value="">Not specified</option>
                                {roles.map((r) => (
                                  <option key={r.id} value={r.id}>
                                    {r.name}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <label style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "4px" }}>
                              <input type="checkbox" checked={editIsActive} onChange={(e) => setEditIsActive(e.target.checked)} />
                              Active
                            </label>
                            <Button type="button" variant="secondary" onClick={() => handleSaveEdit(u)}>
                              Save
                            </Button>
                          </div>
                          {editError && <ErrorBanner message={editError} />}
                        </div>

                        <div>
                          <h3 style={subheadingStyle}>Set password</h3>
                          <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
                            <label style={fieldLabelStyle}>
                              New password
                              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} style={inputStyle} />
                            </label>
                            <Button type="button" variant="secondary" onClick={() => handleSetPassword(u)} disabled={settingPassword || !newPassword}>
                              {settingPassword ? "Setting…" : "Set password"}
                            </Button>
                          </div>
                          {passwordError && <ErrorBanner message={passwordError} />}
                          {passwordSuccess && <p style={{ fontSize: "13px", color: "green" }}>Password updated.</p>}
                        </div>

                        <div>
                          <h3 style={subheadingStyle}>Link to profile</h3>
                          <div style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
                            <label style={fieldLabelStyle}>
                              Profile type
                              <select
                                value={profileType}
                                onChange={(e) => {
                                  setProfileType(e.target.value as ProfileType);
                                  setProfileId("");
                                }}
                                style={inputStyle}
                              >
                                <option value="student">Student</option>
                                <option value="teacher">Teacher</option>
                                <option value="guardian">Guardian</option>
                              </select>
                            </label>
                            <label style={fieldLabelStyle}>
                              Unlinked {profileType}
                              <select value={profileId} onChange={(e) => setProfileId(e.target.value)} style={{ ...inputStyle, minWidth: "220px" }}>
                                <option value="">Select…</option>
                                {profileOptions.map((opt) => (
                                  <option key={opt.id} value={opt.id}>
                                    {opt.label}
                                  </option>
                                ))}
                              </select>
                            </label>
                            <Button type="button" variant="secondary" onClick={() => handleLinkProfile(u)} disabled={linking || !profileId}>
                              {linking ? "Linking…" : "Link"}
                            </Button>
                          </div>
                          {profileOptions.length === 0 && (
                            <p style={{ fontSize: "12px", opacity: 0.6, marginTop: "6px" }}>No unlinked {profileType} profiles available.</p>
                          )}
                          {linkError && <ErrorBanner message={linkError} />}
                        </div>
                      </div>
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

function ActionLink({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{ background: "none", border: "none", padding: 0, fontSize: "13px", color: "var(--navy-primary)", cursor: "pointer", textDecoration: "underline" }}
    >
      {children}
    </button>
  );
}

const panelStyle: React.CSSProperties = { border: "1px solid var(--line)", borderRadius: "8px", padding: "16px", marginBottom: "20px", background: "var(--paper)" };
const subheadingStyle: React.CSSProperties = { fontSize: "13px", color: "var(--navy-primary)", marginBottom: "8px", fontWeight: 600 };
const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: "14px" };
const theadRowStyle: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid var(--line-strong)" };
const tbodyRowStyle: React.CSSProperties = { borderBottom: "1px solid var(--line)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
