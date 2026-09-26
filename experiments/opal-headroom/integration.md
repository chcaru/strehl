# Root-owned execution

No shared Rust changes are needed. Freeze `run.py`, `design.md`, `targets.json`
and this file before invocation. Use one fresh shared build whose source set
includes the unchanged full-stack cache and highlight renderer adapters. The
opal driver additionally binds its runtime sources in every execution receipt.
The checked shipped production binary or the same shared build's production
binary is accepted; every resulting RGB16 sample and ICC must match the cache.

First create the actual current production image, at the already delivered
exposure. Substitute an explicit `--exe`/`--sha256` only if using the fresh
shared build. Existing directories are never reused or overwritten.

```text
python -I -B -X faulthandler scripts/render-native.py --input D:/personal/macro/minerals/rainbow-opal-cabochon/103MSDCF --warp-map outputs/minerals-september24/103msdcf/alignment.txt --exposure=-0.3 --out outputs/quality-september25/opal-103
python -I -B -X faulthandler experiments/opal-headroom/run.py cache --build SHARED_BUILD --production outputs/quality-september25/opal-103 --out experiments/opal-headroom/cache-1
python -I -B -X faulthandler experiments/opal-headroom/run.py controls --build SHARED_BUILD --out experiments/opal-headroom/controls-1
python -I -B -X faulthandler experiments/opal-headroom/run.py replay --build SHARED_BUILD --controls experiments/opal-headroom/controls-1 --cache-run experiments/opal-headroom/cache-1 --out experiments/opal-headroom/replay-1
python -I -B -X faulthandler experiments/opal-headroom/run.py views --run experiments/opal-headroom/replay-1 --out experiments/opal-headroom/views-1
```

The cache invocation reads all155 originals once after the normal production
run. It supplies no `historical` receipt and never compares with a pre-fix TIFF.
Only mode=current is used; the rejected source prior is not executed. Existing
plan hashes and per-source fields are retained. The four-arm replay uses zero
RAW reads and the actual current writer; exposure and resolved development are
held exactly. The views phase retains full native images and whole overviews,
then extracts the two frozen384px regions without resampling.

No cost probe is added: complete183/207/488-source cache runs already exercised
the exact consumer, and this155-source invocation has strict900s/6000CPU/12GiB
bounds. These are resource ceilings, not speed or memory measurements.

Author performed read-only metadata and existing-image inspection only. Root
must execute and independently review before recording any quality decision.
If no clear useful gain, close the omitted comparison without tuning.
