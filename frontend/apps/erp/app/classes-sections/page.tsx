"use client";

import {
  api,
  ApiError,
  type AcademicYear,
  type ClassSection,
  type CurrentUser,
  type SchoolClass,
  type Section,
  type Subject,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Tab = "classes" | "sections" | "subjects" | "class-sections";

export default function ClassesSectionsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>("class-sections");

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router]);

  // UI-only convenience — real access control is entirely server-side
  // (HasModulePermission + RolePermission table, per-module: "classes_sections"
  // covers Classes/Sections/ClassSection offerings, "subjects" is separate).
  // See docs/permissions.md. Hiding a button here grants nothing on its own.
  const canWriteClassesSections = Boolean(
    user?.is_superuser || user?.role === "Admin" || user?.role === "Principal"
  );
  const canDeleteClassesSections = Boolean(user?.is_superuser || user?.role === "Admin");
  const canWriteSubjects = Boolean(user?.is_superuser || user?.role === "Admin");
  const canDeleteSubjects = Boolean(user?.is_superuser || user?.role === "Admin");

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
        }}
      >
        <div>
          <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
            ← Dashboard
          </Link>
          <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>
            Classes / Sections / Subjects
          </h1>
        </div>
      </header>

      <nav style={{ display: "flex", gap: "4px", marginBottom: "20px", borderBottom: "1px solid var(--line)" }}>
        <TabButton active={tab === "class-sections"} onClick={() => setTab("class-sections")}>
          Class-Sections (Offerings)
        </TabButton>
        <TabButton active={tab === "classes"} onClick={() => setTab("classes")}>
          Classes
        </TabButton>
        <TabButton active={tab === "sections"} onClick={() => setTab("sections")}>
          Sections
        </TabButton>
        <TabButton active={tab === "subjects"} onClick={() => setTab("subjects")}>
          Subjects
        </TabButton>
      </nav>

      {tab === "classes" && <ClassesTab canWrite={canWriteClassesSections} canDelete={canDeleteClassesSections} />}
      {tab === "sections" && <SectionsTab canWrite={canWriteClassesSections} canDelete={canDeleteClassesSections} />}
      {tab === "subjects" && <SubjectsTab canWrite={canWriteSubjects} canDelete={canDeleteSubjects} />}
      {tab === "class-sections" && (
        <ClassSectionsTab canWrite={canWriteClassesSections} canDelete={canDeleteClassesSections} />
      )}
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

/* ---------------------------- Classes tab ---------------------------- */

function ClassesTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [items, setItems] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [order, setOrder] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.classes.list();
      setItems(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load classes.");
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
        const page = await api.classes.list();
        if (!cancelled) setItems(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load classes.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.classes.create({ name, order: order ? Number(order) : 0 });
      setName("");
      setOrder("");
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create class.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: SchoolClass) {
    if (!window.confirm(`Delete class "${item.name}"? This can be restored later if needed.`)) return;
    try {
      await api.classes.remove(item.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this class.");
    }
  }

  return (
    <div>
      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Field label="Name (e.g. Std 10)" value={name} onChange={setName} />
            <Field label="Order (sort number)" value={order} onChange={setOrder} type="number" required={false} />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !name}>
            {saving ? "Saving…" : "Add class"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : items.length === 0 ? (
        <Empty text="No classes yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Order</th>
              {canDelete && <th style={thStyle}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={tbodyRowStyle}>
                <td style={tdStyle}>{item.name}</td>
                <td style={tdStyle}>{item.order}</td>
                {canDelete && (
                  <td style={tdStyle}>
                    <ActionLink onClick={() => handleDelete(item)} danger>
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

/* ---------------------------- Sections tab ---------------------------- */

function SectionsTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [items, setItems] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.sections.list();
      setItems(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load sections.");
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
        const page = await api.sections.list();
        if (!cancelled) setItems(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load sections.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.sections.create({ name });
      setName("");
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create section.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: Section) {
    if (!window.confirm(`Delete section "${item.name}"? This can be restored later if needed.`)) return;
    try {
      await api.sections.remove(item.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this section.");
    }
  }

  return (
    <div>
      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Field label="Name (e.g. A)" value={name} onChange={setName} />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !name}>
            {saving ? "Saving…" : "Add section"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : items.length === 0 ? (
        <Empty text="No sections yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Name</th>
              {canDelete && <th style={thStyle}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={tbodyRowStyle}>
                <td style={tdStyle}>{item.name}</td>
                {canDelete && (
                  <td style={tdStyle}>
                    <ActionLink onClick={() => handleDelete(item)} danger>
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

/* ---------------------------- Subjects tab ---------------------------- */

function SubjectsTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [items, setItems] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setListError(null);
    try {
      const page = await api.subjects.list();
      setItems(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load subjects.");
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
        const page = await api.subjects.list();
        if (!cancelled) setItems(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load subjects.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.subjects.create({ name, code });
      setName("");
      setCode("");
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create subject.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: Subject) {
    if (!window.confirm(`Delete subject "${item.name}"? This can be restored later if needed.`)) return;
    try {
      await api.subjects.remove(item.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this subject.");
    }
  }

  return (
    <div>
      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Field label="Name (e.g. Mathematics)" value={name} onChange={setName} />
            <Field label="Code (e.g. MATH)" value={code} onChange={setCode} />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !name || !code}>
            {saving ? "Saving…" : "Add subject"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : items.length === 0 ? (
        <Empty text="No subjects yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Code</th>
              {canDelete && <th style={thStyle}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={tbodyRowStyle}>
                <td style={tdStyle}>{item.name}</td>
                <td style={tdStyle}>{item.code}</td>
                {canDelete && (
                  <td style={tdStyle}>
                    <ActionLink onClick={() => handleDelete(item)} danger>
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

/* ------------------------- Class-Sections tab ------------------------- */

function ClassSectionsTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [items, setItems] = useState<ClassSection[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);

  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [schoolClassId, setSchoolClassId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [yearId, setYearId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [subjectToAdd, setSubjectToAdd] = useState<string>("");
  const [subjectActionError, setSubjectActionError] = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    setListError(null);
    try {
      const [csPage, classesPage, sectionsPage, yearsPage, subjectsPage] = await Promise.all([
        api.classSections.list(),
        api.classes.list(),
        api.sections.list(),
        api.academicYears.list(),
        api.subjects.list(),
      ]);
      setItems(csPage.results);
      setClasses(classesPage.results);
      setSections(sectionsPage.results);
      setYears(yearsPage.results);
      setSubjects(subjectsPage.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load class-sections.");
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
        const [csPage, classesPage, sectionsPage, yearsPage, subjectsPage] = await Promise.all([
          api.classSections.list(),
          api.classes.list(),
          api.sections.list(),
          api.academicYears.list(),
          api.subjects.list(),
        ]);
        if (!cancelled) {
          setItems(csPage.results);
          setClasses(classesPage.results);
          setSections(sectionsPage.results);
          setYears(yearsPage.results);
          setSubjects(subjectsPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load class-sections.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSaving(true);
    try {
      await api.classSections.create({
        school_class: Number(schoolClassId),
        section: Number(sectionId),
        academic_year: Number(yearId),
      });
      setSchoolClassId("");
      setSectionId("");
      setYearId("");
      await loadAll();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create class-section.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: ClassSection) {
    if (!window.confirm(`Delete "${item.school_class_name}-${item.section_name} (${item.academic_year_label})"?`)) return;
    try {
      await api.classSections.remove(item.id);
      await loadAll();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this class-section.");
    }
  }

  async function handleAddSubject(classSectionId: number) {
    if (!subjectToAdd) return;
    setSubjectActionError(null);
    try {
      await api.classSections.addSubject(classSectionId, Number(subjectToAdd));
      setSubjectToAdd("");
      await loadAll();
    } catch (err) {
      setSubjectActionError(err instanceof ApiError ? err.message : "Could not assign this subject.");
    }
  }

  async function handleRemoveSubject(classSectionId: number, subjectId: number) {
    setSubjectActionError(null);
    try {
      await api.classSections.removeSubject(classSectionId, subjectId);
      await loadAll();
    } catch (err) {
      setSubjectActionError(err instanceof ApiError ? err.message : "Could not remove this subject.");
    }
  }

  return (
    <div>
      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Select label="Class" value={schoolClassId} onChange={setSchoolClassId} options={classes.map((c) => ({ value: c.id, label: c.name }))} />
            <Select label="Section" value={sectionId} onChange={setSectionId} options={sections.map((s) => ({ value: s.id, label: s.name }))} />
            <Select
              label="Academic Year"
              value={yearId}
              onChange={setYearId}
              options={years.map((y) => ({ value: y.id, label: y.label }))}
            />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !schoolClassId || !sectionId || !yearId}>
            {saving ? "Saving…" : "Create offering"}
          </Button>
          {(classes.length === 0 || sections.length === 0 || years.length === 0) && (
            <p style={{ fontSize: "12px", color: "var(--ink)", opacity: 0.6, marginTop: "8px" }}>
              Add at least one Class, Section, and Academic Year before creating an offering.
            </p>
          )}
        </form>
      )}

      {subjectActionError && <ErrorBanner message={subjectActionError} />}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : items.length === 0 ? (
        <Empty text="No class-section offerings yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Class-Section</th>
              <th style={thStyle}>Academic Year</th>
              <th style={thStyle}>Class Teacher</th>
              <th style={thStyle}>Subjects</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <>
                <tr key={item.id} style={tbodyRowStyle}>
                  <td style={tdStyle}>
                    {item.school_class_name}-{item.section_name}
                  </td>
                  <td style={tdStyle}>{item.academic_year_label}</td>
                  <td style={tdStyle}>{item.class_teacher_email ?? "—"}</td>
                  <td style={tdStyle}>
                    {item.subjects.length === 0 ? (
                      <span style={{ opacity: 0.5 }}>None</span>
                    ) : (
                      item.subjects.map((s) => s.subject_code).join(", ")
                    )}
                  </td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", gap: "10px" }}>
                      {canWrite && (
                        <ActionLink onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}>
                          {expandedId === item.id ? "Close" : "Manage subjects"}
                        </ActionLink>
                      )}
                      {canDelete && (
                        <ActionLink onClick={() => handleDelete(item)} danger>
                          Delete
                        </ActionLink>
                      )}
                    </div>
                  </td>
                </tr>
                {expandedId === item.id && (
                  <tr>
                    <td colSpan={5} style={{ padding: "12px 8px", background: "var(--paper)" }}>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
                        {item.subjects.map((s) => (
                          <span
                            key={s.id}
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
                            {s.subject_name}
                            <button
                              onClick={() => handleRemoveSubject(item.id, s.subject)}
                              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--red)" }}
                              aria-label={`Remove ${s.subject_name}`}
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "flex-end" }}>
                        <Select
                          label="Add subject"
                          value={subjectToAdd}
                          onChange={setSubjectToAdd}
                          options={subjects
                            .filter((s) => !item.subjects.some((link) => link.subject === s.id))
                            .map((s) => ({ value: s.id, label: `${s.name} (${s.code})` }))}
                        />
                        <Button type="button" onClick={() => handleAddSubject(item.id)} disabled={!subjectToAdd}>
                          Assign
                        </Button>
                      </div>
                    </td>
                  </tr>
                )}
              </>
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
    <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
      {label}
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "7px 9px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px" }}
      />
    </label>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: number; label: string }[];
}) {
  return (
    <label style={{ fontSize: "13px", display: "flex", flexDirection: "column", gap: "4px" }}>
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ padding: "7px 9px", borderRadius: "6px", border: "1px solid var(--line-strong)", fontSize: "14px", minWidth: "160px" }}
      >
        <option value="">Select…</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Loading() {
  return <p style={{ fontSize: "14px", color: "var(--ink)", opacity: 0.6 }}>Loading…</p>;
}

function Empty({ text }: { text: string }) {
  return <p style={{ fontSize: "14px", color: "var(--ink)", opacity: 0.6 }}>{text}</p>;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" style={{ background: "#fdecea", color: "var(--red)", padding: "8px 12px", borderRadius: "6px", fontSize: "13px", margin: "8px 0" }}>
      {message}
    </p>
  );
}

function ActionLink({ children, onClick, danger = false }: { children: React.ReactNode; onClick: () => void; danger?: boolean }) {
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

const panelStyle: React.CSSProperties = {
  border: "1px solid var(--line)",
  borderRadius: "8px",
  padding: "16px",
  marginBottom: "20px",
  background: "var(--paper)",
};

const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: "14px" };
const theadRowStyle: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid var(--line-strong)" };
const tbodyRowStyle: React.CSSProperties = { borderBottom: "1px solid var(--line)" };
const thStyle: React.CSSProperties = { padding: "8px", fontSize: "12px", color: "var(--ink)", opacity: 0.6 };
const tdStyle: React.CSSProperties = { padding: "10px 8px" };
