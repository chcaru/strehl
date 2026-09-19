# Vitamin-C highlight spokes: source localization

**ARGUED photographic finding:** the conspicuous coloured fans already exist in
defocused developed source frames, while the locally focused source glints are
substantially more compact. The complete baseline keeps long coloured spokes
alongside relatively focused crystal structure. This supports investigating
which frames contribute to the highlight tails at each pyramid band. It does
not establish that the merge invented those tails, or identify their physical
origin.

**MEASURED preparation:** `scan.py` read native crops from all 70 existing RGB16
exports, using memory mapping, in 0.410 seconds. This is crop extraction time,
not stacking performance. No RAW was read or decoded; no Rust was modified.
The two windows and glint locator positions were fixed in `plan.md` before the
scan. Mean squared green gradient after 3x3 smoothing nominated index 28 for
facet-edges and index 33 for dark-inclusion. These are inspection locators,
not quality measurements or proof of best focus: the flat/noise control
deliberately demonstrates that noisy flat pixels outscore real weak structure.
The constant scored 0, weak wave 9.89e-7, noisy flat0.00142. Their brightness,
noise and clipping failure directions make these numbers inadmissible as
evidence of recovered detail.

I inspected fourteen individual native 384-square source PNGs and both frozen
baseline PNGs. The first six source views were the nominated indices±3. Root
then fixed distant indices 0,17,52,69 for both windows before those views were
extracted (`distant-plan.md`). This extension and the changed interpretation
are explicit; absence in the first six was never absence in the whole stack.

| Window | Source views | Direct visual observation |
| --- | --- | --- |
| facet-edges | 25,28,31: DSC00119, DSC00122, DSC00125 | The left-hand white glint is compact, with cyan/blue and pink edge colour and some granular structure. The transparent body and lower diagonal rim are relatively distinct. The merged image's conspicuous long, comb-like cyan/green extensions are not comparably visible in these focused views. |
| facet-edges | 0,17,52,69: DSC00094, DSC00111, DSC00146, DSC00163 | Index 0 has a blurred, multicolour scalloped glint. Index 17 is more compact. At 52/69 the left glint broadens and coloured extensions run toward lower-left and across the softened crystal. Similar long-fan structure therefore precedes stacking. |
| dark-inclusion | 30,33,36: DSC00124, DSC00127, DSC00130 | The lower-left bright strip beside the black inclusion is granular and locally coloured, but lacks the baseline's strong long radiating fan. The small bright point on the right is also compact. |
| dark-inclusion | 0,17,52,69: DSC00094, DSC00111, DSC00146, DSC00163 | Index 0 has a diffuse coloured rim; 17 is comparatively compact. At 52, and especially 69, a broad multicolour fan extends below/right from the lower-left glint. The crystal body is much less focused at the same time. The right glint also spreads in the distant frames. |

The useful distinction is **focused compact glint versus defocused coloured
fan**, not colour versus no colour. These are transparent crystals with
specular/refracted light: this check gives no permission to neutralize all
colour, and no white display pixel is evidence of sensor clipping.

## Coordinates and provenance

All indices are zero-based in the original 70-frame order; original filenames
run DSC00094.ARW through DSC00163.ARW. The exported TIFF names match those RAW
stems. The held map has reference 35, quad geometry 3516x2344, and SHA256
`84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f`.
Its bits are used only to map each reference window centre into source active
coordinates. There is no CA composition, image interpolation, rotation or
scale change in these crops. The reference active origin equals the frozen
output origin plus (56,38) native pixels. After applying the pull at the native
window centre, the source origin is rounded once to integer pixels.

| Window | Frozen output origin | Focus nomination | Original active crop origin |
| --- | --- | --- | --- |
| facet-edges | 2500,2700 | 28 / DSC00122 | 2555,2739 |
| dark-inclusion | 3050,1850 | 33 / DSC00127 | 3106,1888 |

Each crop is 384x384. `scan-1/receipt.json` records all 140 window/frame bindings,
exact transform bits, mapped fractional centres, rounded origins, locator
values, original filenames, source TIFF metadata and RGB16 crop hashes.
`distant-1/receipt.json` binds the eight follow-up crops to those same hashes.
PNG conversion is rounded division by 257, identical to the frozen baseline;
RGB16 crop sample values are also retained. No tone/exposure/WB adjustment was
applied. The two baseline PNG copies retain their frozen pixels.

Commands actually run from the repository root:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/quality-september19/vitamin-c-source-highlights/scan.py
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/quality-september19/vitamin-c-source-highlights/distant-crops.py
```

## What this does and does not settle

The exports use the actual source MHC and common fixed developer, but have no
lateral CA gather and are toned before any external RGB merge. The baseline
gathers with CA, merges CFA planes, and develops after merge. Source appearance
thus cannot isolate optics, source MHC, matrix/highlight/tone development,
alignment, or the multiscale weighting. The saved map is a correspondence aid,
not subpixel ground truth. Local scale/rotation differences remain visible.

The prior reports were checked before interpreting these views:
BUILD-HIGHLIGHT and V-HIGHLIGHT show that visually similar fringes have had
different causes, and displayed white can come from tone applied far below
RAW saturation. M109-highlights and M97c-clip-mass establish why partial-frame
pinning cannot be recovered from a post-merge equality check; that mechanism
is not measured here. M26-colour-clipping-measured separates raw DN noise from
WB-scaled colour. M54-clip-mask-measured requires real per-frame pinning and
matched bright controls, unavailable in these developed TIFFs. BUILD-CHROMA
measured longitudinal CA but rejected it as the explanation for its prior
rainbow-speckle/pink-rim cases. None of those old attributions automatically
transfers to this new crystal stack.

**Bounded next discriminator:** retain one actual-consumer highlight patch's
per-band frame contributions and compare them against focused sources 28/33 and
distant fan-bearing sources 52/69, with a neighbouring non-highlight structure
control. First test whether the baseline admits defocused coloured tails where
the focused source is smooth/dark. This would locate the relevant merge input
before proposing a new clipping threshold, CA coefficient, or desaturation
rule. The TIFF evidence alone cannot name the responsible band or consumer.

This is an author photographic interpretation, ready for root's independent
image inspection. No quality improvement, SOTA result, or general algorithm
acceptance is claimed.
