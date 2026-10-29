"""
The prompt that sends compile errors back to the model that wrote the code.

Shared by the automatic SELF_REPAIR loop (pipeline.py) and the manual repair in Modo Teste
(/api/repair-prompt), so both protocols use exactly the same text.
"""
import re


def build_repair_prompt(original_prompt: str, failed_code: str, errors: str) -> str:
    """Construct a repair prompt from the original task, the failed code, and the compiler errors."""
    # compiler paths point inside the pipeline's container: keep only the file name and position
    errors = re.sub(r'file://\S*/(\w+\.kt)', r'\1', errors)
    return (
        f"{original_prompt}\n\n"
        "---\n"
        "⚠️  The code you generated below failed to compile with these errors:\n\n"
        f"{errors}\n\n"
        "Failed code:\n"
        "```kotlin\n"
        f"{failed_code}\n"
        "```\n\n"
        "Fix ONLY the compilation errors listed above. "
        "Return the complete corrected Kotlin file wrapped in ```kotlin ... ```. "
        "Do not add new features or change the app behaviour."
    )
