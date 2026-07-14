# Interaction Engine Validation

> **Status**: Infrastructure ready. PLIP comparison pending Python ≤3.12 environment.

## Methodology

PSF-Reasoner's interaction engine is compared against PLIP (Protein-Ligand
Interaction Profiler, https://github.com/pharmai/plip) on experimentally
determined HIV-1 protease—inhibitor complex structures.

**Reference tool**: PLIP (version TBD)
**Structures**: HIV-1 protease WT (1SDT) + mutants (1SDU, 1SDV) + MK1 (indinavir)
**Comparison date**: TBD

## Interaction Type Mapping

| PLIP Type | PSF-Reasoner Type | Notes |
|-----------|-------------------|-------|
| `hbonds_pdon` + `hbonds_ldon` | `hydrogen_bond` | Direct comparison |
| `hydrophobic_contacts` | `hydrophobic_contact` | Direct comparison |
| `saltbridge_lneg` + `saltbridge_pneg` | `salt_bridge` | Direct comparison |
| `pistacking` | `pi_interaction` | PSF uses single category |
| `pication_laro` + `pication_paro` | `pi_interaction` | Combined PLIP types → single PSF type |
| `water_bridges` | `water_bridge` | Direct comparison |
| `halogen_bonds` | N/A | PLIP-only |

## Known Systematic Differences

### Hydrogen Bonds
- **PSF**: Estimated H-positions from donor geometry (1/2/≥3 base atoms). 110°
  angle threshold with 90° heavy-atom proxy fallback when no explicit H.
- **PLIP**: Uses OpenBabel for protonation. Stricter angle criteria.
- **Expected**: PSF may over-count H-bonds in structures without explicit
  hydrogens. PLIP may be more conservative.

### Hydrophobic Contacts
- **PSF**: Residue-template atom typing (C/S atoms) with 4.0 Å cutoff.
- **PLIP**: Distance-based with OpenBabel atom typing.
- **Expected**: High agreement. Both use similar distance-based approaches.

### Salt Bridges
- **PSF**: Charged-residue atom tables (LYS/ARG/HIS positive, ASP/GLU
  negative) with 4.0 Å cutoff.
- **PLIP**: Distance + angle criteria.
- **Expected**: Moderate agreement.

### Pi Interactions
- **PSF**: Single category based on aromatic residue atom tables (PHE/TYR/
  TRP/HIS) and centroid distance (5.5 Å). Name-based aromaticity.
- **PLIP**: Distinguishes pi-stacking (face-to-face, edge-to-face) from
  pi-cation. Uses SMARTS-based ring perception via OpenBabel.
- **Expected**: PSF name-based aromaticity is less accurate than PLIP's
  SMARTS-based detection. PSF may miss some pi interactions and
  misclassify others.

### Water Bridges
- **PSF**: Distance-only partner selection (water O within 3.5 Å of both
  protein and ligand donor/acceptor atoms).
- **PLIP**: Hydrogen-bond geometry on both sides of the water.
- **Expected**: PSF may over-count water bridges.

## Results

**Comparison date**: 2026-07-14
**PLIP version**: 3.0.0
**Structure**: 1SDT (HIV-1 protease WT + indinavir/MK1, 1.30 Å)

### 1SDT (WT + MK1)

| Interaction Type | PSF Count | PLIP Count | Match | Notes |
|-----------------|-----------|------------|-------|-------|
| hydrogen_bond | 2 | 5 (2 pdon + 3 ldon) | No | PSF more conservative: stricter angle criteria + estimated H positions |
| hydrophobic_contact | 41 | 12 | No | PSF counts all C/S atoms; PLIP only sp3 C with C/H neighbors |
| salt_bridge | 0 | 2 (1 lneg + 1 pneg) | No | PSF uses 4.0A cutoff vs PLIP 5.5A; PSF charge typing may be incomplete |
| pi_interaction | 0 | 0 | Yes | Both agree — indinavir (MK1) has no aromatic rings that trigger detection |
| water_bridge | 7 | 5 | No | PSF over-counts as expected from distance-only method |

### Agreement Summary

| Interaction Type | Agreement | Analysis |
|-----------------|-----------|----------|
| hydrogen_bond | Partial | PSF is ~40% of PLIP. Conservative — may miss real H-bonds. Consider relaxing angle threshold or improving H-position estimation. |
| hydrophobic_contact | Low | PSF over-counts ~3.4x. PLIP definition is stricter (sp3 C only). Consider filtering by carbon hybridization. |
| salt_bridge | Missing | PSF completely misses. Root cause: 4.0A cutoff too strict. PLIP uses 5.5A. |
| pi_interaction | Full | Both detect 0 for this ligand. |
| water_bridge | Good | PSF 7 vs PLIP 5. Difference expected from distance-only method. |

## Parameter Adjustments

*To be filled after comparison: any cutoff distances, angle thresholds, or
typing rules adjusted based on systematic disagreements with PLIP.*

## Running the Comparison

```bash
# Requires Python ≤3.12 (PLIP depends on OpenBabel)
python3.12 -m venv .venv312
.venv312/bin/pip install plip

# Run comparison
.venv312/bin/python -c "
from psf_reasoner.evaluation.external_validation import compare_interactions
from pathlib import Path

result = compare_interactions(Path('examples/data/1sdt.cif'), 'MK1')
for a in result.by_type:
    print(f'{a.interaction_type}: PSF={a.psf_count} PLIP={a.plip_count} match={a.match}')
"
```

## References

- PLIP: Adasme et al. (2021) "PLIP 2021: expanding the scope of the
  protein–ligand interaction profiler to DNA and RNA." Nucleic Acids Res.
  49(W1):W530–W534. PMID: 33950225
- 1SDT/1SDU/1SDV: Mahalingam et al. (2004) "Crystal structures of HIV
  protease V82A and L90M mutants reveal changes in the indinavir-binding
  site." Eur. J. Biochem. 271:1516–1524. PMID: 15066177
