# M119 — capture identity from the RAW file: the teleconverter is detectable, the polariser never will be, and the profile key names a camera string that does not exist

**Agent:** M119-gear-identity. **Pinned SHA:** `a49b442` — every build, test and
cross-check number below was taken in a detached worktree created with an
**explicit sha**, not `HEAD`. Nothing under `D:\` was written. No file outside
`crates/strehl-raw/**` was modified by this milestone, except this report.

**Artefacts.** Scratch, probes and render arms live under
`C:\dev\strehl-out\M119-gear-identity\`: `probe/{ifd_probe,cipher_probe,red_control,crosscheck,byte_identity_final,depth_check}.py`,
`probe/patched-bare.ARW`, `render-final/{A-baseline,B-treatment,C-power-control}.tiff`,
worktrees `wt` / `wt-base` / `wt-final`.

---

## 0. What this milestone was for

`OpticalProfile` (`crates/strehl-core/src/optics.rs:123`) carries measured lateral
chromatic-aberration coefficients for one optical path, keyed
`a7c2-fe100gm-2xtc-x4cpl` (`optics.rs:306`). The correction is one of the
best-measured quality wins in the project — it cuts edge-localised chroma excess
by 61.0 % and 58.7 % on two subjects — and it is **switched off by default and
cannot be switched on**, because selection is by a hand-typed `STREHL_FIX_CA`
environment variable (`optics.rs:435`) and the product parses **no camera identity
at all** (SYNTHESIS facts 1592–1594, discipline 820).

The owner's commission asked for gear specifics to be **pluggable — enhancing
stacking where available, optional otherwise**. The data half shipped. This
milestone is the dispatch half: **a typed capture identity, extracted from the ARW,
exposed from `strehl-raw`, with every field `Option` so that absence is a normal
outcome and a file with no identity decodes exactly as before.**

**I did not wire dispatch.** `optics.rs` belongs to M107. This report proposes the
API; ORCH routes the wiring.

---

## 1. The verbatim strings

Unedited TSV from `cargo run --release -p strehl-raw --example identity`, at the
pinned sha:

```
file                          make  model      lens_model                                     lens_type3  lens_info        focal  f_num  max_ap
macro\bee-3-cpl\DSC00001.ARW  SONY  ILCE-7CM2  FE 100mm F2.8 Macro GM OSS + 2X Teleconverter  33094       200 200 5.6 5.6  200    5.6    5.5959187
macro\coffee-bean\DSC00016    SONY  ILCE-7CM2  FE 100mm F2.8 Macro GM OSS + 2X Teleconverter  33094       200 200 5.6 5.6  200    8      5.5959187
macro\109MSDCF\DSC00009.ARW   SONY  ILCE-7CM2  FE 100mm F2.8 Macro GM OSS + 2X Teleconverter  33094       200 200 5.6 5.6  200    11     5.5959187
macro\wrapped-text-1\DSC00001 SONY  ILCE-7CM2  FE 100mm F2.8 Macro GM OSS + 2X Teleconverter  33094       200 200 5.6 5.6  200    5.6    5.5959187
personal\stockholm\DSC02393   SONY  ILCE-7CM2  24-70mm F2.8 DG DN II | Art 024                50545       24 70 2.8 2.8    30.2   2.8    2.7979593
```

All 24 macro stacks agree in every field except `f_number` (5.6 on most; 8.0 on
`coffee-bean`, `coffee-bubbles`, `foam`; 11.0 on `109/112/113MSDCF`). Within
`bee-3-cpl`, **299 of 299 frames** produce one distinct tuple, at 0.418 ms/frame.

Four consequences, in order of how much damage ignoring them does:

- **`model` is `ILCE-7CM2`.** Not `A7C II`, not `a7c2`. The substring `a7c2` occurs
  in no file. A matcher cannot derive the model from the profile key by string
  manipulation; the correspondence must be an explicit field on `OpticalProfile`.
- **`lens_model` names the teleconverter in plain text**, and it is Sony's
  composed-path string, not a concatenation performed by this parser.
- **`lens_info` reports `200 200 5.6 5.6`** — composed focal length and composed
  maximum aperture. The body knows the TC is mounted and describes the optical path.
- **The third-party lens reads `24-70mm F2.8 DG DN II | Art 024`** — no maker
  prefix, an internal `|`, a trailing build code. Cross-vendor string formats are
  at the lens maker's whim, which bears directly on the match-rule decision.

---

## 2. The teleconverter: detectable, with a control that fires

Two independent encodings.

1. **`LensModel`** (EXIF `0xa434`) names it: `... + 2X Teleconverter`.
2. **`LensType3` = 33094** — Sony's enum for the *composed* path. Per SYNTHESIS
   fact 26: 32893 bare, 33093 +1.4×, 33094 +2×. Every corpus frame reads 33094.

**Red control** (`probe/red_control.py`). An ARW was copied to scratch — nothing was
written to `D:\` — and exactly **two bytes** re-enciphered to plant 32893. Both
readers moved together, from `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` to
`Sony FE 100mm F2.8 Macro GM OSS`. Rule 20 satisfied: there exists an input that
makes the check say "different", so the corpus's "same" carries information.

**The caveat, stated at full strength.** A census of **all 8920 ARW files under
`D:\personal`** returns exactly two lens strings: 4484 TC-rig, 4436 Sigma.
**No bare-FE-100 capture exists anywhere in the owner's library.** The decoder side
is measured; the encoder side — that the camera *writes* 32893 with the TC removed
— is inference (P7).

**The polariser is invisible.** The `-cpl` stacks and the bare stacks are identical
in every identity field. A filter in front of the lens has no electrical contact.
It reports nothing now and will report nothing later.

**This bounds the feature and it is the finding most worth arguing with.** The
shipped key names four elements; the file evidences two. `a7c2-fe100gm-2xtc-x4cpl`
**can never be fully auto-selected.** Automatic dispatch cannot honestly mean "this
capture matches the profile"; it can only mean *"body and composed lens match, and
we are choosing to assume the CPL leg does not change lateral CA enough to matter."*
That assumption is **UNDETERMINED** (P9) — M71 measured CPL effects on transmission
and uniformity, not on CA. I would not flip the default to ON until it is measured,
and the measurement is cheap: fit the same 20 ROIs on a non-CPL stack and compare
`eps_r`.

---

## 3. Proposed API for M107

Live at the pinned sha. Nothing here touches `optics.rs`.

```rust
// crates/strehl-raw/src/identity.rs, re-exported from lib.rs

pub struct CaptureIdentity {
    pub make:           Option<String>,   // "SONY"
    pub model:          Option<String>,   // "ILCE-7CM2"
    pub lens_model:     Option<String>,   // "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"
    pub lens_type3:     Option<u16>,      // 33094
    pub lens_info:      Option<[f32; 4]>, // [200.0, 200.0, 5.6, 5.6]
    pub focal_len_mm:   Option<f32>,
    pub f_number:       Option<f32>,
    pub max_aperture_f: Option<f32>,
}

impl CaptureIdentity {
    pub const EMPTY: Self;
    pub fn is_empty(&self) -> bool;
    pub fn same_gear_as(&self, other: &Self) -> Option<bool>;
}

pub fn identity(path: &Path) -> CaptureIdentity;                       // infallible
pub fn identity_from_reader<R: Read + Seek>(r: R) -> CaptureIdentity;  // testable form
```

- **`same_gear_as` is three-valued on purpose, and `None` must not be collapsed to
  `bool` at the call site.** `None` means "not enough evidence". The errors are
  asymmetric: a false "no" silently disables a 61 % quality win; a false "yes"
  applies one photographer's measured aberration to a stranger's glass at full
  strength — fact 1594's failure mode, and it completes successfully. If M107 wants
  a `bool` he must write `== Some(true)` and be seen to do it.
- **It compares `model` (verbatim) and `lens_type3` only**, and in that order, so a
  foreign body can never reach an offset validated on one body (P10). Per fact 26 it
  ignores `lens_model`, `focal_len_mm`, `f_number`. P4 strengthens that prohibition.
- `identity()` is infallible and never panics: rubbish, truncated, empty, JPEG and
  nonexistent inputs all return `EMPTY`. **Absence is normal**, per the commission.
- It seeks a few hundred bytes rather than pulling a ~50 MB frame; 0.418 ms/frame.
- **It is deliberately not a field on `Frame`.** `strehl-cli/src/stack.rs:1638`
  builds `Frame { … }` as a struct literal, so a new field would force an edit to
  another agent's file. A free function also keeps the change provably off the
  decode path.
- **What `OpticalProfile` needs, from M107 and not from me:** two fields, e.g.
  `match_model: Option<&'static str>` = `"ILCE-7CM2"` and
  `match_lens_type3: Option<u16>` = `33094`. Per P2 the key string cannot be
  reverse-engineered into them.

**Deciding what constitutes a match is ORCH's decision, not mine.** This milestone
supplies the strings and one conservative predicate.

---

## 4. Licence

**No dependency was added. The parser is `std` only.**

Surveyed: `kamadak-exif` (MIT/BSD-2 — clean, but exposes no Sony maker-note lens
fields, so it reaches `Make`/`Model` and stops short of the load-bearing tag),
`nom-exif` (MIT), `quickexif` (MIT), **`rexiv2` (GPL-3.0 — refused on sight** per
`AGENTS.md`). `rawler` 0.7.2 is already linked (LGPL-2.1, link-only, source not
read) and its `raw_metadata` surface does not expose lens identity at all. This
feature therefore adds no licence obligation of any kind.

**Provenance of the Sony decipher, since that is where a reviewer should press.**
`LensType3` lives at offset `0x0009` of maker-note tag `0x940c`, little-endian
`u16`, **after deciphering** — not `0x9050`, a different enciphered block. The
substitution was **derived, not copied**: `exiftool -v3` prints raw and deciphered
forms of tag `0x9403` (raw `98 23 00 00` → deciphered `9e 3e 00 00`), from which
`c = p³ mod 249` was hypothesised (a permutation, since 249 = 3·83 and
gcd(3,2) = gcd(3,82) = 1), verified by hand on both bytes, then tested against 24
stacks and a planted red control. The shipped table is generated at compile time by
a `const fn`; **no 256-entry literal ships**. Tag IDs, offsets and enum values are
uncopyrightable facts per `AGENTS.md`; the ExifTool Perl was never opened.

---

## 5. Verification

### 5.1 Cross-check against a second reader — read the coverage, not the count

`probe/crosscheck.py`, Rust parser vs `exiftool -T`, over both ends of every macro
stack plus three non-macro sets:

```
field        n    distinct   values
make         52      1       SONY
model        52      1       ILCE-7CM2
lens_model   52      2       "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter" ; "24-70mm F2.8 DG DN II | Art 024"
lens_type3   52      2       33094 ; 50545
lens_info    52      2       "200 200 5.6 5.6" ; "24 70 2.8 2.8"
focal        52      6       200 ; 30.2 ; 40.8 ; 55.8 ; 56.2 ; 70
f_number     52      4       11 ; 2.8 ; 5.6 ; 8
max_ap       52      2       2.7979593 ; 5.5959187
```

**52 files × 8 fields = 416 comparisons, 0 disagreements, none vacuous** (every
field is populated on every file, so no comparison was an agreement on absence).
**Distinct values covered: 20, across 1 camera body and 2 lenses.**

**Lead with the 20.** 416 is an honest count of comparisons and a dishonest
impression of independence: the parameter moved (52 files) while the values did
not. What was established is that the parser is **deterministic** across the corpus
and **correct** against twenty values from one body. Coverage is the smaller number
and it is the one that bounds the claim.

The harness has power: feeding it rust(patched) vs exiftool(original) yields
DISAGREE.

*(An earlier message to ORCH said 56 files / 448 fields. Several stacks hold a
single frame, so first-and-last collapses to one file; 52 / 416 is correct.)*

### 5.2 The change alters no output byte

`probe/byte_identity_final.py`. Three arms, full invocation recorded per rule 47.
Command in every arm: `strehl.exe stack D:\personal\macro\wrapped-text-1 --limit N
--gate 4.0 --out <arm>.tiff`, with `STREHL_CACHE_DIR` set to a **private** directory
and `STREHL_FIX_CA` / `STREHL_WARPMAP` / ALIGN / SMOOTH / PHOTOMETRIC all unset.

| arm | binary | `--limit` | sha256 | bytes |
| --- | --- | --- | --- | --- |
| A baseline | `wt-base` (`8a46b47`) | 12 | `0e48537e756805ab04574c6c073006f17792ffb80e0cbced2210853921709f6c` | 49 449 626 |
| B treatment | `wt-final` (`a49b442`) | 12 | `0e48537e756805ab04574c6c073006f17792ffb80e0cbced2210853921709f6c` | 49 449 626 |
| C power control | `wt-base` (`8a46b47`) | 11 | `5a737b5e5a722d8cd315b8eb82619aa88bd65f7630e90c4f917031b6dc4c7b69` | — |

**A == B** and **A != C**: byte-identical, and the comparison can tell renders
apart. The hash is `hashlib.sha256` over `open(path,"rb").read()` — the file's
literal bytes, no decoder in the path.

### 5.3 Build and test, at the pinned sha

Detached worktree `wt-final` at **`a49b442`**:

- `cargo build --release --workspace` — **green**, with `Compiling strehl-core /
  strehl-plugin / strehl-raw / strehl-cli` present in the log (rule 33).
- `cargo test --release --workspace` — **469 passed, 0 failed, 1 ignored.**
- Baseline at `8a46b47` — **454 passed, 0 failed, 1 ignored.** Delta **+15**, all
  mine (`strehl-raw` 11 → 26). No regressions. **The brief's stated baseline of 449
  was already stale.**
- `cargo clippy --release -p strehl-raw --all-targets` — clean, exit 0.

Every pass/fail gate was read from `subprocess.run().returncode` in Python or
captured into `$code` in a separate statement — never through a truncating
pipeline (rule 46).

---

## 6. Exposure to the PIL 16-bit-RGB narrowing hazard

**M119 is NOT EXPOSED. No statistic in this milestone reads pixels.** Its five
pre-existing probe scripts contain no `Image.open`, no `numpy` and no image library
of any kind; the only file-level comparison is §5.2's byte hash, taken upstream of
every decoder. **Input provenance audited rather than assumed**: every absolute path
read is a camera original under read-only `D:\personal`, an executable built by this
milestone, or an output written by `strehl.exe` in-run. Nothing came from another
milestone's scratch directory. The red control's ARW copy is a byte-for-byte
`open(...,"rb")` copy — no decoder there either.

Two earlier reasons offered to ORCH were withdrawn when the triage rules they
rested on were retracted; the reason above is the durable one and is unaffected by
the retractions. **P17 was withdrawn for the same reason and is replaced by P17′.**

### 6.1 The hazard measured on `strehl`'s own output

`probe/depth_check.py`, on the §5.2 render arms:

```
A-baseline.tiff   tifffile = uint16 (2344,3516,3)  min=92  max=10221  levels=9998
                  PIL      = uint8   mode=RGB                          levels=40
B-treatment.tiff  identical to A on both readers          sha256 0e48537e756805ab…
C-power-control   tifffile = uint16 min=115 max=10236 levels=9998 ; PIL 40
                                                          sha256 5a737b5e5a722d8c…
```

**9998 → 40 distinct levels: a 250× loss, on a file the pipeline actually ships**,
worse than the 241× measured on a full-range controlled file. The render occupies
`92..10221`, about **15.5 % of full scale**, and PIL's 8 bits are spread over
`0..65535`; a file confined to the bottom sixth of the range therefore keeps only
~40 of them. Byte hashes are unaffected, because they never decode.

---

## 7. Facts

Grades are strict. MEASURED means a number was read off a run; ARGUED means
inference from measured things; UNDETERMINED means not established.

- **P1 — MEASURED.** All 24 corpus macro stacks report `Make`=`SONY`,
  `Model`=`ILCE-7CM2`, `LensModel`=`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`,
  `LensType3`=33094, `LensInfo`=`200 200 5.6 5.6`, `FocalLength`=200 mm,
  `MaxApertureValue`=5.5959187. Only `FNumber` varies (5.6 / 8.0 / 11.0). Within
  `bee-3-cpl`, 299/299 frames give one distinct tuple.
- **P2 — MEASURED.** The camera's `Model` string is `ILCE-7CM2`; the substring
  `a7c2` from the profile key occurs in no file. A profile cannot be matched to a
  capture by manipulating its key.
- **P3 — MEASURED.** A census of all **8920** ARW files under `D:\personal` yields
  exactly two `LensModel` strings: 4484 TC-rig, 4436 `24-70mm F2.8 DG DN II |
  Art 024` (`LensType3`=50545, same body). **No bare-FE-100 capture exists in the
  owner's library.**
- **P4 — MEASURED, sharpening fact 26.** `LensType` reads 65535 on all 24 stacks
  (uniformly useless). `LensType2` reads 0 on 22 of 24 but **the correct 33094 on
  2 of 24** (`flat-fields`, `wrapped-text-1`). That is worse than uniformly
  useless: a spot-check on the wrong stack would find it apparently working.
  `LensType3` was correct on 24/24.
- **P5′ — MEASURED** *(replaces the earlier P5 framing)*. Rust-vs-exiftool
  agreement: **52 files × 8 fields = 416 comparisons, 0 disagreements, none
  vacuous**; **20 distinct values covered, across 1 body and 2 lenses**. The file
  count demonstrates repeatability; the distinct-value count bounds coverage and is
  the honest headline.
- **P6 — MEASURED.** The 2× teleconverter is doubly encoded: named in `LensModel`
  text, and distinguished by `LensType3` (32893 / 33093 / 33094). A two-byte
  re-encipherment of a scratch copy moved both readers from the TC string to the
  bare string together.
- **P7 — ARGUED.** That a genuine bare-FE-100 capture would report 32893. The
  decoder is measured; the encoder is inferred, because per P3 no such capture
  exists to test. Supported by the body composing 100→200 mm and f2.8→f5.6.
- **P8 — MEASURED.** The circular polariser is undetectable: `-cpl` and bare stacks
  are identical in every identity field. **Corollary (ARGUED):** the shipped key
  `a7c2-fe100gm-2xtc-x4cpl` can never be fully auto-selected.
- **P9 — UNDETERMINED.** Whether lateral CA measured *with* the X4 CPL may safely be
  applied to a capture *without* it. This is the load-bearing unknown between
  default-OFF and a safe default-ON.
- **P10 — ARGUED.** That offset `0x0009` of tag `0x940c` denotes `LensType3` on Sony
  bodies generally. Verified on **one** body. On another body the same offset could
  be read as a confident, wrong lens ID — fact 1594's shape relocated into this
  module. Mitigated by `same_gear_as` requiring `model` first.
- **P11 — MEASURED.** Adding the parser changes no output byte: A == B at sha256
  `0e48537e…`, 49 449 626 bytes, with power control A != C (`5a737b5e…`). Full
  invocation in §5.2.
- **P12 — MEASURED.** Identity extraction costs **0.418 ms/frame** over 299 frames,
  by seeking rather than decoding.
- **P13 — MEASURED.** The test baseline at `8a46b47` is **454 / 0 / 1**, not the 449
  stated in the brief.
- **P14 — MEASURED.** M119's render-invariance proof compares `sha256` over the
  file's literal bytes, no image decoder, so it is unaffected by the PIL narrowing;
  its power control fires, so the comparison is live rather than vacuous.
- **P15 — MEASURED.** `experiments/M114-ca-verify/src/r10a_crop_locate.py` is a
  false positive on the PIL hazard list. Its TIFF pixels come from
  `tifffile.imread` (`:33`, `:125`, narrowing via an explicit `>> 8`); its
  `Image.open` at `:70` reads an 8-bit PNG contact sheet (`PAT` = `ZOOM-*.png`,
  `:30`) for tile-layout segmentation only.
- **P16 — MEASURED.** The 61.0 %/58.7 % edge-chroma figures are unexposed on all
  three independent paths that produced or checked them: M110 original
  (`ca_decile.py:43`, `ca_camera_space.py:22-23`, `ca_matrix_test.py:38`,
  `ca_overshoot.py:150-151`), the V-CA re-derivation (`v1_band_sensitivity.py:53-54`,
  `v2_blur_and_edges.py:36-37`, `v3_green_tail.py:20-21`) and M114 adjudication
  (`r4`, `r8`, `r9`, `r9b`, `r10b`–`r10e`, `r11`) — every one via `tifffile.imread`.
  `M110-sheet/sheet.py:625-632` documents the hazard and asserts dtype;
  `M110-sheet/pil_exposure_check.py:82` independently concludes no M110 number is
  exposed.
- **P17 — WITHDRAWN.** It argued that the 61.0 %/58.7 % figures would compress
  toward zero under narrowing *because they are a small-over-large ratio*. That
  premise was ORCH's triage rule, since retracted. **Do not fold it.**
- **P17′ — UNDETERMINED** *(replaces P17)*. Edge-localised chroma excess is a
  dispersion statistic and would therefore be materially damaged by the narrowing,
  but **the direction of that damage on an on/off ratio is not established** — the
  2.8× rms degradation was measured on a different estimator. The question is
  counterfactual and moot in practice, since P16 measures the chain as unexposed.
- **P18 — MEASURED.** PIL narrowing on a real `strehl` 16-bit RGB output
  (`render-final/A-baseline.tiff`, 2344×3516×3): `tifffile` gives `uint16`, **9998**
  distinct levels, occupied range **92..10221**; `np.asarray(Image.open(p))` gives
  `uint8` / `mode=RGB`, **40** distinct levels — a **250×** loss, exceeding the 241×
  measured on a full-range controlled file. Byte hashes unaffected (A and B both
  `0e48537e…`; C `5a737b5e…`).
- **P19 — ARGUED.** `strehl`'s outputs are systematically low-occupancy — the render
  above fills 15.5 % of full scale, because macro subjects are rarely near
  saturation — so **the project's own artefacts sit in the worse-than-headline
  regime for this hazard by default rather than by accident.**

---

## 8. Disciplines

- **A.** A hardware-keyed profile must ship its identification alongside its data,
  and the identification must denote the **composed** optical path — the lens and
  everything electrically behind it, never the elements in front, which are mute.
- **B.** A gear-match predicate must be three-valued, and "unknown" must be
  un-collapsible at the type level. Matching wrongly applies a stranger's aberration
  at full strength and succeeds; matching too weakly only withholds a feature.
  Asymmetric consequences must not share a return type with `bool`.
- **C.** Derive a vendor's obfuscation as a formula with a test, not as a copied
  table. Five lines of `const fn` with a stated derivation, plus a red control that
  plants a known value, is smaller, re-checkable from a licence-clean source, and
  has power. A pasted table has none of those properties.
- **D.** When the claim is "these two outputs are identical", hash the file's bytes,
  never a decoded array. A decoder sits between you and the evidence and can only
  remove information; every bit it drops is a difference the test can no longer see,
  and the resulting false "identical" is indistinguishable from a real one.
- **E.** A triage list must be read before it is broadcast, and must state its own
  false-positive rate. A false positive on a *shared* reader costs more than a miss
  on a leaf script: the miss leaves one number wrong; the false positive recruits
  several agents to break working code and re-run correct work, and the damage
  arrives dressed as diligence.
- **F.** Narrow bit depth in the source, never in the reader. `(tifffile.imread(p)
  >> 8)` and PIL's silent `uint8` produce the same array; the difference is entirely
  that one is visible to a reviewer at the point it happens.
- **G.** Report a verification's **distinct-value coverage beside its comparison
  count**, and lead with the smaller. A large count over a homogeneous corpus proves
  determinism and is routinely read as proving correctness. The two diverge exactly
  when the corpus was convenient rather than chosen — which is the normal case,
  since a corpus is usually whatever files existed. *(ORCH's control-saturation tell,
  generalised from sweeps to verification harnesses: a comparison count that keeps
  rising while the distinct-value count stands still.)*
- **H.** A hazard grep must be filtered by what happens to the return value, and its
  false-positive count reported with it. Four distinct false-positive classes were
  observed in one night: `com`*`pil`*`ing` in build logs; `Image.open` used for tags
  or layout only (`ca_radial.py`, `r10a_crop_locate.py:70`); docstrings *warning*
  about the hazard (`sheet.py:625`); and probes written to *demonstrate* it
  (`pil_exposure_check.py`). Every one reads as a hit.
- **I.** A triage rule that over-clears is worse than no rule. An agent with no rule
  goes and measures; an agent with a clearing rule stops. Both retracted rules failed
  in the same direction — offering protection to statistics that did not have it —
  and each stopped work that should have continued.

---

## 9. Negative results and surprises

Recorded because negative results are this project's least-supplied commodity.

- **The Sony maker note has no header.** The first probe expected the documented
  `"SONY DSC\0"` magic and found nothing. Measured reality: it is a **bare IFD** —
  the first `u16` at the note offset reads 112, an entry count — with value offsets
  relative to the TIFF base. The spec-shaped parser was wrong on real files.
- **`0x9050` is the wrong block.** It is the tag most often named in connection with
  Sony lens data, and real time went into it. It is a *different* enciphered block;
  its offsets `0x09` / `0x4b` / `0x71` hold other things. The field is in `0x940c`,
  found by dumping the parse tree empirically rather than by reasoning.
- **HEAD moved mid-session.** Two `git worktree add … HEAD` calls twenty minutes
  apart produced `e49281f` and `8a46b47`. Recovered by proving
  `git diff --name-only e49281f 8a46b47 -- crates Cargo.toml Cargo.lock` empty, then
  re-running the byte-identity proof against an explicit sha. **Name the sha.**
- **`exiftool -fast2` silently drops maker notes.** The first census printed
  `LensType3` = `-` for every file and looked like a null result. It was a flag.
- **`LensType2` reads correctly on 2 of 24 stacks** and is otherwise 0. Unexplained,
  not chased; folded as P4 because a partially-working field is a trap, not a dud.
- **`Get-ChildItem -Recurse` over `D:\personal\macro`** surfaces
  `flat-fields/subject-focus-sweep-with-cpl/`, so the parent-directory label is not
  the stack name.
- **The corpus contains no counter-example.** P3 is the most uncomfortable number
  here: every discriminator is validated on one lens pair plus one planted file.
  **Twenty frames of anything shot with the TC off would upgrade P7 from ARGUED to
  MEASURED** — the cheapest evidence upgrade available to this workstream, and it is
  a request for the owner rather than a task for an agent.
- **Big-endian (`MM`) containers** are exercised only by a synthetic test; the corpus
  is `II` throughout.

---

## 10. What is left open

1. **P9** — does the CPL change lateral CA? Blocks any safe default-ON.
2. **P7** — a real bare-lens capture would settle the encoder side.
3. **P10** — the `0x940c[0x0009]` offset on a second Sony body.
4. **The match rule itself** — exact equality, normalisation, or scoring. ORCH's
   decision; §1 supplies the strings it should be made on.
