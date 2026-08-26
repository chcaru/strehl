"""Insert the STREHL_PYRAMID_MEAN_COARSE registry entry into check-defaults.py.

Anchored on a unique full line and hard-errors if the anchor does not land
exactly once, so a silent no-op is impossible.
"""
import io

PATH = r"scripts/check-defaults.py"
ANCHOR = '    "STREHL_PYRAMID_WORKERS": Declared(\n'

ENTRY = '''    "STREHL_PYRAMID_MEAN_COARSE": Declared(
        kind="control",
        default="0 (no Laplacian band averaged; base band is a mean regardless)",
        verified="measured",
        evidence="pyramid.rs (MEAN_COARSE_ENV, DEFAULT_MEAN_COARSE, "
        "mean_coarse_default); applied in the band loop, tested by "
        "averaging_the_coarse_bands_is_not_the_same_merge",
        note=(
            "How many of the COARSEST Laplacian bands the pyramid merge "
            "averages instead of selecting. Built to answer ORCH's registered "
            "criteria on the far-field bowl, measured on a 4-rung ladder over "
            "flower-bud-with-background-fern-cpl, and DELIBERATELY LEFT AT 0. "
            "Off is the right default and it was measured, not assumed: "
            "criterion (a), the bowl, ALREADY PASSES at 0 -- the residual bowl "
            "is +191 DN at d=550, which is +0.35 of 255 at ORCH's operating "
            "point against their 1.00 bar -- while every rung that closes the "
            "bowl further fails criterion (b), retaining only 44.3% (mc=2) and "
            "25.2% (mc=3) of the mid-field win against an 88.6% bar. ORCH "
            "pre-registered the response to exactly that outcome: report it as "
            "a failure and do not ship. mc=1 is a genuine trade rather than an "
            "improvement (better than mc=0 on every row from d=2 to d=90, "
            "worse by 142-194 DN across d=112-225) and is left available. "
            "ORCH's much larger measured bowl came from a toned+sRGB pair "
            "whose blend arm carried a collapsed black point; on untoned "
            "linear renders the control arm's rows transfer at 1.40x and the "
            "blend arm's at 4.79x, a 3.42x discriminating ratio. "
            "COMMISSIONED: rung 0 is byte-identical (SHA-256 84A4661D...D655C) "
            "to the render made before this knob existed, so the default "
            "cannot move a byte, and rungs 1-3 all differ from it, so the env "
            "var demonstrably reaches pixels. Full ladder and both instruments "
            "in docs/research/BUILD-BLEND.md and experiments/BUILD-BLEND/."
        ),
    ),
'''

src = io.open(PATH, encoding="utf-8").read()
if "STREHL_PYRAMID_MEAN_COARSE" in src:
    raise SystemExit("entry already present -- refusing to duplicate")
n = src.count(ANCHOR)
if n != 1:
    raise SystemExit(f"ANCHOR NOT FOUND EXACTLY ONCE (found {n}) -- refusing to edit")
io.open(PATH, "w", encoding="utf-8", newline="").write(src.replace(ANCHOR, ENTRY + ANCHOR, 1))
print("inserted STREHL_PYRAMID_MEAN_COARSE before STREHL_PYRAMID_WORKERS")
