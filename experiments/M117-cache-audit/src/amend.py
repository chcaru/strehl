import pathlib, shutil, os, sys
p = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M117-cache-audit.md")
bak = pathlib.Path(os.environ["TEMP"]) / "M117-cache-audit.md.bak"
shutil.copy2(p, bak)
print("backup ->", bak)
try:
    raw = p.read_text(encoding="utf-8")

    def sub(old, new, want=1):
        n = raw.count(old)
        if n != want:
            raise SystemExit("MUTATION TARGET NOT FOUND: %d/%d occurrences of %r" % (n, want, old[:70]))
        return raw.replace(old, new)

    old1 = "  `reference 0` entry, and both surviving in-window shared entries carry"
    new1 = "  `reference 0` entry, and all three surviving in-window shared entries carry"
    raw = sub(old1, new1)

    anchor = "## 9. Disciplines"
    if raw.count(anchor) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: anchor %r" % anchor)

    add = """
## 10. Addendum — re-derivation after ORCH withdrew the triage rule

ORCH withdrew the absolute-vs-ratio triage rule and asked every milestone to
re-derive exposure for its own estimator. Doing so found a real hole in this
report, which is recorded here rather than quietly repaired.

**The estimators this audit used, and their exposure.**

| # | estimator | used for | exposure to a common floor `q` |
| --- | --- | --- | --- |
| E1 | SHA-256/16 of output bytes | controls, re-runs | none — exact equality |
| E2 | SHA-256 of warp sidecar text | cache forensics | none — lossless f64 |
| E3 | `rms/mean` of a pixel difference | severity (X9) | **6e-6 relative** |

- **X17 (DERIVED).** The warp sidecar is a **lossless** f64 serialisation, so
  E2 has no quantisation floor and discriminates to **1 ULP**. `warpmap.rs:520`
  writes `format!("{:016x}", v.to_bits())` and `:525` reads it back through
  `u64::from_str_radix(s, 16).map(f64::from_bits)`; the trailing decimal is
  stripped at `:727`/`:825` by `.split('#')` and is documented in the file
  header as "a human aid and NOT parsed". This is already guarded by a
  committed test, **Gate W1** (`w1_round_trip_is_bit_identical`), whose doc
  comment states the hazard exactly: *"a format that round-tripped through a
  decimal with too few digits would fail here even though the values printed
  the same."* The byte-identity clearances in section 5 therefore cannot be
  false nulls produced by a coarse serialisation.
- **X18 (DERIVED).** E3's only ratio is exposed at **6 parts per million**.
  Renders are `uint16`, so the floor on a difference of two independently
  rounded images is `sqrt(2/12) = 0.408 DN`. Removing it in quadrature from the
  measured `117.969 DN` gives `117.9683 DN`. X9 stands.
- **X19 (MEASURED) — this report's own defect, found by ORCH's broadcast.**
  The section 5 cache census cleared entries by reading `reference` from the
  sidecar header. The header carries only `reference`, `strategy` and
  `resampler` — it has **no smoothing field**. `STREHL_SMOOTH` and
  `STREHL_SMOOTH_HUBER` were the *other* unkeyed axis (M97n's fact S4), so that
  census was a check pointed at a field structurally incapable of seeing them.
  It is the same shape as the `STREHL_FIX_CA` no-op ORCH reported, occurring
  inside the audit that was looking for it.
- **X20 (MEASURED).** The hole is closed. There are **three** in-window shared
  entries, not the two section 5 recorded. `lavendar-cpl-47e596c1cc69bdfc`
  (11:51:27) is **whole-file byte-identical** — 40 812 bytes, SHA-256/16
  `4D454CCEAEC2479F` — to the clean HEAD private-cache re-solve
  `lavendar-cpl-7a3c5ecc793d30ac`, across all 299 placements and every f64 bit
  pattern. Since the comparison is on coefficients, not headers, it covers
  **every** solve axis including smoothing. `dry-erase-…-57fff568` was already
  closed the same way (`1864A370AE92B377`). The third,
  `bee-3-cpl-ea1d38ea5c9523c5` (10:39:03), is a **6-frame** stack on a path that
  no longer exists, is orphaned by the post-fix key change, and no published
  fact in the corpus uses a 6-frame `bee-3` stack. Verdict unchanged: **0
  contaminated numbers**, now on the smoothing axis as well as the reference
  axis.
- **X21 (MEASURED).** ORCH's `STREHL_FIX_CA` finding reproduces from the source
  independently. `optics::active_profile()` has exactly two callers:
  `align_cmd.rs:324` (`preflight_ca_profile`, which validates and discards) and
  `align_cmd.rs:1317`, inside `warp_frame_in_place`. That function has exactly
  **one** production call site, `merge_cmd.rs:982`, guarded by
  `if let Some(map) = self.warps`. With alignment off `self.warps` is `None`,
  the block never runs, and the CA correction is a byte-identical no-op. Already
  in the corpus as M113's fact 1660.
- **X22 (MEASURED).** A **corpus-wide sweep found zero measurements** that set
  an alignment-nested gate (`STREHL_FIX_CA`, `STREHL_SMOOTH`,
  `STREHL_SMOOTH_HUBER`) while alignment was off. Scanned every fenced block of
  all 163 reports plus `SYNTHESIS.md`, requiring a real assignment to a
  non-empty value rather than a bare token. **Both controls pass**: a planted
  `ALIGN=0` + `FIX_CA=…` block fires, and M97n's rule-47 record — which names
  `STREHL_SMOOTH unset  STREHL_SMOOTH_HUBER unset` — is correctly silent. The
  naive token scan reported that record as a hit; rule 47's practice of
  declaring *every* variable including unset ones is what made a presence test
  useless here.
- **X23 (MEASURED) — the result that does not fit.** The same guard at
  `merge_cmd.rs:982` implies a sharper claim: `FrameWarp::Refused` frames are
  skipped, so CA is applied to **placed** frames only, and a stack with
  refusals would receive a *partial* correction. That claim is **empty on this
  corpus**. M97o's fact T1 measured *"frame-level refusal does not occur on any
  capture in this corpus: four sidecars, 0 refused lines each."* Recorded as a
  dormant hazard, not a live one.

"""
    raw = raw.replace(anchor, add.lstrip("\n") + "---\n\n" + anchor, 1)

    d = """- **D8.** **Re-derive an estimator's exposure by expanding it, not by
  classifying its shape.** This audit's clearances survived only because the
  sidecar is lossless f64 — a property of the format, not of the statistic. Had
  it printed six decimals, the same byte-identity method would have produced
  the same reassuring nulls and they would have meant nothing.
- **D9.** **A census over a header can only clear the axes the header records.**
  Section 5 cleared six entries on `reference` and silently implied all axes.
  The fix is to compare the artifact's full payload against an independent
  re-solve, which is what X20 does and what the `dry-erase` check had already
  done by accident. When a field list is the instrument, enumerate the fields
  and name the perturbations each one cannot see.
"""
    tail = "## 9. Disciplines\n"
    if not raw.rstrip().endswith(d.rstrip()):
        raw = raw.rstrip("\n") + "\n" + d
    p.write_text(raw, encoding="utf-8")
    print("patched OK; lines now", len(raw.splitlines()))
except SystemExit as e:
    shutil.copy2(bak, p)
    print("RESTORED from backup due to:", e)
    sys.exit(1)
