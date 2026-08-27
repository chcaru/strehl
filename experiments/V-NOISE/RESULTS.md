# MOVED — this lane's record is `docs/research/M127-noise-head-to-head.md`

This file used to hold the V-NOISE results. It was allocated milestone **M127**
and the record now lives at:

> **[`docs/research/M127-noise-head-to-head.md`](../../docs/research/M127-noise-head-to-head.md)**

**Do not read a working copy as the record.** Nothing is kept here; the record
moved rather than being duplicated, so there is no second copy to drift.

`experiments/V-NOISE/` remains M127's working directory. The instrument is:

```
python census_src.py      # 63 source frames -> flat tile census (cached)
python clipdiag.py        # the clip-guard deviation, measured
python noisefree.py       # primary statistic + full commissioning
python halfdiff.py        # THE VERDICT: half-stack estimator + commissioning
python chromagain.py      # is the CHROMAGAIN guard circular?
```

`PREREGISTRATION.md` in this directory stays here and stays authoritative for
what was fixed in advance — including its §0 disclosure that the registration
was **not blind**.
