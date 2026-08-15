import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from import_legacy_localstorage import parse_payload  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_parses_demo_fixture_with_no_issues():
    payload = json.loads((SAMPLE_DIR / "khs_erp_data_v1.demo.json").read_text())
    result = parse_payload(payload)

    assert len(result.students) == 3
    assert len(result.teachers) == 2
    assert len(result.books) == 2
    assert len(result.subjects) == 6
    assert result.issues == []


def test_detects_duplicate_roll_numbers():
    payload = json.loads((SAMPLE_DIR / "khs_erp_data_v1.demo.json").read_text())
    payload["students"][1]["roll"] = payload["students"][0]["roll"]

    result = parse_payload(payload)

    assert any("DUPLICATE roll number" in issue.message for issue in result.issues)


def test_detects_non_numeric_marks():
    payload = json.loads((SAMPLE_DIR / "khs_erp_data_v1.demo.json").read_text())
    payload["students"][0]["marks"]["Mathematics"]["fst"] = "abc"

    result = parse_payload(payload)

    assert any("non-numeric value" in issue.message for issue in result.issues)


def test_detects_missing_student_name_and_roll():
    payload = json.loads((SAMPLE_DIR / "khs_erp_data_v1.demo.json").read_text())
    payload["students"].append(
        {"roll": None, "name": "", "marks": {}, "cls": "", "dob": "", "guardian": "", "guardianPhone": "", "address": ""}
    )

    result = parse_payload(payload)

    messages = [i.message for i in result.issues]
    assert any("missing roll number" in m for m in messages)
    assert any("missing/blank name" in m for m in messages)


def test_blank_marks_parse_as_zero_matching_prototype_num_helper():
    payload = json.loads((SAMPLE_DIR / "khs_erp_data_v1.demo.json").read_text())
    result = parse_payload(payload)

    first_student = result.students[0]
    for subject_marks in first_student.marks.values():
        assert subject_marks["fst"] == 0
        assert subject_marks["internal"]["p1"] == 0
