"""Test the LangToolsParams class."""

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
