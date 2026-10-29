"""
Links each analysis, its corrected Kotlin file and its re-analysis through a readable label
(e.g. "01_login_claude"), so nothing is overwritten and the three can be traced back.

- analysis report:    outputs/reports/report_<label>_<run_id>.json      ("meta" block inside)
- corrected file:     outputs/codes/<label>_corrigido.kt + <label>_corrigido.meta.json
- re-analysis report: outputs/reports/reanalise_<label>_<run_id>.json   ("meta" block inside)

The corrected file's sidecar and the re-analysis "meta" carry `source_report`, which ties them
to the original analysis even if the corrected file is renamed later.
"""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

CORRECTED_GLOBS = ("*_corrigido.kt", "*_corrected.kt")

# Stamped into every analysis and re-analysis report. v2: Google ATF 4.1.1 on the AccessibilityNodeInfo
# tree (replacing the custom ST/TT/CT checks) and lint rules that map Kotlin named arguments.
# v2.1 adds the static ComposeSmallTouchTarget rule (TT_static): Compose enlarges small touch areas
# at runtime, so ATF measures 48dp, but the declared size below 48dp is still counted.
# v2.2: the static scanner reads a positional contentDescription (Icon(vector, null) was reported as
# "missing" and its IconButton was not flagged).
# Reports without it come from v1, whose ST and TextField-label counts had false positives.
# v2.3: the ATF test waits for Compose's accessibility tree before the first pass (it was empty,
# so the top of every scrolling screen went unchecked), scrolls in overlapping steps and skips
# elements cut by the scroll edge.
# v2.4: ATF results inside a scrolling container are keyed by content position (the scroll
# distance is measured between passes), so overlapping passes no longer count an element twice.
# v2.5: the ATF test always returns its per-pass diagnostics, so a result of 0 can be checked
# against a first pass that actually read the screen (atf_read_ok).
# v2.6: static rules for headings, vague/jargon descriptions, focus loss on toggled content, and
# disabled fields used to show data (beyond WCAG, counted apart from the total).
# v2.7: the pre-processor no longer breaks valid code (backgroundColor/disabled renamed only as
# named arguments and never when declared by the code; Color<space>Name and '' outside strings;
# Text() gets text = "" only when no text argument exists).
# v2.8: the device is put in light mode before the ATF run and the mode is stored (ui_mode).
# v2.9: the scroll between ATF passes is measured on the hierarchy the checks run on (a stale node
# snapshot missed a scroll and counted the same 4 elements twice in one re-analysis).
ANALYZER_VERSION = "v2.9 (ATF 4.1.1 + lint UAST v2 + estático v3 + pré-processador v2 + modo claro)"

# Static findings outside WCAG: reported, but kept out of `static` and `total`
BEYOND_WCAG_IDS = {"ComposeDisabledFieldWithValue"}


def slug(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (text or "").strip()).strip("_")
    return s[:max_len] or "teste"


def corrected_path(codes_dir: Path, label: str) -> Path:
    """A free <label>_corrigido.kt name; repeats become <label>_2_corrigido.kt, <label>_3_... (suffix kept for listing)."""
    path, n = codes_dir / f"{label}_corrigido.kt", 2
    while path.exists():
        path, n = codes_dir / f"{label}_{n}_corrigido.kt", n + 1
    return path


def sidecar(kt_file: Path) -> Path:
    return kt_file.with_name(kt_file.stem + ".meta.json")


def read_meta(kt_file: Path) -> dict:
    try:
        return json.loads(sidecar(kt_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_meta(kt_file: Path, meta: dict) -> None:
    sidecar(kt_file).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def corrected_files(codes_dir: Path) -> list[Path]:
    files = {p for g in CORRECTED_GLOBS for p in codes_dir.glob(g)}
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def atf_read_ok(entry: dict) -> bool:
    """True when the ATF diagnostics show a first pass that read the app's accessibility tree."""
    diags = entry.get("atf_issues", {}).get("diagnostics") or []
    m = re.match(r"pass 1: (\d+) nodes", diags[0]) if diags else None
    mode = entry.get("atf_issues", {}).get("ui_mode", "")
    return bool(m) and int(m.group(1)) > 1 and mode in ("", "claro")


# Lint (UAST) and the static scanner check some of the same things: the same defect, at the same
# line, must count once. Ids that name the same defect map to one concept.
_SAME_DEFECT = {
    "ComposeIconMissingContentDescription": "icon_missing", "ComposeIconContentDescription": "icon_missing",
    "ComposeIconNullContentDescription": "icon_null",
    "ComposeImageMissingContentDescription": "image_missing", "ComposeImageContentDescription": "image_missing",
    "ComposeImageNullContentDescription": "image_null",
    "ComposeTextFieldMissingLabel": "textfield_label",
}


def _enclosing_block(code: str, pos: int) -> tuple[str, str]:
    """(text before the innermost {...} that contains pos, that block's text)."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        ch = code[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                end, d = i, 0
                for j in range(i, len(code)):
                    if code[j] == "{":
                        d += 1
                    elif code[j] == "}":
                        d -= 1
                        if d == 0:
                            end = j
                            break
                return code[max(0, i - 120):i], code[i + 1:end]
            depth -= 1
    return "", code


def _is_decorative(code: str, line: int) -> bool:
    """
    An Icon/Image with contentDescription = null at `line` sits next to text that names it:
    its innermost block also has a Text(...) call (e.g. Button { Icon(null); Text("Save") }),
    or it fills a slot of a labelled component (leadingIcon/trailingIcon/icon = { Icon(null) }).
    An icon alone inside an IconButton or a clickable is not decorative.
    """
    lines = code.split("\n")
    if not 1 <= line <= len(lines):
        return False
    m = re.search(r"\b(Icon|Image)\s*\(", lines[line - 1])
    pos = sum(len(l) + 1 for l in lines[:line - 1]) + (m.start() if m else 0)
    before, block = _enclosing_block(code, pos)
    if re.search(r"\b(leadingIcon|trailingIcon|icon|label|placeholder)\s*=\s*$", before.rstrip()):
        return True
    return bool(re.search(r"\bText\s*\(", block))


def code_defects(entry: dict) -> dict:
    """
    Defects found in the code by lint + static scanner, each counted once, and how many of them
    are decorative null icons/images (they count by the method's policy; see the battery doc).
    """
    lint = entry.get("accessibility_issues", {}).get("issues", []) or []
    static = [i for i in entry.get("static_issues", {}).get("issues", []) or []
              if i.get("id") not in BEYOND_WCAG_IDS]
    keys = {(_SAME_DEFECT.get(i.get("id", ""), i.get("id", "")), int(i.get("line", 0) or 0)) for i in lint + static}
    # an IconButton flagged for its null icon is the same defect as that icon (a few lines below)
    icon_lines = [l for c, l in keys if c == "icon_null"]
    keys = {(c, l) for c, l in keys
            if not (c == "ComposeIconButtonMissingLabel" and any(l <= x <= l + 6 for x in icon_lines))}
    code = entry.get("generated_code") or ""
    decorative = sum(1 for c, l in keys if c in ("icon_null", "image_null") and code and _is_decorative(code, l))
    return {"code_unique": len(keys), "null_decorative": decorative}


def counts(entry: dict) -> dict:
    """Violation counts of one LLM entry of a report, by analyser and ATF check."""
    atf = entry.get("atf_issues", {}).get("issues", []) or []
    by_check = Counter(i.get("check", "") for i in atf)
    lint = entry.get("accessibility_issues", {}).get("total", 0) or 0
    static_list = entry.get("static_issues", {}).get("issues", []) or []
    by_id = Counter(i.get("id", "") for i in static_list)
    beyond = sum(by_id[i] for i in BEYOND_WCAG_IDS)
    static = (entry.get("static_issues", {}).get("total", 0) or 0) - beyond
    return {
        "build": entry.get("status", ""),
        "atf": len(atf),
        "ST": by_check.get("SpeakableTextPresentCheck", 0),
        "TT": by_check.get("TouchTargetSizeCheck", 0),
        "TT_static": by_id["ComposeSmallTouchTarget"],
        "heading": by_id["ComposeMissingHeading"],
        "desc": by_id["ComposeVagueContentDescription"],
        "focus": by_id["ComposeFocusLossOnToggle"],
        "beyond_wcag": beyond,
        "CT": by_check.get("TextContrastCheck", 0),
        "lint": lint,
        "static": static,
        "total": len(atf) + lint + static,
        **code_defects(entry),
    }


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
