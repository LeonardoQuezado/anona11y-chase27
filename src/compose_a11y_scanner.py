"""
Compose-specific accessibility static analysis.

Scans post-fixer Kotlin/Compose source for patterns that cause accessibility
failures.  Returns LintIssue objects so findings integrate with the existing
report infrastructure (same severity labels, same a11y issue tables).

Checks implemented (high-precision, low false-positive):

  ComposeImageContentDescription    Image() missing contentDescription param
  ComposeImageNullContentDescription Image() has contentDescription = null
  ComposeIconContentDescription     Icon() missing contentDescription param
  ComposeIconNullContentDescription  Icon() has contentDescription = null
  ComposeTextFieldMissingLabel      TextField / OutlinedTextField without label or label=null
  ComposeIconButtonMissingLabel     IconButton whose child Icon has null description
  ComposeSmallTouchTarget           Clickable element or interactive component whose
                                    declared size is below 48dp. Compose may enlarge the
                                    touch area at runtime (so ATF measures 48dp), but the
                                    visible target stays small, so it is counted here.
  ComposeMissingHeading             Text styled as a heading (display*/headline*) without
                                    semantics { heading() } — WCAG 1.3.1
  ComposeVagueContentDescription    contentDescription that is empty, developer jargon
                                    ("placeholder") or names the element type ("icon",
                                    "button"…) — WCAG 1.1.1 / Android guidance
  ComposeFocusLossOnToggle          if/else whose button flips the condition and so removes
                                    itself: focus is lost and the change is not announced
                                    — WCAG 2.4.3 / 4.1.3
  ComposeDisabledFieldWithValue     TextField disabled by a state to show data (use readOnly)
                                    — beyond WCAG (disabled controls are exempt from 1.4.3),
                                    so it is counted apart from the total
"""
import re
from report_generator import LintIssue


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_line_comments(code: str) -> str:
    """Replace // comments with spaces, preserving character positions."""
    return re.sub(r'//[^\n]*', lambda m: ' ' * len(m.group()), code)


def _line_of(code: str, pos: int) -> int:
    return code[:pos].count('\n') + 1


def _extract_call_block(code: str, open_paren: int) -> str | None:
    """
    Return the text between the matching '()' starting at open_paren (exclusive).
    Handles nested parens, double-quoted strings, and triple-quoted strings.
    Returns None if the parens are unbalanced (e.g. truncated code).
    """
    if open_paren >= len(code) or code[open_paren] != '(':
        return None

    depth = 0
    i = open_paren
    n = len(code)

    while i < n:
        # Triple-quoted string — skip entire content
        if code[i:i+3] == '"""':
            i += 3
            while i < n and code[i:i+3] != '"""':
                i += 1
            i += 3
            continue

        ch = code[i]

        # Double-quoted string — skip content (handle escape sequences)
        if ch == '"':
            i += 1
            while i < n and code[i] != '"':
                if code[i] == '\\':
                    i += 1  # skip escaped char
                i += 1
            i += 1
            continue

        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return code[open_paren + 1:i]

        i += 1

    return None  # unbalanced


def _has_param(args: str, param: str) -> bool:
    """True if named parameter `param =` appears in the args string."""
    return bool(re.search(rf'\b{re.escape(param)}\s*=', args))


def _param_is_null(args: str, param: str) -> bool:
    """True if `param = null` appears in the args string."""
    return bool(re.search(rf'\b{re.escape(param)}\s*=\s*null\b', args))


def _content_description(args: str) -> str | None:
    """
    The contentDescription argument of an Icon()/Image() call, named or positional
    (2nd argument in every overload), or None when it is not passed.
    """
    parts = _split_args(args)
    for part in parts:
        m = re.match(r'contentDescription\s*=\s*(.+)$', part, re.S)
        if m:
            return m.group(1).strip()
    if len(parts) >= 2 and not re.match(r'\w+\s*=(?!=)', parts[1]):
        return parts[1]
    return None


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_content_description(
    scan_code: str,
    original_code: str,
    component: str,
    filename: str,
    issues: list[LintIssue],
) -> None:
    """Check Image() and Icon() for missing or null contentDescription."""
    for m in re.finditer(rf'\b{re.escape(component)}\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        line = _line_of(original_code, m.start())
        cd = _content_description(args)

        if cd is None:
            issues.append(LintIssue(
                id=f"Compose{component}ContentDescription",
                severity="Error",
                message=(
                    f"{component}() is missing a contentDescription — "
                    "screen readers cannot describe this element. "
                    "Pass null only for purely decorative images."
                ),
                file=f"[compose-static] {filename}",
                line=line,
                is_a11y=True,
            ))
        elif cd == "null":
            if component == "Image":
                # null is semantically valid (decorative) but worth flagging for review
                issues.append(LintIssue(
                    id="ComposeImageNullContentDescription",
                    severity="Warning",
                    message=(
                        "Image() has contentDescription = null — "
                        "ensure this image is purely decorative and conveys no information."
                    ),
                    file=f"[compose-static] {filename}",
                    line=line,
                    is_a11y=True,
                ))
            else:
                # Icon(contentDescription = null) silences screen readers when the
                # icon is inside a clickable element — it should have a description.
                issues.append(LintIssue(
                    id="ComposeIconNullContentDescription",
                    severity="Warning",
                    message=(
                        "Icon() has contentDescription = null — "
                        "if this icon is inside a clickable element, screen readers "
                        "cannot announce its purpose. Use a descriptive string instead."
                    ),
                    file=f"[compose-static] {filename}",
                    line=line,
                    is_a11y=True,
                ))


def _check_textfield_label(
    scan_code: str,
    original_code: str,
    component: str,
    filename: str,
    issues: list[LintIssue],
) -> None:
    """Check TextField / OutlinedTextField for a missing label parameter."""
    for m in re.finditer(rf'\b{re.escape(component)}\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        line = _line_of(original_code, m.start())

        if (not _has_param(args, "label") and not _has_param(args, "placeholder")) \
                or _param_is_null(args, "label"):
            issues.append(LintIssue(
                id="ComposeTextFieldMissingLabel",
                severity="Warning",
                message=(
                    f"{component}() has no label parameter — "
                    "assistive technology cannot identify this input field."
                ),
                file=f"[compose-static] {filename}",
                line=line,
                is_a11y=True,
            ))


def _check_iconbutton_label(
    scan_code: str,
    original_code: str,
    filename: str,
    issues: list[LintIssue],
) -> None:
    """
    Check IconButton whose inner Icon has contentDescription = null.
    An icon-only button must have a description so screen readers can announce it.
    """
    for m in re.finditer(r'\bIconButton\s*\(', scan_code):
        call_args = _extract_call_block(scan_code, m.end() - 1)
        if call_args is None:
            continue

        # Find the trailing lambda { ... } that follows the IconButton(...) call
        after = m.end() - 1 + 1 + len(call_args) + 1  # position after ')'
        # Skip whitespace
        j = after
        while j < len(scan_code) and scan_code[j] in ' \t\n':
            j += 1
        if j >= len(scan_code) or scan_code[j] != '{':
            continue

        # Find matching closing brace for the lambda
        depth = 0
        k = j
        while k < len(scan_code):
            if scan_code[k] == '{':
                depth += 1
            elif scan_code[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        lambda_body = scan_code[j+1:k]

        # Heuristic: if the lambda contains Icon(contentDescription = null) the
        # button itself has no accessible label.
        if re.search(r'\bIcon\s*\(', lambda_body):
            icon_m = re.search(r'\bIcon\s*\(', lambda_body)
            if icon_m:
                icon_args = _extract_call_block(lambda_body, icon_m.end() - 1)
                if icon_args is not None and _content_description(icon_args) == "null":
                    issues.append(LintIssue(
                        id="ComposeIconButtonMissingLabel",
                        severity="Error",
                        message=(
                            "IconButton contains Icon(contentDescription = null) with no "
                            "other accessible label — screen readers cannot announce this button."
                        ),
                        file=f"[compose-static] {filename}",
                        line=_line_of(original_code, m.start()),
                        is_a11y=True,
                    ))


# ── Touch target size ─────────────────────────────────────────────────────────

_MIN_TOUCH_DP = 48.0
_BIG = float("inf")   # a dimension set by fillMax*/weight/…In(min): not a small target

# Modifiers that make the node they are applied to clickable
_CLICK_MODIFIERS = {"clickable", "combinedClickable", "toggleable", "triStateToggleable", "selectable"}
# Material components that are clickable as a whole; their `modifier` sets their size
_INTERACTIVE_COMPONENTS = (
    "IconButton", "IconToggleButton", "FilledIconButton", "FilledTonalIconButton", "OutlinedIconButton",
    "FilledIconToggleButton", "FilledTonalIconToggleButton", "OutlinedIconToggleButton",
    "Button", "TextButton", "OutlinedButton", "ElevatedButton", "FilledTonalButton",
    "FloatingActionButton", "SmallFloatingActionButton",
    "Checkbox", "TriStateCheckbox", "RadioButton", "Switch",
)
_FIXED_SIZE = {"size", "requiredSize", "width", "requiredWidth", "height", "requiredHeight"}
# Modifiers that size a dimension to the parent or to a minimum — never a small fixed target
_FLEX_W = {"fillMaxWidth", "fillMaxSize", "widthIn", "sizeIn", "requiredWidthIn", "requiredSizeIn", "defaultMinSize"}
_FLEX_H = {"fillMaxHeight", "fillMaxSize", "heightIn", "sizeIn", "requiredHeightIn", "requiredSizeIn", "defaultMinSize"}


def _split_args(args: str) -> list[str]:
    """Split a call's argument text at top-level commas."""
    parts, depth, cur = [], 0, ""
    for ch in args:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [x.strip() for x in parts]


def _dp(expr: str) -> float | None:
    m = re.fullmatch(r'(\d+(?:\.\d+)?)\s*\.\s*dp', expr.strip())
    return float(m.group(1)) if m else None


def _named(parts: list[str]) -> dict[str, str]:
    out = {}
    for x in parts:
        m = re.match(r'(\w+)\s*=\s*(.+)$', x, re.S)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _fixed_size(name: str, args: str) -> tuple[float | None, float | None]:
    """(width, height) in dp set by size/width/height(...); None where not set or not a literal."""
    parts = _split_args(args)
    named = _named(parts)
    if name in ("size", "requiredSize"):
        if named:
            return _dp(named.get("width", "")), _dp(named.get("height", ""))
        if len(parts) == 1:
            v = _dp(parts[0])
            return v, v
        if len(parts) == 2:
            return _dp(parts[0]), _dp(parts[1])
        return None, None
    v = _dp(named.get(name.replace("required", "").lower(), parts[0] if parts else ""))
    return (v, None) if "idth" in name else (None, v)


def _padding(args: str) -> tuple[float, float] | None:
    """Total (horizontal, vertical) padding in dp, or None when it is not made of dp literals."""
    parts = _split_args(args)
    named = _named(parts)
    def val(e: str) -> float | None:
        return 0.0 if e is None else _dp(e)
    if named:
        if "all" in named:
            v = val(named["all"])
            return None if v is None else (2 * v, 2 * v)
        h = val(named.get("horizontal")); v = val(named.get("vertical"))
        st = val(named.get("start")); en = val(named.get("end"))
        to = val(named.get("top")); bo = val(named.get("bottom"))
        if None in (h, v, st, en, to, bo):
            return None
        return 2 * h + st + en, 2 * v + to + bo
    vals = [_dp(x) for x in parts]
    if None in vals:
        return None
    if len(vals) == 1:
        return 2 * vals[0], 2 * vals[0]
    if len(vals) == 2:
        return 2 * vals[0], 2 * vals[1]
    if len(vals) == 4:
        return vals[0] + vals[2], vals[1] + vals[3]
    return None


def _skip_ws(code: str, i: int) -> int:
    while i < len(code) and code[i] in " \t\r\n":
        i += 1
    return i


def _skip_braces(code: str, i: int) -> int | None:
    """Index just after the {...} block that opens at i."""
    depth = 0
    for k in range(i, len(code)):
        if code[k] == "{":
            depth += 1
        elif code[k] == "}":
            depth -= 1
            if depth == 0:
                return k + 1
    return None


def _modifier_chain(code: str, i: int) -> list[tuple[str, str]]:
    """Parse `.name(args) { lambda }` links starting at i (just after `Modifier`), outermost first."""
    ops: list[tuple[str, str]] = []
    while True:
        j = _skip_ws(code, i)
        if j >= len(code) or code[j] != ".":
            return ops
        m = re.match(r'\.\s*(\w+)', code[j:])
        if not m:
            return ops
        name, j = m.group(1), j + m.end()
        args = ""
        k = _skip_ws(code, j)
        if k < len(code) and code[k] == "(":
            args = _extract_call_block(code, k)
            if args is None:
                return ops
            j = k + len(args) + 2
            k = _skip_ws(code, j)
        if k < len(code) and code[k] == "{":
            end = _skip_braces(code, k)
            if end is None:
                return ops
            j = end
        ops.append((name, args))
        i = j


def _dimension(ops: list[tuple[str, str]], axis: int) -> float | None:
    """
    Size along one axis (0 = width, 1 = height) of the node at the end of `ops` (outermost first).
    The outermost fixed size wins and the padding applied inside it shrinks the node;
    fillMax*/weight/…In(min) make it a non-small dimension. None when it cannot be told.
    """
    flex = _FLEX_W if axis == 0 else _FLEX_H
    dim, pad = None, 0.0
    for name, args in ops:
        if name == "padding" and dim is not None:
            p = _padding(args)
            if p is None:
                return None
            pad += p[axis]
        elif name in _FIXED_SIZE and dim is None:
            v = _fixed_size(name, args)[axis]
            if v is not None:
                dim = v
        elif (name in flex or name == "weight") and dim is None:
            return _BIG
    return None if dim is None else dim - pad


def _content_dimension(ops: list[tuple[str, str]], axis: int) -> float | None:
    """Size along one axis of a node with no outer size: the first inner fixed size plus the padding before it."""
    flex = _FLEX_W if axis == 0 else _FLEX_H
    pad = 0.0
    for name, args in ops:
        if name == "padding":
            p = _padding(args)
            if p is None:
                return None
            pad += p[axis]
        elif name in _FIXED_SIZE:
            v = _fixed_size(name, args)[axis]
            if v is not None:
                return v + pad
        elif name in flex or name == "weight":
            return _BIG
    return None


def _small(w: float | None, h: float | None) -> bool:
    return any(d is not None and d < _MIN_TOUCH_DP - 0.5 for d in (w, h))


def _fmt(d: float | None) -> str:
    return "?" if d is None or d == _BIG else f"{d:g}"


def _touch_issue(what: str, w: float | None, h: float | None, filename: str, line: int) -> LintIssue:
    return LintIssue(
        id="ComposeSmallTouchTarget",
        severity="Error",
        message=(
            f"{what} is {_fmt(w)}×{_fmt(h)}dp — below the 48×48dp minimum touch target. "
            "Compose may enlarge the touch area at runtime, but the visible target stays small. "
            "Use Modifier.size(48.dp) or Modifier.sizeIn(minWidth = 48.dp, minHeight = 48.dp)."
        ),
        file=f"[compose-static] {filename}",
        line=line,
        is_a11y=True,
    )


def _check_touch_target(
    scan_code: str,
    original_code: str,
    filename: str,
    issues: list[LintIssue],
) -> None:
    """Flag clickable modifiers and interactive components with a declared size below 48dp."""
    seen_chains: set[int] = set()

    # 1. Interactive components: their whole modifier chain sizes the clickable element
    names = "|".join(_INTERACTIVE_COMPONENTS)
    for m in re.finditer(rf'\b({names})\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        # a Checkbox/Switch/RadioButton with a null callback is not clickable (its row is)
        if re.search(r'\b(onClick|onCheckedChange)\s*=\s*null\b', args):
            continue
        mm = re.search(r'\bmodifier\s*=\s*([Mm]odifier)\b', args)
        if not mm:
            continue
        chain_at = m.end() + mm.end(1)          # position just after `Modifier` in scan_code
        seen_chains.add(chain_at)
        ops = _modifier_chain(scan_code, chain_at)
        w, h = _dimension(ops, 0), _dimension(ops, 1)
        if _small(w, h):
            issues.append(_touch_issue(f"{m.group(1)}()", w, h, filename, _line_of(original_code, m.start())))

    # 2. Clickable modifiers on any composable
    for m in re.finditer(r'(?<![\w.])([Mm]odifier)\b', scan_code):
        if m.end() in seen_chains:
            continue
        ops = _modifier_chain(scan_code, m.end())
        for idx, (name, _) in enumerate(ops):
            if name not in _CLICK_MODIFIERS:
                continue
            before, after = ops[:idx], ops[idx + 1:]
            w = _dimension(before, 0)
            h = _dimension(before, 1)
            w = _content_dimension(after, 0) if w is None else w
            h = _content_dimension(after, 1) if h is None else h
            if _small(w, h):
                issues.append(_touch_issue(f"Element with Modifier.{name}", w, h, filename,
                                           _line_of(original_code, m.start())))
            break


# ── Headings ──────────────────────────────────────────────────────────────────

def _check_heading(scan_code: str, original_code: str, filename: str, issues: list[LintIssue]) -> None:
    """Text() with a display/headline typography style and no heading semantics."""
    for m in re.finditer(r'\bText\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        style = re.search(r'\bstyle\s*=\s*MaterialTheme\.typography\.((?:display|headline)(?:Large|Medium|Small))', args)
        if not style or re.search(r'\bheading\s*\(\s*\)', args):
            continue
        issues.append(LintIssue(
            id="ComposeMissingHeading",
            severity="Warning",
            message=(
                f"Text() styled as {style.group(1)} has no heading semantics — screen reader users "
                "cannot jump between sections. Add Modifier.semantics { heading() }."
            ),
            file=f"[compose-static] {filename}",
            line=_line_of(original_code, m.start()),
            is_a11y=True,
        ))


# ── Content description wording ───────────────────────────────────────────────

# Element types the screen reader already announces, and developer jargon
_ROLE_WORDS = r'icon|image|img|picture|button|btn|graphic|imageview|vector|placeholder|clickable'


def _vague_description(text: str) -> str | None:
    """Why a contentDescription literal is unhelpful, or None when it is fine."""
    t = text.strip()
    if not t:
        return "is empty (use null for a decorative element)"
    word = re.search(rf'\b({_ROLE_WORDS})s?\b', t, re.IGNORECASE)
    if word:
        w = word.group(1).lower()
        if w == "placeholder":
            return f'"{t}" uses developer jargon ("placeholder")'
        return f'"{t}" names the element type ("{w}"), which the screen reader already announces'
    return None


def _check_description_wording(scan_code: str, original_code: str, filename: str, issues: list[LintIssue]) -> None:
    """contentDescription string literals (named, positional in Icon/Image, or semantics) that say little."""
    found: list[tuple[int, str]] = []
    for m in re.finditer(r'\bcontentDescription\s*=\s*"((?:[^"\\]|\\.)*)"', scan_code):
        found.append((m.start(), m.group(1)))
    for m in re.finditer(r'\b(Icon|Image)\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        cd = _content_description(args)
        if cd and re.fullmatch(r'"(?:[^"\\]|\\.)*"', cd) and not re.search(r'\bcontentDescription\s*=', args):
            found.append((m.start(), cd[1:-1]))
    for pos, text in found:
        why = _vague_description(text)
        if why:
            issues.append(LintIssue(
                id="ComposeVagueContentDescription",
                severity="Warning",
                message=f"contentDescription {why}. Describe the purpose, e.g. \"Delete message\".",
                file=f"[compose-static] {filename}",
                line=_line_of(original_code, pos),
                is_a11y=True,
            ))


# ── Focus loss on toggled content ─────────────────────────────────────────────

def _block_after(code: str, i: int) -> tuple[str, int] | None:
    """(body, end) of the {...} block that starts at the first '{' at or after i (whitespace only)."""
    j = _skip_ws(code, i)
    if j >= len(code) or code[j] != "{":
        return None
    end = _skip_braces(code, j)
    return (code[j + 1:end - 1], end) if end else None


def _check_focus_loss(scan_code: str, original_code: str, filename: str, issues: list[LintIssue]) -> None:
    """
    if (flag) { … } else { … } where a button in one branch sets `flag`: activating it removes
    the focused button from the screen, focus is lost and nothing is announced.
    """
    for m in re.finditer(r'\bif\s*\(\s*(!?)\s*(\w+)\s*\)', scan_code):
        flag = m.group(2)
        first = _block_after(scan_code, m.end())
        if not first:
            continue
        body1, end1 = first
        k = _skip_ws(scan_code, end1)
        if not scan_code.startswith("else", k):
            continue
        second = _block_after(scan_code, k + 4)
        if not second:
            continue
        body2 = second[0]
        both = body1 + body2
        if re.search(r'focusRequester|FocusRequester|liveRegion|announceForAccessibility', both):
            continue
        assigns = rf'\b{re.escape(flag)}\s*=(?!=)'
        handlers = re.findall(r'\bonClick\s*=\s*\{(.*?)\}', both, re.S)
        handlers += [b for b in re.findall(r'\.clickable\s*\{(.*?)\}', both, re.S)]
        if any(re.search(assigns, h) for h in handlers):
            issues.append(LintIssue(
                id="ComposeFocusLossOnToggle",
                severity="Warning",
                message=(
                    f"A button that changes `{flag}` swaps the content of this if/else and removes "
                    "itself: screen reader focus is lost and the change is not announced. Move focus "
                    "with a FocusRequester or announce it with Modifier.semantics { liveRegion = … }."
                ),
                file=f"[compose-static] {filename}",
                line=_line_of(original_code, m.start()),
                is_a11y=True,
            ))


# ── Disabled field used to show data ─────────────────────────────────────────

def _check_disabled_field(scan_code: str, original_code: str, filename: str, issues: list[LintIssue]) -> None:
    """TextField/OutlinedTextField disabled (enabled = state or false) with no readOnly."""
    for m in re.finditer(r'\b(OutlinedTextField|TextField)\s*\(', scan_code):
        args = _extract_call_block(scan_code, m.end() - 1)
        if args is None:
            continue
        en = re.search(r'\benabled\s*=\s*([^,\n)]+)', args)
        if not en or en.group(1).strip() == "true" or _has_param(args, "readOnly"):
            continue
        issues.append(LintIssue(
            id="ComposeDisabledFieldWithValue",
            severity="Info",
            message=(
                f"{m.group(1)}() is disabled (enabled = {en.group(1).strip()}): its value is shown in "
                "low-contrast text and announced as \"disabled\". To show data that cannot be edited "
                "yet, use readOnly instead. (Beyond WCAG: disabled controls are exempt from 1.4.3.)"
            ),
            file=f"[compose-static] {filename}",
            line=_line_of(original_code, m.start()),
            is_a11y=True,
        ))


# ── Public API ────────────────────────────────────────────────────────────────

def scan_compose_a11y(code: str, filename: str = "MainActivity.kt") -> list[LintIssue]:
    """
    Scan Kotlin/Compose source code for accessibility anti-patterns.

    Args:
        code:     Full text of the Kotlin source file (post-fixer).
        filename: Base name used in LintIssue.file for display.

    Returns:
        List of LintIssue objects, all with is_a11y=True.
    """
    # Only scan Compose files — plain Activity code doesn't use these patterns
    if not re.search(r'@Composable|setContent\s*\{|androidx\.compose', code):
        return []

    scan_code = _strip_line_comments(code)
    issues: list[LintIssue] = []

    # Image / Icon — contentDescription
    for component in ("Image", "Icon"):
        _check_content_description(scan_code, code, component, filename, issues)

    # TextField / OutlinedTextField — label
    for component in ("OutlinedTextField", "TextField"):
        _check_textfield_label(scan_code, code, component, filename, issues)

    # IconButton — inner Icon with null contentDescription
    _check_iconbutton_label(scan_code, code, filename, issues)

    # Clickable elements / interactive components below 48dp
    _check_touch_target(scan_code, code, filename, issues)

    # Headings, description wording, focus loss, disabled fields showing data
    _check_heading(scan_code, code, filename, issues)
    _check_description_wording(scan_code, code, filename, issues)
    _check_focus_loss(scan_code, code, filename, issues)
    _check_disabled_field(scan_code, code, filename, issues)

    # Deduplicate by (id, line) — the same element should not appear twice
    seen: set[tuple[str, int]] = set()
    deduped: list[LintIssue] = []
    for issue in issues:
        key = (issue.id, issue.line)
        if key not in seen:
            seen.add(key)
            deduped.append(issue)

    return deduped
