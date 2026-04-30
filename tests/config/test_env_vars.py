"""Test that the environment variables are available."""

import os


def test_env_vars() -> None:
    """The environment var LANG_TOOLS_SAMPLE_ENV_VAR is available."""
    assert "LANG_TOOLS_SAMPLE_ENV_VAR" in os.environ
    assert os.environ["LANG_TOOLS_SAMPLE_ENV_VAR"] == "sample"
