# M62 — pre-registration of the acceptance criteria for M64

**Written and committed before M64's diff exists.** I have not seen its design,
its code or its approach, and I have not been told what it intends to do beyond
"make the estimating merge the default path of the shipped binary". Nothing below
is a prediction about M64's outcome. Every number here is either a **requirement**
or a **baseline measured on the current binary**, and the two are labelled apart.

**I am the acceptance authority for M64 and I will implement none of it.** I will
not review its code for correctness, suggest an approach, or comment on a draft.
The author does not verify their own work (rule 12); by the same symmetry the
instrument's author must not be the one who changes what it measures. When the
diff arrives I run the battery below, unmodified, and report.

**Certification is not the goal of this document.** A REJECT that names a
mechanism is as good an outcome as a CERTIFY, and I would rather return one than
soften a threshold. §6 lists what I will not do to reach agreement.

---

## 1. Baseline, measured now, on the current binary

Recorded so it provably predates the work it judges.

**The binary, not the commit, is the identifier.** Six agents are live and HEAD
moved three times while I was measuring (`a8eddc0` → `b0c0f92` → `30e5a17`)
without the executable changing. The baseline binary is
**sha256 `082af420…8e0c16a`**, `crates/` clean at every run, built with
`cargo build --release` in 23.47 s with `Compiling strehl-core` / `strehl-raw` /
`strehl-plugin` / `strehl-cli` visible (rule 33). Full provenance, including the
per-run HEAD, is in `out/10-acceptance-preM64.json`.

- **The battery reproduces M62 exactly.** Every arm agrees with the committed
  `out/04-arms.json` **to every printed digit** — 1.000693306, 5.479128597,
  0.999607525, 0.769033477, 0.976815368, 5.477677513 — and did so on three
  separate runs at three different HEADs. M62's numbers were taken from a
  `git archive` export because the tree would not compile; **the tree compiles
  now and the two builds are numerically identical.** (MEASURED.)
- **The battery's verdict on the current binary is `REJECT`, blocking on
  `DEFAULT`.** `strehl merge <dir> --out <tif>` with no tuning flags exits 1:

  > `Error: --out writes one image, but 4 gates were given; pick one`

  The current default is a **four-gate diagnostic ladder (0.5, 1, 2, 4) that
  writes no image**. There is therefore no default merged output at HEAD at all.
  (MEASURED, `out/10-preM64-s0-DEFAULT.log`.)
- **Focus guard baseline.** On the real 22-frame focus stack `109MSDCF`, the
  same binary reports `mean n_eff` 1.414 / 1.884 / 2.891 / 4.987 across its
  default ladder — `n_eff/N` between **0.064 and 0.227**. On the 30-frame static
  burst it reports `n_eff/N = 1.000`. (MEASURED,
  `out/11-focus-guard-preM64.json`.)

That last contrast is what makes §4 a test rather than a formality: `n_eff` is
demonstrably a live discriminator on this binary, not a constant.

---

## 2. What I will run, and how someone else can run it

Nothing is hardcoded to my binary. The executable comes from `$STREHL_BIN` or
`--exe`, the constants from `$STREHL_SRC` or `--src`, and every arm — subcommand,
flags, expectation, tolerance — lives in `src/acceptance-spec.json` as data.

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release                       # from a committed sha, crates/ clean
cd experiments\M62-sqrt-n
python src\01-pick-latent.py                # once; reads the read-only corpus
python src\10-acceptance.py --tag m64       # the battery
python src\11-focus-guard.py --tag m64      # the degeneracy guard
```

`10-acceptance.py` prints `CERTIFY` or `REJECT` and the blocking arms, and writes
`out/10-acceptance-<tag>.json` containing the binary's **sha256**, the repo HEAD,
whether `crates/` was dirty, the tolerances applied and every per-seed ratio.

An arm the binary refuses is **UNSUPPORTED**, not a crash. That is a result.

---

## 3. The criteria

`N = 30`, three seeds, 891 136 plane pixels per arm, 64×64 block bootstrap.
Thresholds live in `acceptance-spec.json` under `tolerances`.

### 3.1 Instrument arms — if these move, nothing can be certified

| arm | requirement |
| --- | --- |
| `A0-ladder:k`, `k ∈ {1,2,3,5,10,20,30}` | within **1 %** of √k at every rung |
| `B1a-const-selector` | within **0.005** of 1.0 |
| `B1b-random-selector` | within **0.005** of 1.0 |

These touch no binary. If any fails, **the harness changed**, and I report that
ahead of anything about M64 — the finding would be about my instrument, not about
their merge.

### 3.2 The deciding arm

| arm | invocation | requirement |
| --- | --- | --- |
| **`DEFAULT`** | `merge {burst} --flat-roi {roi} --out {out}` — **no tuning flags** | within **2 %** of √30 = 5.4772, i.e. **`R ∈ [5.368, 5.587]`** |

The invocation carries no gate, no target, no tuning of any kind, because the
claim under test is about the **default path**. If certification requires a flag,
the claim is not established and I return REJECT with the flag named.

Two observables reported beside it, both from the binary's own output:

- **efficiency** `R / √(mean n_eff)` — required in **[0.98, 1.02]**. Below,
  the merge wastes samples it admitted; above, it beat the arithmetic bound of
  what it admitted, which means my reference or ROI is wrong and I investigate
  the harness before believing the number.
- **`mean n_eff` on the static burst.** Reported, not gated. Its role is §4.

### 3.3 Power — the battery must be able to fail

Per discipline 419, a battery whose failing arms have all disappeared certifies
nothing.

> **I will not issue CERTIFY unless at least one `power` arm ran and scored below
> `selector_ceiling` = 1.05 on the binary under test, in the same session.**

Two exist: `SELECTOR-shipped` (`stack`, baseline **0.7690**) and
`SELECTOR-same-binary` (`merge --gate 0`, baseline **0.9768**).

**Neither is `required`, and this is the correction I most want on the record.**
I originally wrote `SELECTOR-shipped` as a required-pass arm with a ≤ 1.05
ceiling. That is wrong, and it is wrong in the specific direction that would have
made me useless: **if `stack` is the entry point M64 converts to an estimator,
then `stack` scoring 5.48 is the intended outcome, and a required ceiling would
have auto-rejected the exact change the battery exists to judge.** A
pre-registration that mechanically rejects the hypothesis under test is not
rigour, it is a rigged instrument. Fixed before any diff existed; the superseded
`spec_version: 1.0` is in git history.

So a power arm scoring **high** is recorded as **`NO-POWER`**, not `FAIL`. It
says the control is gone, not that the merge is wrong.

**If every power arm becomes `NO-POWER` or `UNSUPPORTED` I return
`CANNOT-CERTIFY`** — not REJECT and not CERTIFY. The finding is then that the
binary no longer admits a negative control, and the remedy is any invocation that
forces `n_eff ≡ 1`. I will name the cheapest one to retain rather than the result
I would prefer.

### 3.4 Determinism

The decision arm is run **twice on identical input** and the outputs compared by
SHA-256. A mismatch is a REJECT. Cheap, automatic, and it catches a class of
defect the ratio cannot see because averaging hides it. Reported `UNSUPPORTED`
when the decision arm itself does not run.

---

## 4. The blind spot in my own harness, stated before it can be used against me

**A static burst is degenerate for focus. Every frame is in focus.** Therefore
the correct gate behaviour *on my plant* is to admit all N frames — and a merge
that admits everything **unconditionally**, having ceased to discriminate focus
at all, scores exactly √N on my battery.

**My battery cannot distinguish a correct estimator from a merge that has stopped
being a focus stacker.** This is not a hypothetical; it is the most likely way a
change that makes estimation the default could pass a √N test and still be a
regression. I am the author of the instrument and it is my job to say so before
the result exists, not after.

`src/11-focus-guard.py` is the arm that sees it, and it runs on a **real
through-focus stack** where no truth is available, so it scores nothing:

> **Requirement G.** On `109MSDCF` (22 real frames, asserted), the binary must
> report `mean n_eff / N < 0.95` for **at least one** gate on whatever ladder it
> prints. A binary reporting `n_eff/N ≥ 0.95` at **every** gate has stopped
> discriminating focus on real data, and I return **REJECT** regardless of its
> √N score.

Baseline for scale, not as a target: HEAD spans 0.064–0.227 (§1). G is
deliberately far looser than that. It is a floor against degeneracy, not a
demand that M64 reproduce today's ladder.

**What G cannot do.** It reads the binary's self-reported `n_eff`. It does not
verify that the frames admitted are the *right* frames, and it says nothing about
detail. **Focus-correctness is not in my remit and I will not imply it is.**
`M55b`'s detail battery is the instrument for that, and a CERTIFY from me is a
statement about noise and defaults only. I will write that sentence into the
verdict.

---

## 5. Verdicts I can return

| verdict | condition |
| --- | --- |
| **CERTIFY** | every `required` arm PASSes, G passes, determinism holds, efficiency in band, and ≥ 1 power arm scored POWER-OK |
| **REJECT** | any `required` arm FAILs, or G fails, or determinism fails, or the decision arm's efficiency leaves [0.98, 1.02] — reported with the arm, the number, and the mechanism |
| **CANNOT-CERTIFY** | an instrument arm (§3.1) moved, or no power arm scored POWER-OK (§3.3), or the harness cannot be pointed at the binary |

Arm-level verdicts are `PASS` / `FAIL` / `UNSUPPORTED` (invocation refused; exit
code and stderr logged) / `POWER-OK` / `NO-POWER`. The overall verdict is
computed from the spec by `10-acceptance.py`, not assigned by hand, and the
`reason` string is written into the result JSON alongside it.

A `REJECT` states the observable and the mechanism. It does **not** propose a
fix — proposing the fix is implementing, and I do not implement.

---

## 6. What I will not do

- I will not modify `acceptance-spec.json`'s tolerances after seeing M64's diff.
  If a threshold is wrong it was wrong now, and changing it later is the thing
  pre-registration exists to prevent. Any amendment will be committed **before**
  the deciding run, with its reason, exactly as M55b disclosed its two revisions.
- I will not add an arm after seeing a result in order to rescue a verdict, nor
  drop one to produce a pass. Post-hoc arms are permitted only to *explain* a
  result and are labelled post-hoc, as B4 was in M62 §7.2.
- I will not edit M62's `PREREGISTRATION.md` or `PREREGISTRATION-D.md`.
- I will not touch `SYNTHESIS.md` or `AGENTS.md`, or any file under
  `crates/`, or anything under `D:\`.
- I will not tell M64 what score to aim for, and I have not been told what it
  intends. If it asks me mid-flight, my answer is this document, unchanged.

---

## 7. Deliberately absent

**No expected value for `DEFAULT` appears anywhere above.** §3.2 states the
window I will accept and §4 states the trap I will check for; neither says which
side of either I anticipate. The current binary does not produce a default merged
output at all (§1), so I have no measurement to extrapolate from and I decline to
manufacture one.

If M64's default scores √30, I will report that. If it scores 1.0 and behaves as
a selector, I will report that with the same prominence. If it scores √30 by
admitting every frame on real stacks too, **G catches it and I reject**, and that
is the outcome I consider most worth guarding against — which is a statement
about my instrument's weakness, not about my expectation of their work.
