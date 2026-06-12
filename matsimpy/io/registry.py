"""
Format handler registry for table-driven IO dispatch.

Provides FormatHandler (describing a supported file format) and
FormatRegistry (managing all registered handlers). Replaces the
if/elif dispatch chain in io/core.py with table-driven lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class FormatHandler:
    """Describes a supported file format and its read/write functions.

    Each format module (vasp.py, cif.py, etc.) creates one or more
    FormatHandler instances and registers them with the global
    FormatRegistry at import time.

    Attributes:
        name: Unique handler name, e.g. "vasp-poscar", "cif", "xyz".
        extensions: File extensions this handler claims, e.g. (".vasp",).
        aliases: Alternate names users can use, e.g. ("poscar", "vasp").
        description: Human-readable one-liner.
        reader: Callable for reading; None if write-only.
        writer: Callable for writing; None if read-only.
        supports_crystal: True if this format can represent periodic structures.
        supports_molecule: True if this format can represent molecules.
        strict_by_default: True = raise FormatError on malformed input.
        options_schema: JSON Schema dict for format-specific **kwargs.
    """

    name: str
    extensions: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    description: str = ""
    reader: Callable | None = None
    writer: Callable | None = None
    supports_crystal: bool = False
    supports_molecule: bool = False
    strict_by_default: bool = True
    options_schema: dict | None = None


class FormatRegistry:
    """Registry of format handlers, triple-indexed by name, extension, alias.

    Usage::

        from matsimpy.io.registry import registry, FormatHandler

        handler = FormatHandler(
            name="vasp-poscar",
            extensions=(".vasp",),
            aliases=("poscar", "vasp"),
            description="VASP POSCAR format",
            reader=read_POSCAR,
            writer=write_POSCAR,
            supports_crystal=True,
        )
        registry.register(handler)

    Plugin entry point: ``'matsimpy.io_formats'``.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, FormatHandler] = {}
        self._by_extension: dict[str, FormatHandler] = {}
        self._by_alias: dict[str, FormatHandler] = {}

    # ------------------------------------------------------------------
    def register(self, handler: FormatHandler) -> None:
        """Register *handler* under its name, extensions, and aliases.

        Raises:
            ValueError: If an extension or alias is already registered
                        to a different handler.
        """
        # Primary name
        if handler.name in self._by_name:
            existing = self._by_name[handler.name]
            if existing is not handler and existing.name != handler.name:
                raise ValueError(
                    f"Format handler name {handler.name!r} is already registered"
                )
        self._by_name[handler.name] = handler

        # Extensions
        for ext in handler.extensions:
            ext_lower = ext.lower()
            if ext_lower in self._by_extension:
                existing = self._by_extension[ext_lower]
                if existing is not handler and existing.name != handler.name:
                    raise ValueError(
                        f"Extension {ext_lower!r} already registered by "
                        f"{existing.name!r}"
                    )
            self._by_extension[ext_lower] = handler

        # Aliases
        for alias in handler.aliases:
            alias_lower = alias.lower()
            if alias_lower in self._by_alias:
                existing = self._by_alias[alias_lower]
                if existing is not handler and existing.name != handler.name:
                    raise ValueError(
                        f"Alias {alias_lower!r} already registered by "
                        f"{existing.name!r}"
                    )
            self._by_alias[alias_lower] = handler

    # ------------------------------------------------------------------
    def detect(self, filename: str) -> FormatHandler | None:
        """Return the handler matching *filename* extension, or None."""
        ext = Path(filename).suffix.lower()
        return self._by_extension.get(ext)

    # ------------------------------------------------------------------
    def get(self, name_or_alias: str) -> FormatHandler | None:
        """Look up handler by name or alias (case-insensitive)."""
        key = name_or_alias.lower()
        return self._by_alias.get(key) or self._by_name.get(key)

    # ------------------------------------------------------------------
    def read(
        self,
        filename: str,
        format: str | None = None,
        **kwargs,
    ):
        """Read a structure from *filename*.

        Args:
            filename: Path to the file.
            format: Optional format name/alias to bypass detection.
            **kwargs: Passed to the format-specific reader.

        Returns:
            Crystal or Molecule.

        Raises:
            FileNotFoundError: If *filename* does not exist.
            ValueError: If format cannot be detected.
            FormatError: If the file is malformed and strict mode is on.
            StructureTypeError: If the result type is incompatible.
        """
        filepath = Path(filename)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        if format is not None:
            handler = self.get(format)
            if handler is None:
                raise ValueError(f"Unknown format: {format!r}")
        else:
            handler = self.detect(filename)
            if handler is None:
                raise ValueError(
                    f"Could not detect file format from extension: {filename}. "
                    f"Specify format explicitly."
                )

        if handler.reader is None:
            raise ValueError(
                f"Format {handler.name!r} does not support reading."
            )

        return handler.reader(filename, **kwargs)

    # ------------------------------------------------------------------
    def write(
        self,
        structure,
        filename: str,
        format: str | None = None,
        **kwargs,
    ) -> None:
        """Write *structure* to *filename*.

        Args:
            structure: Crystal or Molecule to write.
            filename: Output path.
            format: Optional format name/alias to bypass detection.
            **kwargs: Passed to the format-specific writer.

        Raises:
            ValueError: If format cannot be detected.
            StructureTypeError: If structure type is incompatible.
        """
        from ..core import Crystal, Molecule
        from ..exceptions import StructureTypeError

        if format is not None:
            handler = self.get(format)
            if handler is None:
                raise ValueError(f"Unknown format: {format!r}")
        else:
            handler = self.detect(filename)
            if handler is None:
                raise ValueError(
                    f"Could not detect file format from extension: {filename}. "
                    f"Specify format explicitly."
                )

        if handler.writer is None:
            raise ValueError(
                f"Format {handler.name!r} does not support writing."
            )

        # Type compatibility check
        if isinstance(structure, Crystal) and not handler.supports_crystal:
            raise StructureTypeError(
                f"Format {handler.name!r} does not support Crystal structures."
            )
        if isinstance(structure, Molecule) and not handler.supports_molecule:
            raise StructureTypeError(
                f"Format {handler.name!r} does not support Molecule structures."
            )

        handler.writer(structure, filename, **kwargs)

    # ------------------------------------------------------------------
    def list_readers(self) -> list[str]:
        """Return sorted list of handler names that support reading."""
        return sorted(
            h.name for h in self._by_name.values() if h.reader is not None
        )

    def list_writers(self) -> list[str]:
        """Return sorted list of handler names that support writing."""
        return sorted(
            h.name for h in self._by_name.values() if h.writer is not None
        )


# Module-level singleton
registry = FormatRegistry()


__all__ = ["FormatHandler", "FormatRegistry", "registry"]
