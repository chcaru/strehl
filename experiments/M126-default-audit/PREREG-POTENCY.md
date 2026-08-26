# PREREG — M126 potency addendum: the two gates ORCH handed me

**Written before any measurement.** Commit this, then run.

## Context

ORCH's `check-potency.py` (`d8a44e9a`) reports, on two binaries, `109MSDCF`, 8 frames,
`--merge pyramid --srgb`:

| gate | ORCH's verdict |
| --- | --- |
| `STREHL_ROBUST_ELECTION=1` | byte-identical |
| `STREHL_SMOOTH=1` | byte-identical |
| `STREHL_RESTORE=1` | byte-identical |

He asked me to separate **structurally unreachable** from **measurably useless**, by
reading code rather than inferring from the null, and declined to guess. Correct call.

## What I claim from the code, before measuring

I have read the pin's source (`b9b6921e`) and I claim **neither of the two new gates is
a structural null. Both probes used a value equal to the gate's own default.**

### `STREHL_SMOOTH` — the probe value IS the default

`align_cmd.rs:987–991`:

```rust
const DEFAULT_SMOOTH_LAMBDA: f64 = 1.0;
```

`align_cmd.rs:584–590`:

```rust
fn apply_smooth_env(opts: &mut GlobalOptions) {
    let lambda = match std::env::var("STREHL_SMOOTH") {
        Err(_) => DEFAULT_SMOOTH_LAMBDA,        // unset  -> 1.0
        Ok(v) if v.trim().eq_ignore_ascii_case("off") => 0.0,
        Ok(v) => match v.trim().parse::<f64>() { Ok(x) ... => x,   // "1" -> 1.0
```

`STREHL_SMOOTH=1` and unset both yield `lambda = 1.0`. **Byte-identity is the correct
and expected result and carries no information about the gate.** The doc at L529 states
the default moved: *"ON by default at `lambda = 1.0` since BUILD-SHARP. `STREHL_SMOOTH=0`
or `STREHL_SMOOTH=off` restores the free solve bit-exactly."*

It is also **reachable** from the shipping backend — not unreachable like veil/halo:
`merge_cmd.rs:2285` -> `align_cmd::load_or_solve` (L1186) -> `solve_map` (L1242) ->
`apply_smooth_env` (L1143); `run_pyramid` uses the same resolver (`merge_cmd.rs:4384`).

**The absurd value for this gate is `0`/`off`, not `1`.**

### `STREHL_RESTORE` — same shape, already established

`restore.rs:870` `gain_cap_from_env()` returns `None` unless the value is **strictly
> 1.0**; the value *is* the gain cap. `STREHL_RESTORE=1` is a documented no-op.
Additionally the single consuming call site (`merge_cmd.rs:5916`) is inside
`if demosaic { … }`, so on the binned default it is never called. Both established in
`M126-composite.md` §2.1–2.2 before this prereg.

## Arms

Subject `109MSDCF` (22 frames), pin `b9b6921e`, linear/binned, **private
`STREHL_CACHE_DIR` per arm**, all other `STREHL_*` wiped between arms, banner read on
every arm.

| arm | env |
| --- | --- |
| `S_unset` | *(none)* — the shipped default |
| `S_1` | `STREHL_SMOOTH=1` — ORCH's probe |
| `S_0` | `STREHL_SMOOTH=0` — the prior OFF |
| `S_off` | `STREHL_SMOOTH=off` — the documented spelling |
| `S_1000` | `STREHL_SMOOTH=1000` — genuinely absurd |
| `S_h` | `STREHL_SMOOTH_HUBER=off` — the second solve variable |

## Metric

SHA-256 of the linear 16-bit TIFF; and where outputs differ, on a hard
`tifffile`/`uint16` read: fraction of samples differing, and **peak |difference| in DN
of 65535**, in **linear** — not sRGB.

Scored on ORCH's taxonomy, which I adopt: **DEAD** (byte-identical) / **TOKEN** (differs,
peak <= 2 DN) / **LIVE** (differs, peak > 2 DN).

## Predictions — directional, with rough magnitude

| # | prediction | confidence |
| --- | --- | --- |
| **P1** | `S_1` is **byte-identical** to `S_unset`. ORCH's null is a value trap, not a property of the gate. | very high — arithmetic identity in the source |
| **P2** | `S_0` **differs** from `S_unset`. | high — the doc asserts `0` restores a *different* (free) solve |
| **P3** | `S_off` is **byte-identical to `S_0`** and differs from `S_unset`. | high — both take the `lambda <= 0.0` early return |
| **P4** | `S_1000` differs from **both** `S_unset` and `S_0`. | medium — a huge lambda should over-stiffen the track |
| **P5** | `S_0` scores **LIVE**, peak > 2 DN, but the effect is **small** — I predict peak in the **tens to low hundreds of DN**, well under the 908 DN that `--pyramid-gate 4.5` moved, and I expect **< 50 % of samples** to differ. BUILD-SHARP explicitly disclaims a visible sharpening, and the residual it fixes is ~0.2 px at span 1. | medium |
| **P6** | `S_h` differs from `S_unset` (it is in `SOLVE_ENV` and in the cache key). | medium-low |

**Risk I name in advance:** 109MSDCF is only 22 frames, and I have already measured one
gate (`STREHL_FIX_HALO`) that is byte-inert below ~41 frames. If P2 reads DEAD, that is
**not** evidence the gate is dead — it may be a frame-count floor, and I must escalate to
`bee-3-cpl` (299 frames) before concluding anything. I commit to that escalation now so
it cannot look like a post-hoc rescue of a favourable answer.

**Bias check:** P1 is the comfortable prediction — it makes ORCH wrong and me right. It
is also the one I am most confident in, because it is an arithmetic identity I can read.
P2 is the one that can embarrass me: if the prior is genuinely inert on a real render,
then the default that BUILD-SHARP *moved* is not carrying its claim, and I would have to
report that against my own preference for a tidy "ORCH mis-probed it" story.
