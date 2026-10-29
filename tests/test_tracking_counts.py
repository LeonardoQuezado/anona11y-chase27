"""Defect counting for the battery CSV: lint + static scanner overlap, decorative null icons."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tracking  # noqa: E402

CODE = '''@Composable
fun S() {
    IconButton(onClick = { }) {
        Icon(imageVector = Icons.Filled.Settings, contentDescription = null)
    }
    Row {
        Icon(Icons.Filled.Info, null)
        Text("Tips")
    }
    OutlinedTextField(
        value = v,
        onValueChange = { },
        label = { Text("Email") },
        leadingIcon = { Icon(Icons.Filled.Email, contentDescription = null) }
    )
}'''


def entry(lint, static, code=CODE):
    return {"status": "success", "generated_code": code,
            "accessibility_issues": {"total": len(lint), "issues": [{"id": i, "line": l} for i, l in lint]},
            "static_issues": {"total": len(static), "issues": [{"id": i, "line": l} for i, l in static]},
            "atf_issues": {"issues": []}}


def test_same_defect_from_lint_and_static_counts_once():
    e = entry([("ComposeIconNullContentDescription", 4)],
              [("ComposeIconNullContentDescription", 4), ("ComposeIconButtonMissingLabel", 3)])
    c = tracking.counts(e)
    assert c["total"] == 3 and c["code_unique"] == 1


def test_iconbutton_far_from_a_null_icon_is_its_own_defect():
    e = entry([], [("ComposeIconButtonMissingLabel", 3), ("ComposeIconNullContentDescription", 14)])
    assert tracking.counts(e)["code_unique"] == 2


def test_decorative_icons_next_to_text_or_in_a_slot():
    e = entry([("ComposeIconNullContentDescription", 4), ("ComposeIconNullContentDescription", 7),
               ("ComposeIconNullContentDescription", 14)], [])
    c = tracking.counts(e)
    # line 7 sits next to Text("Tips"), line 14 fills leadingIcon of a labelled field;
    # line 4 is alone inside an IconButton
    assert c["code_unique"] == 3 and c["null_decorative"] == 2


def test_beyond_wcag_kept_out_of_unique_defects():
    e = entry([], [("ComposeDisabledFieldWithValue", 10)])
    assert tracking.counts(e)["code_unique"] == 0
