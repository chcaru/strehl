# Native inference probe

An isolated Rust/Tract compatibility measurement for the fixed V3/V4 predictor
contract. It does not change Strehl, render photographs, supply weights, infer
color semantics, or establish photographic quality. Use only your own trusted
model artifacts. Graph imports are not a sandbox for untrusted models.

The standalone workspace and lockfile keep this experimental inference runtime
out of the application dependency graph. Its optional ONNX parser is needed only
for the first translation; the translated NNEF graph runs in the parser-free
build. All input, model and output identities are recorded in each receipt.

## Execute

From the repository root, provide an exported model and exactly 3,932,160 bytes of
little-endian FP32 input, in `[1,5,384,512]` order: three caller-prepared RGB planes
and two scalar semantic-mask planes. Values must be finite and in `[0,1]`. The
probe does not prepare an image or choose a color space. Match the predictor's
declared input contract separately.

```text
cargo run --release --locked --manifest-path experiments/adaptive-distillation/native-probe/Cargo.toml -- MODEL.onnx INPUT.f32 NEW_RECEIPT_DIRECTORY 24
cargo run --release --locked --no-default-features --manifest-path experiments/adaptive-distillation/native-probe/Cargo.toml -- NEW_RECEIPT_DIRECTORY/model.nnef.tar INPUT.f32 NEW_NNEF_RECEIPT_DIRECTORY 24
```

The output directory must not already exist. The first command writes a translated
NNEF model; both commands write ten FP32 fields and a JSON receipt. Output slots
follow the V3/V4 export contract. Tract's graph-node names are diagnostic and are
not the ONNX output names. Verify the input/model identities and compare all ten
output arrays with the exporter before assigning semantic meaning to an arbitrary
graph of the same shapes.

Inference runs once cold, twice for warm-up, and then for the requested number of
timed repetitions. Every repetition must return the same output hashes. Reported
forward timings exclude validation, hashing and writes. Loading, preparation and
process-lifetime memory observations are separate. These are not editor latency
measurements. Do not call differently configured runtimes a speed comparison.
Reported quantiles select sorted index `ceil((n-1)*p)`; for an even sample count,
the reported median is the upper middle observation rather than their average.

Windows reports process working set and peak through the operating-system API;
Linux reads `/proc/self/status`; other platforms report memory as unavailable.
Only the Windows execution is currently measured in the development report.

## Guards

```text
cargo test --locked --manifest-path experiments/adaptive-distillation/native-probe/Cargo.toml
cargo test --locked --no-default-features --manifest-path experiments/adaptive-distillation/native-probe/Cargo.toml
```

The malformed-input test fails on truncated, nonfinite, negative and overrange
inputs. The parser-free build must explicitly reject an ONNX request. Runtime
checks reject incorrect input/output dimensions or types, nonfinite predictions,
nonpositive gains, and color tables outside the exported bounded contract. These
checks establish a tensor interface, not correct color rendering or robustness
to a malicious graph. Full photographic review remains a separate requirement.
