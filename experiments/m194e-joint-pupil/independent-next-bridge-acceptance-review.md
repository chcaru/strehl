# Prospective bridge acceptance review

2026-09-07. Read-only source/design review during full4. No production code,
render, new metric, active numerical design or source was changed. Reviewed the
current `next-production-bridge-preregister-draft.md`, existing M194/M194b
consumer/observer controls, the actual confidence functions in
`crates/strehl-cli/src/merge_cmd.rs`, and this lane's final CFA reader/commission
format. This review is not a release or an optical/production commission.

The unequal crop, rank2 affine fields, fixed80-site/.25DN oracle, all-five green
mutation and explicit four genuine RGB plus one Gray16/three private RGB
population close the earlier coordinate/potency/count ambiguities. The1MiB
JSON limit and exact6144-byte CFA reads address allocation before parsing;
hashing and decoding the same bounded buffer addresses the actual consumed
bytes. Two narrow acceptance clauses still need to be explicit.

## Auxiliary confidence: name and test the encoded quantity

`confidence_pass` compares gathered green luma to the merged green luma before
MHC/WB/exposure/TIFF quantization. For each pixel, `b` counts observations
strictly below that merged value and `s` counts observations seen.
`write_confidence_map` writes:

```text
s > 0: round(1000 * (1 - 2 * abs(b/s - 0.5)))
s = 0: 65535
```

It is rank centrality in milli-units, not a probability, calibrated uncertainty,
noise estimate or independent optical-fidelity score. Tied identical observations
can give zero even when the merge averages; zero alone does not prove selection.
The source's informal "elected a frame" interpretation must not become a new
bridge acceptance claim.

For the five placed, identity-covered genuine inputs, each pixel has `s=5`;
the auxiliary TIFF therefore has only `{0,400,800}`, no65535, and the actual
analysis quad dimensions, half the main RGB dimensions. Assert the five actual
successful rereads rather than assuming them from the frame list. Independently
read Gray16 channel/type/photometric/orientation, actual samples and hashes;
do not apply the RGB14848/65535 DN normalization to this file.

A range check alone cannot distinguish a correct map from a fabricated all-zero
map. Root selected repeated green levels `[100,200,200,400,500]` for the concrete
private component. Use five32×16 active RGGB `Frame`s, origin0, stride32,
buffer_height16, black512/white15360. Store512 plus the chosen green level at
both green phases; use fixed red700DN and blue900DN above black. These distinct
non-green values power a wrong luma-channel interpretation. All values are exact
f32 integers and remain inside the declared rails.

Call the existing `confidence_pass` directly with
`PyramidDomain::whole(PlaneGeometry::from_active(32,16))`, giving16×8 quad
sites; `warps=None`, `defect=None`, `per_chunk=2`, and the five private source
paths. Use two Rayon threads under the already controlled test environment.
This path calls `load_frame` and `extract_planes`; it does not call the Pyramid
fold, profile noise lookup, MHC, gate probe or RGB writer. The full/active
geometry passes `validate_pyramid_frame`, and every extracted plane contains
128 samples. No actual RAW sentinel file may exist or be decoded.

Supply this eight-element target pattern twice per row, repeated over eight
rows, as the exact128-element `merged_luma` argument:

```text
merged green DN: [99,100,200,201,300,400,500,501]
strict below b:  [ 0,  0,  1,  3,  3,  3,  4,  5]
seen s:         [ 5,  5,  5,  5,  5,  5,  5,  5]
encoded value:  [ 0,  0,400,800,800,800,400,  0]
```

Assert all128 actual `Centrality.below` and `.seen` entries before writing,
and each source's successful decode count equals1 for this direct component
call. The genuine enabled path separately retains its required2 reads/frame.
At target200 strict `<` gives b1/code400; a `<=` interpretation gives b3/code800.
Target300 gives b3/code800. Checking counts as well as codes prevents centrality's
symmetry under b→s−b from hiding a wrong comparison on non-tied sites.

Write exactly **two additional16×8 Gray16 TIFFs**:

1. `confidence-rank-component.tif`: actual returned Centrality through the
   unmodified `write_confidence_map`; independently parse every code above.
2. `confidence-unseen-component.tif`: a manually constructed copy of those
   arrays, with only entry0 changed to b0/s0; the existing writer must encode
   that entry65535 and preserve every other expected code. Entry1 remains a
   reached zero, proving that unseen and ordinary zero are distinct.

Thus the prospective total is seven main RGB files, one genuine auxiliary
Gray16 and these two private Gray16 files: **ten TIFFs**, absent a preserved
failure. There is no extra RGB render or optical input population. Keep the
unmodified comparator/writer as the passing companion. Independent wrong
answers using `<=`, red/blue luma, discarded duplicate200 observations, full-u16
instead of milli-unit normalization, or unseen-as-zero must disagree at a fixed
site. These destroyers alter only the checking interpretation; no production
predicate is changed for this component commission. The actual count and decoded
writer checks, plus nonzero400/800 occurrence, reject an all-zero fake map.

The manual unseen entry checks the writer's sentinel encoding only; it does
not claim the five valid constant sources naturally produce an unseen site.
Quantized final RGB pixels cannot recover exact ranks near ties and are not the
pre-writer luma authority. No optical-confidence or image-quality interpretation
is attached to these rank values.

## Reuse the existing CFA gate's child-result/source closure

The genuine CFA gate already has schema `m194e-cfa-commission-v1`, status PASS,
external manifest and float-commission digests, sample_count15360, and an
`independent_verification` reference to `result.json` relative to that gate.
The manifest/float path fields are absolute recorded locations; they do not use
the child-result relative base. The new adapter should explicitly bind the
existing child result and require:

- `PASS_CFA_CONVERSION_AND_PROVENANCE`, `fixture_only=false`, sample_count15360;
- its externally trusted manifest/float digests equal the supplied gate and
  actual admitted inputs;
- matching source-before/source-after records, source_unchanged=true, and the
  current admitted source/evidence bindings required by the bridge contract.

This is verification of already admitted provenance, not a rerun of the optical
model or another certificate format. Preserve the external CFA-gate digest as
the trust anchor; mutually agreeing rehashed descriptors do not mint authority.
Require the actual result bytes/hash and its existing source closure, rather
than checking only the gate's PASS text. Keep the new bridge executable/compiler
source set separate from the historical producer/verification sources it
consumes. Private coordinate controls must retain a distinct ineligible input
mode and may not reuse the genuine gate after mutating CFA values.

The existing wrong-authority/source/plan and same-buffer file controls can
exercise this closure; only a missing/corrupt child-result companion is needed
if absent from the final test list. No generic evidence engine is requested.
Otherwise the draft remains appropriately limited to identity-gather,
one-band, noiseless input-to-writer integration, pending genuine M194e admission.
