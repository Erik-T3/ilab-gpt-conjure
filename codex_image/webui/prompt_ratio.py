from __future__ import annotations

import re
from typing import Any


_RATIO_RE = re.compile(r"^\s*([1-9]\d{0,2})\s*:\s*([1-9]\d{0,2})\s*$")


def normalize_prompt_ratio(value: Any) -> str:
    match = _RATIO_RE.match(str(value or ""))
    if not match:
        return ""
    return f"{int(match.group(1))}:{int(match.group(2))}"


def ratio_prompt_instruction(value: Any) -> str:
    ratio = normalize_prompt_ratio(value)
    return f"将宽高比设为 {ratio}" if ratio else ""


def append_ratio_prompt_instruction(prompt: str, ratio: Any) -> str:
    instruction = ratio_prompt_instruction(ratio)
    if not instruction:
        return prompt
    prompt_text = str(prompt or "").rstrip()
    if instruction in prompt_text:
        return prompt_text
    if not prompt_text:
        return instruction
    return f"{prompt_text}\n\n{instruction}"
