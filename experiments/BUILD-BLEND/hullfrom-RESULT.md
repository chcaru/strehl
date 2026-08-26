# `--hull-from` sweep: the defect it was built to attack is not present at HEAD

Protocol: ORCH's corrected clean one — camera-linear, `--gate 4`,
`--base-mean`, `flower-bud-alone-cpl` (205 frames). All arms rendered by one
binary (`blend-render` `8F8DECAE`) so binary drift cannot confound the
blend-vs-blend comparison.

| arm | clip% | acuity | microC | p1 | what it is |
|---|---:|---:|---:|---:|---|
| `ref` | 0.0000 | 100.6 | 43.94 | 1044 | `hull=InputRange`, my build |
| `hf6` | 0.0000 | 100.6 | 43.94 | 1047 | per-level bound, levels ≥6 only |
| `hf4` | 0.0000 | 100.6 | 43.94 | 1055 | levels ≥4 |
| `hf2` | 0.0000 | 100.3 | 43.94 | 1060 | levels ≥2 |
| `noca` | 0.0000 | 99.6 | 44.48 | 1043 | `ref` with CA forced off |

`GATE: PASS`, all arms.

## The finding is not about the sweep

ORCH measured **1.4015%** clipping on this exact subject with these exact
flags. I measure **0.0000%**. The flags match, so the difference is the
binary: ORCH's pin `tree-lin-0d9fd28` / `blend-render 19786CC7` against my
build `8F8DECAE`.

Ruled out as the cause:

- **Lateral CA.** The `noca` arm forces it off and still clips `0.0000`, so
  the correction is not masking the defect.
- **My hull work.** `MergeConfig::default()` is `hull=InputRange`,
  `hull_from_level=1`, `hull_low_only=false`, which reproduce prior behaviour
  exactly and are pinned by a passing test. Inert in the `ref` arm.

Something another agent landed between that pin and HEAD fixed it. I have not
identified what, and I am not going to guess.

## A second staleness in the same protocol

Found by the sweep script's own CA guard. Unsetting `STREHL_FIX_CA` no longer
turns CA off:

```
mine  lateral CA : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (default on)
pin   lateral CA : off (STREHL_FIX_CA unset)
```

The default flipped to on-when-gear-matches. `Remove-Item Env:\STREHL_FIX_CA`
is a no-op on matching gear; only `STREHL_FIX_CA="off"` disables it. **Every
"CA explicitly unset" measurement taken against HEAD is confounded**, and the
guard only caught it because it checked for the *line*, not for the *value* I
expected to see.

## Registered predictions, resolved

Written in `hullfrom.ps1` before the first render.

| | prediction | outcome |
|---|---|---|
| P1 | `--hull-from 6` removes a large share of the clip | **UNTESTABLE** — no clip left to remove. Not confirmed. |
| P2 | acuity at `--hull-from 6` is within noise of `ref` (≥0.99) | **CONFIRMED, exactly** — 100.6 vs 100.6. A bound confined to 55 px costs literally nothing at the scales the gate reads. |
| P3 | clip monotone in `hull-from` | **UNTESTABLE**, all zero. |
| P4 | acuity monotone in `hull-from` | **Weakly confirmed, nearly flat** — 100.6 / 100.6 / 100.3 for hf6/hf4/hf2. *Not* comparable to the earlier 0.953 `PerLevel` figure, which was a different subject on a different instrument. |

The scale-separation argument survives as far as it was tested — coarse-only
bounding is free — but the fix it was built for is not needed on this subject
at this HEAD. `Hull::PerLevel` and `hull_from_level` stay opt-in, off by
default, available if the excursion returns.
