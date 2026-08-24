# M103 — pre-registration

Written **before** any corrected estimator was run, and before any correction
existed in `align.rs`. Committed ahead of the fix so that the bars cannot be
moved after seeing a result.

**Order of work, stated plainly so nobody has to reconstruct it.** Three
*diagnostic* runs preceded this file: the shipped-config edge dump (`A`), a
wide-capture edge dump (`B`), and the independent truth ladder
(`data/truth-ladder.json`). Those are measurements of the *defect*, not of any
treatment; no correction existed when they ran. Every bar below scores a
treatment, and no treatment has been run at the time of writing.

---

## 0. What the commission asked, and what the corpus already says about it

The dispatch names two candidate fixes and asserts of the second that *"as far
as the corpus knows this has never been applied to focus-stack registration."*
**That assertion is false, and I record it here before it can shape my
design** (AGENTS rule 43):

- **Candidate 1, per-edge metacalibration, is M23's R4 and it is dead.** Facts
  170, 171, 175, 176, 177, 178. Its local-linearity premise is refuted
  (`R` = 0.5264 at δ=1e-4 and 0.9928 at δ=8e-4 on the same edges), a *shuffled*
  `R` reproduces 93.3% of its effect, and its held-out gate failed.
- **Candidate 2, blur equalisation, is M78's R5 and it is dead.** Facts 1097,
  1098, 1099. Arm A drove `coffee-bean` span-1 conservation from 3.260389 to
  1.073795 and *worsened* held-out prediction.
- **Fact 45's 0.56 recovery ratio — the dispatch's leading evidence — has had
  its causal reading withdrawn** by M23 at fact 174. A zero-defocus self-pair
  on the same harness reads **0.372**, further from unity than the real defocus
  pair, and a resampler-free field reads 0.965. The mechanism is the plant's own
  bilinear resampler, not blur asymmetry.

So the leading hypothesis in my dispatch is built on a withdrawn attribution,
and both proposed fixes have already been measured and refused. I therefore do
**not** pre-register either of them as a primary arm. I pre-register the
question — *where does the solve lose half the drift?* — and the arms the
diagnostics actually point at.

**What is genuinely new and does reopen M78:** both R4 and R5 were scored on
**held-out pairwise error**, and M97 has since established that a held-out
pairwise residual is **structurally blind to a common multiplicative gain
error** (`E*` = 11.56 px coexisting with a 150.2 px end-to-end residual). Fact
1098 says a conservation identity is not a proxy for accuracy; M97 says
held-out error is not a proxy for absolute registration. Neither metric is
sufficient alone. The absolute end-to-end residual is, and it is bar B3.

---

## 1. Bars

### B1 — the conservation identity (self-consistency, no ground truth)

The corrected span-1 ladder must **telescope** toward the long-edge total.
Reported as `recovery = (Σ ln|a| over the span-s chain from 0 to 298) / ln(0.85714)`.
Recorded for every span; **diagnostic, never a gate** (fact 1098). A treatment
that fixes B1 and fails B3 ships nothing.

### B2 — the built-in placebo: the correction must be a measured no-op where there is nothing to correct

Two instances, both required:

- **B2a, the self-pair.** Frame `k` against *itself*, zero true motion, run
  through the corrected estimator. Must read `|a| = 1.000` to within 1e-4 and
  `used` must not fall. This is M23's mandatory self-pair arm (discipline 81).
- **B2b, the uncensored span.** At span 1 the shipped estimator already keeps
  85.9/96 tiles with 0.8 border refusals — there is nothing for a
  capture-range treatment to uncensor. The treatment must move the span-1 mean
  `ln|a|` by **< 20%** of its own value. If it moves span 1 as much as span 128,
  it is not doing what I claim.

### B3 — THE DECIDING BAR: absolute end-to-end residual on the owner's stack

Re-run M97's own instrument (`experiments/M97-warped-merge/src/signtest.py`,
unmodified, ~4 min) against a sidecar produced by the corrected solve. The
**fraction of drift removed** must rise from M97's measured **50.2%**.

- **PASS** if ≥ 80% of drift removed (residual ≤ ~60 plane px from 150.2).
- **PARTIAL** if 60–80%.
- **FAIL** if < 60%.

A held-out pairwise improvement is **not** admissible as evidence here and will
not be quoted as such (M97 §12 Notes item 3).

### B4 — it must not break the good case

Fact 45's control read 1.00; fact 43's corpus range says `112MSDCF` shows
essentially no shrinkage (`1/S_W(1)` = 1.048). Run the same per-span recovery
ladder on **`112MSDCF`** before and after. The treatment must leave its span-1
conservation ratio within **±10%** of where it starts. A treatment that moves a
stack with no defect is not correcting the defect.

### B5 — a positive control that does not perturb its own mechanism

Plant a **known** scale on real frames and require the corrected estimator to
recover it. Per discipline 615 the plant must not act through the mechanism
under test. The mechanism here is **search-window censoring by lever arm**, so
the plant must not itself change the census: it is applied as an extra
similarity composed into the *pair*, with the plant's own resampler arm reported
separately, and a **zero-plant** run must return the untreated answer exactly.

### B6 — the shipped default path must not move unless I mean it to

Any `align.rs` change must either (a) leave `AlignConfig::deep()` untouched, or
(b) if it changes it, say so explicitly and re-measure. Any new field must
default to **current behaviour**, proven by a bit-identical edge dump against
run `A`.

---

## 2. Named failing inputs (AGENTS rule 20)

| bar | input that would make it FAIL, and whether such an input exists |
|---|---|
| B1 | any treatment that leaves long-span edges censored — run `A` **is** that input, at 0.16–0.26 recovery |
| B2a | a treatment that widens the search until a self-pair locks onto a wrong peak; reachable by setting the radius large enough |
| B2b | a treatment implemented as a blanket gain on `ln\|a\|` — it would move span 1 exactly as much as span 128. **This is precisely the `--gain` knob already present in M97's `signtest.py`, so the failing input is not hypothetical: it is on disk.** |
| B3 | run `A`'s own sidecar, which scores 50.2% |
| B4 | any blanket gain > 1 applied to a stack with no shrinkage |
| B5 | an estimator that returns the seed unchanged would recover 0 of any plant |

## 3. Hypotheses on the table, ranked before the treatment runs

1. **Capture-range censoring, lever-biased.** The fine stage searches ±6 plane
   px about a seed. Tiles survive only where the model already predicts them,
   and the residual grows with lever arm, so **corner tiles — the ones carrying
   the scale — are refused first**. Run `A` measures the census collapsing from
   85.9/96 at span 1 to the `min_tiles = 8` floor by span 64, with `border` the
   dominant reason (68.7/96 at span 16). *This is the hypothesis the diagnostics
   point at.*
2. **No long baseline exists.** `DEFAULT_SPANS` tops out at 128 of 298 and
   contains no frame-0 anchor fan, and the direct (0,298) edge is **refused**
   under the shipped config. AGENTS rule 6 prescribes "*a span ladder … plus
   every frame-0 pair*" and "*discard spans 1-2*"; the shipped ladder does
   neither.
3. **Solver compromise.** The global least squares is linear in `A`, not in
   `ln A`, and weights every edge alike, so 595 span-1/2 edges that each
   under-report can outvote 171 span-128 edges.
4. **Blur asymmetry** (the dispatch's hypothesis). Retained, but demoted: the
   fact it rests on has had its causal reading withdrawn, and the census
   evidence in run `A` is a sufficient alternative explanation.

## 4. Trivial explanations to rule out by measurement before any of the above

- an exact factor of 2 anywhere;
- a pairwise estimate averaged where it should be summed;
- a ladder accumulated about the mid-stack reference (149 of 299) but quoted
  end-to-end;
- log-vs-linear confusion in the quoted fraction;
- a half-step in the pyramid or a `/2` in the parabolic centre-of-mass;
- plane px vs sensor px (a factor of exactly 2 in this codebase).

Each is to be reported as ruled out **with the number that rules it out**, not
asserted.
