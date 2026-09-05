# M135 slide commissioning amendment 3

Status: **PRE-FREEZE HARDENING AFTER THE FIRST GREEN AUTHOR-COMMISSIONING RUN**

Run 3 commissioned the originally implemented selectors.  A source audit
before dependency/hash freeze found four fail-closed gaps that its plants did
not yet exercise:

1. non-convergence of the Huber fit was not itself an equivalence failure;
2. a failure in the second stack could discard the first stack's diagnostic
   record instead of returning `IMAGE_RANGE_UNDETERMINED` with both states;
3. role independence checked paired flat/dark lineage tuples, allowing a
   shared flat with different dark IDs, and did not bind disjoint source-file
   identities or a matched-flat manifest hash;
4. the sampling predicate consumed point values rather than the conservative
   reference LCB over scored UCB required by the physical protocol.

This amendment tightens those paths and makes quadrilateral/registration
failures typed `IMAGE_RANGE_UNDETERMINED` or
`FLAT_DIAGNOSTIC_UNDETERMINED`.  It also validates, rather than trusts, any
request to invoke the existing M135 core on four flat streams.  New mutations
are added before the replacement commissioning run.

No preregistered bar, expected count, band edge, lattice coordinate, or
scientific status is weakened.
