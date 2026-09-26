# Fixed composite-reference registration pilot

Prepared September26; unexecuted. This is a new diagnostic question, not a change
to the refused narrow108–116/anchor112 pilot. That pilot remains closed at its
fixed activity bar. Current's complete composite can contain focused evidence at
several depths, but can also drag sources toward its own ghosts. V-NEVERWORSE
§9.23.10 already found ORB/model-ECC failure against all-in-focus masters at focus
extremes; no survivor subset from this new experiment is admissible either.

Use exactly source ordinals112,152,320, each bidirectionally against the corrected
Current master. Its whole TIFF SHA256 is
`19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f`, freshly
verified during preparation. All three complete source TIFFs are the retained
unaligned7032×4688 RGB16 outputs from marigold-comparator/run-2. The held488 order,
reference244 map, crop[191,128,3134,2088], ICC and exact development metadata are
checked by reusing the old preflight; no original RAWs are opened or restatted.
All four selected TIFFs are freshly content-hashed before inference.

The existing frozen source operator performs INTER_AREA source988×658 followed
by held-map bilinear sampling to880×586. The Current master is already in the
6268×4176 output gauge: INTER_AREA directly to880×586 on RGB16, then f32/65535,
with no crop insertion, transform or tone operation. Independent tiny spatial
RGB16 area/channel checks run before photographic reads. Generated estimator
tests do not commission the original RAW or native gather. Exact f32 proxies,
source-coordinate arrays and all six flow fields are retained with hashes.

Reuse the exact previous safely loaded torchvision RAFT-large checkpoint,
float32 inference, twelve updates, deterministic settings and prior four-scene
passing control receipt. Do not rerun those identical scenes. The new independent
target-contamination positive/negative use exactly four generated calls first;
only their recorded pass permits the six real calls. No training, fetch,
installation, threshold adjustment, recentering, temporal selection or retry.

The spatial consumer remains the fixed392-square fan support with32-pixel taper
and328-square full-weight interior at[3258,3028]. Reduce each flow by the same
unweighted componentwise median over that interior. Divide by the exact x/y
proxy scales; forward displacement is then multiplied only by the destination
source similarity's linear part. Reverse destination is Current's output gauge,
so its linear part is identity. No crop or similarity translation enters a
displacement. Learned spatial variation is explicitly discarded.

Apply the unchanged independent forward/reverse judge to all three pairs:
source-native norm<4, native p90 spread≤.75, quadrant separation≤.75, median
closure≤.5 and sampled cycle p90≤.75. All three pairs must pass both directions,
and at least one forward source-native norm must be≥.5 for root-review eligibility.
Record every result before this decision; no favourable subset or clipped vector.
These consistency bars can accept mutually wrong matches, hence the new reference
contamination control. Eligibility is not geometry truth or photographic quality.

Each controls/pilot phase is separately bounded at120s wall,300s CPU,8GiB host
commit and8GiB CUDA allocator with8CPU threads. Existing controller helpers and
all old/new sources, checkpoint, retained controls and independent review are
bound. No native configuration, RAW build, gather change or complete candidate
render is emitted. Current is CA-on while source proxies are CA-off; both are
toned RGB, not raw radiance. A low-resolution flow cannot establish hair-scale
placement or infer an occlusion's physical cause.

Root execution after independent source freeze:

```text
python -I -B -X faulthandler experiments/marigold-composite-registration/run.py plan --out experiments/marigold-composite-registration/plan-1
python -I -B -X faulthandler experiments/marigold-composite-registration/run.py controls --out experiments/marigold-composite-registration/controls-1
python -I -B -X faulthandler experiments/marigold-composite-registration/run.py pilot --controls experiments/marigold-composite-registration/controls-1 --out experiments/marigold-composite-registration/pilot-1
```
