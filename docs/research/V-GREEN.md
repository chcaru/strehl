# V-GREEN — fact 1867 CLOSED: the green-channel difference is not a CA defect, it is the output path refusing to be channel-local

**Transcribed by the orchestrator from lane V-GREEN's final report.** The lane
measured everything below and then could not write it: its operating constraints
allow no file output, so it delivered a paste-ready block and said plainly that
if nobody transcribed it, "fact 1867's closure exists nowhere in the tree and the
next reader finds it OPEN." This file is that transcription. The measurements are
the lane's; any error of transcription is the orchestrator's.

**Facts, disciplines and open questions are numbered LOCALLY as `F1, F2, …` per
rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Build commit:** `9bbb7a1c4142aa44c3b1d5cd326c54975acb0205`
**Pinned exe SHA256:** `54F6D2405A7B674A491975C114052619BF9EBB7C4251B368F8983FB9FA8ECD88`
— **this binary has been deleted.** Recorded at full length deliberately, so the
identity is checkable against a rebuild rather than merely quotable.

**Subject:** `dry-erase-marker-head-cpl`, N=299. One executable, seven arms, only
`--fix-ca` differing between the members of each pair.

Sources under `D:\personal\macro\` were read only.

---

## 1. The arm matrix

Each arm had its own `STREHL_CACHE_DIR`; the shared sidecar was untouched.

| arm | invocation |
|---|---|
| A1 | `--srgb` |
| A2 | `--srgb --fix-ca off` |
| A3 | repeat of A2 (determinism control) |
| B1 | default, binned |
| B2 | `--fix-ca off` |
| C1 | `--demosaic` |
| C2 | `--demosaic --fix-ca off` |

**F1 — MEASURED. Output hashes (all seven files now deleted).**

| arm | SHA256 |
|---|---|
| A1 | `BE73A9956D67A58247A4FF9977C1FF50C9C8922CF132C327221415A19059BCA0` |
| A2 | `631D24A74F0F188763F3AC6EB6865B917087536F1ACBB40C64EA95ADF9010FA1` |
| A3 | `631D24A74F0F188763F3AC6EB6865B917087536F1ACBB40C64EA95ADF9010FA1` |
| B1 | `90298E797716D655116AA2C1874E78435B3DDEDCC4823023F0BA8590CB6D932A` |
| B2 | `3494941769C07F5523D6B83FE3C9C3D11090FAB67FAC99A28B4F838FD414FFBD` |
| C1 | `100CBD34900F56BE8255850E58DAC8CB1780AF00C330404D941D6638D0457A4B` |
| C2 | `026C67E43BB17601ACB2FD673BC0667AE59F9C94815A843BA033867710447EF2` |

**A3 == A2 byte-identical** — the determinism control holds.

**F2 — MEASURED. All seven warpmaps hash identically:**
`522C2E94B96F95417BFBE744D4B977D3EA3FA07F8E2CF4743659B71BED4D4B70`.
The CA coefficient therefore reaches the **gather only, never the solve**. This is
the cleanest line in the lane: it is a positive identity across all seven arms, not
an absence of observed difference.

---

## 2. The green ladder — the measurement that settles it

**F3 — MEASURED.** Each rung adds one output-path stage. Pixels differing between
the CA-on and CA-off member of the pair, in the green channel:

| rung | pair | px differing / total | % | max DN |
|---|---|---|---|---|
| binned, camera-linear | B1 vs B2 | 0 / 8,250,880 | **0.0000%** | **0** |
| + MHC demosaic | C1 vs C2 | 14,920,511 / 33,003,520 | 45.2088% | 10003 |
| + sRGB matrix + tone | A1 vs A2 | 30,852,031 / 33,003,520 | 93.4810% | 8635 |
| original fact-1867 pair | — | 30,872,990 / 33,003,520 | 93.5445% | 9595 |

Read down the first column: the green difference is **exactly zero** before
demosaic, and only becomes large as output stages are added. The defect was never
in the channel; it was in the path.

**F4 — MEASURED, and the decisive one. CFA-site parity.** Partitioning the
`C1 vs C2` green differences by the photosite each green value sits on:

```
R sites 7,511,352  +  B sites 7,409,159  +  G1 sites 0  +  G2 sites 0
                                        =  14,920,511   exactly
```

**All 16,501,760 MEASURED greens are bit-identical. Only INTERPOLATED greens
move.** The partition sums to the total with no remainder, so no differing pixel
is unaccounted for — this is a partition, not a sample.

---

## 3. Verdicts on the candidate explanations

| # | explanation | verdict | evidence |
|---|---|---|---|
| 1 | CA correction touches green | **REFUTED** | `eps(Green)=None` short-circuits `compose` before translation (`optics.rs:277`, `:344`). Commissioned: planted `Some(0.0)` → **RED**, exit 101 → restored → **GREEN**. |
| 2 | channel election / coupling in the merge | **REFUTED** | binned green differs by 0 px / 0 DN while red differs 91.01% and blue 88.68% |
| 3 | the original pair differed in something else | **REFUTED** | one exe reproduces to 0.068%; CA-OFF byte-identical across builds 3 h 37 m apart |
| 4 | **the output path is not channel-local** | **CONFIRMED** | MHC demosaic estimates G at every R/B photosite (`demosaic.rs:403`, `:408`); the camera→sRGB 3×3 then mixes all channels |

Explanation 4 was **not on the list the lane was given**. It found it by
elimination and code reading after the first three died.

**D1 — DISCIPLINE. A commissioning plant must be shown to go RED, and then the
restoration shown to go GREEN.** Explanation 1's refutation rests on
`eps(Green)=None`; the plant `Some(0.0)` proved the check could fail, and the
restore proved the GREEN reading afterwards was the code and not the harness.

---

## 4. Verified vs. assumed

**Verified by measurement:** F1, F2, F3, F4, and verdicts 1, 2, 3 and the
determinism control.

**Derived by elimination plus code reading, not isolated experimentally:** the
split of the 45.21 → 93.48 point rise between the colour matrix and the tone
curve. **NOT MEASURED — would have cost ~2 GB of scratch the owner does not
have**, and there is no matrix-without-demosaic CLI mode to isolate it with.

**Scope limits, stated rather than buried:** one subject only
(`dry-erase-marker-head-cpl`); merged CFA planes were never dumped.

**Unreproducible from here:** the original pair. `D:\strehl-out\BUILD-CROP` was
deleted by its owner before this lane ran, and these arms are now deleted too, so
the cross-build control `A2 == m-caoff.tiff` cannot be re-checked without a fresh
~2 GB re-render. The recipe, flags and pinned commit are recorded above, so the
*result* is re-derivable even though the *pixels* are gone.

---

## 5. Defects this lane leaves standing

These were reported by the lane and are **not re-verified by the orchestrator**.

- **HIGH — fact 1886's build-drift mechanism does not reproduce** (`SYNTHESIS.md:2444`).
  Its 33,003,417 px is **103 short** of the full 33,003,520, which is the signature
  of a global operation, not of drift. **Do not cite fact 1886 to retire an
  absolute.**
- **MEDIUM — fact 1867's "mean 51.39 DN" is the mean over *differing* pixels only.**
  The all-pixel mean is **48.0718**, which is what `gdisc.py:41` prints. Two
  different quantities have been carrying one number.
- **MEDIUM — `BUILD-CROP.md` §16.3 names only the demosaic half** of the mechanism
  and omits the colour matrix.
- **MEDIUM, process, and it affects every lane — `Copy-Item` restore preserves
  `LastWriteTime`.** Cargo therefore skips the rebuild, and a "restored" arm
  silently re-runs the **mutant**. It failed safe in this lane because of the
  ordering used; **the mirrored ordering yields a false GREEN.** Any negative
  control that restores a source file by copying it back is suspect until the
  rebuild is proved to have happened.

---

## 6. Proposed facts

Numbered locally; the orchestrator allocates absolute numbers at fold. **This lane
did not edit `SYNTHESIS.md`.**

- **F3/F4 together are the row worth folding:** the green channel is bit-identical
  at every measured photosite and differs only where it was interpolated, so the
  observed green difference is a property of the output path, not of the CA
  correction — and the CFA-site partition sums exactly, leaving no residue.
- **F2 is the structural row:** identical warpmap hashes across all seven arms
  place the CA coefficient in the gather and not in the solve.
- **The `Copy-Item` / `LastWriteTime` item is the methodological row**, and it is
  the one with reach beyond this lane.
