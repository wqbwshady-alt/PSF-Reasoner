# Examples

`hiv1_protease_v82a.request.json` is the first bidirectional contract fixture.
It references `data/1hsg.cif`, the RCSB PDB 1HSG HIV-1 protease--MK1 complex.
The coordinate provider now reports observed V82-to-MK1 geometry from this source.
It does not model the A82 mutant, so mutation-induced contact changes remain
hypotheses to validate.

`hiv1_protease_v82a_pair.request.json` provides a paired WT/mutant structure
example using 1SDT and 1SDV. It enables direct geometric comparison, but the
reported deltas remain conditional on these two experimental structures.
