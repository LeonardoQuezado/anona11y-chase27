"""
corrector.py — Accessibility correction of generated Kotlin code by an LLM.

Usage:
    python src/corrector.py [report_path]

If report_path is omitted the latest report in outputs/reports/ is used.

The script reads a JSON report produced by save_json_report(), calls the
correction model for each LLM that has accessibility issues, and writes
corrected Kotlin files to outputs/codes/{llm}_corrected.kt.

The correction model is chosen with CORRECTOR_PROVIDER (default: labserver):
  labserver  Qwen3-Coder on a lab server running Open WebUI (may need VPN) — LAB_SERVER_* vars
  ollama     local Ollama server — OLLAMA_BASE_URL / OLLAMA_MODEL
  openai, anthropic, gemini, groq, deepseek, xai — online APIs, key from {NAME}_API_KEY
  custom     any OpenAI-compatible server (CORRECTOR_BASE_URL)
CORRECTOR_API_KEY, CORRECTOR_MODEL and CORRECTOR_BASE_URL override the
provider's key, model and URL (the web page sets them per run).
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from tracking import slug, corrected_path, write_meta, counts, now_iso

load_dotenv()

# provider -> display name, chat-completions URL (or "anthropic"), key env var, default model
PROVIDERS = {
    "labserver": ("Lab server (Open WebUI)",
                  (os.getenv("LAB_SERVER_BASE_URL", "").rstrip("/") + "/api/chat/completions") if os.getenv("LAB_SERVER_BASE_URL") else "",
                  "LAB_SERVER_TOKEN",  os.getenv("LAB_SERVER_MODEL", "qwen3-coder-30b-a3b-instruct-fp8")),
    "ollama":    ("Ollama",           os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434") + "/v1/chat/completions",
                  None,                os.getenv("OLLAMA_MODEL", "llama3.2")),
    "openai":    ("OpenAI",           "https://api.openai.com/v1/chat/completions",
                  "OPENAI_API_KEY",    "gpt-4.5"),
    "anthropic": ("Anthropic Claude", "anthropic",
                  "ANTHROPIC_API_KEY", "claude-sonnet-4-6"),
    "gemini":    ("Gemini",           "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                  "GEMINI_API_KEY",    "gemini-2.5-pro"),
    "groq":      ("Groq",             "https://api.groq.com/openai/v1/chat/completions",
                  "GROQ_API_KEY",      "llama-3.3-70b-versatile"),
    "deepseek":  ("DeepSeek",         "https://api.deepseek.com/v1/chat/completions",
                  "DEEPSEEK_API_KEY",  "deepseek-coder"),
    "xai":       ("xAI Grok",         "https://api.x.ai/v1/chat/completions",
                  "XAI_API_KEY",       "grok-3-mini"),
    "custom":    ("OpenAI-compatible server", "", None, ""),
}

PROVIDER = os.getenv("CORRECTOR_PROVIDER", "labserver").strip().lower() or "labserver"
if PROVIDER not in PROVIDERS:
    sys.exit(f"[ERROR] Unknown CORRECTOR_PROVIDER {PROVIDER!r}. Use one of: {', '.join(PROVIDERS)}")
PROVIDER_NAME, _url, _key_var, _model = PROVIDERS[PROVIDER]


def _chat_url(base: str) -> str:
    """Accepts a server root, a /v1 base or the full endpoint."""
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if PROVIDER == "labserver":
        return base + "/api/chat/completions"
    if PROVIDER == "ollama" and not base.endswith("/v1"):
        base += "/v1"
    return base + "/chat/completions"


_base_override = os.getenv("CORRECTOR_BASE_URL", "").strip()
URL   = _chat_url(_base_override) if _base_override else _url
TOKEN = os.getenv("CORRECTOR_API_KEY", "").strip() or (os.getenv(_key_var, "") if _key_var else "")
MODEL = os.getenv("CORRECTOR_MODEL", "").strip() or _model
PROMPT_VERSION = "v5"   # see results/CORRECTION_LOG.md
REPORTS_DIR = Path("outputs/reports")
CODES_DIR   = Path("outputs/codes")

SYSTEM_PROMPT = """\
You are an expert Android Kotlin developer specialising in Jetpack Compose accessibility.
Your task is to fix ONLY the accessibility violations listed by the user.
Do NOT restructure, refactor, or rewrite anything beyond what is strictly necessary to
resolve each listed violation. Keep all original logic, style, and variable names intact.
Return ONLY the corrected Kotlin source code — no explanation, no markdown fences,
no comments about what changed.

## Jetpack Compose accessibility rules — follow exactly

### SpeakableTextPresentCheck (ATF)
Elements without speakable text. Fix using Modifier.semantics, NOT as a constructor parameter:
  WRONG:  Box(contentDescription = "...")         // compile error
  WRONG:  Row(contentDescription = "...")         // compile error
  CORRECT: Box(modifier = Modifier.semantics { contentDescription = "Play button" }) { ... }
  CORRECT: Icon(imageVector = ..., contentDescription = "Menu")   // Icon/Image accept it directly
  CORRECT: IconButton(modifier = Modifier.semantics { contentDescription = "Close" }) { ... }
For clickable containers (Box, Row, Column with onClick), add semantics on the modifier:
  Box(modifier = Modifier.clickable { }.semantics { contentDescription = "Album: Jazz" }) { ... }

### TouchTargetSizeCheck (ATF)
Interactive elements smaller than 48×48 dp. Fix with minimumInteractiveComponentSize or sizeIn:
  CORRECT: Box(modifier = Modifier.minimumInteractiveComponentSize().clickable { }) { ... }
  CORRECT: IconButton(modifier = Modifier.size(48.dp)) { ... }

### TextContrastCheck (ATF / Lint)
Text contrast ratio below 4.5:1. Fix by darkening/lightening the text or background color.
Use Color values that pass WCAG AA. Do not change layout or logic.

### ComposeIconNullContentDescription (Lint) + ComposeIconButtonMissingLabel (Lint/Static) + SpeakableTextPresentCheck (ATF)

THE ONLY PATTERN THAT SATISFIES BOTH LINT AND ATF FOR IconButton:
Use Modifier.clearAndSetSemantics on the IconButton. This clears child semantic nodes
and defines the description at the button level — the only way ATF reliably sees it.

  REQUIRED IMPORT: import androidx.compose.ui.semantics.clearAndSetSemantics

  CORRECT — use clearAndSetSemantics on every IconButton:
    IconButton(
        onClick = { ... },
        modifier = Modifier.clearAndSetSemantics { contentDescription = "Play" }
    ) {
        Icon(imageVector = Icons.Filled.PlayArrow, contentDescription = "Play", ...)
    }

  Keep a matching, non-null contentDescription on the Icon() as well (prevents Lint warnings).
  The clearAndSetSemantics on the modifier is what fixes the ATF check.

  WRONG — contentDescription only on Icon, no modifier (ATF still fails at runtime):
    IconButton(onClick = {}) {
        Icon(contentDescription = "Play", ...)
    }

  WRONG — Modifier.semantics without clearAndSetSemantics (creates conflicting nodes):
    IconButton(modifier = Modifier.semantics { contentDescription = "Play" }) { ... }

  Apply clearAndSetSemantics to ALL IconButtons in the file, not just the flagged ones.

  For a standalone Icon (not inside IconButton) that is NOT decorative:
  CORRECT: Icon(imageVector = Icons.Default.Star, contentDescription = "Favorite")

  Truly decorative icons (no action, label provided by parent):
    Icon(imageVector = Icons.Default.Circle, contentDescription = null) // decorative

## Required imports when using clearAndSetSemantics
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics  (only if also using Modifier.semantics for non-IconButton elements like Slider)

### ComposeTextFieldMissingLabel (Lint)
TextField/OutlinedTextField without a label parameter.
  CORRECT: OutlinedTextField(value = text, onValueChange = { text = it }, label = { Text("Search") })

## Import required for semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
These must be present at the top of the file when you use Modifier.semantics.

## Summary of rules for contentDescription placement
- Icon() inside IconButton()  → contentDescription on Icon()
- Icon() standalone/clickable → contentDescription on Icon()
- Box/Row/Column/Card clickable → Modifier.semantics { contentDescription = "..." }
- Slider/SeekBar              → Modifier.semantics { contentDescription = "..." }
- Image()                     → contentDescription parameter directly"""

CORRECTION_TEMPLATE = """\
/no_think
Fix ONLY the accessibility violations listed below in the Kotlin/Compose source code.
Apply the exact API patterns described in your system instructions.
Do NOT change anything unrelated to the listed violations.

## Violations to fix
{violations}

## Kotlin source code
```kotlin
{code}
```

Return only the complete corrected Kotlin file. No explanations, no markdown fences."""


def _find_latest_report() -> Path:
    reports = sorted(REPORTS_DIR.glob("report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        sys.exit(f"[ERROR] No reports found in {REPORTS_DIR}. Run the pipeline first.")
    return reports[0]


def _format_violations(entry: dict) -> str:
    lines = []

    for iss in entry.get("accessibility_issues", {}).get("issues", []):
        lines.append(f"- [Lint/{iss['id']}] line {iss['line']}: {iss['message']}")

    for iss in entry.get("static_issues", {}).get("issues", []):
        lines.append(f"- [StaticLint/{iss['id']}] line {iss['line']}: {iss['message']}")

    for iss in entry.get("atf_issues", {}).get("issues", []):
        lines.append(f"- [ATF/{iss['check']}] {iss['message']}")

    return "\n".join(lines) if lines else "(no violations)"


def _call_model(prompt: str) -> str:
    if PROVIDER not in ("ollama", "custom") and not TOKEN:
        sys.exit(f"[ERROR] No API key for {PROVIDER_NAME}. Type it in the page or set {_key_var} in .env.")
    if not URL:
        sys.exit(f"[ERROR] No server URL for {PROVIDER_NAME}. Type it in the page or set "
                 f"{'LAB_SERVER_BASE_URL' if PROVIDER == 'labserver' else 'CORRECTOR_BASE_URL'} in .env.")
    if not MODEL:
        sys.exit("[ERROR] CORRECTOR_MODEL is not set.")

    if URL == "anthropic":
        url     = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": TOKEN, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload = {
            "model": MODEL,
            "max_tokens": 8192,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        extract = lambda data: data["content"][0]["text"]
    else:
        url     = URL
        headers = {"Content-Type": "application/json"}
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.1,
            "stream": False,
        }
        extract = lambda data: data["choices"][0]["message"]["content"]

    for attempt in range(1, 4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=300)
            if resp.status_code in (400, 401, 403, 404):
                # wrong key, model or URL: retrying will not help
                sys.exit(f"[ERROR] {PROVIDER_NAME} answered HTTP {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            return extract(resp.json())
        except requests.exceptions.RequestException as exc:
            wait = 2 ** attempt
            print(f"  [WARN] Attempt {attempt} failed: {exc}. Retrying in {wait}s...")
            time.sleep(wait)

    hint = " Check VPN and token." if PROVIDER == "labserver" else " Check the URL and that the server is running." if PROVIDER in ("ollama", "custom") else ""
    sys.exit(f"[ERROR] {PROVIDER_NAME} unreachable after 3 attempts.{hint}")


def _strip_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences if the model adds them."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0]
    return text.strip()


def correct(report_path: Path) -> None:
    print(f"[corrector] Reading report: {report_path}")
    print(f"[corrector] Correction model: {PROVIDER_NAME} ({MODEL})")
    data = json.loads(report_path.read_text(encoding="utf-8"))

    run_id = data.get("run_id", "unknown")
    llms   = data.get("llms", {})
    meta   = data.get("meta", {})
    label  = slug(meta.get("label") or f"run_{run_id}")

    CODES_DIR.mkdir(parents=True, exist_ok=True)

    for llm, entry in llms.items():
        if entry.get("status") != "success":
            print(f"[{llm}] Skipped (status={entry.get('status')})")
            continue

        total_violations = (
            entry.get("accessibility_issues", {}).get("total", 0)
            + entry.get("static_issues", {}).get("total", 0)
            + entry.get("atf_issues", {}).get("total", 0)
        )
        if total_violations == 0:
            print(f"[{llm}] No violations — nothing to correct.")
            continue

        code = entry.get("generated_code")
        if not code:
            fallback = CODES_DIR / f"{llm}_output.kt"
            if fallback.exists():
                code = fallback.read_text(encoding="utf-8")
                print(f"[{llm}] generated_code not in report; using {fallback}")
            else:
                print(f"[{llm}] No source code found — skipping.")
                continue

        violations_text = _format_violations(entry)
        prompt = CORRECTION_TEMPLATE.format(violations=violations_text, code=code)

        print(f"[{llm}] Calling {PROVIDER_NAME} ({total_violations} violation(s))...")
        corrected = _call_model(prompt)
        corrected = _strip_fences(corrected)

        stem = label if len(llms) == 1 else f"{label}_{slug(llm)}"
        out_path = corrected_path(CODES_DIR, stem)   # never overwrite an earlier correction
        out_path.write_text(corrected, encoding="utf-8")
        write_meta(out_path, {
            "kind": "corrigido", "label": out_path.stem.removesuffix("_corrigido"),
            "source_report": report_path.name, "llm": llm,
            "screen": meta.get("screen", ""), "generator": meta.get("generator", "") or llm,
            "corrector_provider": PROVIDER, "corrector_model": MODEL, "corrector_prompt": PROMPT_VERSION,
            "created_at": now_iso(), "before": counts(entry),
        })
        print(f"[{llm}] Corrected code saved → {out_path}")
        print(f"CORRECTED_FILE:{out_path.name}")

    print(f"\n[corrector] Done. Run ID: {run_id}")
    print(f"[corrector] Corrected files are in {CODES_DIR}/")
    print("[corrector] To re-analyse: run the pipeline with these files as input.")


def main() -> None:
    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
        if not report_path.exists():
            sys.exit(f"[ERROR] File not found: {report_path}")
    else:
        report_path = _find_latest_report()

    correct(report_path)


if __name__ == "__main__":
    main()
