# Complete chip observation: bounded benefit, unresolved quality gap

MEASURED: the separately authorized unchanged coarse-source prior produced a
complete 299-frame pair at 6468x4300. Every baseline RGB16 pixel matches the
retained current result. The generated general qualification remains false;
the photograph does not reverse the measured far-detail loss or glint damage.

Root visually inspected both complete 1617x1075 overviews and all seven frozen
native pairs. Large central compartment borders become more compact, with
less broad colour contamination. The upper-left contacts still carry strong
bright spill; any improvement there is partial. The independent reader also
identifies cleaner contact separation. Central coloured stipple persists and
looks more prominent. Upper-colour and lower-array changes are small, the
lower-colour green smear remains, and no additional resolved fine structure
was identified. No obvious scratch trajectory, rail or cell disappeared in
the fixed views. This limited visual inspection cannot establish true colour,
calibrated noise, or absence of loss at every native pixel.

VERDICT: a bounded photographic benefit worth retaining as an experiment,
insufficient to close the observed commercial-reference gap. No default or
general mode is promoted. The failure on two superposed depths remains a real
counterexample, and opacity alone does not protect against the glint failures.
The next investigation is coherent whole-image source choice using the same
native gather, not an exponent/window rescue of this recipe.

## Complete images

Current and candidate share reference149, quad crop [141,97,3234,2150], normal
optical CA, current rounded native GPU gathering, seven AC bands, injected
noise/probe, canonical chunks75/75/75/74, WB, matrix and fixed development.
CA-before-MHC remains off. Both full-resolution RGB16 masters retain the same
ICC. Whole PNGs and matching quarter-size overviews use the same fixed high-byte
conversion without automatic contrast. The user was shown both whole images
with both master links before a final photographic judgement.

- [Complete current TIFF](chip-full-1/output/baseline.tiff)
- [Complete experimental TIFF](chip-full-1/output/candidate.tiff)
- [Current whole view](chip-views-1/baseline-overview.png)
- [Experimental whole view](chip-views-1/candidate-overview.png)
- [Full display/region bindings](chip-views-1/completion.json)

The seven native region pairs are secondary evidence. They are exact same-gauge
copies with baseline left and candidate right, not registered vendor crops.
The existing vendor mapping refusal remains; this report claims no matched
native superiority over Helicon and no SOTA result.

## Execution and controls

Root ran the following with Python312, `-I -B -X faulthandler`:

```text
experiments/cross-scale-source-prior/chip-run.py build --out experiments/cross-scale-source-prior/chip-build-1
experiments/cross-scale-source-prior/chip-run.py controls --build experiments/cross-scale-source-prior/chip-build-1 --out experiments/cross-scale-source-prior/chip-controls-1
experiments/cross-scale-source-prior/chip-run.py cost --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --out experiments/cross-scale-source-prior/chip-cost-1
experiments/cross-scale-source-prior/chip-run.py full --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --cost experiments/cross-scale-source-prior/chip-cost-1 --out experiments/cross-scale-source-prior/chip-full-1
experiments/cross-scale-source-prior/chip-run.py finalise --build experiments/cross-scale-source-prior/chip-build-1 --screen experiments/cross-scale-source-prior/chip-controls-1 --run experiments/cross-scale-source-prior/chip-full-1 --out experiments/cross-scale-source-prior/chip-views-1
```

MEASURED: fresh core/CLI compilation took186.328s; the two instrument tests
took2.641s and reproduce the original 12-case screen byte for byte, including
`photographic_replay_admitted=false`. The explicit single-source149/full-size
route preserves all four collapsed CFA planes and delivered RGB16 exactly.
Its measured5,035,110,400-byte peak and padded1047.4243s estimate admit resources
for the observation only. These are not quality gates or speed benchmarks.

MEASURED: the complete pair finished in400.563s, using999.25 CPU seconds and
peak job commitment5,470,801,920 bytes. The first/second source passes take
174.1321s/224.5349s; recorded finishing takes1.2826s. This is an instrumented
two-pass observational pair, including baseline and extensive replay hashing,
not a production throughput comparison. The fixed1800wall/7200CPU/16GiB job
limits were not reached. All299 sources reproduce historical active-u16
hashes and beta values, and each second-pass known4/guide/variance/beta and
canonical energy/floor/weight field matches its first pass. Every per-source
and final held-state check passes, including exact repeated-current collapse.
Finest/base/fallback/hull accumulator identity does not imply unchanged visible
fine appearance after reconstruction; the generated tests already disprove
that inference. No materialized aligned stack is retained.

The independent source reviewer had reported no adapter blocker before root
started compilation. The final source-review document was written afterward
and before RAW execution; it is separately hash-pinned, not retroactively added
to the build source list. See chip-execution-review.md for that distinction.

## Identity

- CLI test executable: `f1953bc3bbc53c11bb502c326e3a95b25ef25d94786bde19b57ec955eb7566ef`
- Preserved generated screen: `a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144`
- Current RGB16 pixels: `7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db`
- Candidate RGB16 pixels: `739ccc91c206ad4a6728d3c534fd8cba7dc916f54e521ae4945ecf12accdc996`
- Current TIFF: `0de5ca7aa417bd74426033f8ea30dd82b75d570b886289bcc62b5609b7680113`
- Candidate TIFF: `c13049efe1f417f7b11733177296e6ab6434d333275722852ad5717c054b1af9`
- Complete adapter receipt: `190d045e23d4b59f14c6f2c33722153729aeaec643977fa11b70d4ab961e79cc`
- View completion: `8a900544f9a494ac7147c56905fa5803c951b0686f8a723ba8f3f45c3f56dbd3`

Independent reviews: chip-review.md, chip-execution-review.md and
chip-photographic-review.md. Existing results.md/results-review.md retain the
failed general qualification. No SYNTHESIS fold or general-quality assertion
is made here.
