"""LangTools project params.

Parameters are actual value of the config.

The class is a singleton, so it can be accessed from anywhere in the code.

There is a parameter regarding the environment type (stage and location), which
is used to load different paths and other parameters based on the environment.
"""

from loguru import logger as lg

from lang_tools.metaclasses.singleton import Singleton
from lang_tools.params.env_type import EnvType
from lang_tools.params.lang_tools_paths import LangToolsPaths
from lang_tools.params.sample_params import SampleParams
from lang_tools.params.webapp import WebappParams


class LangToolsParams(metaclass=Singleton):
    """LangTools project parameters."""

    def __init__(self) -> None:
        """Load the LangTools params."""
        lg.info("Loading LangTools params")
        self.set_env_type()

    def set_env_type(self, env_type: EnvType | None = None) -> None:
        """Set the environment type.

        Args:
            env_type (EnvType | None): The environment type.
                If None, it will be set from the environment variables.
                Defaults to None.
        """
        if env_type is not None:
            self.env_type = env_type
        else:
            self.env_type = EnvType.from_env_var()
        self.load_config()

    def load_config(self) -> None:
        """Load the lang_tools configuration."""
        self.paths = LangToolsPaths(env_type=self.env_type)
        self.sample = SampleParams()
        self.webapp = WebappParams(
            stage=self.env_type.stage,
            location=self.env_type.location,
        )

    def __str__(self) -> str:
        """Return the string representation of the object."""
        s = "LangToolsParams:"
        s += f"\n{self.paths}"
        s += f"\n{self.sample}"
        s += f"\n{self.webapp}"
        return s

    def __repr__(self) -> str:
        """Return the string representation of the object."""
        return str(self)


def get_lang_tools_params() -> LangToolsParams:
    """Get the lang_tools params."""
    return LangToolsParams()


def get_lang_tools_paths() -> LangToolsPaths:
    """Get the lang_tools paths."""
    return get_lang_tools_params().paths


def get_webapp_params() -> WebappParams:
    """Get the webapp params."""
    return get_lang_tools_params().webapp
