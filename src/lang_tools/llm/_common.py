"""Helpers shared by the per-chain factories.

Each `build_*_chain` factory loads a versioned Jinja template from
``base_prompt_fol / <prompt_name> / vN.jinja`` via `llm-core`'s `PromptLoader`
and wires it into a `StructuredLLMChain`. `default_prompts_fol` returns the
in-package prompt directory (used when callers omit the explicit folder).
"""

from __future__ import annotations

from pathlib import Path

from llm_core.prompts.prompt_loader import PromptLoader
from llm_core.prompts.prompt_loader import PromptLoaderConfig

import lang_tools


def default_prompts_fol() -> Path:
    """Return the in-package ``prompts/`` directory.

    The folder ships alongside the source tree so that the chains work without
    requiring callers to copy templates into their own project.
    """
    return Path(lang_tools.__file__).parent / "prompts"


def load_prompt(
    prompt_name: str,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> str:
    """Load a versioned Jinja prompt by name.

    Args:
        prompt_name: Subfolder name under `base_prompt_fol`.
        base_prompt_fol: Root prompts folder; defaults to `default_prompts_fol()`.
        version: Explicit version (``"1"``) or ``"auto"`` for the highest.

    Returns:
        The template string.
    """
    base_fol = base_prompt_fol if base_prompt_fol is not None else default_prompts_fol()
    config = PromptLoaderConfig(
        base_prompt_fol=base_fol,
        prompt_name=prompt_name,
        version=version,
    )
    return PromptLoader(config).load_prompt()
