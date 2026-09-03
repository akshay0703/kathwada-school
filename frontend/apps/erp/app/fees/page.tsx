"use client";

import {
  api,
  ApiError,
  type AcademicYear,
  type ClassSection,
  type CurrentUser,
  type FeeInvoice,
  type FeeInvoiceListItem,
  type FeeStructure,
  type StudentListItem,
} from "@kathwada/api-client";
import { Button } from "@kathwada/ui";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type Tab = "structures" | "invoices";

export default function FeesPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>("invoices");

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
  // (HasModulePermission + RolePermission, module_key="fees"). See
  // docs/permissions.md's "Fees" row: Admin VCEDX, Principal VX (no
  // Create), Teacher none at all, Staff VCEX, Student V (own), Parent VX.
  const canWrite = Boolean(user?.is_superuser || ["Admin", "Staff"].includes(user?.role ?? ""));
  const canDelete = Boolean(user?.is_superuser || user?.role === "Admin");

  if (checking) return null;

  return (
    <main style={{ padding: "32px", fontFamily: "var(--font-body)", maxWidth: "1040px" }}>
      <header style={{ borderBottom: "1px solid var(--line)", paddingBottom: "16px", marginBottom: "20px" }}>
        <Link href="/dashboard" style={{ fontSize: "13px", color: "var(--navy-primary)", textDecoration: "none" }}>
          ← Dashboard
        </Link>
        <h1 style={{ color: "var(--navy-primary)", fontSize: "22px", margin: "4px 0 0" }}>Fees</h1>
      </header>

      <nav style={{ display: "flex", gap: "4px", marginBottom: "20px", borderBottom: "1px solid var(--line)" }}>
        <TabButton active={tab === "invoices"} onClick={() => setTab("invoices")}>
          Student Invoices
        </TabButton>
        <TabButton active={tab === "structures"} onClick={() => setTab("structures")}>
          Fee Structures
        </TabButton>
      </nav>

      {tab === "structures" && <StructuresTab canWrite={canWrite} canDelete={canDelete} />}
      {tab === "invoices" && <InvoicesTab canWrite={canWrite} canDelete={canDelete} />}
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

/* --------------------------- Fee Structures tab --------------------------- */

function StructuresTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [items, setItems] = useState<FeeStructure[]>([]);
  const [classSections, setClassSections] = useState<ClassSection[]>([]);
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [classSectionId, setClassSectionId] = useState("");
  const [academicYearId, setAcademicYearId] = useState("");
  const [feeHead, setFeeHead] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setListError(null);
    try {
      const [structuresPage, csPage, yearsPage] = await Promise.all([
        api.feeStructures.list(),
        api.classSections.list(),
        api.academicYears.list(),
      ]);
      setItems(structuresPage.results);
      setClassSections(csPage.results);
      setAcademicYears(yearsPage.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load fee structures.");
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
        const [structuresPage, csPage, yearsPage] = await Promise.all([
          api.feeStructures.list(),
          api.classSections.list(),
          api.academicYears.list(),
        ]);
        if (!cancelled) {
          setItems(structuresPage.results);
          setClassSections(csPage.results);
          setAcademicYears(yearsPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load fee structures.");
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
      await api.feeStructures.create({
        class_section: Number(classSectionId),
        academic_year: Number(academicYearId),
        fee_head: feeHead,
        amount,
        due_date: dueDate,
      });
      setFeeHead("");
      setAmount("");
      setDueDate("");
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create this fee structure.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: FeeStructure) {
    if (!window.confirm(`Delete fee structure "${item.fee_head}" for ${item.school_class_name}-${item.section_name}?`)) return;
    try {
      await api.feeStructures.remove(item.id);
      await load();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this fee structure.");
    }
  }

  return (
    <div>
      {canWrite && (
        <form onSubmit={handleCreate} style={panelStyle}>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Select
              label="Class-Section"
              value={classSectionId}
              onChange={setClassSectionId}
              options={classSections.map((cs) => ({ value: cs.id, label: `${cs.school_class_name}-${cs.section_name} (${cs.academic_year_label})` }))}
            />
            <Select label="Academic Year" value={academicYearId} onChange={setAcademicYearId} options={academicYears.map((y) => ({ value: y.id, label: y.label }))} />
            <Field label="Fee head (e.g. Tuition)" value={feeHead} onChange={setFeeHead} />
            <Field label="Amount" value={amount} onChange={setAmount} type="number" />
            <Field label="Due date" value={dueDate} onChange={setDueDate} type="date" />
          </div>
          {formError && <ErrorBanner message={formError} />}
          <Button type="submit" disabled={saving || !classSectionId || !academicYearId || !feeHead || !amount || !dueDate}>
            {saving ? "Saving…" : "Add fee structure"}
          </Button>
        </form>
      )}

      {loading ? (
        <Loading />
      ) : listError ? (
        <ErrorBanner message={listError} />
      ) : items.length === 0 ? (
        <Empty text="No fee structures yet." />
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr style={theadRowStyle}>
              <th style={thStyle}>Class-Section</th>
              <th style={thStyle}>Fee head</th>
              <th style={thStyle}>Amount</th>
              <th style={thStyle}>Due date</th>
              {canDelete && <th style={thStyle}></th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={tbodyRowStyle}>
                <td style={tdStyle}>
                  {item.school_class_name}-{item.section_name} ({item.academic_year_label})
                </td>
                <td style={tdStyle}>{item.fee_head}</td>
                <td style={tdStyle}>{item.amount}</td>
                <td style={tdStyle}>{item.due_date}</td>
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

/* ---------------------------- Invoices tab ---------------------------- */

function InvoicesTab({ canWrite, canDelete }: { canWrite: boolean; canDelete: boolean }) {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [studentId, setStudentId] = useState("");
  const [feeStructures, setFeeStructures] = useState<FeeStructure[]>([]);
  const [invoices, setInvoices] = useState<FeeInvoiceListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [feeStructureId, setFeeStructureId] = useState("");
  const [creatingInvoice, setCreatingInvoice] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<FeeInvoice | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentDate, setPaymentDate] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [payingInProgress, setPayingInProgress] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const [studentsPage, structuresPage] = await Promise.all([api.students.list({}), api.feeStructures.list()]);
        if (!cancelled) {
          setStudents(studentsPage.results);
          setFeeStructures(structuresPage.results);
        }
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load filters.");
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadInvoices() {
    if (!studentId) return;
    setLoading(true);
    setListError(null);
    try {
      const page = await api.feeInvoices.list({ student: Number(studentId) });
      setInvoices(page.results);
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not load invoices.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!studentId) {
        if (!cancelled) setInvoices([]);
        return;
      }
      setLoading(true);
      setListError(null);
      try {
        const page = await api.feeInvoices.list({ student: Number(studentId) });
        if (!cancelled) setInvoices(page.results);
      } catch (err) {
        if (!cancelled) setListError(err instanceof ApiError ? err.message : "Could not load invoices.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [studentId]);

  async function handleCreateInvoice(e: React.FormEvent) {
    e.preventDefault();
    if (!studentId || !feeStructureId) return;
    setCreateError(null);
    setCreatingInvoice(true);
    try {
      await api.feeInvoices.create({ student: Number(studentId), fee_structure: Number(feeStructureId) });
      setFeeStructureId("");
      await loadInvoices();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Could not create this invoice.");
    } finally {
      setCreatingInvoice(false);
    }
  }

  async function toggleExpand(invoiceId: number) {
    if (expandedId === invoiceId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(invoiceId);
    setPaymentError(null);
    try {
      const full = await api.feeInvoices.retrieve(invoiceId);
      setDetail(full);
    } catch (err) {
      setPaymentError(err instanceof ApiError ? err.message : "Could not load this invoice.");
    }
  }

  async function handleRecordPayment(e: React.FormEvent) {
    e.preventDefault();
    if (!detail || !paymentAmount || !paymentDate) return;
    setPayingInProgress(true);
    setPaymentError(null);
    try {
      await api.feePayments.create({ fee_invoice: detail.id, amount: paymentAmount, paid_at: paymentDate, method: paymentMethod });
      setPaymentAmount("");
      setPaymentDate("");
      const full = await api.feeInvoices.retrieve(detail.id);
      setDetail(full);
      await loadInvoices();
    } catch (err) {
      setPaymentError(err instanceof ApiError ? err.message : "Could not record this payment.");
    } finally {
      setPayingInProgress(false);
    }
  }

  async function handleDeleteInvoice(invoice: FeeInvoiceListItem) {
    if (!window.confirm(`Delete invoice for "${invoice.fee_head}"?`)) return;
    try {
      await api.feeInvoices.remove(invoice.id);
      await loadInvoices();
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : "Could not delete this invoice.");
    }
  }

  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <Select label="Student" value={studentId} onChange={setStudentId} options={students.map((s) => ({ value: s.id, label: `${s.full_name} (${s.admission_no})` }))} />
      </div>

      {!studentId ? (
        <Empty text="Select a student to view their fee invoices." />
      ) : (
        <>
          {canWrite && (
            <form onSubmit={handleCreateInvoice} style={{ display: "flex", gap: "10px", alignItems: "flex-end", marginBottom: "16px", flexWrap: "wrap" }}>
              <Select
                label="Bill against fee structure"
                value={feeStructureId}
                onChange={setFeeStructureId}
                options={feeStructures.map((fs) => ({ value: fs.id, label: `${fs.school_class_name}-${fs.section_name} — ${fs.fee_head} (${fs.amount})` }))}
              />
              <Button type="submit" disabled={creatingInvoice || !feeStructureId}>
                {creatingInvoice ? "Creating…" : "Create invoice"}
              </Button>
            </form>
          )}
          {createError && <ErrorBanner message={createError} />}

          {loading ? (
            <Loading />
          ) : listError ? (
            <ErrorBanner message={listError} />
          ) : invoices.length === 0 ? (
            <Empty text="No invoices for this student yet." />
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr style={theadRowStyle}>
                  <th style={thStyle}>Fee head</th>
                  <th style={thStyle}>Amount due</th>
                  <th style={thStyle}>Paid</th>
                  <th style={thStyle}>Balance</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}></th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <>
                    <tr key={inv.id} style={tbodyRowStyle}>
                      <td style={tdStyle}>{inv.fee_head}</td>
                      <td style={tdStyle}>{inv.amount_due}</td>
                      <td style={tdStyle}>{inv.amount_paid}</td>
                      <td style={tdStyle}>{inv.balance}</td>
                      <td style={tdStyle}>
                        <StatusBadge status={inv.status} />
                      </td>
                      <td style={tdStyle}>
                        <div style={{ display: "flex", gap: "10px" }}>
                          <ActionLink onClick={() => toggleExpand(inv.id)}>{expandedId === inv.id ? "Close" : "Payments"}</ActionLink>
                          {canDelete && (
                            <ActionLink onClick={() => handleDeleteInvoice(inv)} danger>
                              Delete
                            </ActionLink>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedId === inv.id && detail && (
                      <tr>
                        <td colSpan={6} style={{ padding: "12px 8px", background: "var(--paper)" }}>
                          {detail.payments.length === 0 ? (
                            <p style={{ fontSize: "13px", opacity: 0.6, marginBottom: "10px" }}>No payments recorded yet.</p>
                          ) : (
                            <table style={{ ...tableStyle, marginBottom: "10px" }}>
                              <thead>
                                <tr style={theadRowStyle}>
                                  <th style={thStyle}>Amount</th>
                                  <th style={thStyle}>Paid on</th>
                                  <th style={thStyle}>Method</th>
                                  <th style={thStyle}>Recorded by</th>
                                </tr>
                              </thead>
                              <tbody>
                                {detail.payments.map((p) => (
                                  <tr key={p.id} style={tbodyRowStyle}>
                                    <td style={tdStyle}>{p.amount}</td>
                                    <td style={tdStyle}>{p.paid_at}</td>
                                    <td style={tdStyle}>{p.method}</td>
                                    <td style={tdStyle}>{p.recorded_by_email ?? "—"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                          {canWrite && detail.status !== "paid" && (
                            <form onSubmit={handleRecordPayment} style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap" }}>
                              <Field label="Amount" value={paymentAmount} onChange={setPaymentAmount} type="number" />
                              <Field label="Paid on" value={paymentDate} onChange={setPaymentDate} type="date" />
                              <label style={fieldLabelStyle}>
                                Method
                                <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} style={{ ...inputStyle, minWidth: "120px" }}>
                                  <option value="cash">Cash</option>
                                  <option value="cheque">Cheque</option>
                                  <option value="online">Online</option>
                                  <option value="card">Card</option>
                                  <option value="other">Other</option>
                                </select>
                              </label>
                              <Button type="submit" disabled={payingInProgress || !paymentAmount || !paymentDate}>
                                {payingInProgress ? "Recording…" : "Record payment"}
                              </Button>
                            </form>
                          )}
                          {paymentError && <ErrorBanner message={paymentError} />}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------ Shared UI ------------------------------ */

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = { pending: "#8a6d00", partial: "#8a4b00", paid: "green" };
  return <span style={{ color: colors[status] ?? "inherit", fontWeight: 600, textTransform: "capitalize" }}>{status}</span>;
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label style={fieldLabelStyle}>
      {label}
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
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
    <label style={fieldLabelStyle}>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} style={{ ...inputStyle, minWidth: "180px" }}>
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
