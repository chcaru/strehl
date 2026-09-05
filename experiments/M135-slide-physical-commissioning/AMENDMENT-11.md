# M135 slide commissioning amendment 11

Status: **TERMINAL CLOSEOUT AFTER FINAL REVIEW**

The final review identified three remaining failure paths:

1. a Stage C artifact could carry internally consistent synthetic curves while
   naming a real decode artifact;
2. role-ledger and matched-flat bytes were hashed and parsed in separate
   opens; and
3. an empty tilted directory crashed `focus_histogram` instead of producing an
   inventory mismatch.

`summarize` now reruns Stage C from the bound inventory and all-frame
independent-decode artifact and requires the complete measurement projection
(curves, peaks, fit, bars, and density) to match.  JSON lineage files are read
once into immutable bytes, hashed, and parsed from those same bytes.  Empty
focus populations return a typed missing histogram.

The replacement commissioning adds a range-recompute mutation and the empty
focus control.  No threshold or interpretation changes.
