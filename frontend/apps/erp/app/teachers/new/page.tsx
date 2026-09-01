"use client";

import { api, ApiError, type CurrentUser, type TeacherWritePayload } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function NewTeacherPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [form, setForm] = useState<TeacherWritePayload>({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    joined_date: "",
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        // UI-only convenience — the server still re-checks on submit via
        // HasModulePermission (only Admin has Create on "teachers").
        const allowed = u.is_superuser || u.role === "Admin";
        if (!allowed) router.replace("/teachers");
      })
      .catch(() => router.replace("/login"))
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  function update<K extends keyof TeacherWritePayload>(key: K, value: TeacherWritePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const teacher = await api.teachers.create({ ...form, joined_date: form.joined_date || null });
      router.push(`/teachers/detail?id=${teacher.id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create this teacher.");
      setSaving(false);
    }
  }

  if (checking) return null;
  if (!user) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "680px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/teachers" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Teachers
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Add teacher</h1>
      </header>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <Row>
          <Field label="First name *" value={form.first_name} onChange={(v) => update("first_name", v)} />
          <Field label="Last name *" value={form.last_name} onChange={(v) => update("last_name", v)} />
        </Row>
        <Row>
          <Field label="Phone" value={form.phone ?? ""} onChange={(v) => update("phone", v)} required={false} />
          <Field label="Email" value={form.email ?? ""} onChange={(v) => update("email", v)} type="email" required={false} />
        </Row>
        <Row>
          <Field label="Joined date" value={form.joined_date ?? ""} onChange={(v) => update("joined_date", v)} type="date" required={false} />
        </Row>

        {formError && <ErrorBanner message={formError} />}

        <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
          <Button type="submit" disabled={saving || !form.first_name || !form.last_name}>
            {saving ? "Saving…" : "Add teacher"}
          </Button>
          <Link href="/teachers" style={{ textDecoration: "none" }}>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </Link>
        </div>
        <p style={{ fontSize: "12px", opacity: 0.6 }}>
          You can assign this teacher to class-section subjects from their profile page after saving.
        </p>
      </form>
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

function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px", margin: 0 }}>
      {message}
    </p>
  );
}

const fieldLabelStyle: React.CSSProperties = { fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" };
const inputStyle: React.CSSProperties = { padding: "8px 10px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", fontFamily: "var(--font-body)" };
