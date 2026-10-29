"""
reanalyse.py — Re-runs build + Lint + ATF on corrected Kotlin files.

Usage:
    python src/reanalyse.py [path/to/file_corrected.kt]

If no file is given, every corrected file in outputs/codes/ is processed.
Report saved with 'reanalise_' prefix in outputs/reports/.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import process_llm, connect_emulator, CODES_DIR, REPORTS_DIR
from report_generator import save_json_report
from tracking import slug, read_meta, corrected_files, now_iso, ANALYZER_VERSION


def main():
    if len(sys.argv) > 1:
        kt_path = Path(sys.argv[1])
        if not kt_path.is_absolute():
            kt_path = Path("/app") / kt_path
        if not kt_path.exists():
            print(f"[ERROR] File not found: {kt_path}", flush=True)
            sys.exit(1)
        files = [kt_path]
    else:
        files = corrected_files(CODES_DIR)
        if not files:
            print(f"[ERROR] No corrected files found in {CODES_DIR}", flush=True)
            sys.exit(1)

    print(f"[reanalyse] {len(files)} file(s) to re-analyse:", flush=True)
    for f in files:
        print(f"  {f.name}", flush=True)

    emulator_serial = connect_emulator()
    if emulator_serial:
        print(f"[reanalyse] Device: {emulator_serial}", flush=True)
    else:
        print("[reanalyse] No device — ATF will be skipped", flush=True)

    results: dict = {}
    metas = {}
    for kt_file in files:
        meta = read_meta(kt_file)
        llm_name = meta.get("llm") or kt_file.stem
        metas[llm_name] = (kt_file, meta)
        code = kt_file.read_text(encoding="utf-8")
        raw = f"```kotlin\n{code}\n```"
        print(f"\n[{llm_name}] Starting re-analysis...", flush=True)
        result = process_llm(llm_name, raw, t_gen=0.0, emulator_serial=emulator_serial)
        results[llm_name] = result

    prompt = "[re-analysis of corrected code]"
    json_path, run_id = save_json_report(results, prompt, REPORTS_DIR)

    # Rename to reanalise_<label>_ and link it to the corrected file and the original analysis
    if len(files) == 1:
        kt_file, meta = next(iter(metas.values()))
        label = slug(meta.get("label") or kt_file.stem.removesuffix("_corrigido").removesuffix("_corrected"))
    else:
        kt_file, meta, label = None, {}, "lote"
    reanalise_path = REPORTS_DIR / f"reanalise_{label}_{run_id}.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["source"] = "reanalise"
    data["run_id"] = f"reanalise_{run_id}"
    data["meta"] = {
        **{k: v for k, v in meta.items() if k not in ("before", "kind")},
        "kind": "reanalise", "label": label, "corrected_file": kt_file.name if kt_file else "",
        "created_at": now_iso(), "analyzer": ANALYZER_VERSION,
    }
    reanalise_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    json_path.unlink()

    print(f"\n[reanalyse] Done. Run ID: {data['run_id']}", flush=True)
    print(f"[reanalyse] Report saved: {reanalise_path}", flush=True)
    print(f"REANALYSIS_REPORT:{reanalise_path.name}", flush=True)


if __name__ == "__main__":
    main()
