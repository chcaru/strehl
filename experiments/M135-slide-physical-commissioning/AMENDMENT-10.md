# M135 slide commissioning amendment 10

Status: **MEASUREMENT-BINDING CLOSEOUT BEFORE COMMIT**

The last review found that two derived statuses could still be internally
consistent without being tied back to their measured rows:

- coarse equality duplicated histogram summaries instead of recomputing them
  from each frame's `FocusPosition2`; and
- range equivalence recomputed its bars from a supplied fit but not the fit
  from the recorded 64 site peaks.

Inventory validation now rebuilds both histograms from frame records and
derives the coarse status.  Range validation rebuilds the two `PeakEstimate`
populations from the recorded fixed-lattice sites, reruns
`adjudicate_range_pairs`, and requires the eligible set, normalized peaks,
Huber fit, residuals, bars, and node-density result to match exactly.

New forged-coarse and forged-range controls prove both paths go red.  No bar,
frequency, role, or target population changes.
