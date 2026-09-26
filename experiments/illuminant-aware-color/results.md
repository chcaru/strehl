# Illuminant-aware color: complete comparisons, no useful visible gain

2026-09-25. MEASURED two complete writer comparisons; no production promotion.
The fixed3000K transform changes hue but does not establish useful additional
gradation or detail in either the155-source opal or488-source marigold.
Root and independent review of both complete images and all seven fixed native
pairs agree. The broad reflection and duplicated/soft hairs remain. Without a
physical color reference, this does not establish which rendition is more
color-accurate. Close this arm without a temperature or saturation sweep.

Executed commands with Python3.12, `-I -B -X faulthandler`, from the repository:

```
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py build --out experiments/illuminant-aware-color/build-1
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py build --out experiments/illuminant-aware-color/build-2
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py controls --build experiments/illuminant-aware-color/build-2 --out experiments/illuminant-aware-color/controls-1
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py metadata --build experiments/illuminant-aware-color/build-2 --controls experiments/illuminant-aware-color/controls-1 --out experiments/illuminant-aware-color/metadata-1
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py cached --build experiments/illuminant-aware-color/build-2 --controls experiments/illuminant-aware-color/controls-1 --metadata experiments/illuminant-aware-color/metadata-1 --out experiments/illuminant-aware-color/cached-1
python -I -B -X faulthandler experiments/illuminant-aware-color/run.py views --run experiments/illuminant-aware-color/cached-1 --out experiments/illuminant-aware-color/views-1
```

The first build retains an8.843s E0284 compile failure: one independently
authored test array needed its explicit `[f64;3]` type. No calculation or bar
changed. The fresh second build succeeds in170.296s. Four exact numerical
controls pass in0.297s; the two-first-frame metadata route takes0.422s and
the complete cached writer pair3.750s. These are operational costs, not
stacking-speed benchmarks. The cached phase reads no originals.

Actual captures provide A/D65 calibrations and identical consumed WB, matching
their complete caches. At the declared3000K coordinate the warm interpolation
fraction is0.9144210526315789. That coordinate is an assumption from the owner's
lighting/WB setup, not a measured spectrum. Independent controls commission
matrix direction, WB undo, one adaptation, normalization, interpolation and
refusal on malformed inputs. Live wrong-matrix/double-WB/adaptation controls
fail as intended. Synthetic RGB noise variances change by1.169059/1.358060/
1.858054x and match independent propagation within6.4e-6 relative error;
these are synthetic covariance facts, not photographic noise measurements.

Both complete current replays and pinned rewrites match retained RGB16/ICC
exactly. Merged CFA caches remain unchanged. The sole changed development
setting is the final matrix. The existing rolloff, tone and gamut code can
respond differently to that matrix, so fixed settings do not mean fixed
per-pixel actions. No glare-recovery or independent calibration claim follows.

Root's native review sees the same slanted opal reflection bands and fine
surface marks. Blue/purple shifts toward cyan, with no clearly new gradation;
the pink transition is somewhat less distinct. All five marigold targets retain
the existing hair/petal geometry and haze. The bright rim surface becomes
stronger yellow-orange and the bud slightly warmer, without new useful detail.
`independent-results.md` records the separately chosen visual interpretation;
`independent-numerical-results.md` records the arithmetic/identity limits.

Complete TIFF masters are in `cached-1/output`, and both current/candidate
full JPEGs in `views-1`. The complete candidate outputs were shown to the owner
with links to the complete current images. Nothing here replaces the shipped
renderer or resolves the outstanding SOTA gap.
