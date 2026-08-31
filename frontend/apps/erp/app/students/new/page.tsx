"use client";

import { api, ApiError, type CurrentUser, type StudentWritePayload } from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function NewStudentPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);

  const [form, setForm] = useState<StudentWritePayload>({
    admission_no: "",
    first_name: "",
    last_name: "",
    dob: "",
    gender: "",
    address: "",
    phone: "",
    admission_date: "",
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
        // HasModulePermission; this just avoids showing a form the user
        // can't actually submit.
        const allowed = u.is_superuser || ["Admin", "Principal", "Staff"].includes(u.role ?? "");
        if (!allowed) router.replace("/students");
      })
      .catch(() => router.replace("/login"))
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  function update<K extends keyof StudentWritePayload>(key: K, value: StudentWritePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      const student = await api.students.create({
        ...form,
        admission_date: form.admission_date || null,
      });
      router.push(`/students/detail?id=${student.id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create this student.");
      setSaving(false);
    }
  }

  if (checking) return null;
  if (!user) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "680px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/students" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Students
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Add student</h1>
      </header>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <Row>
          <Field label="Admission No *" value={form.admission_no} onChange={(v) => update("admission_no", v)} placeholder="e.g. KHS-2026-0001" />
          <Field label="Admission date" value={form.admission_date ?? ""} onChange={(v) => update("admission_date", v)} type="date" required={false} />
        </Row>
        <Row>
          <Field label="First name *" value={form.first_name} onChange={(v) => update("first_name", v)} />
          <Field label="Last name *" value={form.last_name} onChange={(v) => update("last_name", v)} />
        </Row>
        <Row>
          <Field label="Date of birth *" value={form.dob} onChange={(v) => update("dob", v)} type="date" />
          <label style={fieldLabelStyle}>
            Gender
            <select
              value={form.gender}
              onChange={(e) => update("gender", e.target.value as StudentWritePayload["gender"])}
              style={inputStyle}
            >
              <option value="">Not specified</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </label>
        </Row>
        <Row>
          <Field label="Phone" value={form.phone ?? ""} onChange={(v) => update("phone", v)} required={false} />
        </Row>
        <label style={fieldLabelStyle}>
          Address
          <textarea
            value={form.address}
            onChange={(e) => update("address", e.target.value)}
            rows={3}
            style={{ ...inputStyle, resize: "vertical" as const }}
          />
        </label>

        {formError && <ErrorBanner message={formError} />}

        <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
          <Button type="submit" disabled={saving || !form.admission_no || !form.first_name || !form.last_name || !form.dob}>
            {saving ? "Saving…" : "Add student"}
          </Button>
          <Link href="/students" style={{ textDecoration: "none" }}>
            <Button type="button" variant="secondary">
              Cancel
            </Button>
          </Link>
        </div>
        <p style={{ fontSize: "12px", opacity: 0.6 }}>
          You can assign this student to a class-section (with a roll number) from their profile page after saving.
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
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label style={{ ...fieldLabelStyle, flex: "1 1 220px" }}>
      {label}
      <input
        type={type}
        required={required}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        style={inputStyle}
      />
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
