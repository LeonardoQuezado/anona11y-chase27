"""
Subprocess entry-point for the /teste page.

Reads the Kotlin code written to /app/prompts/test_code.kt, wraps it in
code fences so extract_kotlin() can parse it, then runs the full
build + lint + ATF pipeline and emits JSON at the end so the web server
can serve the report.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import (
    connect_emulator,
    process_llm,
    EMULATOR_HOST,
    REPORTS_DIR,
)
from report_generator import save_json_report
from tracking import slug, now_iso, ANALYZER_VERSION

PROMPTS_DIR = Path("/app/prompts")


def main() -> None:
    code_file = PROMPTS_DIR / "test_code.kt"
    if not code_file.exists():
        print("[FAIL] test_code.kt not found.")
        sys.exit(1)

    kotlin_code = code_file.read_text(encoding="utf-8").strip()
    if not kotlin_code:
        print("[FAIL] Empty code.")
        sys.exit(1)

    # Wrap in fences so extract_kotlin() works normally
    raw = f"```kotlin\n{kotlin_code}\n```"

    print("\n" + "=" * 60)
    print("  CODE TEST — Build + Lint + ATF")
    print("=" * 60 + "\n")

    if EMULATOR_HOST:
        emulator_serial = connect_emulator()
        if emulator_serial:
            print(f"  Emulator connected: {emulator_serial}")
        else:
            print("  [WARN] Emulator not reachable — using Robolectric")
    else:
        emulator_serial = None
        print("  No emulator (EMULATOR_HOST not set) — using Robolectric\n")

    try:
        meta = json.loads((PROMPTS_DIR / "test_meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    label = slug(meta.get("label") or "teste")
    llm_key = slug(meta.get("generator") or "manual").lower()
    print(f"  Test    : {label}\n")

    t0 = time.perf_counter()
    result = process_llm(llm_key, raw, 0.0, emulator_serial)
    elapsed = time.perf_counter() - t0

    print(f"\n{'─' * 60}")
    print(f"  Status  : {result.status}")
    print(f"  Time    : {elapsed:.1f}s")
    if result.error_msg:
        print(f"  Error   : {result.error_msg.splitlines()[0]}")

    # Save a labelled report so it can be corrected and traced later
    json_path, run_id = save_json_report({llm_key: result}, "[direct code test]", REPORTS_DIR)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["meta"] = {
        "kind": "analise", "label": label, "llm": llm_key,
        "screen": meta.get("screen", ""), "generator": meta.get("generator", ""),
        "prompt_file": meta.get("prompt_file", ""), "created_at": now_iso(),
        "repair_attempt": int(meta.get("repair_attempt", 0)),
        "analyzer": ANALYZER_VERSION,
    }
    final = REPORTS_DIR / f"report_{label}_{run_id}.json"
    final.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if final != json_path:
        json_path.unlink()
    print(f"  Report  : {final.name}")
    print(f"REPORT_FILE:{final.name}")

    print("\nPipeline complete.\n")


if __name__ == "__main__":
    main()
