"""OpenBabel-backed atom typing — protonation, aromaticity, donor/acceptor.

Provides a fallback-enhanced atom typer that uses OpenBabel for explicit
hydrogen addition, SMARTS-based aromaticity perception, and H-bond
donor/acceptor detection.  When OpenBabel is unavailable or fails on a
particular structure, falls back to the heuristic typing in
``physical/interactions.py``.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from psf_reasoner.component_status import ComponentStatus, component_registry

logger = logging.getLogger(__name__)

_import_attempted = False


class OpenBabelAtomTyper:
    """Wrap OpenBabel for protonation, aromaticity, and donor/acceptor detection.

    Usage::

        typer = OpenBabelAtomTyper()
        protonated = typer.add_hydrogens(Path("structure.pdb"))
        # protonated is a Path to a PDB file with explicit hydrogens
        # aromatic, donor, acceptor info available via atom properties
    """

    def __init__(self) -> None:
        self._available = self._check_openbabel()

    @staticmethod
    def _check_openbabel() -> bool:
        global _import_attempted
        try:
            from openbabel import openbabel  # noqa: F401

            available = True
        except ImportError as exc:
            available = False
            if not _import_attempted:
                logger.debug("OpenBabel atom typing unavailable, using heuristics: %s", exc)
                component_registry.set(
                    ComponentStatus(
                        "openbabel",
                        enabled=True,
                        available=False,
                        implementation="heuristic_typing",
                        detail="openbabel package not installed",
                    )
                )
                _import_attempted = True
        if available and not _import_attempted:
            component_registry.set(
                ComponentStatus(
                    "openbabel",
                    enabled=True,
                    available=True,
                    implementation="openbabel",
                )
            )
            _import_attempted = True
        return available

    @property
    def available(self) -> bool:
        return self._available

    def add_hydrogens(self, pdb_path: Path, ph: float = 7.4) -> Path:
        """Add explicit hydrogen atoms at a given pH.

        Returns a path to a new PDB file with hydrogens added.
        Falls back to the original path if OpenBabel fails.
        """
        if not self._available:
            return pdb_path

        try:
            from openbabel import openbabel as ob

            conv = ob.OBConversion()
            conv.SetInAndOutFormats("pdb", "pdb")

            mol = ob.OBMol()
            conv.ReadFile(mol, str(pdb_path))

            mol.AddHydrogens(False, ph)  # False = add polar H only

            output = Path(tempfile.mktemp(suffix=".pdb"))
            conv.WriteFile(mol, str(output))
            return output
        except Exception as exc:
            logger.debug("OpenBabel add_hydrogens failed, returning input PDB: %s", exc)
            return pdb_path

    def perceive_aromaticity(self, pdb_path: Path) -> dict[str, bool]:
        """Return a dict mapping atom labels to aromaticity status.

        Atom labels are formatted as ``"chain:resname:resnum:atomname"``.
        Falls back to an empty dict if OpenBabel fails.
        """
        if not self._available:
            return {}

        try:
            from openbabel import openbabel as ob

            conv = ob.OBConversion()
            conv.SetInFormat("pdb")
            mol = ob.OBMol()
            conv.ReadFile(mol, str(pdb_path))

            result: dict[str, bool] = {}
            for atom in ob.OBMolAtomIter(mol):
                residue = atom.GetResidue()
                label = f"{residue.GetChain()}:{residue.GetName()}:{residue.GetNum()}:{atom.GetName()}"
                result[label] = atom.IsAromatic()
            return result
        except Exception as exc:
            logger.debug("OpenBabel aromaticity perception failed, using heuristic fallback: %s", exc)
            return {}

    def get_donors_acceptors(self, pdb_path: Path) -> tuple[set[str], set[str]]:
        """Return (donor_atom_labels, acceptor_atom_labels) from OpenBabel.

        Uses OpenBabel's built-in H-bond donor/acceptor SMARTS patterns.
        """
        if not self._available:
            return set(), set()

        try:
            from openbabel import openbabel as ob

            conv = ob.OBConversion()
            conv.SetInFormat("pdb")

            # Need explicit hydrogens for donor detection
            mol = ob.OBMol()
            conv.ReadFile(mol, str(pdb_path))
            mol.AddHydrogens(False, 7.4)

            donors: set[str] = set()
            acceptors: set[str] = set()

            for atom in ob.OBMolAtomIter(mol):
                residue = atom.GetResidue()
                label = f"{residue.GetChain()}:{residue.GetName()}:{residue.GetNum()}:{atom.GetName()}"
                if atom.IsHbondDonor():
                    donors.add(label)
                if atom.IsHbondAcceptor():
                    acceptors.add(label)

            return donors, acceptors
        except Exception as exc:
            logger.debug("OpenBabel donor/acceptor detection failed, using heuristic fallback: %s", exc)
            return set(), set()
