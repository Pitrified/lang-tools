"""Test the LangToolsParams class."""

import subprocess
import sys

from lang_tools.params.lang_tools_params import LangToolsParams
from lang_tools.params.lang_tools_params import get_lang_tools_params
from lang_tools.params.lang_tools_paths import LangToolsPaths
from lang_tools.params.sample_params import SampleParams


def test_lang_tools_params_singleton() -> None:
    """Test that LangToolsParams is a singleton."""
    params1 = LangToolsParams()
    params2 = LangToolsParams()
    assert params1 is params2
    assert get_lang_tools_params() is params1


def test_lang_tools_params_init() -> None:
    """Test initialization of LangToolsParams."""
    params = LangToolsParams()
    assert isinstance(params.paths, LangToolsPaths)
    assert isinstance(params.sample, SampleParams)


def test_lang_tools_params_str() -> None:
    """Test string representation."""
    params = LangToolsParams()
    s = str(params)
    assert "LangToolsParams:" in s
    assert "LangToolsPaths:" in s
    assert "SampleParams:" in s


def test_lexicon_loads_without_the_webapp_extra() -> None:
    """The params and the lexicon load with fastapi-tools absent.

    A fresh interpreter, since this one has already imported fastapi-tools;
    a ``None`` entry in `sys.modules` makes its import fail.
    """
    code = (
        "import sys\n"
        "sys.modules['fastapi_tools'] = None\n"
        "from lang_tools.lexicon import get_store\n"
        "from lang_tools.params.lang_tools_params import get_lang_tools_params\n"
        "print(get_lang_tools_params().paths.data_fol)\n"
    )
    result = subprocess.run(  # noqa: S603 - a fixed command, no user input
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_webapp_params_load_on_first_use() -> None:
    params = LangToolsParams()
    assert params.webapp is params.webapp
