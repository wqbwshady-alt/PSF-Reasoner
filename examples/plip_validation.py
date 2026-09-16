"""Reproduce the HIV-1 protease interaction comparison with PLIP installed.

Run from the repository root with ``python examples/plip_validation.py``.
The output is JSON so the counts and residue-level overlap can be archived.
"""

from __future__ import annotations

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from psf_reasoner.evaluation.external_validation import compare_interactions

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    results = {}
    for pdb_id in ("1sdt", "1sdv", "1sdu"):
        path = ROOT / "examples" / "data" / f"{pdb_id}.cif"
        comparison = compare_interactions(path, "MK1")
        psf_residues = comparison.psf_hydrophobic_residues
        plip_residues = comparison.plip_hydrophobic_residues
        results[pdb_id.upper()] = {
            "structure_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "psf_counts": {item.interaction_type: item.psf_count for item in comparison.by_type},
            "plip_counts": comparison.plip_counts,
            "hydrophobic_residue_precision": comparison.hydrophobic_residue_precision,
            "hydrophobic_residue_recall": comparison.hydrophobic_residue_recall,
            "hydrophobic_residues_both": sorted(psf_residues & plip_residues),
            "hydrophobic_residues_psf_only": sorted(psf_residues - plip_residues),
            "hydrophobic_residues_plip_only": sorted(plip_residues - psf_residues),
        }
    print(json.dumps({"plip_version": version("plip"), "results": results}, indent=2))


if __name__ == "__main__":
    main()
