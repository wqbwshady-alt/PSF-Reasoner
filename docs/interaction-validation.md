# Interaction engine validation against PLIP

## Reproducible comparison (2026-09-15)

PLIP 3.0.1 with OpenBabel 3.2.1 was run on the bundled HIV-1 protease/MK1
complexes. The WT structure is **1SDT**, V82A is **1SDV**, and L90M is
**1SDU**. Run `python examples/plip_validation.py` from the repository root
in a Python 3.12 environment with `pip install -e '.[dev]' plip`; the script
prints raw counts, protein-residue overlap, and SHA-256 checksums as JSON.

| Complex | H-bonds PSF / PLIP | Hydrophobic atom events PSF / PLIP | Salt bridges PSF / PLIP | Water bridges PSF / PLIP | Hydrophobic residue precision / recall |
|---|---:|---:|---:|---:|---:|
| 1SDT WT | 2 / 5 | 33 / 12 | 1 / 2 | 7 / 5 | 11/13 / 11/11 |
| 1SDV V82A | 2 / 4 | 24 / 11 | 1 / 2 | 6 / 5 | 11/12 / 11/11 |
| 1SDU L90M | 2 / 7 | 24 / 13 | 1 / 2 | 7 / 5 | 13/13 / 13/13 |

Both tools reported zero pi interactions in these three complexes. PLIP's
hydrophobic contacts are mostly one reported event per protein residue;
PSF counts each qualifying atom pair. Raw counts therefore have different
units of redundancy. At residue level, PLIP's positives were all found by
PSF in this small set. PSF-only residues were A:ILE84 and B:ILE150 in 1SDT,
A:ILE84 in 1SDV, and none in 1SDU. These are **PLIP-relative** precision
and recall values, not accuracy against an experimental ground truth.

Atom-level inspection found that PSF misses ligand hydroxyl donor H-bonds
from MK1 O2 to B:ASP125 and MK1 O4 to B:ASP129. PLIP adds polar hydrogens
and reports these events; the distributed crystal CIFs have no ligand H.
The PSF ligand bond graph previously discarded explicit hydrogens even when
present, so it could not type hydroxyl oxygen as a donor. That path is now
fixed. Inferring an OH donor from a bare C--O distance alone was also tried
but produced extra contacts to A:ASP25 and duplicate carboxylate oxygens;
it was not retained. PSF also has a 3.5 Å donor-acceptor cutoff, while PLIP
reported some donor-acceptor distances above 3.9 Å after protonation.

Salt bridges use different geometry (PSF charged atom pairs; PLIP charge-group
centers). Water bridges likewise use different partner/geometry filters.
PLIP is an independent rule-based comparator, not an experimental truth set.
Its hydrogen addition can be nondeterministic, so the table records one run;
do not use these three related structures to claim broad performance or tune
cutoffs. The next validation should add chemically distinct ligands and
protein families, retain PLIP atom-level output, and use adjudicated examples
before changing interaction rules.

The comparison API now raises an error when PLIP is unavailable or fails to
identify MK1, instead of silently interpreting absent reference data as zero
interactions. `total_agreement_rate` is only the fraction of categories with
identical raw counts; it is not a scientific accuracy metric.

During full-suite verification, the CLI's import-time runner was also found
to capture ambient `PSF_LLM=1` before test environment isolation and route a
test through the external DeepSeek API. The CLI now creates its runner at
command invocation, so the provider choice follows the current environment.
