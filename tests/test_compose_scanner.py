"""
Tests for compose_a11y_scanner.scan_compose_a11y().

Each test uses a minimal Kotlin/Compose snippet and asserts which check IDs
are (or are not) raised, plus the expected severity and line number.
"""
import sys
import types
from pathlib import Path
import pytest

# Stub heavy dependencies (same pattern as test_pipeline_fixes.py)
for _mod in ("openai", "anthropic", "google", "google.genai",
             "aiohttp", "fastapi", "uvicorn", "dotenv"):
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compose_a11y_scanner import scan_compose_a11y


# ── helpers ───────────────────────────────────────────────────────────────────

COMPOSE_HEADER = (
    "package com.test\n"
    "import androidx.compose.runtime.Composable\n"
    "@Composable\n"
)


def issue_ids(code: str) -> set[str]:
    return {i.id for i in scan_compose_a11y(COMPOSE_HEADER + code)}


def issues_for(code: str, check_id: str):
    return [i for i in scan_compose_a11y(COMPOSE_HEADER + code) if i.id == check_id]


# ═══════════════════════════════════════════════════════════════════════════════
# Non-Compose file — scanner must be a no-op
# ═══════════════════════════════════════════════════════════════════════════════

def test_non_compose_file_produces_no_issues():
    plain = "package com.test\nclass Foo { fun bar() {} }"
    assert scan_compose_a11y(plain) == []


# ═══════════════════════════════════════════════════════════════════════════════
# Image — missing contentDescription
# ═══════════════════════════════════════════════════════════════════════════════

def test_image_without_contentdescription_raises_error():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x)) }'
    ids = issue_ids(code)
    assert "ComposeImageContentDescription" in ids


def test_image_with_contentdescription_string_no_issue():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x), contentDescription = "Profile") }'
    ids = issue_ids(code)
    assert "ComposeImageContentDescription" not in ids


def test_image_contentdescription_null_raises_warning():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x), contentDescription = null) }'
    issues = issues_for(code, "ComposeImageNullContentDescription")
    assert len(issues) == 1
    assert issues[0].severity == "Warning"


def test_image_contentdescription_null_no_error():
    # null is valid (decorative) — must NOT raise the Error variant
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x), contentDescription = null) }'
    ids = issue_ids(code)
    assert "ComposeImageContentDescription" not in ids


def test_image_multiline_without_contentdescription():
    code = (
        "fun Screen() {\n"
        "    Image(\n"
        "        painter = painterResource(R.drawable.photo),\n"
        "        modifier = Modifier.size(64.dp)\n"
        "    )\n"
        "}"
    )
    ids = issue_ids(code)
    assert "ComposeImageContentDescription" in ids


def test_image_multiline_with_contentdescription_no_issue():
    code = (
        "fun Screen() {\n"
        "    Image(\n"
        "        painter = painterResource(R.drawable.photo),\n"
        "        contentDescription = \"User avatar\",\n"
        "        modifier = Modifier.size(64.dp)\n"
        "    )\n"
        "}"
    )
    ids = issue_ids(code)
    assert "ComposeImageContentDescription" not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# Image — correct line number reported
# ═══════════════════════════════════════════════════════════════════════════════

def test_image_line_number_is_accurate():
    code = "fun Screen() {\n    val x = 1\n    Image(painter = painterResource(R.drawable.x))\n}"
    all_issues = scan_compose_a11y(COMPOSE_HEADER + code)
    img_issues = [i for i in all_issues if i.id == "ComposeImageContentDescription"]
    assert img_issues, "Expected at least one ComposeImageContentDescription issue"
    # COMPOSE_HEADER is 3 lines; the Image call is 3 lines into `code`
    # (line 1: "fun Screen() {", line 2: "    val x = 1", line 3: "    Image(...)")
    header_lines = COMPOSE_HEADER.count('\n')
    assert img_issues[0].line == header_lines + 3


# ═══════════════════════════════════════════════════════════════════════════════
# Icon — missing contentDescription
# ═══════════════════════════════════════════════════════════════════════════════

def test_icon_without_contentdescription_raises_error():
    code = 'fun Screen() { Icon(imageVector = Icons.Filled.Edit) }'
    ids = issue_ids(code)
    assert "ComposeIconContentDescription" in ids


def test_icon_with_string_contentdescription_no_issue():
    code = 'fun Screen() { Icon(imageVector = Icons.Filled.Edit, contentDescription = "Edit") }'
    ids = issue_ids(code)
    assert "ComposeIconContentDescription" not in ids


def test_icon_with_null_contentdescription_no_error():
    # null contentDescription on Icon is valid (decorative) — no Error
    code = 'fun Screen() { Icon(imageVector = Icons.Filled.Edit, contentDescription = null) }'
    ids = issue_ids(code)
    assert "ComposeIconContentDescription" not in ids


def test_icon_in_comment_not_flagged():
    code = '// Icon(imageVector = Icons.Filled.Edit)\nfun Screen() {}'
    ids = issue_ids(code)
    assert "ComposeIconContentDescription" not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# TextField / OutlinedTextField — missing label
# ═══════════════════════════════════════════════════════════════════════════════

def test_textfield_without_label_raises_warning():
    code = 'fun Screen() { TextField(value = "", onValueChange = {}) }'
    issues = issues_for(code, "ComposeTextFieldMissingLabel")
    assert len(issues) == 1
    assert issues[0].severity == "Warning"


def test_outlinedtextfield_without_label_raises_warning():
    code = 'fun Screen() { OutlinedTextField(value = "", onValueChange = {}) }'
    ids = issue_ids(code)
    assert "ComposeTextFieldMissingLabel" in ids


def test_textfield_with_label_no_issue():
    code = (
        'fun Screen() { TextField(value = "", onValueChange = {}, '
        'label = { Text("Name") }) }'
    )
    ids = issue_ids(code)
    assert "ComposeTextFieldMissingLabel" not in ids


def test_outlinedtextfield_with_placeholder_no_issue():
    # placeholder is an acceptable substitute for label
    code = (
        'fun Screen() { OutlinedTextField(value = "", onValueChange = {}, '
        'placeholder = { Text("Enter name") }) }'
    )
    ids = issue_ids(code)
    assert "ComposeTextFieldMissingLabel" not in ids


def test_multiple_textfields_each_flagged():
    code = (
        "fun Screen() {\n"
        "    TextField(value = name, onValueChange = { name = it })\n"
        "    TextField(value = email, onValueChange = { email = it })\n"
        "}"
    )
    all_issues = [i for i in scan_compose_a11y(COMPOSE_HEADER + code)
                  if i.id == "ComposeTextFieldMissingLabel"]
    assert len(all_issues) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# IconButton — child Icon with null contentDescription
# ═══════════════════════════════════════════════════════════════════════════════

def test_iconbutton_with_null_icon_raises_error():
    code = (
        "fun Screen() {\n"
        "    IconButton(onClick = {}) {\n"
        "        Icon(imageVector = Icons.Filled.Delete, contentDescription = null)\n"
        "    }\n"
        "}"
    )
    ids = issue_ids(code)
    assert "ComposeIconButtonMissingLabel" in ids


def test_iconbutton_with_labeled_icon_no_issue():
    code = (
        "fun Screen() {\n"
        "    IconButton(onClick = {}) {\n"
        "        Icon(imageVector = Icons.Filled.Delete, contentDescription = \"Delete item\")\n"
        "    }\n"
        "}"
    )
    ids = issue_ids(code)
    assert "ComposeIconButtonMissingLabel" not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# Deduplication — same line must not appear twice
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_duplicate_issues_same_line():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x)) }'
    all_issues = scan_compose_a11y(COMPOSE_HEADER + code)
    img = [i for i in all_issues if i.id == "ComposeImageContentDescription"]
    assert len(img) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# File name appears in issue.file with [compose-static] prefix
# ═══════════════════════════════════════════════════════════════════════════════

def test_issue_file_has_compose_static_prefix():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x)) }'
    all_issues = scan_compose_a11y(COMPOSE_HEADER + code)
    for issue in all_issues:
        assert "[compose-static]" in issue.file


def test_issue_is_a11y_true():
    code = 'fun Screen() { Image(painter = painterResource(R.drawable.x)) }'
    all_issues = scan_compose_a11y(COMPOSE_HEADER + code)
    for issue in all_issues:
        assert issue.is_a11y is True


# ═══════════════════════════════════════════════════════════════════════════════
# Real-world snippet: the Ollama-generated profile screen pattern
# ═══════════════════════════════════════════════════════════════════════════════

def test_real_profile_screen_snippet():
    """
    Reproduce the exact accessibility pattern that ATF caught (SpeakableTextPresentCheck)
    but lint missed: a profile image with contentDescription = null, plus an
    unlabelled text field.
    """
    code = (
        "@Composable\n"
        "fun ProfileScreen() {\n"
        "    Column {\n"
        "        Image(\n"
        "            painter = painterResource(R.drawable.profile),\n"
        "            contentDescription = null\n"
        "        )\n"
        "        OutlinedTextField(\n"
        "            value = name,\n"
        "            onValueChange = { name = it }\n"
        "        )\n"
        "    }\n"
        "}\n"
    )
    # Use raw code (already has @Composable)
    all_issues = scan_compose_a11y(code)
    ids = {i.id for i in all_issues}
    assert "ComposeImageNullContentDescription" in ids   # image flagged as warning
    assert "ComposeTextFieldMissingLabel" in ids          # field flagged as warning
    # No false error on the Image (null is valid, just a warning)
    assert "ComposeImageContentDescription" not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# ComposeSmallTouchTarget — declared size of clickable elements below 48dp
# ═══════════════════════════════════════════════════════════════════════════════

TT = "ComposeSmallTouchTarget"


def test_small_clickable_box_flagged():
    found = issues_for('fun S() { Box(modifier = Modifier.size(24.dp).clickable { }) { } }', TT)
    assert len(found) == 1 and "24×24dp" in found[0].message


def test_clickable_box_48dp_not_flagged():
    assert TT not in issue_ids('fun S() { Box(Modifier.size(48.dp).clickable { }) { } }')


def test_size_after_clickable_counts_inner_padding():
    # clickable wraps padding(12) + size(24): the clickable node is 48dp
    assert TT not in issue_ids('fun S() { Box(Modifier.clickable { }.padding(12.dp).size(24.dp)) { } }')
    assert TT in issue_ids('fun S() { Box(Modifier.clickable { }.padding(4.dp).size(24.dp)) { } }')


def test_outer_padding_shrinks_clickable():
    # size(48) then padding(12) outside the clickable: the clickable node is 24dp
    assert TT in issue_ids('fun S() { Box(Modifier.size(48.dp).padding(12.dp).clickable { }) { } }')


def test_outermost_size_wins():
    assert TT not in issue_ids('fun S() { Box(Modifier.size(56.dp).size(24.dp).clickable { }) { } }')


def test_short_height_on_full_width_row_flagged():
    found = issues_for('fun S() { Row(Modifier.fillMaxWidth().height(36.dp).clickable { }) { } }', TT)
    assert len(found) == 1 and "?×36dp" in found[0].message


def test_fill_and_min_height_not_flagged():
    assert TT not in issue_ids('fun S() { Row(Modifier.fillMaxWidth().heightIn(min = 48.dp).toggleable(value = a, onValueChange = { })) { } }')


def test_clickable_without_size_not_flagged():
    assert TT not in issue_ids('fun S() { Text("Hi", modifier = Modifier.clickable { }) }')


def test_non_literal_size_not_flagged():
    assert TT not in issue_ids('fun S() { Box(Modifier.size(iconSize).clickable { }) { } }')


def test_size_with_width_and_height():
    assert TT in issue_ids('fun S() { Box(Modifier.size(width = 120.dp, height = 32.dp).clickable { }) { } }')
    assert TT not in issue_ids('fun S() { Box(Modifier.size(120.dp, 48.dp).clickable { }) { } }')


def test_small_iconbutton_flagged_once():
    code = 'fun S() { IconButton(onClick = { }, modifier = Modifier.size(28.dp)) { Icon(Icons.Filled.Add, "Add") } }'
    found = issues_for(code, TT)
    assert len(found) == 1 and found[0].message.startswith("IconButton()")


def test_default_iconbutton_not_flagged():
    assert TT not in issue_ids('fun S() { IconButton(onClick = { }) { Icon(Icons.Filled.Add, "Add") } }')


def test_button_with_short_height_flagged():
    assert TT in issue_ids('fun S() { Button(onClick = { }, modifier = Modifier.fillMaxWidth().height(36.dp)) { Text("Go") } }')
    assert TT not in issue_ids('fun S() { Button(onClick = { }, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Go") } }')


def test_checkbox_with_null_callback_not_flagged():
    assert TT not in issue_ids('fun S() { Checkbox(checked = c, onCheckedChange = null, modifier = Modifier.size(20.dp)) }')
    assert TT in issue_ids('fun S() { Checkbox(checked = c, onCheckedChange = { }, modifier = Modifier.size(20.dp)) }')


def test_multiline_chain_with_semantics_lambda():
    code = '''fun S() {
        Box(
            modifier = Modifier
                .size(24.dp)
                .clickable { }
                .semantics { contentDescription = "Close" },
        ) { }
    }'''
    assert TT in issue_ids(code)


# ═══════════════════════════════════════════════════════════════════════════════
# Positional contentDescription (2nd argument of Icon/Image)
# ═══════════════════════════════════════════════════════════════════════════════

def test_icon_positional_null_is_null_not_missing():
    ids = issue_ids('fun S() { Icon(Icons.Filled.Delete, null) }')
    assert "ComposeIconNullContentDescription" in ids
    assert "ComposeIconContentDescription" not in ids


def test_icon_positional_string_no_issue():
    ids = issue_ids('fun S() { Icon(Icons.Filled.Delete, "Delete") }')
    assert not ids & {"ComposeIconNullContentDescription", "ComposeIconContentDescription"}


def test_icon_positional_vector_then_named_modifier_is_missing():
    assert "ComposeIconContentDescription" in issue_ids('fun S() { Icon(Icons.Filled.Delete, modifier = Modifier) }')


def test_iconbutton_with_positional_null_icon_raises_error():
    code = 'fun S() { IconButton(onClick = { }) { Icon(Icons.Filled.Delete, null) } }'
    assert "ComposeIconButtonMissingLabel" in issue_ids(code)


# ═══════════════════════════════════════════════════════════════════════════════
# v2.6 rules: headings, description wording, focus loss, disabled fields
# ═══════════════════════════════════════════════════════════════════════════════

HD, VD, FL, DF = ("ComposeMissingHeading", "ComposeVagueContentDescription",
                  "ComposeFocusLossOnToggle", "ComposeDisabledFieldWithValue")


def test_headline_text_without_heading_flagged():
    assert HD in issue_ids('fun S() { Text("Settings", style = MaterialTheme.typography.headlineSmall) }')
    assert HD in issue_ids('fun S() { Text(text = "Hi", style = MaterialTheme.typography.displayLarge) }')


def test_headline_text_with_heading_not_flagged():
    code = 'fun S() { Text("Settings", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.semantics { heading() }) }'
    assert HD not in issue_ids(code)


def test_body_and_title_text_not_flagged_as_heading():
    assert HD not in issue_ids('fun S() { Text("Hi", style = MaterialTheme.typography.bodyLarge) }')
    assert HD not in issue_ids('fun S() { Text("Hi", style = MaterialTheme.typography.titleMedium) }')


def test_description_with_role_word_flagged():
    assert VD in issue_ids('fun S() { Icon(imageVector = Icons.Filled.Email, contentDescription = "Email icon") }')
    assert VD in issue_ids('fun S() { Icon(Icons.Filled.Settings, "Settings button") }')
    assert VD in issue_ids('fun S() { Box(Modifier.semantics { contentDescription = "image" }) { } }')


def test_description_jargon_and_empty_flagged():
    assert VD in issue_ids('fun S() { Image(imageVector = Icons.Filled.Person, contentDescription = "Profile photo placeholder") }')
    assert VD in issue_ids('fun S() { Icon(imageVector = Icons.Filled.Person, contentDescription = "") }')


def test_meaningful_descriptions_not_flagged():
    for cd in ("Delete message", "Profile photo", "Show password", "Close banner", "Favorites"):
        assert VD not in issue_ids(f'fun S() {{ Icon(imageVector = Icons.Filled.Star, contentDescription = "{cd}") }}')


def test_role_word_inside_other_word_not_flagged():
    # "Imagery" and "Buttonhole" are not the words "image"/"button"
    assert VD not in issue_ids('fun S() { Icon(Icons.Filled.Star, "Imagery gallery") }')


def test_button_that_removes_itself_flagged():
    code = '''fun S() {
        if (isEditing) {
            Button(onClick = { isEditing = false }) { Text("Done") }
        } else {
            Button(onClick = { isEditing = true }) { Text("Edit") }
        }
    }'''
    assert FL in issue_ids(code)


def test_toggle_with_focus_requester_not_flagged():
    code = '''fun S() {
        if (isEditing) {
            Button(onClick = { isEditing = false }, modifier = Modifier.focusRequester(fr)) { Text("Done") }
        } else {
            Button(onClick = { isEditing = true }) { Text("Edit") }
        }
    }'''
    assert FL not in issue_ids(code)


def test_if_else_without_toggling_button_not_flagged():
    code = 'fun S() { if (on) { Text("On") } else { Button(onClick = { other = true }) { Text("Go") } } }'
    assert FL not in issue_ids(code)


def test_comparison_is_not_assignment():
    code = 'fun S() { if (on) { Button(onClick = { log(on == true) }) { Text("A") } } else { Text("B") } }'
    assert FL not in issue_ids(code)


def test_disabled_field_flagged_readonly_not():
    assert DF in issue_ids('fun S() { OutlinedTextField(value = v, onValueChange = { }, label = { Text("Name") }, enabled = editing) }')
    assert DF not in issue_ids('fun S() { OutlinedTextField(value = v, onValueChange = { }, label = { Text("Name") }, readOnly = !editing) }')
    assert DF not in issue_ids('fun S() { TextField(value = v, onValueChange = { }, label = { Text("Name") }, enabled = true) }')
