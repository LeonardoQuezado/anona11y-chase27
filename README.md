# ANONA11Y

End-to-end automated pipeline for generating, compiling, evaluating the
accessibility of, and AI-assisted correction of Android Jetpack Compose
interfaces produced by LLMs. Developed as a research artifact.

---

## What the project is

**ANONA11Y A11Y** is a research tool that evaluates the accessibility of
Android Jetpack Compose interfaces on two fronts:

- **Analysis** — generates interfaces with LLMs, compiles them, runs custom
  static Lint and dynamic ATF on a physical device, and consolidates the results
  in a JSON report.
- **Correction** — takes a violations report and sends the original code,
  together with the list of problems, to a correction model of your choice
  (a local one such as Qwen3-Coder-30B on a lab server or Ollama, or an online API),
  which returns the corrected code. The pipeline re-analyzes the result and
  compares before/after.

The goal is to show that end-to-end automation can make accessibility
evaluation reproducible and scalable, substantially reducing the manual effort
needed to evaluate fast-evolving LLMs.

---

## Web interface

Open `http://localhost:8000` after starting the environment.

| Route | Description |
|-------|-------------|
| `/` | Landing page — project overview |
| `/analise` | Generation + evaluation with LLMs |
| `/correcao` | Assisted correction of violations with a local or online LLM |
| `/docs` | Documentation: architecture, checks, supported LLMs |
| `/teste` | CHASE 2027: paste generated code and analyze it without API keys |

---

## Analysis pipeline — 5 stages

```
[Prompt] → [LLM] → [Extraction + Auto-fix] → [Build] → [Lint] → [ATF] → [Report]
```

| Stage | What happens |
|-------|--------------|
| **1. Generation** | The prompt is sent to the LLM via API; the answer contains the Kotlin/Compose code |
| **2. Extraction + Auto-fix** | Code blocks are extracted; 55 deterministic rules fix compilation errors (imports, namespaces, missing resources); 128 regression tests make sure new fixes do not break earlier cases |
| **3. Build** | Gradle compiles the project and produces a real APK (`assembleDebug`) — Kotlin 1.9.22, AGP 8.2.2, Compose BOM 2024.02.00, compileSdk/targetSdk 36 |
| **4. Static Lint** | Custom UAST rules detect accessibility problems at compile time |
| **5. Dynamic ATF** | The app is installed on a physical device over ADB; ATF runs its checks while scrolling the screen (3 upward and 3 downward sweeps) |

On the Analysis page, each LLM is selected from a list; selecting one opens its
fields (API key and model; server URL and model for Ollama). Keys typed there
are passed to that run only and never written to disk; blank fields fall back to
`.env` and the default model.

---

## Correction pipeline

```
[JSON report] → [Violation extraction] → [Correction model] → [Corrected code] → [Re-analysis]
```

The correction model is chosen on the `/correcao` page: a lab server running
Open WebUI (Qwen3-Coder, possibly over VPN), local Ollama, any other OpenAI-compatible server (LM Studio, vLLM,
llama.cpp) or an online API (OpenAI, Anthropic, Gemini, Groq, DeepSeek, xAI)
with the user's own key. Outside the page, `corrector.py` reads
`CORRECTOR_PROVIDER`, `CORRECTOR_API_KEY`, `CORRECTOR_MODEL` and
`CORRECTOR_BASE_URL` from `.env` (default: the lab server).

The corrector (`src/corrector.py`):

1. Reads the latest JSON report (or a specific one passed as an argument)
2. For each LLM with status `success`, extracts the generated code and the list of violations
3. Builds a structured prompt with the original code + violations + correction instructions
4. Sends it to the chosen correction model (default: `qwen3-coder-30b-a3b-instruct-fp8` on the lab server)
5. Saves the corrected code in `outputs/codes/{llm}_corrected.kt`
6. Re-runs Lint + ATF on the corrected code for comparison

### Lab server configuration

```env
LAB_SERVER_BASE_URL=https://your-lab-server
LAB_SERVER_TOKEN=your_token_here
LAB_SERVER_MODEL=qwen3-coder-30b-a3b-instruct-fp8
```

> The lab server may require a VPN connection to the lab. The corrector must run on the
> host (outside Docker) or through Docker with WSL2 in mirrored networking mode.

---

## Accessibility checks

### Static Lint — custom rules (UAST)

| Check | What it detects |
|-------|-----------------|
| `ComposeIconNullContentDescription` | `Icon()` with `contentDescription = null` in interactive components or as the only semantic cue of an action |
| `ComposeTextFieldMissingLabel` | `TextField`/`OutlinedTextField` without a `label` parameter (static heuristic flagging a missing accessible name at runtime) |

### Dynamic ATF — physical device over ADB

| Check | What it detects |
|-------|-----------------|
| `SpeakableTextPresentCheck` | Focusable views with no content TalkBack can read |
| `TouchTargetSizeCheck` | Interactive elements with a touch area smaller than 48 × 48 dp |
| `TextContrastCheck` | Insufficient text contrast (WCAG AA ratio: 4.5:1) measured with `UiAutomation.takeScreenshot()` on the central region of the screen |

ATF scrolls the screen (3 upward and 3 downward sweeps) to capture elements
outside the initial viewport.

### Dark mode

```bash
adb shell cmd uimode night yes   # turns dark mode on
adb shell cmd uimode night no    # back to light mode
```

---

## Supported LLMs

| LLM | Default model | Type |
|-----|---------------|------|
| Google Gemini | `gemini-2.5-pro` | API — free tier |
| OpenAI ChatGPT | `gpt-4.5` | API — paid |
| Anthropic Claude | `claude-sonnet-4-6` | API — paid |
| Groq | `llama-3.3-70b-versatile` | API — free tier |
| DeepSeek | `deepseek-coder` | API — paid |
| xAI Grok | `grok-3-mini` | API — paid |
| Ollama | configurable | Local (offline) |

Gemini, Groq and Ollama are free to use. Every model can be changed on the
Analysis page, and keys can be typed there or kept in `.env`.

---

## Requirements

- [Docker](https://www.docker.com/) and Docker Compose
- An API key for at least one LLM (Google Gemini is free at [aistudio.google.com](https://aistudio.google.com)), or Ollama
- *(Optional)* Ollama installed locally with a model configured
- *(Optional)* API keys for OpenAI, Anthropic, Groq, DeepSeek or xAI
- *(Optional, for real ATF)* An Android device with **USB debugging** enabled, connected to the host computer
- *(Optional, for Correction with the lab server)* access to the lab server (VPN if needed) + an Open WebUI session token

> Without an Android device, the static Lint stages keep working normally.
> ATF is skipped with a warning in the report.

---

## Setup

### 1. Clone the repository

```bash
git clone <anonymized-repository-url> accessibility-llm-pipeline
cd accessibility-llm-pipeline
```

### 2. Set the environment variables

```bash
cp .env.example .env
```

Edit `.env` with your keys (all optional — they can also be typed on the pages):

```env
GEMINI_API_KEY=your_key_here

# Optional — each LLM is enabled automatically when its key is present
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
DEEPSEEK_API_KEY=
XAI_API_KEY=

# Ollama (local — no key needed)
OLLAMA_MODEL=llama3.2

# ATF on a real device
EMULATOR_HOST=host.docker.internal
ADB_KEYS_DIR=C:/Users/your_user/.android

# Correction model (default for corrector.py)
CORRECTOR_PROVIDER=labserver

# Correction with a lab server running Open WebUI (may require VPN)
LAB_SERVER_BASE_URL=
LAB_SERVER_TOKEN=
LAB_SERVER_MODEL=qwen3-coder-30b-a3b-instruct-fp8
```

### 3. Start the environment

```bash
docker-compose up --build
```

On the first run Docker downloads the Android SDK and the Gradle dependencies.
Later builds use a persistent cache and are much faster.

### 4. Open the web interface

```
http://localhost:8000
```

---

## Project structure

```
accessibility-llm-pipeline/
├── src/
│   ├── pipeline.py              # Main orchestration of the 5 stages
│   ├── corrector.py             # Assisted correction with a local or online LLM
│   ├── llm_client.py            # Integration with the 7 LLMs (API + local Ollama)
│   ├── code_extractor.py        # Extracts Kotlin blocks from LLM answers
│   ├── autocorrect.py           # 55 fix rules + 128 regression tests
│   ├── report_generator.py      # Consolidates Lint and ATF results into JSON
│   ├── web_server.py            # FastAPI server with SSE streaming
│   └── templates/
│       ├── landing.html         # Home page
│       ├── index.html           # Analysis interface
│       ├── correcao.html        # Correction interface
│       ├── docs.html            # Documentation
│       └── teste.html           # CHASE 2027 page
├── lint-rules/                  # Gradle module with custom UAST rules
├── templates/
│   └── android-project/         # Base Jetpack Compose project template
├── article/
│   └── main.tex                 # Research paper
├── outputs/                     # APKs, reports and JSONs (created at runtime)
│   ├── reports/                 # JSON reports per run
│   └── codes/                   # Generated and corrected code per LLM
├── dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Research context

This pipeline was used to evaluate LLMs at generating accessible Android
interfaces in Jetpack Compose, covering several screen types in light and dark
mode. The results are described in the paper at `article/main.tex`.

---

## Work in progress

### AI-assisted correction

The correction module (`/correcao`) is under active development:

- [x] `/api/correct` endpoint with SSE streaming
- [x] Web interface with report and violation views
- [x] Choice of correction model: lab server (Open WebUI), Ollama, OpenAI-compatible servers and online APIs
- [ ] Automatic re-analysis after correction
- [ ] Visual diff between original and corrected code

### Extension to real apps (F-Droid)

We plan to extend the correction module to accept screens from real open-source
apps as input, in addition to LLM-generated code. This will let us compare
accessibility violations in synthetic code (LLM-generated) vs. real code
(human-written), and evaluate how well correction works in both settings.

**Candidate app dataset:**

| App | Repository | Category |
|-----|------------|----------|
| Seal | `JunkFood02/Seal` | Media |
| Breezy Weather | `breezy-weather/breezy-weather` | Weather |
| Musify | `gokadzev/Musify` | Music |
| Fossify Notes | `FossifyOrg/Notes` | Productivity |

The pipeline will extract individual screens (screen-like `@Composable`s) from
each repository and process them with the same Lint + Correction flow already
implemented, without compiling the full app.

## Authorship

Omitted for double-blind review.

## License

Academic, non-commercial license. See [`LICENSE`](LICENSE).
