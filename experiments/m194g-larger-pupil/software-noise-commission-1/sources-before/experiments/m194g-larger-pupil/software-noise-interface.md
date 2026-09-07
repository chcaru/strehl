# Software-noise controller handoff

2026-09-07. Source preparation only; no execution is authorized by this file.
The committed noise contract and full-float authority schema govern the law
and prerequisites. This freezes the controller's narrow serialization interface.

The CLI is `software-noise-run.py --mode commission|intended --output NEWDIR
--runtime PATH --runtime-sha256 SHA --execution-release PATH
--execution-release-sha256 SHA`. Intended additionally requires
`--float-commission PATH --float-commission-sha256 SHA --noise-commission PATH
--noise-commission-sha256 SHA`. Private constant controls need no full-float
authority. The release uses `m194g-numerical-execution-release-v1`, scope
`noise-commission` or `noise-emission`, and the existing exact source/input/
original-argv mechanism. No noise core is imported before that entry check.

All FileRefs contain exactly path/sha256/bytes; ArrayRefs add dtype/shape.
Private-index children and deterministic payload refs resolve from the index
parent. Each private trace's array refs resolve from its own record parent.
The copied contract and runtime are ordinary bounded FileRefs, not embedded
objects. Source bindings map repository-relative paths to sha256/bytes.

The private index has schema `m194g-software-noise-private-index-v1`, status
`COMPLETE_PRIVATE_TRACES_UNCOMMISSIONED`, and exactly these keys:
schema/status/contract/runtime/source_bindings/records/deterministic/work.
Records is the ordered1186-entry list `{call_id,record:FileRef}`. Work is the
shared Budget receipt immediately before index persistence, not final success.

Temporal IDs are `baseline-s{level}-r{r:02d}`, in levels0/64/4096/12000 then
r0..63 order. Next come the seven contract-table faults, each64 fault calls
then64 restored calls, with IDs `fault-{fault_id}-r{r:02d}` and
`restored-{fault_id}-r{r:02d}`. Group is the prefix before `-rNN`. Fault IDs in
order: c-after-poisson, gain-double, omit-read, reuse-repeat-zero, clone-green,
read-lag2-mix, clamp-black. All temporal observer modes are off.

Supplemental IDs, in order: live-a-s701-f0..4, live-a-s709-f0..4,
live-b-s701-f0; observer-count, observer-placebo; replay-f4..0; dark-f0..4;
shared-read-frame-f0..4; shared-read-frame-restored-f0..4;
component-key-restored. Groups are live/observer/replay/dark/shared-read-frame/
shared-read-frame-restored/component-key-restored. Phase is baseline for live
and dark, replay for observer and reordered calls, fault/restored for the
shared-key pair, and restored for component-key-restored. The last retains
fault_id omit-component-key with no active mutation. Seeds, levels and frame
identities are exactly the committed contract's34-call table.

Deterministic is an ordered list with uniform keys
call_id/kind/input/q/witness/status/exception/details. Input and q are ArrayRef
or null; witness is the core operation counters or null. Status is VALUE or
REFUSED, exception null or `{type,message}`, and details is a bounded object.
IDs: round-baseline/round-half-up/round-restored; reject-nan/reject-posinf/
reject-neginf; tag-baseline/tag-swap-rb/tag-rb-restored/tag-swap-green/
tag-green-restored; noise-off-off/noise-off-count/noise-off-placebo;
component-key-omitted; resource-stale-owner; independent-key-preflight. The three nonfinite X inputs are
retained as deliberately invalid NPY fixtures. Their metadata cannot be used
as a healthy-array admission. Tag input is the literal scalar ramp; noise-off
input is constant12000. Details binds the sampled tuple for the malformed-key
refusal and the injected stale-owner/actual-alias byte counts for the resource
check. The independent-key record has input/q/witness null and details exactly
component_keys_checked2372/key_bytes_checked true/entropy_words_checked true.
It counts independent comparisons of the actual two forwarded keys per noisy
call before the first draw, not additional Generator constructions or samples.
Deterministic refusals must be the named ValueError, not a budget or I/O
failure. A complete ordinary reader entrypoint call follows index persistence.

Literal kind values are rounding/nonfinite/tag/noise-off/omitted-key/resource/
key-preflight, respectively. Nonfinite, omitted-key, resource and key-preflight
witnesses are null. Successful rounding/tag witnesses show one encoding, zero
samples/hooks/collection. Nonfinite exception type is ValueError and message
`encoder input contains nonfinite values`; omitted-key exception type is
ValueError and message `RNG key bytes mismatch`. Successful records have null
exception. Details is empty for rounding/nonfinite/tag. Noise-off details has
exactly generator_delta0/requested_delta0/forbidden_sampler_calls0/audit, with
audit the actual core SampledFrame.audit_record() including null seed/streams,
input and consumed hashes, Q hash and operation witness. Omitted-key
details has exactly spec/generator_delta0/requested_delta0, where spec contains
scene control-live-a, seed701, frame_index0, width128, height96, scalar_level12000.
Resource details has exactly expired_owner_dead true/live_shape[5,8]/
live_nbytes320/registered_owner_is_live true/registered_bytes320/
live_delta_bytes320/alias_delta_bytes0/oversize_refused true/
restored_alias_same_bytes true. The refusal inside this successful resource
control is BudgetError; it is recorded as the oversize_refused boolean, not
mistaken for the deterministic numerical ValueError arms.

The reader returns `PASS_SOFTWARE_NOISE_PRIVATE_TRACES`. The controller writes
its returned record separately and only then may write
`m194g-software-noise-run-v1` status `PASS_SOFTWARE_NOISE_COMMISSION`.
Run-record keys are schema/mode/status/invocation/execution_release/runtime/
sources_before/sources_after/inputs_before/inputs_after/index/manifest/
independent_reader/work/error/finalization_errors. Unfinished or failed runs
have status `UNCOMMISSIONED_SOFTWARE_NOISE`; index/manifest/reader are null
until actually persisted. Final source/input/time/output checks remain required.

The intended manifest has schema `m194g-software-noise-manifest-v1`, status
`COMPLETE_NOISE_FILES_UNCOMMISSIONED`, and exact keys
schema/status/ref_root/upstream_ref_root/contract/float_commission/
noise_commission/runtime/source_bindings/geometry/sensor/bundles.
ref_root is `manifest-parent`; upstream_ref_root is `repository`.
Contract/runtime and all CFA/audit refs are manifest-relative. Only the two
commission refs are repository-relative. This mixed convention is explicit,
not inferred from the authority file's location.

Geometry has width320/height240/cfa_origin[0,0]/reference_index2/
frame_indices[0,1,2,3,4]/inverse_foci[.5,.625,.75,.875,1.0]/forward_similarity
equal to the registered identity object. Sensor has cfa `RGGB`,
factors_f64[.75,1,1,.6], gain_dn_per_e[.25,.25,.25,.25],
read_noise_e[4,4,4,4], black[512,512,512,512], white[15360,15360,15360,15360],
quantization `ties-even-then-clip-[0,15360]`,
wb_rgb_f32[1.3333333730697632,1.0,1.6666666269302368]. The latter is a later
consumer convention, never an emitter multiplication. All dimension/index/
byte fields are genuine integers; bool/float aliases refuse.

Bundles are ordered textured then flat, each noise-off then the eight seeds in
contract order. Each bundle has scene/noise_enabled/seed/frames, with five
frames ordered0..4; each frame has index/inverse_focus/cfa/audit. CFA is an
ArrayRef for headerless little-endian u16[240,320], exactly153600 bytes. Audit
is a FileRef for the core's actual audit_record. Its expected-scalar hash is
of raw contiguous f64 payload, distinct from an upstream NPY file hash.
No intended intermediate arrays or random replay are retained/performed.

An intended generation result can only have status
`COMPLETE_NOISE_FILES_UNCOMMISSIONED`. A later independent actual-CFA read
issues `m194g-software-noise-admission-v1`, status
`PASS_SOFTWARE_NOISE_FILES_ONLY`, with exact keys schema/status/ref_root/
manifest/generation_result/independent_read/float_commission/noise_commission.
ref_root is repository and all five references are repository-relative FileRefs.
That gate's implementation belongs to the independent reader lane; the
generation controller does not issue it or claim physical calibration.
