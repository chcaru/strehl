# Fixed insect field: complete negative result

2026-10-27. **MEASURED / independently VERIFIED.** Close the exact six-scalar
per-bracket-step stationarity hypothesis. All 12 primary held populations are
complete; 10 fail the fixed 20% MSE reduction gate. All six replication cells
have greater error than the zero-residual null. This is not a missing-data
refusal. It does not disprove every focus-dependent geometry model, identify
a physical cause, or justify a corrective warp.

Commands actually run from the repository root:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-field-stability/run.py controls
python -B -X faulthandler experiments/raw-quality-2026-10-27/insect-field-stability/run.py actual
```

Both exit 0 with complete bounded-job receipts. Controls use 0.718s and
24,784,896 bytes peak job commitment; actual saved-data scoring uses 2.328s
and 23,658,496 bytes. One worker; limits 120s wall/CPU and 4GiB. Source and
dependency identities are bound in the job directories under
`outputs/raw-quality-2026-10-27/insect-field-{controls,actual}-1/`.
Analyzer SHA256 is `b0205a3ec0f258011be4068de04a60fe5af90ec64cf8ee36100cf886d496cec1`.

The 7,020-row inventory retains all statuses and MAD flags. Training uses
88 span-8 pairs per site, including tile15's 15 MAD outliers. The other two
training sites have none. Only tile41 improves in the first held interval
(33.1%/34.0% for spans1/8); its replication instead worsens by113.1%/156.9%.
All other primary site/interval combinations worsen. Span32 refusals and all
descriptive subblocks remain in the receipt; they do not replace the primary
population.

The independently specified controls pass their actual fit/scorer tests:
known stable field, zero/noise null, held reversal, wrong-site/span,
missing-row and overlapping-acquisition foils. The identical persistent-bias
lookalike passes numerically while retaining false physical attribution,
demonstrating why even a positive result would not identify displacement.

[Independent conclusions](independent-results.md) and
[receipt audit](independent-receipt-audit.md) agree. No source photograph was
decoded, no warp changed, and no new stacked image was produced. There is no
photographic improvement to present. No site, interval, outlier rule, threshold
or larger model is retuned under this allocation.
