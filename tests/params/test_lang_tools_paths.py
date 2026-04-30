"""Test the lang_tools paths."""

from lang_tools.params.lang_tools_params import get_lang_tools_paths


def test_lang_tools_paths() -> None:
    """Test the lang_tools paths."""
    lang_tools_paths = get_lang_tools_paths()
    assert lang_tools_paths.src_fol.name == "lang_tools"
    assert lang_tools_paths.root_fol.name == "lang-tools"
    assert lang_tools_paths.data_fol.name == "data"
