"""Append section 13 (the 0.30-0.35 narrow-band measurement) to V-LINEAR-BANDS.md.

Writes with explicit LF newlines and a trailing newline, because appending from
PowerShell has twice introduced CRLF into this pure-LF file.
"""
import io
import os

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "docs", "research", "V-LINEAR-BANDS.md")
DOC = os.path.normpath(DOC)

S13 = """
---

## 13. The 0.30–0.35 cyc/px narrow-band measurement (MEASURED)

### 13.1 Why this section exists

ORCH's broadcast figures — the confidence-dependent exponent removing 27.2% of
the softening at `coffee-bubbles` 9→19 but **−44.6%** at `112MSDCF` 39→79, and
the "harmful at depth" conclusion built on them — are measured at **0.30–0.35
cyc/px**. This lane's finest committed slice was **0.30–0.40**. Section 10 shows
`112MSDCF` FAILs the wider slice at R=1.089.

That is a withdrawal of licence, **not a refutation**: a FAIL on the wider slice
does not prove the narrower band inside it is noise. The narrower band is
narrower, and a subject could carry signal in part of a slice that fails as a
whole. ORCH authorised measuring 0.30–0.35 specifically. This section is that
measurement.

It was pre-registered in `experiments/V-LINEAR/PREREG-NARROW.md`, committed at
`09394648` **before any 0.30–0.35 number existed**, with four readings named in
advance including the one that would show this lane's withdrawal was unnecessary.

### 13.2 The instrument change, and why it is appended rather than inserted

`bandsweep.py` gained `EXTRA = [(0.30, 0.35), (0.35, 0.40)]`, evaluated as
`allb = BANDS + FINE + EXTRA + [(SEL_LO, SEL_HI)]`.

**The order matters and it is not cosmetic.** `ratio_ci` draws bootstrap samples
from a single module-level generator seeded once per process
(`bandsignal.py:69`). Every call consumes randomness, so *inserting* a band in
the middle of the list would shift the random stream for every band after it and
silently move CIs — and therefore verdicts — on bands this document has already
committed. Appending leaves every existing band at its existing position in the
stream.

That is a claim about the instrument, so it was measured rather than asserted.
Each subject's post-change JSON was diffed against its committed pre-change JSON
on all three reported quantities (R, CI low, CI high) of all 12 pre-existing
bands, requiring **exact** equality, not equality to a tolerance:

| subject | pre-existing bands moved | difference |
| --- | ---: | --- |
| `paper-sweep` | 0 of 12 | exact zero |
| `dry-erase-marker-head-cpl` | 0 of 12 | exact zero |
| `112MSDCF` | 0 of 12 | exact zero |
| `lavendar-cpl` | 0 of 12 | exact zero |

`112MSDCF`'s derived boundary was additionally recomputed: 0.20 before, 0.20
after. The document's other 241 checks were re-run and still pass.

### 13.3 The gate: can this instrument qualify a 0.05-wide band at all? (MEASURED)

This was pre-registered as the trap, because it is the reading that most
resembles a win for this lane while actually being uninformative. If a
0.05-wide band at 0.30–0.35 failed on **every** subject including the strongest,
that would not show `112MSDCF` carries no signal there — it would show the
statistic cannot resolve a band that narrow, and the whole section would be
void.

It is not void. On the strongest qualifier:

| subject | band | R | 95% CI | verdict |
| --- | --- | ---: | --- | --- |
| `dry-erase-marker-head-cpl` | 0.30–0.35 | **4.530** | [3.115, 5.947] | **PASS** |

A 0.05-wide slice at exactly the frequency in question qualifies decisively, on
the same code path, the same estimator and the same bar. **A FAIL at 0.30–0.35
is therefore a property of the subject, not of the band width.** The gate is
passed and the remaining numbers mean something.

The CI widths corroborate this. Narrowing 0.30–0.40 to 0.30–0.35 costs very
little precision: on `paper-sweep` the CI width goes 0.23 → 0.27, on `112MSDCF`
0.082 → 0.081. The narrow band is not meaningfully noisier than the wide one.

### 13.4 Results (MEASURED)

All at `--far 20` except where noted, same estimator, same frozen bar
(PASS ≥ 2.0, MARGINAL ≥ 1.5, else FAIL).

| subject | N | 0.25–0.30 | **0.30–0.35** | 95% CI | 0.35–0.40 | verdict at 0.30–0.35 |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `dry-erase-marker-head-cpl` | 300 | 9.665 | **4.530** | [3.115, 5.947] | 5.283 | **PASS** |
| `paper-sweep` | 62 | 3.203 | **1.965** | [1.832, 2.100] | 2.045 | MARGINAL |
| `coffee-bubbles` | 19 | 1.963 | **1.542** | [1.181, 2.154] | 1.523 | MARGINAL (reduced `far`, §13.6) |
| `lavendar-cpl` | 300 | 2.435 | **1.523** | [1.274, 1.759] | 1.452 | MARGINAL |
| `112MSDCF` | 79 | 1.202 | **1.079** | [1.040, 1.121] | 1.102 | **FAIL (noise)** |

### 13.5 The decisive subject: `112MSDCF` carries no resolvable signal at 0.30–0.35

`112MSDCF` is the subject carrying ORCH's **−44.6%**, the figure on which
"harmful at depth" rests.

**R = 1.079, 95% CI [1.040, 1.121].**

This is not a marginal call and it should not be reported as one. The **upper**
end of the confidence interval, 1.121, sits **0.379 below the MARGINAL bar** and
**0.879 below the PASS bar**. R is the ratio of in-focus to defocused band power;
R ≈ 1.08 means the in-focus frames carry about 8% more power at 0.30–0.35 than
frames deliberately chosen 20 exposures away from focus, which should carry
almost no real detail there at all. Roughly 92% of what is present in that band
on that subject is common to focused and defocused frames alike.

Combined with §13.3, the conclusion is measured on both sides:

- The instrument **can** qualify 0.30–0.35 (`dry-erase`, R=4.530). MEASURED.
- `112MSDCF` **does not**, decisively (R=1.079, CI upper 1.121). MEASURED.
- Therefore the −44.6% is computed in a band that carries no resolvable signal
  on the subject it was computed from. DERIVED.

**This upgrades ORCH's status for that figure from "licence withdrawn pending
measurement" to "measured".** The pending measurement has been taken and it did
not rescue the number.

### 13.6 `coffee-bubbles`, the 27.2% subject, and a confound that had to be controlled

`coffee-bubbles` is a **19-frame** stack. `sweep()` requests a defocus reference
`far = max(20, N/6) = 20` frames from focus, but 19 frames cannot supply 20, so
the guard `n - 2*far < 6` reduces the realised `far` to **6**. A closer defocus
reference has more real detail in it, which inflates the denominator and biases R
**downward**. Left uncontrolled, `coffee-bubbles` would fail for a reason that
has nothing to do with its content.

So the confound was measured rather than argued away, by re-running the strongest
qualifier at the **same realised `far`**:

| `dry-erase-marker-head-cpl` | realised `far` | 0.30–0.35 | verdict |
| --- | ---: | ---: | --- |
| `--far 20` | 5 developed frames | 4.530 | PASS |
| `--far 24` | 6 developed frames | **4.659** | **PASS** |

A strong subject still qualifies decisively at the reduced separation, so the
reduced `far` is **not by itself** fatal to qualification, and
`coffee-bubbles`'s 1.542 is not merely an artifact of it.

**The residual confound, stated because it is not fully removed.** The control
matches the *developed-frame* count, not the physical defocus. `coffee-bubbles`
is swept at step 1, so 6 developed frames is 6 real exposures; `dry-erase` is
swept at step 4, so its 6 developed frames span 24 real exposures. The reference
really is physically closer to focus for `coffee-bubbles`, and that bias points
**downward**. Its R is therefore a **conservative** reading — the true value
under a far reference could be higher.

**Verdict for `coffee-bubbles`: MARGINAL, conservatively biased, and it does not
qualify as measured.** It is not called noise. The 27.2% is unlicensed but is on
materially weaker ground than the −44.6%: 1.542 with a conservative bias is a
different situation from 1.079 with a CI that excludes 1.13.

`coffee-bubbles` is **deliberately excluded from the canonical eleven-subject
tables in §0, §7, §8 and §10.** Those tables are a single protocol (`far = 20`),
and folding in a subject measured at `far = 6` would silently mix protocols
inside a table that other lanes read as homogeneous. It is reported here in full
instead, with its protocol difference named. Its derived boundary, for the
record, is **0.25**, which falls in the existing 0.25 group and adds no new
distinct boundary.

### 13.7 The narrow band tracks the wide band (MEASURED)

Every subject's 0.30–0.35 reading is close to its committed 0.30–0.40 reading:

| subject | 0.30–0.40 | 0.30–0.35 | Δ |
| --- | ---: | ---: | ---: |
| `dry-erase-marker-head-cpl` | 4.877 | 4.530 | −7.1% |
| `lavendar-cpl` | 1.490 | 1.523 | +2.2% |
| `paper-sweep` | 2.002 | 1.965 | −1.8% |
| `112MSDCF` | 1.089 | 1.079 | −0.9% |
| `coffee-bubbles` | 1.533 | 1.542 | +0.6% |

The largest move is 7.1% and no subject changes verdict *group*. One subject
crosses a bar: `paper-sweep` goes 2.002 PASS → 1.965 MARGINAL on a 1.8% move,
which is precisely the fragility §7.5 flagged in advance for cells sitting on the
bar. Nobody should lean on `paper-sweep` at this frequency in either direction.

**Consequence for the project:** the wider 0.30–0.40 slice was, on these five
subjects, a good proxy for 0.30–0.35. That retrospectively supports using §10's
committed table to triage which subjects a fine-scale claim may be quoted on —
but it is n=5 and it is a measured correlation, not a guarantee, so a claim that
turns on the narrow band should still be measured on the narrow band.

### 13.8 What this establishes, and what it does not

**Establishes (MEASURED):**

1. The instrument resolves a 0.05-wide band at 0.30–0.35 and can qualify it
   (`dry-erase` R=4.530 PASS).
2. `112MSDCF` fails it decisively, CI upper bound 1.121.
3. `coffee-bubbles` does not qualify either, at 1.542 with a downward bias.
4. Adding the two narrow bands moved no pre-existing number on any of four
   subjects.

**Does NOT establish:**

1. **That the confidence-dependent exponent is harmful, harmless, or beneficial
   at depth.** This section says only that the *evidence offered* for "harmful at
   depth" was collected in a band carrying no resolvable signal on the subject it
   was collected from. That is a statement about the measurement, not about the
   fix. The fix remains unadjudicated and ORCH's requirement that it be measured
   at depth before shipping is untouched.
2. **That `112MSDCF` has no fine detail.** R compares in-focus to defocused
   frames of the same subject. A subject can be genuinely soft at 0.30–0.35 —
   which is a fact about the capture, not a defect — and that is indistinguishable
   here from a subject whose detail is buried in noise. Either way the band cannot
   carry a difference measurement.
3. **Anything about bands other than those measured.** In particular this says
   nothing about 0.20–0.30, where `112MSDCF` reads 1.724 MARGINAL at 0.20–0.25
   and would be the place to re-measure a depth effect on that subject.

**Recommendation, offered and not decided here:** re-score the exponent at depth
on `bee-1-cpl` (N=299, 0.30–0.40 R=4.732 PASS) or `dry-erase-marker-head-cpl`
(N=300, R=4.877 PASS, and now R=4.530 PASS at 0.30–0.35 specifically). Both are
deep and qualified at the exact band in question. This is unchanged from the
recommendation in `depthqual.py`, and it is now supported at the narrow band
rather than only at the wide one.
"""


def main():
    with io.open(DOC, "r", encoding="utf-8", newline="") as fh:
        body = fh.read()
    if "\r\n" in body:
        raise SystemExit("REFUSING: document already contains CRLF before append")
    if "## 13." in body:
        raise SystemExit("REFUSING: section 13 already present")
    if not body.endswith("\n"):
        raise SystemExit("REFUSING: document lacks trailing newline before append")
    out = body + S13.replace("\r\n", "\n")
    if not out.endswith("\n"):
        out += "\n"
    with io.open(DOC, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print("appended section 13")
    print("lines: %d -> %d" % (body.count("\n"), out.count("\n")))
    print("CRLF present:", "\r\n" in out)
    print("trailing newline:", out.endswith("\n"))


if __name__ == "__main__":
    main()
