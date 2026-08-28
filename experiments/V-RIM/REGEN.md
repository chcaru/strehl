# V-RIM: regeneration recipe, and the inputs that no longer exist

*Banked 2026-08-28 during session wind-down, before deleting lane scratch.
Companion to `docs/research/V-RIM.md` (commit `15f6837d`). This file exists so
that every number in that report has a stated provenance and a stated
reproducibility status. Read the second section before trusting any of it.*

## 1. THE INPUTS ARE GONE. Measured, not assumed.

At 03:04 on 2026-08-28, during the tree-wide disk reclaim, I re-measured the
two directories every number in `V-RIM.md` was taken from:

```
C:\dev\strehl-out\ORCH-FAITHFUL\faithful   1 file,  0.00 GB, 0 tiff
                                           (render.log + an empty preview\)
C:\dev\strehl-out\acceptance\SHIP-V4     107 files, 0.00 GB, 0 tiff
                                           (26 .log, 26 .ok, 26 .out,
                                            28 .txt, 1 .tsv -- metadata only)
```

**Both master sets have been deleted.** They held the 26 shipping masters and
the 26 SHIP-V4 acceptance renders respectively. The `.provenance.txt` files
survive; the pixels do not.

The consequences, stated plainly:

- **`experiments/V-GATHER/rimaxis.py` can no longer run.** Its `SEAL_DIR` at
  line 52 is `acceptance/SHIP-V4`, which now contains no TIFF. The original
  13 tight-scale FAILs behind SYNTHESIS fact 1881 **cannot be re-derived by
  anyone**, and neither can my acquittal of them.
- **My mid-scale re-run cannot be repeated either.** Its three arms read
  `ORCH-FAITHFUL/faithful`, `acceptance/SHIP-V4`, and a linearisation of the
  first. All three sources are gone.
- Section 15 of `V-RIM.md` criticises the earlier mid-scale lane for publishing
  a 5-of-14 result whose inputs had been deleted. **The tight-scale axis is now
  in exactly the same condition, and so is my own adjudication of it.** The
  symmetry is not lost on me and it should not be softened in the retelling.

What survives, and is enough to audit the *reasoning* though not to reproduce
the *pixels*:

- Every table in `V-RIM.md` sections 1-18 -- the ladder, the read-across, the
  isotonic pedestal, the rim-free floor, the per-subject `z` scoring, the
  four-arm mid-scale table, the specificity table.
- The 26 `.provenance.txt` files under `acceptance/SHIP-V4`, which still carry
  the render argv, the binary pin `9b05d0b7`, the per-file SHA256, and the
  `colour space : sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY` line
  that is the third instrument defect in section 16.
- `D:\strehl-out\V-RIM\pics\` -- 39 crops, 4.55 MB, the only surviving pixel
  evidence for any rim verdict in this project.

## 2. What the deleted scratch held, and how it was produced

All of it was regenerable **at the time it was deleted**; it is not regenerable
now, for the reason above. Recorded so the loss is legible rather than silent.

| deleted | held | produced by |
|---|---|---|
| `ladder.json` | extended rim-free ladder, 10 rungs, achieved sd 0.0175-0.3930 | `python experiments\V-RIM\vr_ladder.py` |
| `ladder2.json` | in-place isotonic pedestal, 15 subjects | `python experiments\V-RIM\vr_ladder2.py 3` and `... C` |
| `ladder3.json` | rim-free coherent floor, planted-rim z-calibration | `python experiments\V-RIM\vr_ladder3.py` |
| `score13.json` | final per-subject z scoring of the thirteen | `python experiments\V-RIM\vr_score13.py` |
| `shoulder.json` | kurtosis and dark-arm probe on `coffee-bean` | `python experiments\V-RIM\vr_shoulder.py` |
| `ring\*.json` (9) | mid-scale ring on the deliverable | `python experiments\V-RIM\vr_ring.py run` then `score` |
| `ring-ship\*.json` (5) | mid-scale ring on SHIP-V4 | `python experiments\V-RIM\vr_ring_ship.py` |
| `ring-lin\*.json` (5) | mid-scale ring, sRGB curve undone | `python experiments\V-RIM\vr_ring_lin.py` |
| `ring_spec.json`, `ring2.json` | specificity arms, first and corrected | `python experiments\V-RIM\vr_ring.py spec`, `vr_ring2.py spec2` |
| `ring_window.json` | window-asymmetry test on correlated noise | `python experiments\V-RIM\vr_ring.py window` |
| `lin\*.tiff` (5, 989,656,912 bytes) | linearised masters, sRGB curve undone | `python experiments\V-RIM\vr_ring_lin.py` |
| `AS_STORED.png`, `CURVE_APPLIED.png` | the visual A/B establishing the colour space | throwaway probe, not committed |

Every script named above is committed at `15f6837d`. None of them will run
today, because none of their inputs exist.

## 3. If someone wants these numbers again

`C:\dev\strehl-out\DELIVER-V6\masters` holds 33 TIFFs and **all 13 subject
names are present**, under the same `<name>.tiff` convention the old deliverable
used. Repointing the scripts at it requires only a path edit.

**That would not be a reproduction.** V6 is a later render from a different
binary than the `9b05d0b7` pin that produced SHIP-V4 and than whatever produced
ORCH-FAITHFUL. Any result obtained that way is a **new measurement on a new
input**, and must be reported as one. It can corroborate my conclusions; it
cannot verify my numbers. Anyone who runs it and quietly presents the output as
a check on this report will be doing the thing this project keeps being burned
by.

## 4. NOT MEASURED

- The USM amplitude ladder for the mid-scale axis, requested by ORCH. Never
  run; now unrunnable on its intended inputs.
- The tight-scale axis in linear light. Section 16 argues its direction from the
  shape of the sRGB curve only. Now unrunnable on its intended inputs.
- Whether the vanished `1cacb61` render carried a genuine mid-scale ring.
  Untestable since before this session began.
