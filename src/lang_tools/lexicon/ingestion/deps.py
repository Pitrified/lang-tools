"""One optional-dependency error for the build and staging paths.

The ingestion and staging paths pull in packages the runtime never needs (``wn``
for OMW, ``wordfreq`` for token frequency, ``xlrd`` for the Kelly ``.xls`` lists),
so each is an optional extra imported lazily at its call site. Before phase 6
each site carried its own `ImportError` subclass, one of which hardcoded both the
package and the extra into its message; when `wordfreq` moved from the ``enrich``
extra to ``ingest`` that message would have started naming the wrong extra.

`OptionalDependencyMissingError` carries the pair instead, so one class serves
every site and the message always names the extra that actually ships the package.

Each call site keeps its own literal ``import`` statement rather than routing
through a shared ``import_module`` helper: a real import gives the type checker a
typed module (`wn` in particular ships stubs), which an `importlib` shim returning
`ModuleType` would erase. The four-line try/except is the price of that, and it is
the part worth repeating.

The runtime-layer `codec.StoreDependencyMissingError` (``pyarrow`` / ``duckdb``)
is deliberately **not** folded in here: it guards the store's load path, not the
build, and this module lives under `ingestion`.
"""

from __future__ import annotations


class OptionalDependencyMissingError(ImportError):
    """Raised when a build or staging path needs an extra that is not installed.

    Attributes:
        package: The importable name that was missing.
        extra: The project extra that provides it.
    """

    def __init__(self, package: str, extra: str) -> None:
        """Initialize with the missing package and the extra that ships it.

        Args:
            package: The importable name that failed to import.
            extra: The optional-dependency extra providing `package`.
        """
        super().__init__(
            f"This path needs the '{extra}' extra ({package}). Install it with "
            f"`uv sync --extra {extra}`.",
        )
        self.package = package
        self.extra = extra
