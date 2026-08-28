# DELIVER-V6 — banked delivery record for all 33 masters

Written before the lane's non-deliverable scratch was reclaimed, so that every
number below survives the deletion of the files it was measured from. The
masters themselves are the shipping product and are retained.

## Reproduction recipe

```
exe        : C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe
exe SHA256 : 2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7
exe build  : strehl 0.0.0 (6af834dac08d)
commit     : 6af834dac08d6605aee7ea3ad75809fdf6313770
sources    : D:\personal\macro\<subject>   (READ-ONLY)
invocation : <exe> stack <dir> -o <out>\<subject>.tiff --srgb
env        : STREHL_CACHE_DIR=<private>; all other STREHL_* unset
driver     : experiments/DELIVER-V6/render.ps1  (26)
             experiments/DELIVER-V6/render-list.ps1 -Tag A|B|C  (7)
```

**The binary is deterministic end to end.** ORCH independently rendered the same
seven subjects with this exe between 02:36 and 02:47; DELIVER-V6 re-rendered them
between 03:38 and 03:50 in three concurrent streams. All seven came out
**byte-for-byte identical, whole-file SHA256 including container metadata**. A
fixed binary reproduces exactly; it is a *moving tree* that does not.

That comparison was re-run immediately before ORCH's copies were reclaimed:
**7 of 7 identical**, same byte count, across a different concurrency (1 stream
vs 3), a different cache directory and a different hour. The seven SHA256 values
in the table below are therefore the output of *two* independent runs, so the
proof outlives the deleted copies. This bounds corpus fact 1886 usefully: the
33,003,417-pixel drift it records is attributable to the tree moving under the
build, not to nondeterminism in the pipeline. Pin the binary and absolutes hold.

## Commissioning control for the tag reader

`experiments/DELIVER-V6/tagcheck.py` refuses to certify anything unless it first
reads the defect in a file known to have it. That control file lives outside the
protected paths and may be reclaimed by another lane, so it is identified here:

```
path   : C:\dev\strehl-out\marker.tif   (rendered 2026-08-23, predates ICC fix 96b7e119)
bytes  : 49505882
sha256 : E9ED246B8FCB09F06DAA8606C33536D0828AC9C65936ED462877132244A3DAB2
reads  : ICC 34675 ABSENT | XResolution 1/1 | ResolutionUnit 1 (none)
```

If it is gone, any TIFF written by strehl before 2026-08-26 11:27 carries the same
signature and will serve. ORCH-FAITHFUL masters will **not** — they postdate the fix.

## Per-subject record

ICC/DPI columns are read from the delivered bytes by BUILD-OUTPUT's raw-IFD
parser, not from the code and not from the run log.

| subject | set | frames | ISO | secs | bytes | ICC | dpi | unit | output SHA256 |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| `109MSDCF` | corpus-26 | 22 | — | 16.4 | 197801290 | 2716 B | 300/1 | inch | `A8448B5E99445D0071B3CFA5A8802F5C3EEA700421EDDE19F52C99C10B5E8D59` |
| `112MSDCF` | corpus-26 | 79 | — | 70.6 | 197801290 | 2716 B | 300/1 | inch | `5AE988996541476CF74FD9FA1E0844E807C1A6A0452AFEA087F6BD21A75B9B24` |
| `113MSDCF` | corpus-26 | 63 | — | 47.5 | 197801290 | 2716 B | 300/1 | inch | `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F` |
| `119MSDCF` | corpus-26 | 33 | — | 31.8 | 197801290 | 2716 B | 300/1 | inch | `65AE95D15061EA455C239EC47CEC094A6461D1BD42A900A4139630499B162B9B` |
| `bee-1-cpl` | corpus-26 | 299 | — | 241.6 | 197801290 | 2716 B | 300/1 | inch | `AF54EAF542BB673E5150F0DD0AA607134B734C4BFBF2C49063702615E411F89B` |
| `bee-2-cpl` | corpus-26 | 299 | — | 362 | 197801290 | 2716 B | 300/1 | inch | `51CC51DE1A464188491AF5C8B5492B1B019EAD427B4A4AFFE5904AC912C323DF` |
| `bee-3-cpl` | corpus-26 | 299 | — | 197.5 | 197801290 | 2716 B | 300/1 | inch | `B1E8BB72B2F5E38FF31A86F5351CF286451A0B952AE28DA57AFB818B4C995A27` |
| `chia-seeds-cpl` | new-7 (stream C) | 130 | 50 | 158.3 | 197801290 | 2716 B | 300/1 | inch | `2320CB71A790C41CD050889C87EDECB45417EACF5354901E03F3985D420905A8` |
| `coffee-bean` | corpus-26 | 105 | — | 125.4 | 197801290 | 2716 B | 300/1 | inch | `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC` |
| `coffee-bubbles` | corpus-26 | 19 | — | 31.2 | 197801290 | 2716 B | 300/1 | inch | `6FE6A4903CD7C744EFB2C1334E69B93B63F5DD924109AE63DC74998CEB374CAA` |
| `couch-fibers-cpl` | corpus-26 | 299 | — | 223.4 | 198026314 | 2716 B | 300/1 | inch | `9E37B3CE22A2BFEC1D62CABAD8454420DECA0ACAD57E6E695E68BC8B1E33EC42` |
| `dime-flat-narrow-slices-cpl` | new-7 (stream A) | 207 | 100 | 187.7 | 197801290 | 2716 B | 300/1 | inch | `E5798BC7899288F187F6771268ACF8CC76FA147943FA80DE9190EA81C8503399` |
| `dry-erase-marker-head-cpl` | corpus-26 | 299 | — | 264 | 198026314 | 2716 B | 300/1 | inch | `1AC15798B29B27FC8A1F5ABD4E8D2199DA1CDF471D53AD862B49C024063C51EF` |
| `duck-tape-side-layers-cpl` | new-7 (stream B) | 197 | 50 | 209.9 | 197801290 | 2716 B | 300/1 | inch | `00043B3812E03062BA9B820B6BFA22FBC5A527EDB2E5CA4AE45E14435AA0C7EE` |
| `flat-on-ruler-cpl` | corpus-26 | 79 | — | 76.6 | 198026314 | 2716 B | 300/1 | inch | `F5F15FF96A819C5E2BE0A38675E6FB6075FFAEA8EF30F32A43CDF09F6D3A1D1A` |
| `flower-bud-alone-cpl` | corpus-26 | 205 | — | 163.1 | 198026314 | 2716 B | 300/1 | inch | `63D8C4EFBB12DB42DB647C2028DA57C5FB4C814279E436E442625A3361F29AAB` |
| `flower-bud-with-background-fern-cpl` | corpus-26 | 299 | — | 276.5 | 198026314 | 2716 B | 300/1 | inch | `96199EA134CE19E2F9B6E3C9DF9A6B201553592CAF8C7BB332AF2E0D4D855B46` |
| `flower-inner-edge-cpl` | corpus-26 | 299 | — | 306.9 | 197801290 | 2716 B | 300/1 | inch | `9B4C4204B4A1DDBEDF73834FD805D648E15BC416F51A014E43981E1BDD62160E` |
| `flowers-cpl` | corpus-26 | 176 | — | 143.6 | 198026314 | 2716 B | 300/1 | inch | `E5DCCB8FAF61372BA743481B5FF8997EA7AA7FF6A1B89EBBBD3B5E507B5237C8` |
| `foam` | corpus-26 | 100 | — | 98.6 | 197801290 | 2716 B | 300/1 | inch | `76270C86E292A3419CA7C9B4D206E5660DC5C82D48E02E8319474C9093A2E365` |
| `highly-angled-ruler-mm-cpl` | corpus-26 | 299 | — | 63 | 198026314 | 2716 B | 300/1 | inch | `DE48DA8F8697BB7EC24931AD23DA749FDA3B9C4B3D6B98AA302DC4810341AE6B` |
| `lavendar-cpl` | corpus-26 | 299 | — | 265.4 | 198026314 | 2716 B | 300/1 | inch | `07ACE285A00C0C8215838672735CE8C3A426DADEC49F7F02FB6AD78E448E68B6` |
| `lead-1-cpl` | corpus-26 | 123 | — | 171 | 198026314 | 2716 B | 300/1 | inch | `293480F6A7A6420C81403ECE5389E9903186FB361A763BC652979D3B2616A4EA` |
| `leaf-2-cpl` | corpus-26 | 182 | — | 185.8 | 198026314 | 2716 B | 300/1 | inch | `77C857DD900779611B1E4F34FA5EF5D2EAFE260DD70F79E5CC1FC08DC768A90C` |
| `maldon-sea-salt-cpl` | new-7 (stream A) | 255 | 50 | 315.1 | 197801290 | 2716 B | 300/1 | inch | `6E29C074238A15FA66306DF1AB847FB0798FECE2BED4B324FF2A6AA504673E07` |
| `medication-pill-cpl` | new-7 (stream C) | 146 | 50 | 179.8 | 197801290 | 2716 B | 300/1 | inch | `4E9F6675B067B456DBF9EFBC17D4B168E35693BA6F382733D3BE2DEF8BEC8EC5` |
| `pencil-flatter-angle-cpl` | corpus-26 | 299 | — | 336.6 | 197801290 | 2716 B | 300/1 | inch | `918F7FD7F6FC31C6F407E82B770605E7FC6A676BBBED00A537F1CF6AEBE7B7B8` |
| `pencil-steep-angle-cpl` | corpus-26 | 299 | — | 406 | 197801290 | 2716 B | 300/1 | inch | `9BAFE727979AD3104428F2E3CE859FA2F37571BF1C085F71DFFF8A0A9FF5133A` |
| `pottery-art-glazed-cpl` | new-7 (stream C) | 123 | 50 | 116.4 | 197801290 | 2716 B | 300/1 | inch | `863E477000E9B54033DD9A11C9855380D51CA7C952D6520147E9B34469FF979A` |
| `tweezers-cpl` | corpus-26 | 100 | — | 166.9 | 198026314 | 2716 B | 300/1 | inch | `72392AFFAAD1B72F95EFD60C0C598E4133150FDFC10A48D9C7DD0E619EF6822E` |
| `unpopped-popcorn-kernels-cpl` | new-7 (stream B) | 234 | 50 | 277.1 | 197801290 | 2716 B | 300/1 | inch | `A7C6555900FB5DD63343BF8594F4AB5B6332AC35596CABBE89E386E3B29EEC26` |
| `wrapped-text-1` | corpus-26 | 130 | — | 165.3 | 197801290 | 2716 B | 300/1 | inch | `F8FCA99B692129B34207FFB80583B350447910B080D276AF8A465C4CEB10B139` |
| `wrapped-text-2` | corpus-26 | 120 | — | 163.5 | 197801290 | 2716 B | 300/1 | inch | `539579182778DDA3224F783B1E982246F789E0D032B7961C956B7CB8ED6BD399` |

ISO is recorded only for the seven new subjects; the 26 predate the manifest
field. Six of the seven are **ISO 50**, below the shipped noise profile's ISO 100
calibration floor, so every gate that divides by sigma is extrapolating on them.

## Alignment disposition, seven new subjects

```
chia-seeds-cpl                 ON (solved), reference frame 65, 130 placed / 0 refused, 18.6 s
dime-flat-narrow-slices-cpl    ON (solved), reference frame 103, 207 placed / 0 refused, 31.9 s
duck-tape-side-layers-cpl      ON (solved), reference frame 98, 197 placed / 0 refused, 29.1 s
maldon-sea-salt-cpl            ON (solved), reference frame 127, 255 placed / 0 refused, 63.5 s
medication-pill-cpl            ON (solved), reference frame 73, 146 placed / 0 refused, 44.0 s
pottery-art-glazed-cpl         ON (solved), reference frame 61, 123 placed / 0 refused, 16.8 s
unpopped-popcorn-kernels-cpl   ON (solved), reference frame 117, 234 placed / 0 refused, 63.0 s
```

Every new subject solved an alignment and placed **every frame, none refused**.

## Clipping and crush

Full per-subject, per-channel census in `data/clip-census-33.txt`. Reported as
numbers, never as a verdict: `orch_printready.py`'s clip gate measures the sRGB
gamut wall, not the tone scale, and it failed the one master in the corpus with
zero blown highlights.

## Sheets

```
D:\strehl-out\DELIVER-V6\corpus-all33\sheet-00..10.jpg   all 33 subjects
D:\strehl-out\DELIVER-V6\corpus-new7\sheet-00..02.jpg    the 7 new subjects
D:\strehl-out\DELIVER-V6\corpus\, corpus-registered\     the 26, CA before/after
D:\strehl-out\DELIVER-V6\ca-ab\                          magenta A/B crops
```

**Sampling:** tiles are 520 px crops taken at native resolution and pasted without
scaling, so one image pixel is one sheet pixel. No zoom, no resampling. Generator
is the committed `experiments/ORCH-drift-check/orch_corpuseye.py`, which this lane
verified reproduces ORCH-EYE's `sheet-00.jpg` byte-identically before use.

## What was reclaimed, and what was kept

Deleted, because every measurement taken from it is written down above:

- `masters\..\orch-rendered-7\` — ORCH's duplicate copies of the seven new
  subjects. Proven byte-identical to the delivered masters, so they carried no
  information the masters do not.
- `view-new7\` — NTFS hardlinks into `masters\`. Reported ~1.29 GB by size but
  occupied no additional blocks; deleting it reclaims approximately nothing and
  is **not** counted as space recovered.
- `scratch\` — warpmap caches, already near zero.

Kept, deliberately:

- `masters\` (33 TIFFs) and `bin\strehl.exe` — the shipping product.
- `bin\strehl-caold.exe` — the old-coefficient control binary, 9.4 MB. Cannot be
  reproduced without another clean worktree build; the entire before/after
  magenta comparison rests on it.
- All manifests, logs, banners, JSON and sheets. Text and JPEG, 0.07 GB total.

Measured, by directory:

```
before   C: 8.6793 GB   D: 0.0703 GB   total 8.7496 GB
after    C: 6.1000 GB   D: 0.0703 GB   total 6.1703 GB
logical difference                            2.5793 GB
of which hardlinks (view-new7), freeing nothing 1.2895 GB
genuinely reclaimed                            1.2898 GB
```

**The honest number is 1.29 GB, not 2.58 GB.** `view-new7` was a directory of
NTFS hardlinks into `masters\`, verified with `fsutil hardlink list` (2 links per
file) before deletion; it inflated any recursive byte count but occupied no
blocks of its own. The C: volume free-space delta across the purge was 1.646 GB,
which is *larger* than this lane reclaimed because sixteen other lanes were
freeing scratch at the same time. Volume free space is not attributable to one
lane during a concurrent purge; the directory measurement is.

The remaining 6.17 GB is the deliverable itself and is on the protected list.
After the purge all **33 masters re-hashed clean against the table above (33 OK,
0 mismatch, 0 missing)** and both pinned binaries still match their recorded
SHA256 — deleting the hardlinks did not touch the product.
