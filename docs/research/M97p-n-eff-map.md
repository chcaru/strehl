# M97p — `--n-eff-map`, the twin of the election map

Status: SHIPPED. Milestone M97, at the orchestrator's request.

## 1. What it is

`--n-eff-map <PATH>` (and `STREHL_DUMP_NEFF=<path>`) writes the per-pixel
`n_eff` field — the number of frames the noise gate could not separate from the
winner, and therefore averaged — as a single-channel 16-bit TIFF.

It is the twin of `--index-map` (M97m, `b27904a`) and deliberately shares its
grid: the **plane** grid at half sensor resolution, one value per 2×2 CFA quad.
The two maps are the same size and overlay pixel-for-pixel with no resampling.
One says *which* frame won; this says *how many* were indistinguishable from it.

**Values** are literal frame counts starting at **1** — the winner is always
within tolerance of itself, so no decided pixel can read 0. The ceiling is the
u16 one, **65535**; a value outside `1..=frames_folded` is refused rather than
written, because a saturated count read as a real one would understate
averaging exactly where averaging was heaviest.

`n_eff` is **per-gate**, so `--n-eff-map` requires exactly one `--gate`,
refused before a frame is read. This mirrors `--out`'s existing rule. A debug
map silently labelled with the wrong gate is worse than no map, because it
looks like evidence.

## 2. Why it was worth building

`n_eff` is already this project's headline quality number and is reported only
as a **scalar mean**, yet the gate that reaches `n_eff = 3` spans 0.7618 to
21.9934 across the corpus — a factor of **28.9** — and `foam` cannot reach 3
anywhere on the shipped ladder. A mean over a field that varies that much
between scenes is averaging over structure nobody could see.

It also makes a specific hypothesis about the "waxy blob" artefact testable:
that the gate admits frames on a **focus-measure** test while what actually
licenses averaging is **PSF similarity**, so in smooth defocused regions it
averages frames whose PSFs differ and produces extra blur rather than less
noise. That predicts `n_eff` high and near-constant inside a blob with a jump
at its boundary. **That hypothesis is ARGUED and is not mine**; this map is the
instrument that can kill it.

## 3. Pre-registered bars, and the results

Written before the code (`prereg-E.txt`), with the named falsification input:
*if E1 fails, the export perturbs the render and must not ship at all — an
instrument that changes its subject is not an instrument.*

| bar | claim | result |
| --- | --- | --- |
| E1 | merged bytes identical: no map / flag / env | **PASS** — `09FA927898ABF314` all three |
| E1b | PLANT: the hash must be able to move | **PASS** — gate 2 gives `360634D92341C3CA` |
| E2 | both mechanisms agree; flag wins | **PASS** — maps both `7E557F83C8F55A82`; env path not written |
| E3 | map mean reproduces the printed scalar | **PASS** — 4.5633 vs 4.5630, Δ 0.00026 |
| E3b | PLANT: same at a second gate, and the two differ | **PASS** — 2.8295 vs 2.8290, Δ 0.00047 |
| E5 | two gates refused before reading a frame | **PASS** — exit 1, no map written |

### Facts

- **U1 (MEASURED).** The export does not perturb the render: three invocations
  differing only in whether and how the map was requested produce the identical
  merged image `09FA927898ABF314`.
- **U2 (MEASURED).** That null is not vacuous: the same wiring at gate 2 moves
  the hash to `360634D92341C3CA`.
- **U3 (MEASURED).** The map is *connected*, not merely present. Its mean
  reproduces the `mean n_eff` scalar that `report()` computes independently, to
  0.00026 at gate 4 and 0.00047 at gate 2 — and the two means are far apart
  (4.563 vs 2.829), which a disconnected or constant buffer could not do at
  both gates.
- **U4 (MEASURED).** On `flat-on-ruler-cpl --limit 20 --gate 4` the field spans
  the full `1..20`, all 20 counts present. The gate is not degenerate here: it
  is neither pure selection nor a flat mean.
- **U5 (DERIVED).** Because `n_eff` at gate 4 averages 4.563 of 20 frames while
  the same stack at 79 frames reported mean 1.154, `n_eff` is not a fixed
  fraction of bracket length — consistent with M52's refutation of fact 324's
  stated mechanism.

## 4. What is NOT verified

- **The range guard (E4) is unexercised.** No run produced a value outside
  `1..=frames_folded`, so the `ensure!` that refuses a saturated or zero count
  has never fired on real data. It is a guard, not a measurement, and is
  recorded as such rather than claimed as verified.
- **This map changes no pixels.** Like the election map, it is an instrument.
  It does not address the owner's complaint by itself; it lets someone else
  test a hypothesis about it.
- The blob hypothesis in §2 is the orchestrator's and is ARGUED. Nothing here
  supports or refutes it — that is M111's work, and the point of shipping the
  map is that the question becomes answerable rather than arguable.

## 5. Method note

E3 is the bar that matters, and it is the one an "export exists" check would
have missed. Comparing the exported bytes against a scalar computed by a
*different* code path in `report()` is what distinguishes a live probe from a
plausible-looking buffer. Running it at two gates (E3b) is the plant: a
constant, a stale buffer or an off-by-one field could match one printed scalar
by luck, but not two that differ by 1.7 frames.
