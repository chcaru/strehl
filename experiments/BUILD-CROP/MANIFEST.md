# BUILD-CROP — scratch manifest and regeneration recipe

Written at wind-down, **before** deleting scratch, per ORCH's bank-first rule.
Everything below is text so that nothing measured dies with the bytes.

All measured numbers this lane produced already live in
`docs/research/BUILD-CROP.md` (sections 6, 14, 15, 16, 17). This file records
only what the *scratch files themselves* were, so a future reader can tell
what was destroyed and how close they can get to it again.

---

## 1. Deleted artifacts, by identity

| file | bytes | SHA256 (first 32) |
|---|---|---|
| `D:\strehl-out\BUILD-CROP\chroma\m-default.tiff` | 198026309 | `2BCABD30358C68CAEF7D125868805DEA` |
| `D:\strehl-out\BUILD-CROP\chroma\m-caoff.tiff`   | 198026309 | `631D24A74F0F188763F3AC6EB6865B91` |
| `D:\strehl-out\BUILD-CROP\pin\strehl-refit508.exe`   | 9861632 | `2B2AC29A20DAAEC89A6739E2421ADFB4` |
| `D:\strehl-out\BUILD-CROP\pin\strehl-shipped704.exe` | 9861632 | `9FB3ECB2C775B14FBDB9444AFA6BAE28` |

Full SHA256 of the two pinned binaries, recorded at pin time and re-hashed
unchanged after the corpus run (also in section 17.1):

- `strehl-refit508.exe`  `2B2AC29A20DAAEC89A6739E2421ADFB4E59D3A9AC00B9C2D3E98E57D9404EF5D`
- `strehl-shipped704.exe` `9FB3ECB2C775B14FBDB9444AFA6BAE286396365FDBC8D2442977BB0142678F72`

Also deleted: five small JPEG crops (`repro.jpg`, `zoom-m-default.jpg`,
`zoom-m-caoff.jpg`, `zoom-s1-default.jpg`, `zoom-s2-caoff.jpg`, ~0.6 MB total).
`repro.jpg` and `zoom-m-default.jpg` were byte-identical duplicates
(`CDE93E9161AE493A3C6B7A8833920E70`).

## 2. What the two TIFFs were

Read from the file before deletion: **4688 x 7040 x 3, uint16, sRGB**, i.e. a
full-resolution master pair rendered with `--demosaic --srgb`. They are a
lateral-CA **A/B pair**: `m-default` with the correction at its shipping state
(default on, gear matched) and `m-caoff` with `STREHL_FIX_CA=off`.

**Subject: NOT RECORDED at render time.** It is believed to be
`dry-erase-marker-head-cpl`, the section 14 magenta subject, but I could not
confirm this from committed text or from the file, and I am not asserting it.
Treat the subject as unknown.

**Structural cause, worth fixing:** strehl's output TIFF embeds a colour-space
description but **no source directory and no build identifier** -- its
`Software` tag reads literally `strehl 0.0.0 (unknown)`. A render therefore
cannot be traced to its inputs or its binary from the artifact alone. This is
the mechanism behind unreproducible published results, not an accident of
anyone's bookkeeping.

## 3. Regeneration recipe, and why it will NOT reproduce these bytes

```
# arm A (correction at shipping default)
strehl.exe stack <SUBJECT_DIR> --demosaic --srgb --out m-default.tiff

# arm B (correction disabled)
$env:STREHL_FIX_CA="off"
strehl.exe stack <SUBJECT_DIR> --demosaic --srgb --out m-caoff.tiff
Remove-Item Env:\STREHL_FIX_CA
```

The pinned binaries are rebuildable from committed source: set
`eps_r` in `crates/strehl-core/src/optics.rs` (L461) to `-508.4e-6` or
`-704.5e-6` and build with a private `--target-dir`. The coefficient is
**compile-time**, which is why two binaries were needed rather than one.

**Critical caveat (this lane's own fact 1886).** Re-rendering will *not*
reproduce the SHA256s above. The CA-off arm is coefficient-independent and so
*must* reproduce bit-exactly, yet on re-render it differed on **33,003,417 px,
max 23210 DN**, because other lanes moved the tree underneath it. The same two
arms scored **0.15999 / 0.20807** one night and **0.11377 / 0.15576** the next.
Therefore: **orderings are reproducible, absolutes are not.** Any future
comparison must render every arm from ONE pinned build.

## 4. Where the numbers live

- Crop-vs-scale cover mode, and the border-ringing defect — sections 6, 6c
- Magenta diagnosis, and the WITHDRAWN 1.82x recommendation — section 14
- The `eps_r` re-fit and its reversal audit — section 15
- Three-arm score, cross-tree finding, green question — section 16
- Corpus verification and the tilted-subject inertness finding — section 17

## 5. NOT MEASURED (explicit gaps, not run)

- `highly-angled-ruler-mm-cpl` was never scored with `--force-tilted`, so the
  **under-corrected end of the re-fit has no control**. Reason: wind-down; no
  new measurement started.
- Three corpus subjects never scored: `113MSDCF`, `119MSDCF`, `coffee-bean`.
- The four proxy "losses" were never re-run at full master resolution, so two
  of them (fifth-decimal) remain unresolvable. Not reported as passes.
- `cacorpus.py` was never polarity-audited through its entry point: no known
  worse arm was planted and confirmed to report LOSS.
