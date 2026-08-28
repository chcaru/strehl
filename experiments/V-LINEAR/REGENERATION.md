# V-LINEAR — regeneration recipe for deleted scratch

**Status: the pixels are gone; the numbers are not.** This lane deleted every
developed linear TIFF it held, to return disk to the owner. This file plus
`develops-manifest.json` is what makes that deletion recoverable rather than
destructive.

Nothing this lane measured lived only in those TIFFs. Every band verdict is in
`experiments/V-LINEAR/bandsweep*.json`, committed; every claim built on them is
in `docs/research/V-LINEAR-BANDS.md`, committed and checked by 804
cell-anchored assertions.

## What was deleted

**Deleted last, and byte-verifiable.** SHA256 and byte length of every frame is
banked in `develops-manifest.json` (374 entries), so a rebuild of these two can
be proved byte-identical rather than merely plausible. These are the only two
subjects in the corpus licensed at 0.30-0.35 cyc/px, which is why they were
kept longest and hashed before removal.

| subject | develops | size (MEASURED) | source, READ-ONLY, verified present |
| --- | --- | --- | --- |
| `bee-1-cpl` | 299 | 55.08 GB | `D:\personal\macro\bee-1-cpl` — 299 .ARW, 10.55 GB |
| `dry-erase-marker-head-cpl` | 75 | 13.83 GB | `D:\personal\macro\dry-erase-marker-head-cpl` — 299 .ARW, 18.72 GB |

**Deleted earlier in the same session, before the manifest existed.** These are
regenerable from the same recipe but are **not** byte-verifiable, because no
hash of them was taken. That is a real asymmetry and it is stated rather than
hidden. Total across all six paths: **55.36 GB (MEASURED in aggregate; the
per-path figures were printed at deletion time and not banked, so no per-subject
size is claimed here).**

```
D:\strehl-out\V-LINEAR\r2\112MSDCF          79  .ARW source,  2.76 GB
D:\strehl-out\V-LINEAR\r2\lavendar-cpl     299  .ARW source, 18.72 GB
D:\strehl-out\V-LINEAR\r2\flat-fields      focus-sweep captures
D:\strehl-out\V-LINEAR\r2\coffee-bubbles    19  .ARW source,  1.19 GB
C:\dev\strehl-out\V-LINEAR\lintiff         113MSDCF, 63 .ARW source, 2.87 GB
C:\dev\strehl-out\V-LINEAR\r2\_bincheck    binary-identity probe, trivial
```

## The command

```
powershell -File experiments/V-LINEAR/r2_develop.ps1 -Key <subject>
```

`r2_develop.ps1` is committed (`d2193a55`) and parameterised: it reads
`$src = "D:\personal\macro\$Key"`, copies each frame to a private one-frame
directory, and never writes to the source. `develop_frames.ps1` is an earlier,
hard-coded variant that produced `113MSDCF` only — do not mistake it for the
general recipe.

**Binary (Rule 47):**
`C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe`,
sha256 `15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0` — the
same build V-HEADTOHEAD2 rendered its strehl arm with.

**Flags:** `stack --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic`.
**Not passed:** `--srgb`, `--binned`, `--exposure`, `--auto-exposure`,
`--limit`, `--resampler`, `--fix-ca`, `--photometric`, `--gate`, `--stats`.
**Env:** `STREHL_FULLRES_GATHER=1`, `STREHL_ALIGN=0`; every other `STREHL_*`
is cleared by name before each render.

`STREHL_ALIGN=0` matters and is not a detail. With alignment on, a one-frame
stack reports "field of view scaled to 0.9974 ... then upsampled", which is a
CatmullRom resample — it would put a resampling kernel inside a measurement
about resolution. Off, the develop is decode -> CA -> demosaic -> matrix -> u16
with nothing resampled.

## Cost to rebuild (MEASURED, §14.8)

Develop **3.2-7 s/frame** and dominates; sweep **0.65 s/frame** once develops
exist; **~189 MB/frame** on disk. So `bee-1-cpl` is **16-35 min and 55 GB**,
`dry-erase` 4-9 min, `112MSDCF` 4-9 min, `coffee-bubbles` 1-2 min.

**Correction worth carrying:** the "~4.5 hours to rebuild bee" figure that
circulated during the session, and which put these develops on a protected
list, is **not** this lane's measurement. Against the measured per-frame rate a
bee develop is well under an hour. If the 4.5 h figure is used to decide
whether to keep something, it is overstating the cost by roughly an order of
magnitude.

## The numbers these pixels produced

Recorded verbatim from the committed records, so a rebuild has something exact
to reproduce:

| field | `bee-1-cpl` | `dry-erase-marker-head-cpl` |
| --- | --- | --- |
| record | `bandsweep-far20-bee-1-cpl.json` | `bandsweep-far20-decim4-dry-erase-marker-head-cpl.json` |
| `n_real` | 299 | 300 |
| `step` | 4 | 4 |
| `decim` | 1 | 4 |
| `far_real` | 20 | 20 |
| tiles kept / confirmed | 27 / 21 | 24 / 19 |
| **0.30-0.35** | **R = 5.3109**, CI [3.0829, 7.6381], **PASS** | **R = 4.5296**, CI [3.1152, 5.9472], **PASS** |

`far` is part of a cell's identity, not a nuisance parameter: 0 of 120 record
pairs sharing a `far` differ by more than 1e-9, and 182 of 182 pairs at
different `far` differ. A rebuild compared against a record at a different
`far` will disagree for that reason alone.

These two are the **only** subjects licensed at 0.30-0.35 cyc/px. Of 34 corpus
subjects, 6 have been measured at that slice — 2 PASS, 1 FAIL(noise), 3
MARGINAL — and **28 have never been measured there at all**. Check any subject
with `python bandq.py <subject> <lo> <hi>`, which exits non-zero unless the
cell is licensed.

## Verifying a rebuild

Re-develop, then compare each frame's SHA256 against
`subjects[<key>]["files"][<name>]["sha256"]` in `develops-manifest.json`; the
directory each subject was read from is in `subjects[<key>]["root"]`. A
mismatch means the decoder changed, and the band numbers above should not be
assumed to carry over — re-run `bandsweep.py` and compare `R` before quoting
anything.

**The manifest is commissioned, not merely written.** Before the pixels were
deleted, 6 frames drawn at random across both subjects were re-hashed with
`pwsh Get-FileHash` — a different implementation from the `hashlib` that
produced the manifest — and all 6 agreed, with a one-nibble-corrupted
expectation rejected as a live negative control.

That check caught a defect of the project's most common class on its first run.
The initial version resolved paths wrongly, `Get-FileHash` returned an empty
string, and all six positives read `BAD` — while the **negative control still
read "correct", because an empty string disagrees with everything.** A
completely dead instrument scored green on the control that existed to prove it
was alive. The fix was to require a real 64-character hex digest before a
result may count as either agreement or disagreement, which turned 6 silent
`BAD` into 6 explicit `DEAD`. Root cause: this machine's `powershell` host has
no `Get-FileHash` cmdlet; `pwsh` does. Use `pwsh` for hashing here.

## NOT MEASURED

- `leaf-2-cpl` was never band-qualified at any slice. Its develops were removed
  by another lane's cleanup mid-run; `align_image_stack` (pid 50776) then spent
  ~4.4 CPU-hours reading a directory that no longer existed and produced no
  output. Rebuilding needs a full 182-frame develop first, and
  `bandsweep.py:109` still points the subject at the removed path.
- The 28 subjects never measured at 0.30-0.35 are **UNQUALIFIED, not failing**.
  Nothing is known about them in either direction.
- The five trees deleted before the manifest existed cannot be proved
  byte-identical on rebuild, only re-measured.
