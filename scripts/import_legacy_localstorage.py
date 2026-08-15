#!/usr/bin/env python3
"""
Phase 0.13 — legacy prototype data migration: DRY-RUN PARSER ONLY.

Reads a `khs_erp_data_v1` JSON export (see architecture doc §15 for the exact
shape) and validates/normalizes it into the shapes the production schema
expects (§3.2). Prints a summary report. Writes NOTHING to any database —
that write path is intentionally not built yet, per your instruction to keep
this a validation-only script until you provide real data.

Usage:
    python scripts/import_legacy_localstorage.py scripts/sample_data/khs_erp_data_v1.demo.json

Exit code is 0 if the file parses cleanly, 1 if any row fails validation
(all failures are collected and reported together, not fail-fast, so you see
every problem in one pass).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

TEST_KEYS = ["fst", "sst", "ut1", "ut2", "main"]


@dataclass
class ValidationIssue:
    entity: str
    identifier: str
    message: str


@dataclass
class ParsedStudent:
    legacy_roll: int
    name: str
    dob: str
    guardian_name: str
    guardian_phone: str
    address: str
    marks: dict  # subject -> {fst, sst, ut1, ut2, main, internal: {p1,p2,p3}}


@dataclass
class ParsedTeacher:
    legacy_id: int
    name: str
    subject: str
    classes_raw: str
    phone: str
    email: str


@dataclass
class ParsedBook:
    legacy_id: int
    title: str
    author: str
    category: str
    copies: int


@dataclass
class ParseResult:
    school_name: str = ""
    class_label: str = ""
    academic_year_label: str = ""
    subjects: list = field(default_factory=list)
    max_marks: dict = field(default_factory=dict)
    pass_marks: dict = field(default_factory=dict)
    internal_max: dict = field(default_factory=dict)
    internal_pass: int = 0
    students: list = field(default_factory=list)
    teachers: list = field(default_factory=list)
    books: list = field(default_factory=list)
    attendance_dates: int = 0
    fee_records: int = 0
    library_issues: int = 0
    issues: list = field(default_factory=list)  # ValidationIssue


def _to_decimal_or_blank(raw, field_name, entity, identifier, issues: list):
    """Mirrors the prototype's num() helper: blank string -> 0, else parse."""
    if raw == "" or raw is None:
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        issues.append(ValidationIssue(entity, identifier, f"{field_name}: non-numeric value {raw!r}"))
        return Decimal("0")


def parse_payload(payload: dict) -> ParseResult:
    result = ParseResult()
    issues = result.issues

    result.school_name = payload.get("school", "")
    result.class_label = payload.get("classLabel", "")
    result.academic_year_label = payload.get("year", "")
    result.subjects = payload.get("subjects", [])
    result.max_marks = payload.get("max", {})
    result.pass_marks = payload.get("pass", {})
    result.internal_max = payload.get("internalMax", {})
    result.internal_pass = payload.get("internalPass", 0)

    if not result.class_label:
        issues.append(ValidationIssue("ClassSection", "-", "classLabel is empty — cannot infer Class/Section"))
    if not result.academic_year_label:
        issues.append(ValidationIssue("AcademicYear", "-", "year is empty — cannot infer AcademicYear"))
    if not result.subjects:
        issues.append(ValidationIssue("Subject", "-", "subjects list is empty"))

    seen_rolls = set()
    for raw_student in payload.get("students", []):
        roll = raw_student.get("roll")
        name = (raw_student.get("name") or "").strip()
        identifier = f"roll={roll!r} name={name!r}"

        if roll is None:
            issues.append(ValidationIssue("Student", identifier, "missing roll number"))
        elif roll in seen_rolls:
            # The prototype has NO uniqueness enforcement (architecture doc §2/§17) —
            # this is exactly the kind of latent data-integrity problem this dry run
            # is meant to surface before anything is written to production.
            issues.append(ValidationIssue("Student", identifier, f"DUPLICATE roll number {roll} in source data"))
        else:
            seen_rolls.add(roll)

        if not name:
            issues.append(ValidationIssue("Student", identifier, "missing/blank name"))

        marks = {}
        for subject in result.subjects:
            subject_marks = (raw_student.get("marks") or {}).get(subject, {})
            parsed_subject_marks = {}
            for key in TEST_KEYS:
                parsed_subject_marks[key] = _to_decimal_or_blank(
                    subject_marks.get(key, ""), f"marks[{subject}][{key}]", "Student", identifier, issues
                )
            internal = subject_marks.get("internal", {})
            parsed_subject_marks["internal"] = {
                part: _to_decimal_or_blank(
                    internal.get(part, ""), f"marks[{subject}].internal.{part}", "Student", identifier, issues
                )
                for part in ("p1", "p2", "p3")
            }
            marks[subject] = parsed_subject_marks

        result.students.append(
            ParsedStudent(
                legacy_roll=roll,
                name=name,
                dob=raw_student.get("dob", ""),
                guardian_name=raw_student.get("guardian", ""),
                guardian_phone=raw_student.get("guardianPhone", ""),
                address=raw_student.get("address", ""),
                marks=marks,
            )
        )

    for raw_teacher in payload.get("teachers", []):
        identifier = f"id={raw_teacher.get('id')!r} name={raw_teacher.get('name')!r}"
        if not raw_teacher.get("name"):
            issues.append(ValidationIssue("Teacher", identifier, "missing/blank name"))
        result.teachers.append(
            ParsedTeacher(
                legacy_id=raw_teacher.get("id"),
                name=raw_teacher.get("name", ""),
                subject=raw_teacher.get("subject", ""),
                classes_raw=raw_teacher.get("classes", ""),
                phone=raw_teacher.get("phone", ""),
                email=raw_teacher.get("email", ""),
            )
        )

    for raw_book in payload.get("books", []):
        result.books.append(
            ParsedBook(
                legacy_id=raw_book.get("id"),
                title=raw_book.get("title", ""),
                author=raw_book.get("author", ""),
                category=raw_book.get("category", ""),
                copies=raw_book.get("copies", 0),
            )
        )

    result.attendance_dates = len(payload.get("attendanceByDate", {}))
    result.fee_records = len(payload.get("feeTotals", {})) + len(payload.get("feePayments", []))
    result.library_issues = len(payload.get("issues", []))

    return result


def print_report(result: ParseResult) -> None:
    print("=" * 70)
    print("Kathwada legacy data — DRY RUN parse report (no DB writes performed)")
    print("=" * 70)
    print(f"School:            {result.school_name!r}")
    print(f"Class label:       {result.class_label!r}  -> maps to a Class+Section pair")
    print(f"Academic year:     {result.academic_year_label!r}  -> maps to an AcademicYear row")
    print(f"Subjects ({len(result.subjects)}):    {', '.join(result.subjects)}")
    print(f"Max/pass marks:    {result.max_marks} / {result.pass_marks}")
    print(f"Internal max/pass: {result.internal_max} / pass={result.internal_pass}")
    print()
    print(f"Students:          {len(result.students)}")
    print(f"Teachers:          {len(result.teachers)}")
    print(f"Books:             {len(result.books)}")
    print(f"Attendance dates:  {result.attendance_dates}  (no cumulative % in source — see architecture doc §11)")
    print(f"Fee records:       {result.fee_records}  (flat total+payments, no fee heads — see §12)")
    print(f"Library issues:    {result.library_issues}")
    print()

    marks_entered = sum(
        1
        for s in result.students
        for subj in s.marks.values()
        for key in TEST_KEYS
        if subj[key] != 0
    )
    print(f"Non-zero mark entries found: {marks_entered} "
          f"({'none — this looks like empty/demo data' if marks_entered == 0 else 'real marks present'})")
    print()

    if result.issues:
        print(f"⚠ {len(result.issues)} VALIDATION ISSUE(S):")
        for issue in result.issues:
            print(f"  - [{issue.entity}] {issue.identifier}: {issue.message}")
    else:
        print("✓ No validation issues found.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", help="Path to a khs_erp_data_v1 JSON export")
    args = parser.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        payload = json.load(f)

    result = parse_payload(payload)
    print_report(result)

    sys.exit(1 if result.issues else 0)


if __name__ == "__main__":
    main()
