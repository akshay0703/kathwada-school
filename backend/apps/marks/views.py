from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasModulePermission
from apps.exams.models import Exam, ExamSubject
from apps.marks.models import Mark
from apps.marks.serializers import BulkMarkSaveSerializer, MarkSerializer
from apps.people.models import Student

STANDARD_ACTION_MAP = {
    "list": "view",
    "retrieve": "view",
    "create": "create",
    "update": "edit",
    "partial_update": "edit",
    "destroy": "delete",
}


class MarkViewSet(viewsets.ModelViewSet):
    """
    /api/v1/marks/ — permissions per the "Marks Entry" matrix row: Admin
    VCEDX, Principal VE (no Create), Teacher VCE (own assigned
    subjects/classes only), Staff none at all, Student V (own), Parent V
    (own child).

    Row-level scoping implemented now, same mechanism/pattern as
    Attendance:
    - Teacher: queryset filtered to ClassSections they're assigned to via
      TeacherAssignment (docs/permissions.md names Marks explicitly for
      this exact scoping rule).
    - Student: sees only their own marks (via `student.user`).
    - Admin/Principal/superuser: full queryset. Staff: no RolePermission
      rows on this module at all, so they 403 before reaching get_queryset.

    Deliberately NOT yet implemented (documented, not silently skipped):
    - Parent "V (own child)" needs `StudentGuardian`, which doesn't exist
      yet — Parents get an empty queryset rather than an error.
    - No draft->publish gate: checked directly against
      apps/accounts/management/commands/seed_permissions.py, the "marks"
      module row has no PUBLISH action at all (only report_cards/
      website_cms do), so Student/Parent's View is unconditional once
      scoped to their own record.
    """

    queryset = Mark.objects.select_related(
        "student", "exam_subject__exam", "exam_subject__subject", "exam_subject__class_section", "entered_by"
    ).all()
    serializer_class = MarkSerializer
    permission_classes = [HasModulePermission]
    module_key = "marks"
    permission_action_map = {**STANDARD_ACTION_MAP, "bulk_save": "create", "marksheet": "view", "class_marksheet": "view"}

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if not user.is_superuser:
            role_name = user.role.name if user.role else None
            if role_name in ("Admin", "Principal"):
                pass
            elif role_name == "Teacher":
                qs = qs.filter(exam_subject__class_section__in=_teacher_class_section_ids(user))
            elif role_name == "Student":
                qs = qs.filter(student__user=user)
            else:
                # Staff (no rows on this module) / Parent (StudentGuardian
                # doesn't exist yet): deny by default.
                return qs.none()

        exam_subject_id = self.request.query_params.get("exam_subject")
        if exam_subject_id:
            qs = qs.filter(exam_subject_id=exam_subject_id)
        exam_id = self.request.query_params.get("exam")
        if exam_id:
            qs = qs.filter(exam_subject__exam_id=exam_id)
        student_id = self.request.query_params.get("student")
        if student_id:
            qs = qs.filter(student_id=student_id)
        return qs

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["post"], url_path="bulk-save")
    def bulk_save(self, request):
        """
        POST /api/v1/marks/bulk-save/
        body: {"exam_subject": <id>, "records": [{"student": <id>,
               "marks_obtained": 78}, ...]}

        Saves (or corrects) marks for a whole class-section/subject/exam
        combination in one request — every student listed must be actively
        enrolled in that exam_subject's class-section, and no mark may
        exceed that exam_subject's max_marks. Existing marks are updated in
        place, so re-submitting a corrected sheet works the same way
        editing a single mark does.
        """
        if not self.request.user.is_superuser:
            role_name = self.request.user.role.name if self.request.user.role else None
            if role_name == "Teacher":
                exam_subject_id = request.data.get("exam_subject")
                exam_subject_class_section_id = _class_section_id_for_exam_subject(exam_subject_id)
                if exam_subject_class_section_id is not None and exam_subject_class_section_id not in _teacher_class_section_ids(
                    self.request.user
                ):
                    return Response(
                        {"exam_subject": ["You are not assigned to this class-section."]},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        serializer = BulkMarkSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        records = serializer.save(entered_by=request.user)
        return Response(MarkSerializer(records, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="marksheet")
    def marksheet(self, request):
        """
        GET /api/v1/marks/marksheet/?student=<id>&exam=<id>

        Computed on the fly from existing Exam/ExamSubject/Mark/Enrollment
        data — nothing here is persisted or duplicated. Aggregates every
        ExamSubject configured for the student's class-section (for that
        exam's academic year) against that student's Mark rows, and
        totals/percentages/pass-fail across them. See _build_marksheet for
        the calculation itself and its documented pass/fail rule.
        """
        student_id = request.query_params.get("student")
        exam_id = request.query_params.get("exam")
        if not student_id or not exam_id:
            return Response({"detail": "Both 'student' and 'exam' query params are required."}, status=status.HTTP_400_BAD_REQUEST)

        student = _get_or_404(Student, student_id, "student")
        if isinstance(student, Response):
            return student
        exam = _get_or_404(Exam, exam_id, "exam")
        if isinstance(exam, Response):
            return exam

        denial = _check_marksheet_access(request.user, student)
        if denial is not None:
            return denial

        result = _build_marksheet(student, exam)
        if result is None:
            return Response(
                {"detail": f"{student.full_name} has no active enrollment for {exam.academic_year.label}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(result)

    @action(detail=False, methods=["get"], url_path="class-marksheet")
    def class_marksheet(self, request):
        """
        GET /api/v1/marks/class-marksheet/?class_section=<id>&exam=<id>

        Same computation as `marksheet`, run for every actively enrolled
        student in the class-section — a class-wide summary view (totals/
        percentage/result per student, no subject-level breakdown) for
        Admin/Principal/an assigned Teacher to review at a glance.
        """
        from apps.academics.models import ClassSection

        class_section_id = request.query_params.get("class_section")
        exam_id = request.query_params.get("exam")
        if not class_section_id or not exam_id:
            return Response(
                {"detail": "Both 'class_section' and 'exam' query params are required."}, status=status.HTTP_400_BAD_REQUEST
            )

        class_section = _get_or_404(ClassSection, class_section_id, "class_section")
        if isinstance(class_section, Response):
            return class_section
        exam = _get_or_404(Exam, exam_id, "exam")
        if isinstance(exam, Response):
            return exam

        if not request.user.is_superuser:
            role_name = request.user.role.name if request.user.role else None
            if role_name in ("Admin", "Principal"):
                pass
            elif role_name == "Teacher":
                if class_section.id not in _teacher_class_section_ids(request.user):
                    return Response({"class_section": ["You are not assigned to this class-section."]}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"detail": "You do not have permission to view this."}, status=status.HTTP_403_FORBIDDEN)

        students = Student.objects.filter(
            enrollments__class_section=class_section, enrollments__status="active"
        ).distinct()
        summaries = []
        for student in students:
            result = _build_marksheet(student, exam)
            if result is not None:
                summaries.append(
                    {
                        "student": result["student"],
                        "total_obtained": result["total_obtained"],
                        "total_max": result["total_max"],
                        "percentage": result["percentage"],
                        "all_marks_entered": result["all_marks_entered"],
                        "overall_result": result["overall_result"],
                    }
                )
        return Response(summaries)


def _teacher_class_section_ids(user):
    from apps.people.models import Teacher

    return set(
        Teacher.objects.filter(user=user).values_list(
            "assignments__class_section_subject__class_section_id", flat=True
        )
    )


def _class_section_id_for_exam_subject(exam_subject_id):
    from apps.exams.models import ExamSubject

    if not exam_subject_id:
        return None
    return ExamSubject.objects.filter(pk=exam_subject_id).values_list("class_section_id", flat=True).first()


def _get_or_404(model, pk, field_name):
    try:
        return model.objects.get(pk=pk)
    except (model.DoesNotExist, ValueError, TypeError):
        return Response({field_name: [f"{model.__name__} not found."]}, status=status.HTTP_404_NOT_FOUND)


def _check_marksheet_access(user, student):
    """Returns a Response if access should be denied, or None if allowed."""
    if user.is_superuser:
        return None
    role_name = user.role.name if user.role else None
    if role_name in ("Admin", "Principal"):
        return None
    if role_name == "Teacher":
        student_class_section_ids = set(student.enrollments.filter(status="active").values_list("class_section_id", flat=True))
        if student_class_section_ids & _teacher_class_section_ids(user):
            return None
        return Response({"student": ["You are not assigned to this student's class-section."]}, status=status.HTTP_403_FORBIDDEN)
    if role_name == "Student":
        if student.user_id == user.id:
            return None
        return Response({"detail": "You do not have permission to view this."}, status=status.HTTP_403_FORBIDDEN)
    # Staff (no rows on the "marks" module at all) / Parent (StudentGuardian
    # doesn't exist yet): deny by default.
    return Response({"detail": "You do not have permission to view this."}, status=status.HTTP_403_FORBIDDEN)


def _build_marksheet(student, exam):
    """
    Computes a student's marksheet for one exam entirely from existing
    Enrollment/ExamSubject/Mark data — nothing is persisted.

    Pass/fail rule (deliberately simple, per instruction "do not build
    complex grading unless existing docs require it" — no ranking, no
    grade letters, no compensatory formulas):
    - A subject is "failed" only if its ExamSubject has `passing_marks` set
      AND the student's marks_obtained for it is below that threshold.
    - `overall_result` is "fail" if any configured subject was failed, is
      "pass" if every subject that has a passing_marks configured was
      passed AND every subject has a mark entered, and is None (not yet
      determinable) otherwise — e.g. no subject on this exam has a
      passing_marks configured at all, or marks are still incomplete with
      no failure detected yet.
    """
    enrollment = student.enrollments.filter(status="active", class_section__academic_year=exam.academic_year).first()
    if enrollment is None:
        return None
    class_section = enrollment.class_section

    exam_subjects = ExamSubject.objects.filter(exam=exam, class_section=class_section).select_related("subject")
    marks_by_exam_subject = {
        m.exam_subject_id: m for m in Mark.objects.filter(student=student, exam_subject__in=exam_subjects)
    }

    subject_rows = []
    total_obtained = Decimal("0")
    total_max = Decimal("0")
    all_marks_entered = True
    has_passing_rule = False
    any_failed = False

    for exam_subject in exam_subjects:
        mark = marks_by_exam_subject.get(exam_subject.id)
        marks_obtained = mark.marks_obtained if mark else None
        passed = None
        if exam_subject.passing_marks is not None:
            has_passing_rule = True
            if marks_obtained is not None:
                passed = marks_obtained >= exam_subject.passing_marks
                if not passed:
                    any_failed = True

        total_max += exam_subject.max_marks
        if marks_obtained is not None:
            total_obtained += marks_obtained
        else:
            all_marks_entered = False

        subject_rows.append(
            {
                "exam_subject": exam_subject.id,
                "subject_name": exam_subject.subject.name,
                "subject_code": exam_subject.subject.code,
                "max_marks": exam_subject.max_marks,
                "passing_marks": exam_subject.passing_marks,
                "marks_obtained": marks_obtained,
                "passed": passed,
            }
        )

    percentage = round(float(total_obtained) / float(total_max) * 100, 2) if total_max > 0 else None

    if any_failed:
        overall_result = "fail"
    elif has_passing_rule and all_marks_entered:
        overall_result = "pass"
    else:
        overall_result = None

    return {
        "student": {"id": student.id, "full_name": student.full_name, "admission_no": student.admission_no},
        "exam": {"id": exam.id, "code": exam.code, "name": exam.name},
        "academic_year_label": exam.academic_year.label,
        "class_section_label": f"{class_section.school_class.name}-{class_section.section.name}",
        "roll_no": enrollment.roll_no,
        "subjects": subject_rows,
        "total_obtained": total_obtained,
        "total_max": total_max,
        "percentage": percentage,
        "all_marks_entered": all_marks_entered,
        "overall_result": overall_result,
    }
