"""Web interface for the Accessibility LLM Pipeline.

Runs automatically via docker-compose.
Access at: http://localhost:8000
"""
import asyncio
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import json

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel

REPORTS_DIR = Path("/app/outputs/reports")

sys.path.insert(0, str(Path(__file__).parent))
import tracking  # noqa: E402

PROMPTS_DIR       = Path("/app/prompts")
TEMPLATES_DIR     = Path(__file__).parent / "templates"
VALIDATION_DIR    = Path(__file__).parent / "validation_screens"
STATIC_DIR        = Path(__file__).parent / "static"

_VALIDATION_META = {
    "ProfileScreen":      "3 IN · 2 TF (LINT) + ST (ATF)",
    "GalleryGridScreen":  "1 IN (LINT) · 1 TT (STATIC) · 12 ST (ATF) — v1 reported 16",
    "SettingsFormScreen": "4 TF · 2 IN (LINT) + ST (ATF)",
    "CalibracaoLimpaScreen":    "Negative control — expected 0 in LINT, STATIC and ATF",
    "CalibracaoDefeitosScreen": "Positive control — LINT 2 · STATIC 4 (includes TT) · ATF ST 2 · CT 1",
    "CalibracaoCoberturaScreen": "Coverage — LINT 7 · STATIC 17 (+1 beyond WCAG) · ATF 14 (ST 7 · TT 5 · CT 2)",
}

app = FastAPI(
    title="Melodie A11Y — Accessibility Pipeline",
    description="Automated pipeline for generating, compiling and evaluating the accessibility of Jetpack Compose interfaces produced by LLMs.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_SWAGGER_CSS = """
body { background: #0d0718 !important; }
.swagger-ui { background: #0d0718; color: #e2d9f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
.swagger-ui .topbar { background: #160d2a; border-bottom: 1px solid #2a1a4a; padding: 10px 20px; }
.swagger-ui .topbar-wrapper img { display: none; }
.swagger-ui .topbar-wrapper::before {
  content: 'Melodie A11Y — API';
  color: #f1eaff; font-weight: 700; font-size: 1rem; letter-spacing: -0.01em;
}
.swagger-ui .info { margin: 32px 0 20px; }
.swagger-ui .info .title { color: #f1eaff; }
.swagger-ui .info .description p { color: #9286ae; }
.swagger-ui .info .base-url { color: #9286ae; }
.swagger-ui .scheme-container { background: #160d2a; border: 1px solid #2a1a4a; box-shadow: none; padding: 16px 20px; border-radius: 10px; }
.swagger-ui select { background: #1a0d30; border: 1px solid #3d2060; color: #e2d9f3; border-radius: 6px; }
.swagger-ui .opblock-tag { color: #e2d9f3; border-bottom: 1px solid #2a1a4a; font-size: 0.95rem; }
.swagger-ui .opblock-tag:hover { background: #1a0a2e; }
.swagger-ui .opblock { border-radius: 8px; border: 1px solid #2a1a4a; margin: 6px 0; box-shadow: none; }
.swagger-ui .opblock .opblock-summary { border-radius: 7px; }
.swagger-ui .opblock.opblock-get { background: rgba(168,85,247,0.08); border-color: #4c1d95; }
.swagger-ui .opblock.opblock-get .opblock-summary { border-color: #4c1d95; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: #7c3aed; border-radius: 5px; }
.swagger-ui .opblock.opblock-post { background: rgba(251,146,60,0.07); border-color: #7c2d12; }
.swagger-ui .opblock.opblock-post .opblock-summary { border-color: #7c2d12; }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background: #c2410c; border-radius: 5px; }
.swagger-ui .opblock-summary-path { color: #e2d9f3 !important; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.85rem; }
.swagger-ui .opblock-summary-description { color: #9286ae; }
.swagger-ui .opblock-body { background: #130920; }
.swagger-ui .opblock-description-wrapper p, .swagger-ui .opblock-section-header h4 { color: #c4b5fd; }
.swagger-ui .opblock-section-header { background: #1a0d30; border-bottom: 1px solid #2a1a4a; }
.swagger-ui table thead tr th, .swagger-ui table thead tr td { color: #9286ae; border-bottom: 1px solid #2a1a4a; }
.swagger-ui .response-col_status { color: #b268f8; }
.swagger-ui .response-col_description { color: #e2d9f3; }
.swagger-ui textarea, .swagger-ui input[type=text], .swagger-ui input[type=password] {
  background: #1a0d30; border: 1px solid #3d2060; color: #e2d9f3; border-radius: 6px;
}
.swagger-ui .btn { border-radius: 6px; }
.swagger-ui .btn.execute { background: #7c3aed; border-color: #7c3aed; color: #fff; }
.swagger-ui .btn.execute:hover { background: #6d28d9; }
.swagger-ui .btn.cancel { background: transparent; border-color: #3d2060; color: #9286ae; }
.swagger-ui .model-box { background: #130920; border: 1px solid #2a1a4a; border-radius: 8px; }
.swagger-ui .model { color: #e2d9f3; }
.swagger-ui .model-title { color: #c4b5fd; }
.swagger-ui section.models { border: 1px solid #2a1a4a; border-radius: 10px; background: #160d2a; }
.swagger-ui section.models.is-open h4 { border-bottom: 1px solid #2a1a4a; color: #e2d9f3; }
.swagger-ui .prop-type { color: #c084fc; }
.swagger-ui .prop-format { color: #9286ae; }
.swagger-ui .highlight-code { background: #0a0414 !important; border-radius: 6px; }
.swagger-ui .microlight { background: #0a0414 !important; color: #c4b5fd !important; }
.swagger-ui .arrow { fill: #7c6d9e; }
.swagger-ui a.nostyle, .swagger-ui a.nostyle:visited { color: #c084fc; }
"""

@app.get("/api-docs", include_in_schema=False, response_class=HTMLResponse)
async def api_docs():
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Melodie A11Y — API Docs",
        swagger_favicon_url="/static/logo-icon.png",
    )
    # Inject purple theme CSS
    styled = html.body.decode().replace(
        "</head>",
        f"<style>{_SWAGGER_CSS}</style></head>"
    )
    return HTMLResponse(styled)

_pipeline_lock = asyncio.Lock()
_current_process: asyncio.subprocess.Process | None = None


# ── Models ────────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    prompt: str
    selected_llms: list[str] = []
    few_shot_examples: str = ""
    n_runs: int = 1
    self_repair: bool = False
    # Per-run LLM settings typed in the analysis page: {llm: {field: value}}.
    # Passed to the pipeline process as env vars only; never written to disk.
    credentials: dict[str, dict[str, str]] = {}


# llm -> field -> env var read by llm_client.py
_LLM_CREDENTIAL_ENV = {
    "gemini":    {"api_key": "GEMINI_API_KEY",    "model": "GEMINI_MODEL"},
    "groq":      {"api_key": "GROQ_API_KEY",      "model": "GROQ_MODEL"},
    "deepseek":  {"api_key": "DEEPSEEK_API_KEY",  "model": "DEEPSEEK_MODEL"},
    "xai":       {"api_key": "XAI_API_KEY",       "model": "XAI_MODEL"},
    "openai":    {"api_key": "OPENAI_API_KEY",    "model": "OPENAI_MODEL"},
    "anthropic": {"api_key": "ANTHROPIC_API_KEY", "model": "ANTHROPIC_MODEL"},
    "ollama":    {"base_url": "OLLAMA_BASE_URL",  "model": "OLLAMA_MODEL"},
}


def _credential_env(credentials: dict[str, dict[str, str]]) -> dict[str, str]:
    env = {}
    for llm, fields in credentials.items():
        for field, value in (fields or {}).items():
            var = _LLM_CREDENTIAL_ENV.get(llm, {}).get(field)
            if var and isinstance(value, str) and value.strip():
                env[var] = value.strip()
    return env


class TestRunRequest(BaseModel):
    kotlin_code: str
    label: str = ""          # e.g. "01_login_claude"
    screen: str = ""         # e.g. "01_login"
    generator: str = ""      # e.g. "Claude"
    prompt_file: str = ""
    repair_attempt: int = 0  # 0 = the model's first answer; 1–2 = answer to the repair prompt


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    return HTMLResponse((TEMPLATES_DIR / "landing.html").read_text(encoding="utf-8"))


@app.get("/analise", response_class=HTMLResponse)
async def analise():
    return HTMLResponse((TEMPLATES_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/correcao", response_class=HTMLResponse)
async def correcao():
    return HTMLResponse((TEMPLATES_DIR / "correcao.html").read_text(encoding="utf-8"))


@app.get("/docs", response_class=HTMLResponse)
async def docs():
    return HTMLResponse((TEMPLATES_DIR / "docs.html").read_text(encoding="utf-8"))


@app.get("/log", response_class=HTMLResponse)
async def log():
    return HTMLResponse((TEMPLATES_DIR / "log.html").read_text(encoding="utf-8"))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse((TEMPLATES_DIR / "dashboard.html").read_text(encoding="utf-8"))


@app.get("/teste", response_class=HTMLResponse)
async def teste():
    return HTMLResponse((TEMPLATES_DIR / "teste.html").read_text(encoding="utf-8"))


@app.get("/api/validation-screens")
async def validation_screens():
    if not VALIDATION_DIR.exists():
        return JSONResponse({"screens": []})
    screens = []
    for f in sorted(VALIDATION_DIR.glob("*.kt")):
        screens.append({
            "id": f.stem,
            "name": f.stem,
            "expected": _VALIDATION_META.get(f.stem, ""),
            "code": f.read_text(encoding="utf-8"),
        })
    return JSONResponse({"screens": screens})


@app.post("/api/test-run")
async def test_run(body: TestRunRequest):
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="The pipeline is already running")

    async def generate():
        global _current_process
        async with _pipeline_lock:
            PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            (PROMPTS_DIR / "test_code.kt").write_text(body.kotlin_code, encoding="utf-8")
            (PROMPTS_DIR / "test_meta.json").write_text(json.dumps({
                "label": tracking.slug(body.label or f"{body.screen}_{body.generator}" or "teste"),
                "screen": body.screen[:60], "generator": body.generator[:40], "prompt_file": body.prompt_file[:80],
                "repair_attempt": max(0, min(body.repair_attempt, REPAIR_MAX)),
            }, ensure_ascii=False), encoding="utf-8")

            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            _current_process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "/app/src/test_run.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(
                            _current_process.stdout.readline(), timeout=25.0
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    yield f"data: {text}\n\n"
                await _current_process.wait()
            finally:
                _current_process = None

            yield "data: __DONE__\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _ping_ollama() -> bool:
    """Tries to reach the local Ollama server with a 2 s timeout."""
    base = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    try:
        timeout = aiohttp.ClientTimeout(total=2)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{base}/api/tags") as resp:
                return resp.status == 200
    except Exception:
        return False


@app.get("/api/status")
async def get_status():
    ollama_ok = await _ping_ollama()
    return {
        "running": _pipeline_lock.locked(),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
        "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
        "labserver": bool(os.environ.get("LAB_SERVER_TOKEN")),
        "labserver_base_url": os.environ.get("LAB_SERVER_BASE_URL", ""),
        "labserver_model": os.environ.get("LAB_SERVER_MODEL", "qwen3-coder-30b-a3b-instruct-fp8"),
        "llms": {
            "gemini":    bool(os.environ.get("GEMINI_API_KEY")),
            "groq":      bool(os.environ.get("GROQ_API_KEY")),
            "deepseek":  bool(os.environ.get("DEEPSEEK_API_KEY")),
            "xai":       bool(os.environ.get("XAI_API_KEY")),
            "openai":    bool(os.environ.get("OPENAI_API_KEY")),
            "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "ollama":    ollama_ok,
        },
    }


@app.get("/api/reports")
async def list_reports():
    """List all available reports, newest first."""
    if not REPORTS_DIR.exists():
        return JSONResponse({"reports": []})
    files = sorted(REPORTS_DIR.glob("report_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    reports = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            llms = list(data.get("llms", {}).keys())
            total_v = sum(
                (e.get("accessibility_issues", {}).get("total", 0)
                 + e.get("static_issues", {}).get("total", 0)
                 + e.get("atf_issues", {}).get("total", 0))
                for e in data.get("llms", {}).values()
                if e.get("status") == "success"
            )
            reports.append({
                "filename": f.name,
                "run_id":   data.get("run_id", f.stem),
                "timestamp": data.get("timestamp", ""),
                "prompt_preview": (data.get("prompt", "") or "")[:60],
                "llms": llms,
                "total_violations": total_v,
                "label": data.get("meta", {}).get("label", ""),
                "meta": data.get("meta", {}),
            })
        except Exception:
            continue
    return JSONResponse({"reports": reports})


@app.get("/api/reports/{filename}")
async def get_report_by_filename(filename: str):
    if "/" in filename or ".." in filename or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/report/latest")
async def get_latest_report():
    if not REPORTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No reports yet")
    files = sorted(REPORTS_DIR.glob("report_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise HTTPException(status_code=404, detail="No reports yet")
    return JSONResponse(json.loads(files[-1].read_text(encoding="utf-8")))


@app.get("/api/prompts")
async def list_prompts():
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(p.name for p in PROMPTS_DIR.glob("*.txt"))
    return {"prompts": files}


@app.get("/api/prompts/{name}")
async def get_prompt(name: str):
    if "/" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid file name")
    path = PROMPTS_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"name": name, "content": path.read_text(encoding="utf-8")}


@app.post("/api/run")
async def run_pipeline(body: RunRequest):
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline already running")

    async def generate():
        global _current_process
        async with _pipeline_lock:
            PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
            (PROMPTS_DIR / "prompt.txt").write_text(body.prompt, encoding="utf-8")
            few_shot_file = PROMPTS_DIR / "few_shot_examples.txt"
            if body.few_shot_examples.strip():
                few_shot_file.write_text(body.few_shot_examples, encoding="utf-8")
            elif few_shot_file.exists():
                few_shot_file.unlink()

            env = {**os.environ, "PYTHONUNBUFFERED": "1", **_credential_env(body.credentials)}
            if body.selected_llms:
                env["ENABLED_LLMS"] = ",".join(body.selected_llms)
            env["N_RUNS"] = str(max(1, min(body.n_runs, 10)))
            if body.self_repair:
                env["SELF_REPAIR"] = "true"
            _current_process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "/app/src/pipeline.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(
                            _current_process.stdout.readline(), timeout=25.0
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    yield f"data: {text}\n\n"
                await _current_process.wait()
            finally:
                _current_process = None

            yield "data: __DONE__\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


CODES_DIR = Path("/app/outputs/codes")


class CorrectRequest(BaseModel):
    filename: str = ""
    # Correction model chosen in the page; empty fields fall back to .env (see corrector.py).
    provider: str = ""
    api_key: str = ""
    model: str = ""
    base_url: str = ""


_CORRECTOR_PROVIDERS = {"labserver", "ollama", "openai", "anthropic", "gemini", "groq", "deepseek", "xai", "custom"}


class ReanalyseRequest(BaseModel):
    kt_file: str = ""


@app.post("/api/correct")
async def correct_violations(body: CorrectRequest = CorrectRequest()):
    """Run corrector.py as a streaming subprocess."""
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="The pipeline is already running")

    report_path = None
    if body.filename:
        if "/" in body.filename or ".." in body.filename or not body.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Invalid filename")
        report_path = REPORTS_DIR / body.filename
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
    if body.provider and body.provider not in _CORRECTOR_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown provider")

    async def generate():
        global _current_process
        async with _pipeline_lock:
            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            for var, value in (("CORRECTOR_PROVIDER", body.provider), ("CORRECTOR_API_KEY", body.api_key),
                               ("CORRECTOR_MODEL", body.model), ("CORRECTOR_BASE_URL", body.base_url)):
                if value.strip():
                    env[var] = value.strip()
            cmd = [sys.executable, "-u", "/app/src/corrector.py"]
            if report_path:
                cmd.append(str(report_path))
            _current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(
                            _current_process.stdout.readline(), timeout=25.0
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    yield f"data: {text}\n\n"
                await _current_process.wait()
            finally:
                _current_process = None

            yield "data: __DONE__\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/corrected-files")
async def list_corrected_files():
    """List corrected Kotlin files available for re-analysis."""
    if not CODES_DIR.exists():
        return JSONResponse({"files": []})
    files = tracking.corrected_files(CODES_DIR)
    from datetime import datetime
    out = []
    for f in files:
        meta = tracking.read_meta(f)
        out.append({
            "name": f.name,
            "label": meta.get("label") or f.stem.removesuffix("_corrigido").removesuffix("_corrected"),
            "source_report": meta.get("source_report", ""),
            "generator": meta.get("generator", ""),
            "screen": meta.get("screen", ""),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified_at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M:%S"),
        })
    return JSONResponse({"files": out})


class RenameRequest(BaseModel):
    name: str
    label: str


@app.post("/api/corrected-files/rename")
async def rename_corrected_file(body: RenameRequest):
    """Rename a corrected file (and its sidecar); re-analysis reports keep pointing at it."""
    if "/" in body.name or ".." in body.name or not body.name.endswith(".kt"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    old = CODES_DIR / body.name
    if not old.exists():
        raise HTTPException(status_code=404, detail="Corrected file not found")
    label = tracking.slug(body.label)
    new = old if old.name == f"{label}_corrigido.kt" else tracking.corrected_path(CODES_DIR, label)
    meta = tracking.read_meta(old)
    if new != old:
        old_meta = tracking.sidecar(old)
        old.rename(new)
        if old_meta.exists():
            old_meta.rename(tracking.sidecar(new))
    meta["label"] = new.stem.removesuffix("_corrigido")
    tracking.write_meta(new, meta)
    for rp in REPORTS_DIR.glob("reanalise_*.json"):
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if data.get("meta", {}).get("corrected_file") == old.name:
            data["meta"]["corrected_file"] = new.name
            data["meta"]["label"] = meta["label"]
            rp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return JSONResponse({"name": new.name, "label": meta["label"]})


class ReportLabelRequest(BaseModel):
    filename: str
    label: str


@app.post("/api/reports/label")
async def set_report_label(body: ReportLabelRequest):
    """Give an analysis or re-analysis report a readable name (stored inside the report)."""
    if "/" in body.filename or ".." in body.filename or not body.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = REPORTS_DIR / body.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("meta", {})["label"] = tracking.slug(body.label)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return JSONResponse({"label": data["meta"]["label"]})


BATTERY_DIR = PROMPTS_DIR / "bateria_chase2027"


REPAIR_MAX = 2   # same limit as the automatic SELF_REPAIR loop


@app.get("/api/repair-prompt/{filename}")
async def repair_prompt(filename: str):
    """
    The repair prompt for a report whose build failed: the screen's original prompt, the compile
    errors and the code that failed (the same text the automatic SELF_REPAIR sends). The user
    pastes it in the same chat and analyses the answer as the next repair attempt.
    """
    from repair_prompt import build_repair_prompt
    path = REPORTS_DIR / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    entry = next(iter(data.get("llms", {}).values()), {})
    if entry.get("status") != "build_failed":
        raise HTTPException(status_code=400, detail="This report compiled: there is nothing to repair")
    meta = data.get("meta", {})
    attempt = int(meta.get("repair_attempt", 0))
    if attempt >= REPAIR_MAX:
        raise HTTPException(status_code=400, detail=f"Limite de {REPAIR_MAX} reparos atingido")
    prompt_path = BATTERY_DIR / Path(meta.get("prompt_file", "")).name
    original = prompt_path.read_text(encoding="utf-8") if meta.get("prompt_file") and prompt_path.exists() else ""
    return JSONResponse({
        "text": build_repair_prompt(original, entry.get("generated_code", ""), entry.get("error", "")),
        "next_attempt": attempt + 1,
        "max": REPAIR_MAX,
    })


@app.get("/api/battery-prompts")
async def battery_prompts():
    """The ready-to-paste prompts of the CHASE 2027 battery."""
    if not BATTERY_DIR.exists():
        return JSONResponse({"prompts": []})
    return JSONResponse({"prompts": [
        {"id": f.stem, "name": f.stem.split("_", 1)[-1].replace("_", " ").title(), "file": f.name,
         "text": f.read_text(encoding="utf-8")}
        for f in sorted(BATTERY_DIR.glob("*.txt"))
    ]})


def _battery_rows() -> list[dict]:
    """One row per test label (its latest analysis): counts, latest corrected file and latest re-analysis.

    Re-running the analysis of a label (e.g. after an analyser fix) replaces the older row.
    """
    rows: dict[str, dict] = {}
    for rp in sorted(REPORTS_DIR.glob("report_*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
        except ValueError:
            continue
        meta = data.get("meta", {})
        if meta.get("kind") != "analise" or meta.get("screen", "").startswith("validacao_"):
            continue
        entry = next(iter(data.get("llms", {}).values()), {})
        rows[rp.name] = {"label": meta.get("label", ""), "screen": meta.get("screen", ""), "generator": meta.get("generator", ""),
                         "analysis": rp.name, "analysed_at": data.get("timestamp", ""), "before": tracking.counts(entry),
                         "analyzer": meta.get("analyzer", "v1"), "corrected": "", "reanalysis": "", "after": None,
                         "reanalyzer": "", "atf_ok": tracking.atf_read_ok(entry), "atf_ok_after": None,
                         "repair_attempts": int(meta.get("repair_attempt", 0))}
    for kt in sorted(tracking.corrected_files(CODES_DIR), key=lambda p: p.stat().st_mtime):
        src = tracking.read_meta(kt).get("source_report")
        if src in rows:
            rows[src]["corrected"] = kt.name
    for rp in sorted(REPORTS_DIR.glob("reanalise_*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
        except ValueError:
            continue
        src = data.get("meta", {}).get("source_report")
        if src in rows:
            entry = next(iter(data.get("llms", {}).values()), {})
            rows[src]["reanalysis"] = rp.name
            rows[src]["after"] = tracking.counts(entry)
            rows[src]["reanalyzer"] = data.get("meta", {}).get("analyzer", "v1")
            rows[src]["atf_ok_after"] = tracking.atf_read_ok(entry)
    latest: dict[str, dict] = {}
    for r in rows.values():                    # rows were added oldest first
        latest[r["label"] or r["analysis"]] = r
    return sorted(latest.values(), key=lambda r: (r["screen"], r["generator"], r["analysed_at"]))


class BatteryDeleteRequest(BaseModel):
    screen: str = ""        # with generator: one cell of the grid; both empty + all=True: the whole battery
    generator: str = ""
    all: bool = False


def _battery_files(screen: str, generator: str, everything: bool) -> list[Path]:
    """Every file of the matching battery tests: analysis reports, corrected .kt + sidecar, re-analyses."""
    analyses: set[str] = set()
    files: list[Path] = []
    for rp in REPORTS_DIR.glob("report_*.json"):
        try:
            meta = json.loads(rp.read_text(encoding="utf-8")).get("meta", {})
        except ValueError:
            continue
        if meta.get("kind") != "analise" or meta.get("screen", "").startswith("validacao_"):
            continue
        if everything or (meta.get("screen") == screen
                          and meta.get("generator", "").lower() == generator.lower()):
            analyses.add(rp.name)
            files.append(rp)
    for kt in tracking.corrected_files(CODES_DIR):
        if tracking.read_meta(kt).get("source_report") in analyses:
            files += [kt] + ([tracking.sidecar(kt)] if tracking.sidecar(kt).exists() else [])
    for rp in REPORTS_DIR.glob("reanalise_*.json"):
        try:
            src = json.loads(rp.read_text(encoding="utf-8")).get("meta", {}).get("source_report")
        except ValueError:
            continue
        if src in analyses:
            files.append(rp)
    return files


@app.post("/api/battery/delete")
async def battery_delete(body: BatteryDeleteRequest):
    """Move the files of one grid cell (or of the whole battery) to outputs/lixeira/<time>/ so it can be redone."""
    if not body.all and not (body.screen and body.generator):
        raise HTTPException(status_code=400, detail="Give a screen and an AI, or all=true")
    files = _battery_files(body.screen, body.generator, body.all)
    if not files:
        return JSONResponse({"moved": [], "trash": ""})
    trash = REPORTS_DIR.parent / "lixeira" / datetime.now().strftime("%Y%m%d_%H%M%S")
    trash.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in files:
        dest = trash / f.name
        n = 2
        while dest.exists():
            dest = trash / f"{f.stem}_{n}{f.suffix}"
            n += 1
        shutil.move(str(f), str(dest))
        moved.append(f.name)
    return JSONResponse({"moved": moved, "trash": str(trash.relative_to(REPORTS_DIR.parent.parent))})


@app.get("/api/battery")
async def battery_status():
    return JSONResponse({"rows": _battery_rows()})


@app.get("/api/battery.csv")
async def battery_csv():
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    keys = ["build", "ST", "TT", "TT_static", "CT", "heading", "desc", "focus", "atf", "lint", "static", "total",
            "beyond_wcag", "code_unique", "null_decorative"]
    # categories compared one by one for regressions (a fixed heading must not hide a new defect)
    cats = ["ST", "TT", "TT_static", "CT", "heading", "desc", "focus", "atf", "lint", "static", "code_unique"]

    def pct(before: int, after: int):
        return round(100 * (before - after) / before, 1) if before else ""
    w.writerow(["label", "tela", "gerador", "relatorio_analise", "arquivo_corrigido", "relatorio_reanalise"]
               + [f"antes_{k}" for k in keys] + [f"depois_{k}" for k in keys]
               + ["resultado_reparo", "reducao_%", "reducao_codigo_unico_%", "reducao_sem_decorativo_%",
                  "regressao", "categorias_pioraram",
               "analisador_antes", "analisador_depois", "leitura_atf_antes", "leitura_atf_depois",
               "tentativas_reparo"])
    for r in _battery_rows():
        b, a = r["before"], r["after"] or {}
        result = red = red_u = red_nd = regress = worse = ""
        if b.get("build") != "success":
            result = "análise não compilou"
        elif not b.get("total") and not a:
            result = "sem violações"
        elif a and a.get("build") != "success":
            # the corrected code did not compile: a failed repair, not a 100 % reduction
            result = red = red_u = red_nd = regress = "falha de build"
        elif a:
            red = pct(b["total"], a["total"])
            red_u = pct(b["code_unique"] + b["atf"], a["code_unique"] + a["atf"])
            red_nd = pct(b["code_unique"] - b["null_decorative"] + b["atf"],
                         a["code_unique"] - a["null_decorative"] + a["atf"])
            worse = " ".join(k for k in cats if a.get(k, 0) > b.get(k, 0))
            regress = "sim" if worse else "não"
            result = ("limpo" if a["total"] == 0 else "piorou" if a["total"] > b["total"]
                      else "sem efeito" if a["total"] == b["total"] else "parcial")
        w.writerow([r["label"], r["screen"], r["generator"], r["analysis"], r["corrected"], r["reanalysis"]]
                   + [b.get(k, "") for k in keys] + [a.get(k, "") for k in keys]
                   + [result, red, red_u, red_nd, regress, worse,
                   r["analyzer"], r["reanalyzer"], "ok" if r["atf_ok"] else "SEM DIAGNÓSTICO",
                   "" if r["atf_ok_after"] is None else ("ok" if r["atf_ok_after"] else "SEM DIAGNÓSTICO"),
                   r["repair_attempts"]])
    return PlainTextResponse("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="bateria_chase2027.csv"'})


@app.get("/api/reanalise-reports")
async def list_reanalise_reports():
    """List re-analysis reports (reanalise_*.json), newest first."""
    if not REPORTS_DIR.exists():
        return JSONResponse({"reports": []})
    files = sorted(REPORTS_DIR.glob("reanalise_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    reports = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            llms = list(data.get("llms", {}).keys())
            total_v = sum(
                (e.get("accessibility_issues", {}).get("total", 0)
                 + e.get("static_issues", {}).get("total", 0)
                 + e.get("atf_issues", {}).get("total", 0))
                for e in data.get("llms", {}).values()
                if e.get("status") == "success"
            )
            reports.append({
                "filename": f.name,
                "run_id":   data.get("run_id", f.stem),
                "timestamp": data.get("timestamp", ""),
                "llms": llms,
                "total_violations": total_v,
                "label": data.get("meta", {}).get("label", ""),
                "meta": data.get("meta", {}),
            })
        except Exception:
            continue
    return JSONResponse({"reports": reports})


@app.post("/api/reanalyse")
async def reanalyse_violations(body: ReanalyseRequest = ReanalyseRequest()):
    """Run reanalyse.py as a streaming subprocess."""
    if _pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="The pipeline is already running")

    kt_path = None
    if body.kt_file:
        if "/" in body.kt_file or ".." in body.kt_file or not body.kt_file.endswith(".kt"):
            raise HTTPException(status_code=400, detail="Invalid filename")
        kt_path = CODES_DIR / body.kt_file
        if not kt_path.exists():
            raise HTTPException(status_code=404, detail="Corrected file not found")

    async def generate():
        global _current_process
        async with _pipeline_lock:
            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            cmd = [sys.executable, "-u", "/app/src/reanalyse.py"]
            if kt_path:
                cmd.append(str(kt_path))
            _current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(
                            _current_process.stdout.readline(), timeout=25.0
                        )
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").rstrip()
                    yield f"data: {text}\n\n"
                await _current_process.wait()
            finally:
                _current_process = None
            yield "data: __DONE__\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/scan", response_class=HTMLResponse)
async def scan():
    return HTMLResponse((TEMPLATES_DIR / "scan.html").read_text(encoding="utf-8"))


@app.get("/fix", response_class=HTMLResponse)
async def fix():
    return HTMLResponse((TEMPLATES_DIR / "correcao_geral.html").read_text(encoding="utf-8"))


@app.get("/relatorios", response_class=HTMLResponse)
async def relatorios():
    return HTMLResponse((TEMPLATES_DIR / "relatorios.html").read_text(encoding="utf-8"))


class GeneralCorrectRequest(BaseModel):
    provider: str = "openai"   # "openai" | "anthropic" | "custom"
    api_key: str
    model: str = "gpt-4o-mini"
    base_url: str = ""         # required for "custom"
    report: dict


async def _call_openai_compat(base_url: str, api_key: str, model: str, prompt: str) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
            ssl=False,
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}: {(await resp.text())[:300]}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"]


async def _call_anthropic(api_key: str, model: str, prompt: str) -> str:
    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={"model": model, "max_tokens": 8192,
                  "messages": [{"role": "user", "content": prompt}]},
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}: {(await resp.text())[:300]}")
            data = await resp.json()
            return data["content"][0]["text"]


async def _call_llm_general(body: GeneralCorrectRequest, prompt: str) -> str:
    BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "groq":   "https://api.groq.com/openai/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    }
    if body.provider == "anthropic":
        return await _call_anthropic(body.api_key, body.model, prompt)
    base = body.base_url.rstrip("/") if body.provider == "custom" else BASE_URLS.get(body.provider, BASE_URLS["openai"])
    return await _call_openai_compat(base, body.api_key, body.model, prompt)


@app.post("/api/correct-general")
async def correct_general(body: GeneralCorrectRequest):
    """Correct violations using any LLM provider. Streams structured SSE events."""

    async def generate():
        llms_data = body.report.get("llms", {})
        any_processed = False

        for llm_name, entry in llms_data.items():
            if entry.get("status") != "success":
                yield f"data: STATUS:Skipping {llm_name} (status: {entry.get('status','?')})\n\n"
                continue

            code = entry.get("generated_code", "")
            if not code:
                yield f"data: STATUS:Skipping {llm_name}: code not found in the report\n\n"
                continue

            lint_issues   = entry.get("accessibility_issues", {}).get("issues", [])
            static_issues = entry.get("static_issues", {}).get("issues", [])
            atf_issues    = entry.get("atf_issues", {}).get("issues", [])
            all_issues = lint_issues + static_issues + atf_issues
            if not all_issues:
                yield f"data: STATUS:Skipping {llm_name}: no violations\n\n"
                continue

            lines = []
            for i in lint_issues:
                lines.append(f"- {i.get('id','')} (Lint) line {i.get('line','?')}: {i.get('message','')}")
            for i in static_issues:
                lines.append(f"- {i.get('id','')} (Static) line {i.get('line','?')}: {i.get('message','')}")
            for i in atf_issues:
                lines.append(f"- {i.get('check','')} (ATF): {i.get('message','')}")

            prompt = (
                "/no_think\n\n"
                "You are an Android accessibility expert specializing in Jetpack Compose.\n"
                "Fix ONLY the violations listed below. Do not restructure the code, "
                "do not rename variables, do not add comments.\n\n"
                f"Detected violations:\n{chr(10).join(lines)}\n\n"
                f"Original code:\n{code}\n\n"
                "Return ONLY the corrected Kotlin code, no explanations."
            )

            yield f"data: STATUS:Sending to {body.provider} ({body.model})...\n\n"
            try:
                corrected = await _call_llm_general(body, prompt)
                yield f"data: CODE_START:{llm_name}\n\n"
                for line in corrected.splitlines():
                    yield f"data: {line}\n\n"
                yield f"data: CODE_END:{llm_name}\n\n"
                any_processed = True
            except Exception as e:
                yield f"data: STATUS:ERROR in {llm_name}: {e}\n\n"

        if not any_processed:
            yield "data: STATUS:No LLM with violations found in the report.\n\n"
        yield "data: __DONE__\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
