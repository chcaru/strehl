import io, sys

RS = "HALO-residual.md"
OLD = """## 6. Three-way partition, all 26

| category | n |
|---|---|
| VISIBLE defect | **0** |
| MEASURED-but-not-visible (old false positives) | **4** |
| clean | **14** |
| UNSCORED, per-subject reason in section 2 | **8** |
| **total** | **26** |
"""

NEW = """## 6. Three-way partition, all 26

**CORRECTED 2026-08-28. This section previously read `clean 14 / UNSCORED 8`.**
That split credited `halo3` with rescuing `coffee-bean`,
`flower-inner-edge-cpl` and `wrapped-text-1` from UNSCORED to clean.
**`halo3` failed its own commission (section 4), so it cannot move any subject
out of UNSCORED**, and section 7 forbids exactly those rescues -- the file
contradicted itself in the direction that understates residual risk. The
partition below is taken from `halo_profile.py` alone, the only commissioned
instrument, and agrees row-for-row with `HALO-falsepositive.md` section 4.
**Do not re-derive `14 / 8` from the section 5 table; that table is uncertified.**

| category | n |
|---|---|
| VISIBLE defect | **0** |
| MEASURED-but-not-visible (old false positives) | **4** |
| clean, full 7-band walk | **11** |
| clean but BLIND beyond 32-50 px, not a pass | **4** |
| UNMEASURABLE, per-subject reason in section 2 | **7** |
| **total** | **26** |

**Residual risk is 11 subjects UNSCORED** -- the 4 blind plus the 7
unmeasurable. It is not 8, and it is not the 6 I reported from `vh_union.py`;
both credited an uncommissioned instrument and are withdrawn.
"""

t = io.open(RS, encoding="utf-8").read()
if t.count(OLD) != 1:
    sys.exit("ANCHOR NOT FOUND (%d occurrences) -- nothing written" % t.count(OLD))
io.open(RS, "w", newline="\n", encoding="utf-8").write(t.replace(OLD, NEW, 1))
print("patched section 6 of", RS)
