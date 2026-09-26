# Complete chip reconstruction: numerical refusal

2026-09-25. MEASURED complete299-source execution; no candidate photograph.
The unchanged reconstruction fails its numerical admission in both green
planes. Its earlier generated glint/detail failures remain. Close this fixed
recipe without a cap, tolerance or norm sweep; no production default changes.

Commands executed from the repository with Python3.12:

```
python -I -B -X faulthandler experiments/consistent-reconstruction/full-run.py build --out experiments/consistent-reconstruction/build-2
python -I -B -X faulthandler experiments/consistent-reconstruction/full-run.py controls --build experiments/consistent-reconstruction/build-2 --out experiments/consistent-reconstruction/controls-2
python -I -B -X faulthandler experiments/consistent-reconstruction/full-run.py full --build experiments/consistent-reconstruction/build-2 --controls experiments/consistent-reconstruction/controls-2 --execute-approved-observation --out experiments/consistent-reconstruction/full-1
```

Fresh CLI compilation completed in175.875s. All four controls and twelve cases
completed in2.094s, reproducing the original screen byte for byte, including
its false preservation/general/photographic admission. Independent runner
review caught a seven-versus-eight stored-level validation error before build;
the corrected validator checks seven AC levels plus the terminal Gaussian.

The full observation completed in202.188s with peak job committed memory
3,273,506,816bytes. These are bounded operational costs, not speed benchmarks.
All299 original sources, the held reference149 and current crop
[133,89,3250,2166] were consumed. Current production RGB16 and ICC matched
exactly. The same-binary coefficient observer's complete off/on TIFF SHA256
was `84fbf88efe111f1b36d75fc5df80a8bdfd00cee98c8fb4f2cd804248e36cfefb`
for both files. Source, coefficient, accumulator and input-bound identities
passed; all original file metadata remained unchanged.

| Plane | Iterations | Recorded error bound, RMS camera DN | Admission |
| --- | --- | --- | --- |
| R | 6 | 0.0128669964 | Pass |
| G1 | 32 | 0.0281794635 | Refuse: iteration cap |
| G2 | 32 | 0.0278118051 | Refuse: iteration cap |
| B | 6 | 0.0099752423 | Pass |

The fixed bar is0.02DN and all four planes must pass. These are residual-based
exact-linear bounds qualified by earlier f32 controls, not measured image
errors or interval certificates. A bound above the bar does not prove the
true error exceeds it; it means the prescribed admission was not established.
Lower full objectives in all four planes do not establish photographic quality.
The saved receipts record the last iterate hashes, but no refused iterate,
partial plane combination or baseline placeholder was rendered as a candidate.

`full-1/completion.json` records `NUMERICAL_REFUSAL` and `candidate_valid=false`.
The candidate TIFF and candidate plane-cache files are absent. The complete
canonical coefficient cache is150,194,784bytes and is retained with per-level
extents/hashes for reproducibility, without another RAW pass. There is no new
image improvement to show or native-pair visual verdict. Independent execution
interpretation is in `independent-full-results.md`.
