const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

// Fetches a fresh CSRF token before every unsafe request and reads it
// directly from the JSON response body, not from document.cookie. The
// previous version relied on the browser making the csrftoken cookie
// readable via JS after ensureCsrfCookie()'s fetch — which works fine
// same-origin in local dev, but is exactly the kind of cross-site cookie
// access that Safari's Intelligent Tracking Prevention (and Chrome's
// ongoing third-party-cookie restrictions) can silently block, even with
// SameSite=None; Secure set correctly on the backend (see
// config/settings/prod.py) — SameSite=None controls whether the browser
// *sends* the cookie on a cross-site request, not whether JS is allowed
// to *read* it back afterward via document.cookie, and those are governed
// by separate, stricter anti-tracking rules in some browsers. Reading the
// token from the response body sidesteps that failure mode entirely: it's
// just parsing an ordinary (CORS-permitted) JSON response, not touching
// the cookie jar at all. The session cookie itself still depends on
// SameSite=None; Secure being sent by the browser on the request — that
// part is unavoidable and already handled — this only hardens CSRF
// *token acquisition*, the other half of the same cross-site cookie story.
async function fetchCsrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: "include" });
  if (!response.ok) {
    throw new ApiError(response.status, null, "Could not obtain a CSRF token. Please reload the page and try again.");
  }
  const data = (await response.json()) as { csrfToken?: string };
  if (!data.csrfToken) {
    throw new ApiError(0, data, "Could not obtain a CSRF token. Please reload the page and try again.");
  }
  return data.csrfToken;
}

export type CurrentUser = {
  id: number;
  email: string;
  role: string | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
};

export type Role = {
  id: number;
  name: string;
  description: string;
};

export type ManagedUser = {
  id: number;
  email: string;
  role: string | null;
  role_id: number | null;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at: string | null;
  created_at: string;
};

export type UserCreatePayload = {
  email: string;
  password: string;
  role_id?: number | null;
  is_active?: boolean;
};

export type UserUpdatePayload = {
  email?: string;
  role_id?: number | null;
  is_active?: boolean;
};

export type AcademicYear = {
  id: number;
  school: string;
  label: string;
  start_date: string; // "YYYY-MM-DD"
  end_date: string;
  is_current: boolean;
  created_at: string;
  updated_at: string;
};

export type SchoolClass = {
  id: number;
  name: string;
  order: number;
  created_at: string;
  updated_at: string;
};

export type Section = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
};

export type Subject = {
  id: number;
  name: string;
  code: string;
  created_at: string;
  updated_at: string;
};

export type ClassSectionSubject = {
  id: number;
  subject: number;
  subject_name: string;
  subject_code: string;
};

export type ClassSection = {
  id: number;
  school_class: number;
  school_class_name: string;
  section: number;
  section_name: string;
  academic_year: number;
  academic_year_label: string;
  class_teacher: number | null;
  class_teacher_email: string | null;
  subjects: ClassSectionSubject[];
  created_at: string;
  updated_at: string;
};

export type StudentCurrentClassSection = {
  id: number;
  label: string; // e.g. "Std 10-A (2026-27)"
  roll_no: number;
};

export type StudentListItem = {
  id: number;
  admission_no: string;
  first_name: string;
  last_name: string;
  full_name: string;
  dob: string; // "YYYY-MM-DD"
  gender: "male" | "female" | "other" | "";
  phone: string;
  current_class_section: StudentCurrentClassSection | null;
};

export type Student = {
  id: number;
  user: number | null;
  admission_no: string;
  first_name: string;
  last_name: string;
  full_name: string;
  dob: string;
  gender: "male" | "female" | "other" | "";
  address: string;
  phone: string;
  admission_date: string | null;
  enrollments: Enrollment[];
  created_at: string;
  updated_at: string;
};

export type EnrollmentStatus = "active" | "transferred" | "graduated";

export type Enrollment = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  class_section: number;
  school_class_name: string;
  section_name: string;
  academic_year_label: string;
  roll_no: number;
  status: EnrollmentStatus;
  created_at: string;
  updated_at: string;
};

export type StudentWritePayload = {
  admission_no: string;
  first_name: string;
  last_name: string;
  dob: string;
  gender?: "male" | "female" | "other" | "";
  address?: string;
  phone?: string;
  admission_date?: string | null;
  user?: number | null;
};

export type TeacherAssignment = {
  id: number;
  teacher: number;
  teacher_name: string;
  class_section_subject: number;
  subject_name: string;
  subject_code: string;
  school_class_name: string;
  section_name: string;
  academic_year_label: string;
  created_at: string;
};

export type TeacherListItem = {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  email: string;
  joined_date: string | null;
  assignment_count: number;
};

export type Teacher = {
  id: number;
  user: number | null;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  email: string;
  joined_date: string | null;
  assignments: TeacherAssignment[];
  created_at: string;
  updated_at: string;
};

export type TeacherWritePayload = {
  first_name: string;
  last_name: string;
  phone?: string;
  email?: string;
  joined_date?: string | null;
  user?: number | null;
};

export type AttendanceStatus = "present" | "absent" | "late" | "excused";

export type AttendanceRecord = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  class_section: number;
  school_class_name: string;
  section_name: string;
  academic_year_label: string;
  date: string; // "YYYY-MM-DD"
  status: AttendanceStatus;
  marked_by: number | null;
  marked_by_email: string | null;
  marked_at: string;
  created_at: string;
  updated_at: string;
};

export type Exam = {
  id: number;
  academic_year: number;
  academic_year_label: string;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  sequence_order: number;
  exam_subjects: ExamSubject[];
  created_at: string;
  updated_at: string;
};

export type ExamListItem = {
  id: number;
  academic_year: number;
  academic_year_label: string;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  sequence_order: number;
  subject_count: number;
};

export type ExamWritePayload = {
  academic_year: number;
  code: string;
  name: string;
  start_date: string;
  end_date: string;
  sequence_order?: number;
};

export type ExamSubject = {
  id: number;
  exam: number;
  exam_name: string;
  class_section: number;
  school_class_name: string;
  section_name: string;
  subject: number;
  subject_name: string;
  subject_code: string;
  max_marks: string;
  passing_marks: string | null;
};

export type Mark = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  exam_subject: number;
  exam_name: string;
  subject_name: string;
  subject_code: string;
  max_marks: string;
  marks_obtained: string;
  entered_by: number | null;
  entered_by_email: string | null;
  entered_at: string;
  created_at: string;
  updated_at: string;
};

export type MarksheetSubjectRow = {
  exam_subject: number;
  subject_name: string;
  subject_code: string;
  max_marks: string;
  passing_marks: string | null;
  marks_obtained: string | null;
  passed: boolean | null;
};

export type Marksheet = {
  student: { id: number; full_name: string; admission_no: string };
  exam: { id: number; code: string; name: string };
  academic_year_label: string;
  class_section_label: string;
  roll_no: number;
  subjects: MarksheetSubjectRow[];
  total_obtained: string;
  total_max: string;
  percentage: number | null;
  all_marks_entered: boolean;
  overall_result: "pass" | "fail" | null;
};

export type ClassMarksheetRow = {
  student: { id: number; full_name: string; admission_no: string };
  total_obtained: string;
  total_max: string;
  percentage: number | null;
  all_marks_entered: boolean;
  overall_result: "pass" | "fail" | null;
};

export type FeeStructure = {
  id: number;
  class_section: number;
  school_class_name: string;
  section_name: string;
  academic_year: number;
  academic_year_label: string;
  fee_head: string;
  amount: string;
  due_date: string;
  created_at: string;
  updated_at: string;
};

export type FeeInvoiceStatus = "pending" | "partial" | "paid";

export type FeePayment = {
  id: number;
  fee_invoice: number;
  amount: string;
  paid_at: string;
  method: "cash" | "cheque" | "online" | "card" | "other";
  recorded_by: number | null;
  recorded_by_email: string | null;
  created_at: string;
};

export type FeeInvoice = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  fee_structure: number;
  fee_head: string;
  due_date: string;
  academic_year_label: string;
  amount_due: string;
  amount_paid: string;
  balance: string;
  status: FeeInvoiceStatus;
  payments: FeePayment[];
  created_at: string;
  updated_at: string;
};

export type FeeInvoiceListItem = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  fee_structure: number;
  fee_head: string;
  amount_due: string;
  amount_paid: string;
  balance: string;
  status: FeeInvoiceStatus;
};

export type GuardianRelationship = "father" | "mother" | "guardian" | "other";

export type StudentGuardianLink = {
  id: number;
  student: number;
  student_name: string;
  student_admission_no: string;
  guardian: number;
  guardian_name: string;
  is_primary_contact: boolean;
};

export type Guardian = {
  id: number;
  user: number | null;
  name: string;
  phone: string;
  email: string;
  relationship: GuardianRelationship | "";
  student_links: StudentGuardianLink[];
  created_at: string;
  updated_at: string;
};

export type GuardianListItem = {
  id: number;
  name: string;
  phone: string;
  email: string;
  relationship: GuardianRelationship | "";
  child_count: number;
};

export type GuardianWritePayload = {
  name: string;
  phone?: string;
  email?: string;
  relationship?: GuardianRelationship | "";
  user?: number | null;
};

export type Book = {
  id: number;
  title: string;
  author: string;
  category: string;
  total_copies: number;
  available_copies: number;
  created_at: string;
  updated_at: string;
};

export type BookWritePayload = {
  title: string;
  author?: string;
  category?: string;
  total_copies?: number;
};

export type BookIssue = {
  id: number;
  book: number;
  book_title: string;
  student: number;
  student_name: string;
  student_admission_no: string;
  issue_date: string;
  due_date: string;
  return_date: string | null;
  fine_amount: string;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

// Thrown by request<T>() so callers can distinguish "the server explained
// what was wrong" (e.g. a 400 validation error) from a generic failure.
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function toQueryString(params: Record<string, string | number | undefined | null>): string {
  const usable = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (usable.length === 0) return "";
  const search = new URLSearchParams(usable.map(([k, v]) => [k, String(v)]));
  return `?${search.toString()}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const isUnsafe = !["GET", "HEAD", "OPTIONS"].includes(method);

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (isUnsafe) {
    const csrfToken = await fetchCsrfToken();
    headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include", // send the HttpOnly session cookie
  });

  if (!response.ok) {
    let body: unknown = null;
    let detail = response.statusText;
    try {
      body = await response.json();
      detail = extractErrorMessage(body) ?? detail;
    } catch {
      // response had no JSON body — fall back to statusText
    }
    throw new ApiError(response.status, body, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// DRF error bodies vary in shape: {"detail": "..."} for permission/auth
// errors, {"field_name": ["msg"]} or {"non_field_errors": ["msg"]} for
// serializer validation errors. This normalizes all of them into one
// human-readable string for display.
function extractErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const obj = body as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  const messages: string[] = [];
  for (const [field, value] of Object.entries(obj)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    messages.push(field === "non_field_errors" ? text : `${field}: ${text}`);
  }
  return messages.length ? messages.join(" ") : null;
}

// For following a paginated response's `next`/`previous` URLs directly
// (DRF returns full absolute URLs for those, already including API_BASE_URL).
async function requestAbsolute<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) {
    let body: unknown = null;
    let detail = response.statusText;
    try {
      body = await response.json();
      detail = extractErrorMessage(body) ?? detail;
    } catch {
      // no JSON body
    }
    throw new ApiError(response.status, body, detail);
  }
  return response.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<CurrentUser>("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),
  me: () => request<CurrentUser>("/auth/me/"),
  health: () => request<{ status: string; database: boolean }>("/health/"),

  academicYears: {
    list: () => request<PaginatedResponse<AcademicYear>>("/academic-years/"),
    create: (data: Pick<AcademicYear, "label" | "start_date" | "end_date">) =>
      request<AcademicYear>("/academic-years/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Pick<AcademicYear, "label" | "start_date" | "end_date">>) =>
      request<AcademicYear>(`/academic-years/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/academic-years/${id}/`, { method: "DELETE" }),
    markCurrent: (id: number) => request<AcademicYear>(`/academic-years/${id}/mark-current/`, { method: "POST" }),
  },

  classes: {
    list: () => request<PaginatedResponse<SchoolClass>>("/classes/"),
    create: (data: Pick<SchoolClass, "name" | "order">) =>
      request<SchoolClass>("/classes/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Pick<SchoolClass, "name" | "order">>) =>
      request<SchoolClass>(`/classes/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/classes/${id}/`, { method: "DELETE" }),
  },

  sections: {
    list: () => request<PaginatedResponse<Section>>("/sections/"),
    create: (data: Pick<Section, "name">) => request<Section>("/sections/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Pick<Section, "name">>) =>
      request<Section>(`/sections/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/sections/${id}/`, { method: "DELETE" }),
  },

  subjects: {
    list: () => request<PaginatedResponse<Subject>>("/subjects/"),
    create: (data: Pick<Subject, "name" | "code">) =>
      request<Subject>("/subjects/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Pick<Subject, "name" | "code">>) =>
      request<Subject>(`/subjects/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/subjects/${id}/`, { method: "DELETE" }),
  },

  classSections: {
    list: () => request<PaginatedResponse<ClassSection>>("/class-sections/"),
    create: (data: { school_class: number; section: number; academic_year: number; class_teacher?: number | null }) =>
      request<ClassSection>("/class-sections/", { method: "POST", body: JSON.stringify(data) }),
    update: (
      id: number,
      data: Partial<{ school_class: number; section: number; academic_year: number; class_teacher: number | null }>
    ) => request<ClassSection>(`/class-sections/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/class-sections/${id}/`, { method: "DELETE" }),
    addSubject: (id: number, subjectId: number) =>
      request<ClassSectionSubject>(`/class-sections/${id}/subjects/`, {
        method: "POST",
        body: JSON.stringify({ subject: subjectId }),
      }),
    removeSubject: (id: number, subjectId: number) =>
      request<void>(`/class-sections/${id}/subjects/remove/`, {
        method: "POST",
        body: JSON.stringify({ subject: subjectId }),
      }),
  },

  students: {
    list: (params?: { search?: string; gender?: string; class_section?: number; ordering?: string; unlinked?: boolean }) =>
      request<PaginatedResponse<StudentListItem>>(
        `/students/${toQueryString({ ...params, unlinked: params?.unlinked ? "true" : undefined })}`
      ),
    listPage: (url: string) => requestAbsolute<PaginatedResponse<StudentListItem>>(url),
    retrieve: (id: number) => request<Student>(`/students/${id}/`),
    create: (data: StudentWritePayload) =>
      request<Student>("/students/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<StudentWritePayload>) =>
      request<Student>(`/students/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/students/${id}/`, { method: "DELETE" }),
  },

  enrollments: {
    list: (params?: { student?: number; class_section?: number; status?: string }) =>
      request<PaginatedResponse<Enrollment>>(`/enrollments/${toQueryString(params ?? {})}`),
    create: (data: { student: number; class_section: number; roll_no: number; status?: EnrollmentStatus }) =>
      request<Enrollment>("/enrollments/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<{ class_section: number; roll_no: number; status: EnrollmentStatus }>) =>
      request<Enrollment>(`/enrollments/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/enrollments/${id}/`, { method: "DELETE" }),
  },

  teachers: {
    list: (params?: { search?: string; class_section?: number; ordering?: string; unlinked?: boolean }) =>
      request<PaginatedResponse<TeacherListItem>>(
        `/teachers/${toQueryString({ ...params, unlinked: params?.unlinked ? "true" : undefined })}`
      ),
    listPage: (url: string) => requestAbsolute<PaginatedResponse<TeacherListItem>>(url),
    retrieve: (id: number) => request<Teacher>(`/teachers/${id}/`),
    create: (data: TeacherWritePayload) =>
      request<Teacher>("/teachers/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<TeacherWritePayload>) =>
      request<Teacher>(`/teachers/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/teachers/${id}/`, { method: "DELETE" }),
  },

  teacherAssignments: {
    list: (params?: { teacher?: number; class_section_subject?: number }) =>
      request<PaginatedResponse<TeacherAssignment>>(`/teacher-assignments/${toQueryString(params ?? {})}`),
    create: (data: { teacher: number; class_section_subject: number }) =>
      request<TeacherAssignment>("/teacher-assignments/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/teacher-assignments/${id}/`, { method: "DELETE" }),
  },

  attendance: {
    list: (params?: { class_section?: number; date?: string; student?: number }) =>
      request<PaginatedResponse<AttendanceRecord>>(`/attendance/${toQueryString(params ?? {})}`),
    update: (id: number, data: { status: AttendanceStatus }) =>
      request<AttendanceRecord>(`/attendance/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/attendance/${id}/`, { method: "DELETE" }),
    bulkMark: (data: { class_section: number; date: string; records: { student: number; status: AttendanceStatus }[] }) =>
      request<AttendanceRecord[]>("/attendance/bulk-mark/", { method: "POST", body: JSON.stringify(data) }),
  },

  exams: {
    list: (params?: { academic_year?: number }) =>
      request<PaginatedResponse<ExamListItem>>(`/exams/${toQueryString(params ?? {})}`),
    retrieve: (id: number) => request<Exam>(`/exams/${id}/`),
    create: (data: ExamWritePayload) => request<Exam>("/exams/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<ExamWritePayload>) =>
      request<Exam>(`/exams/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/exams/${id}/`, { method: "DELETE" }),
  },

  examSubjects: {
    list: (params?: { exam?: number; class_section?: number }) =>
      request<PaginatedResponse<ExamSubject>>(`/exam-subjects/${toQueryString(params ?? {})}`),
    create: (data: { exam: number; class_section: number; subject: number; max_marks: string }) =>
      request<ExamSubject>("/exam-subjects/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/exam-subjects/${id}/`, { method: "DELETE" }),
  },

  marks: {
    list: (params?: { exam_subject?: number; exam?: number; student?: number }) =>
      request<PaginatedResponse<Mark>>(`/marks/${toQueryString(params ?? {})}`),
    update: (id: number, data: { marks_obtained: string }) =>
      request<Mark>(`/marks/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/marks/${id}/`, { method: "DELETE" }),
    bulkSave: (data: { exam_subject: number; records: { student: number; marks_obtained: string }[] }) =>
      request<Mark[]>("/marks/bulk-save/", { method: "POST", body: JSON.stringify(data) }),
    marksheet: (params: { student: number; exam: number }) =>
      request<Marksheet>(`/marks/marksheet/${toQueryString(params)}`),
    classMarksheet: (params: { class_section: number; exam: number }) =>
      request<ClassMarksheetRow[]>(`/marks/class-marksheet/${toQueryString(params)}`),
  },

  feeStructures: {
    list: (params?: { class_section?: number; academic_year?: number }) =>
      request<PaginatedResponse<FeeStructure>>(`/fee-structures/${toQueryString(params ?? {})}`),
    create: (data: { class_section: number; academic_year: number; fee_head: string; amount: string; due_date: string }) =>
      request<FeeStructure>("/fee-structures/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/fee-structures/${id}/`, { method: "DELETE" }),
  },

  feeInvoices: {
    list: (params?: { student?: number; fee_structure?: number; status?: string }) =>
      request<PaginatedResponse<FeeInvoiceListItem>>(`/fee-invoices/${toQueryString(params ?? {})}`),
    retrieve: (id: number) => request<FeeInvoice>(`/fee-invoices/${id}/`),
    create: (data: { student: number; fee_structure: number; amount_due?: string }) =>
      request<FeeInvoice>("/fee-invoices/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/fee-invoices/${id}/`, { method: "DELETE" }),
  },

  feePayments: {
    create: (data: { fee_invoice: number; amount: string; paid_at: string; method: string }) =>
      request<FeePayment>("/fee-payments/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/fee-payments/${id}/`, { method: "DELETE" }),
  },

  guardians: {
    list: (params?: { search?: string; unlinked?: boolean }) =>
      request<PaginatedResponse<GuardianListItem>>(
        `/guardians/${toQueryString({ ...params, unlinked: params?.unlinked ? "true" : undefined })}`
      ),
    retrieve: (id: number) => request<Guardian>(`/guardians/${id}/`),
    create: (data: GuardianWritePayload) =>
      request<Guardian>("/guardians/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<GuardianWritePayload>) =>
      request<Guardian>(`/guardians/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/guardians/${id}/`, { method: "DELETE" }),
  },

  studentGuardians: {
    list: (params?: { student?: number; guardian?: number }) =>
      request<PaginatedResponse<StudentGuardianLink>>(`/student-guardians/${toQueryString(params ?? {})}`),
    create: (data: { student: number; guardian: number; is_primary_contact?: boolean }) =>
      request<StudentGuardianLink>("/student-guardians/", { method: "POST", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/student-guardians/${id}/`, { method: "DELETE" }),
  },

  books: {
    list: (params?: { search?: string; category?: string }) =>
      request<PaginatedResponse<Book>>(`/books/${toQueryString(params ?? {})}`),
    create: (data: BookWritePayload) => request<Book>("/books/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<BookWritePayload>) =>
      request<Book>(`/books/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/books/${id}/`, { method: "DELETE" }),
  },

  bookIssues: {
    list: (params?: { book?: number; student?: number; outstanding?: boolean }) =>
      request<PaginatedResponse<BookIssue>>(
        `/book-issues/${toQueryString({ ...params, outstanding: params?.outstanding ? "true" : undefined })}`
      ),
    create: (data: { book: number; student: number; issue_date: string; due_date?: string }) =>
      request<BookIssue>("/book-issues/", { method: "POST", body: JSON.stringify(data) }),
    returnBook: (id: number, returnDate?: string) =>
      request<BookIssue>(`/book-issues/${id}/return/`, {
        method: "POST",
        body: JSON.stringify(returnDate ? { return_date: returnDate } : {}),
      }),
    remove: (id: number) => request<void>(`/book-issues/${id}/`, { method: "DELETE" }),
  },

  users: {
    list: (params?: { search?: string; role?: number; is_active?: boolean }) =>
      request<PaginatedResponse<ManagedUser>>(
        `/auth/users/${toQueryString({ ...params, is_active: params?.is_active === undefined ? undefined : String(params.is_active) })}`
      ),
    retrieve: (id: number) => request<ManagedUser>(`/auth/users/${id}/`),
    create: (data: UserCreatePayload) =>
      request<ManagedUser>("/auth/users/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: UserUpdatePayload) =>
      request<ManagedUser>(`/auth/users/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
    setPassword: (id: number, password: string) =>
      request<{ detail: string }>(`/auth/users/${id}/set-password/`, {
        method: "POST",
        body: JSON.stringify({ password }),
      }),
  },

  roles: {
    list: () => request<PaginatedResponse<Role>>("/auth/roles/"),
  },
};
