# V-HEADTOHEAD3 — transfer checker correction

**Recorded after the first real checker run and before any corrected checker
outcome.**

The author result retained 24 sites, fitted PMax40 scale `1.003`, and returned
candidate `UNRESOLVED`.  The first independent result retained 18 sites,
fitted scale `1.008`, and returned candidate `REAL_TRANSFER_PARTIAL`; the
adjudicator stopped.

Inspection found a specification mismatch in the independent registration
implementation.  The frozen sharpening arm uses a Hann-windowed phase
correlation with the search explicitly restricted to ±32 pixels.  The checker
instead called an unwindowed, unrestricted library estimator and rejected a
site when its global maximum lay outside ±32.  Six fixed sites were consequently
deleted on the basis of an unrelated strehl/PMax40 registration.  On the 18
common sites, author and checker PMax40/PMax0 geometric means were
`2.565520525` and `2.569463819`, showing that the apparent disagreement came
from complete-case deletion rather than from `Q25`.

The correction independently implements the registered Hann window and
restricted search with a real-valued FFT.  Before rerunning real pixels, a
fixed edge-corruption plant makes the windowed estimator recover `(-5,+7)` and
the no-window mutant fail; a planted `(40,-39)` displacement proves that the
±32 bound is enforced and an unrestricted mutant goes RED.  The full checker
commission now has 30 controls GREEN and 14/14 mutants RED.  No threshold,
site, operator, statistic, band, bootstrap seed, or interpretation rule was
changed.
