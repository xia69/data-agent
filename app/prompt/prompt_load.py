from pathlib import Path


def load_prompt(filename: str) -> str:
    prompts_dir = Path(__file__).parents[2] / "prompts"
    return (prompts_dir / filename).read_text(encoding="utf-8")
