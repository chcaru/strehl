# Fixed RAW temporal-affinity support falsifier

Generated-only implementation; author does not execute or validate it. No
automatic ownership claim, new source winner, full-photo adapter or promotion.
This tests the saved bounded proposal after radius32 mean pooling and categorical
Potts source fields failed their truth screens. It does not reopen those rules.

Use the actual supplied u16 CFA, injected noise model, held pull geometry,
rounded GPU MHC/Catmull consumer with no CA profile for generated paths. First
pass retains only source-by-block four-DN means on fixed8x8 output-quad blocks;
partial edge blocks use their actual samples. Consecutive signed differences
include every source and all four planes in order. There is no compression,
WB scaling, fitted noise, time lag, source-curve peak or fitted cosine cutoff.

Each block is an anchor. Its neighbours have block centres within32 quads on
each axis (at most9x9 blocks). Self-weight is exactly1. Other weights are the
squared positive part of their signed four-channel temporal cosine. Exact
zero temporal norm gives neighbour weight0. Clamp above1 only handles f32
roundoff. A shared late brightening can create a spurious association: that is
an explicit independent destroyer, not a property declared solved.

Second pass repeats the identical actual BandWorker inputs and beta probe.
For each source, pool production finest green energy and injected floor
separately: sum(weight * block field sum)/sum(weight * block area). Copy that
E/F pair across the anchor block, then use the existing SoftPower exponent,
gate/floor convention and accumulation. This is explicitly a block-centre
neighbourhood, not a per-pixel65x65 box; block boundaries may create defects.
All coarser weights, terminal mean, fallback sums and original hull remain
unchanged. Existing public rb_own_guide diagnostic methods suffice; no core
hook or production edit is needed. Existing camera_rgb supplies the same
WB normalization and final MHC for camera-linear truth comparison.

Modes: Off replays canonical fields exactly. Affinity is the fixed rule.
AllAffinity replaces every neighbour weight by1 within the same support as a
cue-free pooling placebo; it does not pool over the whole image. The explicit
forced-source test wrapper overrides only finest weights with one/zero and
exists solely to commission the independent truth score. The algorithm never
elects or calls that source. No mode is environmental/default-on.

Evidence: original-storage hash, known4/guide/variance/beta equality across
passes, descriptor and canonical/pooled E/F hashes, weight hashes, averaged
fractions, and actual nonfinest accumulator equality after every replay source.
The original complete baseline must equal its replay; Off output is bit-exact.
These are implementation assertions, not the author's quality verification.
Independent controls own fixtures, thresholds, nuisance truth conventions and
the decision to reject; root owns all builds/execution.

Scope: at most70 generated sources, native extent at most512 on either axis,
one actual current source and fixed merge workspaces. Retained temporal state
is four f32 block means per source, never an aligned source-frame collection.
No stored source focus/colour pyramids. Production applicability, performance,
noise calibration and complete-photograph transfer are unmeasured.

Integration after root releases the active diagnostic: add only a test/feature
gated `raw_affinity_support` include of implementation.rs in merge_cmd.rs,
matching the neighbouring generated experiments. Existing features
native-direct-planes/native-gpu-gather/native-correction-variance provide the
core methods. Independent module is independent_controls; no root-owned file
is edited by this author.
