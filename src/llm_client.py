import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from google import genai
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        # Gemini (opcional, requer chave)
        self.gemini_key    = os.getenv("GEMINI_API_KEY")
        self.gemini_client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None

        # Models — the evaluation defaults; the analysis page can override them per run
        self.gemini_model    = os.getenv("GEMINI_MODEL")    or "gemini-2.5-pro"
        self.groq_model      = os.getenv("GROQ_MODEL")      or "llama-3.3-70b-versatile"
        self.deepseek_model  = os.getenv("DEEPSEEK_MODEL")  or "deepseek-coder"
        self.xai_model       = os.getenv("XAI_MODEL")       or "grok-3-mini"
        self.openai_model    = os.getenv("OPENAI_MODEL")    or "gpt-4.5"
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-4-6"

        # Groq, OpenAI e Anthropic (opcionais, requerem chave)
        self.groq_key      = os.getenv("GROQ_API_KEY")
        self.deepseek_key  = os.getenv("DEEPSEEK_API_KEY")
        self.xai_key       = os.getenv("XAI_API_KEY")
        self.openai_key    = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        self.groq = AsyncOpenAI(
            api_key=self.groq_key,
            base_url="https://api.groq.com/openai/v1",
        ) if self.groq_key else None
        self.deepseek = AsyncOpenAI(
            api_key=self.deepseek_key,
            base_url="https://api.deepseek.com/v1",
        ) if self.deepseek_key else None
        self.xai = AsyncOpenAI(
            api_key=self.xai_key,
            base_url="https://api.x.ai/v1",
        ) if self.xai_key else None
        self.openai    = AsyncOpenAI(api_key=self.openai_key) if self.openai_key else None
        self.anthropic = AsyncAnthropic(api_key=self.anthropic_key) if self.anthropic_key else None

        # Ollama (local) — connects through its OpenAI-compatible API
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        self.ollama_model    = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.ollama = AsyncOpenAI(
            base_url=f"{self.ollama_base_url}/v1",
            api_key="ollama",          # required by the SDK, not checked by Ollama
        )

        self._print_enabled_llms()

    def _print_enabled_llms(self):
        print("\n" + "=" * 50)
        print("LLMs enabled:")
        print("=" * 50)
        if self.gemini_client:
            print(f"[enabled]  Gemini ({self.gemini_model})")
        else:
            print("[disabled] Gemini (no API key)")
        if self.groq:
            print(f"[enabled]  Groq ({self.groq_model})")
        else:
            print("[disabled] Groq (no API key)")
        if self.deepseek:
            print(f"[enabled]  DeepSeek ({self.deepseek_model})")
        else:
            print("[disabled] DeepSeek (no API key)")
        if self.xai:
            print(f"[enabled]  xAI Grok ({self.xai_model})")
        else:
            print("[disabled] xAI Grok (no API key)")
        if self.openai:
            print(f"[enabled]  OpenAI ({self.openai_model})")
        else:
            print("[disabled] OpenAI (no API key)")
        if self.anthropic:
            print(f"[enabled]  Anthropic Claude ({self.anthropic_model})")
        else:
            print("[disabled] Anthropic Claude (no API key)")
        print(f"[local]    Ollama — model: {self.ollama_model} @ {self.ollama_base_url}")
        print("=" * 50 + "\n")
    
    async def generate_gemini(self, prompt: str) -> str:
        """Gemini — retries up to 3x on transient 503/UNAVAILABLE errors."""
        if not self.gemini_client:
            return "SKIPPED"
        loop = asyncio.get_running_loop()
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt == 0:
                print(f"Calling Gemini ({self.gemini_model})...")
            else:
                print(f"Calling Gemini (retry {attempt}/{max_attempts - 1})...")
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=prompt
                    )
                )
                return response.text
            except Exception as e:
                err = str(e)
                is_transient = any(w in err for w in ("503", "UNAVAILABLE", "529", "overloaded"))
                if is_transient and attempt < max_attempts - 1:
                    wait = 5 * (2 ** attempt)   # 5s, 10s
                    print(f"  Gemini unavailable — retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise
    
    async def generate_groq(self, prompt: str) -> str:
        """Groq — free API, llama-3.3-70b-versatile model by default (fast)."""
        if not self.groq:
            return "SKIPPED"
        print(f"Calling Groq ({self.groq_model})...")
        response = await self.groq.chat.completions.create(
            model=self.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
        )
        return response.choices[0].message.content

    async def generate_deepseek(self, prompt: str) -> str:
        """DeepSeek Coder — specialized in code."""
        if not self.deepseek:
            return "SKIPPED"
        print(f"Calling DeepSeek ({self.deepseek_model})...")
        response = await self.deepseek.chat.completions.create(
            model=self.deepseek_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
        )
        return response.choices[0].message.content

    async def generate_xai(self, prompt: str) -> str:
        """xAI Grok — grok-3-mini by default ($25 free credits on sign-up)."""
        if not self.xai:
            return "SKIPPED"
        print(f"Calling xAI Grok ({self.xai_model})...")
        response = await self.xai.chat.completions.create(
            model=self.xai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
        )
        return response.choices[0].message.content

    async def generate_openai(self, prompt: str) -> str:
        """OpenAI ChatGPT 5.5 — used in the WebMedia 2026 evaluation."""
        if not self.openai:
            return "SKIPPED"
        print(f"Calling OpenAI ({self.openai_model})...")
        response = await self.openai.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    async def generate_anthropic(self, prompt: str) -> str:
        """Anthropic Claude Sonnet 4.6 — used in the WebMedia 2026 evaluation."""
        if not self.anthropic:
            return "SKIPPED"

        print(f"Calling Anthropic Claude ({self.anthropic_model})...")
        response = await self.anthropic.messages.create(
            model=self.anthropic_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def generate_ollama(self, prompt: str) -> str:
        """Ollama — local LLM (OpenAI-compatible API)"""
        print(f"Calling Ollama ({self.ollama_model})...")
        try:
            response = await self.ollama.chat.completions.create(
                model=self.ollama_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except Exception as e:
            msg = str(e).lower()
            if any(w in msg for w in ("connection", "refused", "connect", "unreachable")):
                print(f"[SKIP] Ollama unavailable ({self.ollama_base_url})")
                return "SKIPPED"
            raise

    async def generate_all(self, prompt: str) -> Dict[str, str]:
        """Generates code with every enabled LLM in parallel."""
        enabled = set(os.getenv("ENABLED_LLMS", "").split(",")) - {""}
        candidates = {
            "gemini":    self.generate_gemini,
            "groq":      self.generate_groq,
            "deepseek":  self.generate_deepseek,
            "xai":       self.generate_xai,
            "openai":    self.generate_openai,
            "anthropic": self.generate_anthropic,
            "ollama":    self.generate_ollama,
        }
        tasks = {
            name: fn(prompt)
            for name, fn in candidates.items()
            if not enabled or name in enabled
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        output = dict(zip(tasks.keys(), results))
        return {k: v for k, v in output.items() if v != "SKIPPED"}

    async def generate_all_timed(self, prompt: str) -> Dict[str, tuple]:
        """Generates code in parallel, returning (response, time_s) per LLM.

        Returns: {llm_name: (response_or_Exception, elapsed_seconds)}
        Disabled LLMs (SKIPPED) are left out of the result.
        """
        async def _timed(name: str, coro) -> tuple:
            t = time.perf_counter()
            try:
                result = await coro
                return name, result, time.perf_counter() - t
            except Exception as exc:
                return name, exc, time.perf_counter() - t

        # Respect ENABLED_LLMS env var (set by the web UI LLM selector)
        enabled = set(os.getenv("ENABLED_LLMS", "").split(",")) - {""}

        candidates = {
            "gemini":    self.generate_gemini,
            "groq":      self.generate_groq,
            "deepseek":  self.generate_deepseek,
            "xai":       self.generate_xai,
            "openai":    self.generate_openai,
            "anthropic": self.generate_anthropic,
            "ollama":    self.generate_ollama,
        }
        tasks = [
            _timed(name, fn(prompt))
            for name, fn in candidates.items()
            if not enabled or name in enabled
        ]
        raw = await asyncio.gather(*tasks)
        return {
            name: (resp, elapsed)
            for name, resp, elapsed in raw
            if resp != "SKIPPED"
        }
    
    async def generate_one(self, llm_name: str, prompt: str) -> str:
        """Call a single LLM by name. Raises ValueError if unknown or disabled."""
        generators: dict = {
            "gemini":    self.generate_gemini,
            "groq":      self.generate_groq,
            "deepseek":  self.generate_deepseek,
            "xai":       self.generate_xai,
            "openai":    self.generate_openai,
            "anthropic": self.generate_anthropic,
            "ollama":    self.generate_ollama,
        }
        fn = generators.get(llm_name)
        if fn is None:
            raise ValueError(f"Unknown LLM: {llm_name!r}")
        result = await fn(prompt)
        if result == "SKIPPED":
            raise ValueError(f"{llm_name} is not enabled")
        return result

    def save_codes(self, results: dict, output_dir: str = "/app/outputs/codes"):
        """Saves the generated code"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for llm, code in results.items():
            if isinstance(code, Exception):
                print(f"❌ Error in {llm}: {code}")
                continue
            
            file_path = output_path / f"{llm}_output.kt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"✅ Code saved: {file_path}")


if __name__ == "__main__":
    client = LLMClient()
    
    prompt = """Generate a complete Android Activity in Kotlin that:
    - Displays 'Hello World' in a TextView
    - Uses ViewBinding
    - Include all necessary imports
    - Only return the MainActivity.kt code, nothing else"""
    
    print("🚀 Generating code with LLMs...\n")
    results = asyncio.run(client.generate_all(prompt))
    
    print("\n" + "="*50)
    print("📝 RESULTADOS")
    print("="*50)
    
    for llm, code in results.items():
        if isinstance(code, Exception):
            continue
        print(f"\n{'─'*50}")
        print(f"  {llm.upper()}")
        print(f"{'─'*50}")
        print(code[:300] + "..." if len(code) > 300 else code)
    
    client.save_codes(results)
    print("\n✅ Pipeline finished!")