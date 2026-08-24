"""Verify `docs/research/M95-kernel.md` against the JSON it claims to report.

Two passes, on the model of the arm-7 and arm-8 verifiers:

* **PRESENT** -- every expected value, formatted exactly as the report should
  render it, occurs in the report text.
* **DISCRIMINATE** -- the same value, perturbed in its last significant digit,
  does *not* occur. This is what makes PRESENT mean something: a check that
  passes on any text is not a check.

The report is read whitespace-collapsed, because prose wraps and a plain
substring search fails on a phrase that spans a line break.

Exit code 0 = green, 1 = red.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPORT = HERE.parents[1] / "docs" / "research" / "M95-kernel.md"
OUT = HERE / "out"


def collapse(s):
    return re.sub(r"\s+", " ", s)


def bump(tok):
    """Perturb the last digit of a numeric token, for the DISCRIMINATE pass."""
    m = re.search(r"\d(?!.*\d)", tok)
    if not m:
        return None
    d = int(m.group())
    return tok[: m.start()] + str((d + 1) % 10) + tok[m.end() :]


class Check:
    def __init__(self, text):
        self.text = text
        self.rows = []

    def _find(self, tok, ctx):
        if ctx is None:
            return tok in self.text
        pat = re.escape(ctx) + r".{0,90}?" + re.escape(tok)
        return re.search(pat, self.text) is not None

    def has(self, label, tok, ctx=None):
        """Assert `tok` is in the report and its last-digit decoy is not.

        `ctx` anchors short tokens. A bare "0.5" or "320" is almost certain to
        occur somewhere in a long report by coincidence, so its decoy occurs
        too and DISCRIMINATE fails for a reason that has nothing to do with the
        claim. Anchoring on a neighbouring literal from the same table row
        restores the check instead of weakening it.
        """
        present = self._find(tok, ctx)
        alt = bump(tok)
        discriminates = alt is not None and not self._find(alt, ctx)
        self.rows.append((label, tok, present, discriminates, alt))

    def report(self):
        npass = 0
        print(f"  {'claim':<44} {'value':>14}  PRESENT  DISCRIM")
        for label, tok, p, d, alt in self.rows:
            ok = p and d
            npass += ok
            print(
                f"  {label:<44} {tok:>14}  {'yes' if p else 'NO ':>7}  "
                f"{'yes' if d else 'NO ':>7}" + ("" if ok else f"   <- decoy {alt!r}")
            )
        return npass, len(self.rows)


def main():
    k1 = json.loads((OUT / "k1_radius.json").read_text(encoding="utf-8"))
    k3 = json.loads((OUT / "k3_kernel.json").read_text(encoding="utf-8"))
    p64 = json.loads((OUT / "k3_port64.json").read_text(encoding="utf-8"))
    k5 = json.loads((OUT / "k5_port.json").read_text(encoding="utf-8"))
    txt = collapse(REPORT.read_text(encoding="utf-8"))

    c = Check(txt)

    # ---- B23 ladder ------------------------------------------------------
    r = k3["b23_ringing"]
    c.has("B23 p99 gradient DN", f"{r['t99_dn']:.2f}")
    c.has("B23 p99.9 gradient DN", f"{r['t999_dn']:.2f}")
    for g in r["ladder"]:
        gate = int(g["gate_dn"])
        c.has(f"B23 gate {gate} population", f"{g['n']:,}".replace(",", " "))
        for kk in g["kernels"]:
            if kk["kernel"] not in ("catmull-rom", "lanczos3"):
                continue
            short = "cr" if kk["kernel"] == "catmull-rom" else "lz"
            c.has(f"B23 gate {gate} {short} mean", f"{kk['mean_dn']:.4f}")
            c.has(f"B23 gate {gate} {short} max", f"{kk['max_dn']:.4f}")

    # ---- K22 step --------------------------------------------------------
    for k in ("catmull-rom", "lanczos3"):
        v = r["k22_step"][k]
        c.has(f"K22 {k} overshoot DN", f"{v['overshoot_dn']:.4f}")
        c.has(f"K22 {k} pct of step", f"{v['pct_of_step']:.4f}")

    # ---- spatial extent --------------------------------------------------
    for k in ("catmull-rom", "lanczos3"):
        for i, v in enumerate(r["radial"][k]):
            c.has(f"radial {k} d={i}", f"{v:.4f}")

    # ---- B24 election ----------------------------------------------------
    e = k3["b24_election"]
    c.has("B24 pixels compared", f"{e['n_pixels']:,}".replace(",", " "))
    c.has("K23 null pct", f"{100 * e['k23_null']:.6f}")
    c.has("K24 power pct", f"{100 * e['k24_power']:.6f}")
    c.has("B24 lanczos3 pct", f"{100 * e['b24_lanczos3']:.6f}")
    c.has("B24 ref bilinear pct", f"{100 * e['ref_bilinear']:.6f}")
    c.has("K24 planted win share pct", f"{100 * e['k24_planted_share']:.4f}")
    c.has("K24 share of reachable pct", f"{100 * e['k24_of_reachable']:.4f}")
    c.has("B24 median margin at flip", f"{e['b24_median_margin']:.6f}")
    c.has("B24 median margin overall", f"{e['all_median_margin']:.6f}")
    c.has("B24 separation", f"{e['all_median_margin'] / e['b24_median_margin']:.1f}")

    # ---- crops -----------------------------------------------------------
    for d in k3["diff_split"]:
        tag = f"crop x{d['x']} y{d['y']}"
        c.has(f"{tag} p99.9", f"{d['p999_dn']:.2f}")
        c.has(f"{tag} RMS edge", f"{d['rms_edge_dn']:.3f}")
        c.has(f"{tag} RMS flat", f"{d['rms_flat_dn']:.3f}")
        c.has(f"{tag} edge/flat", f"{d['edge_over_flat']:.2f}", ctx=f"{d['rms_flat_dn']:.3f}")
    w = k3["worst_overshoot"]
    c.has("worst gated overshoot DN", f"{w['dn']:.2f}")
    c.has("worst gated local contrast", f"{w['contrast_dn']:.1f}", ctx="contrast")

    # ---- B22 port --------------------------------------------------------
    c.has("B22 phases probed", str(k5["n_phases"]), ctx="Probed at")
    c.has("B22 catmull-rom tap error", f"{k5['tap_max_dw']['catmull-rom']:.3e}")
    c.has("B22 lanczos3 tap error", f"{k5['tap_max_dw']['lanczos3']:.3e}")
    for k in ("nearest", "bilinear", "catmull-rom", "lanczos3"):
        c.has(f"B22 {k} support", f"{p64['b22_taps'][k]['support']:.1f}", ctx=f"| {k} |")
    a = k5["arms"]
    c.has("B22 catmull-rom gather cost", f"{a['catmull-rom'][0]:.4f}")
    c.has("B22 lanczos3 gather cost", f"{a['lanczos3'][0]:.4f}")
    c.has("B22 tile-warp n", str(a["lanczos3"][2]), ctx=f"{a['lanczos3'][0]:.4f}")
    c.has("B22 kernel gain", f"{k5['gain']:.4f}")
    c.has("B22 arm8 gain", f"{k5['arm8_gain']:.4f}")
    c.has("normalisation sum at f=0.5", f"{k5['unnorm_sum_half']:.7f}")
    c.has("normalisation gain error pct", f"{100 * (k5['unnorm_sum_half'] - 1):.4f}".lstrip("-"))
    sq = k5["unnorm_sum_half"] ** 2
    c.has("normalisation 2-D squared", f"{sq:.7f}")
    c.has("normalisation 2-D pct", f"{100 * (sq - 1):.4f}".lstrip("-"))

    # ---- B20 b-spline ----------------------------------------------------
    c.has("B20 z", f"{k1['z']:.10f}".lstrip("-"))
    c.has("B20 decay per unit R", f"{1 / abs(k1['z']):.4f}")
    for row in k1["radius_sweep"]:
        if row["R"] >= 8:
            c.has(f"B20 R={row['R']} error", f"{row['max_err']:.6e}")
    c.has("B21 b-spline interp error", f"{k1['B21_interp_err']:.3e}")

    print("PASS 1 -- PRESENT and DISCRIMINATE, report vs JSON\n")
    npass, ntot = c.report()
    print(f"\n  {npass}/{ntot} numeric claims verified")

    # ---- structural checks ----------------------------------------------
    print("\nPASS 2 -- structural claims\n")
    struct = []
    # Collapsed, not raw: prose wraps, and a plain substring search fails on a
    # phrase that spans a line break. That trap fired on the very first run of
    # this verifier, on "unchanged at `catmull-rom`".
    raw = collapse(REPORT.read_text(encoding="utf-8"))
    for lbl in [f"**P{i}" for i in range(95, 104)]:
        struct.append((f"fact label {lbl.strip('*')}", lbl in raw))
    struct.append(("default stated unchanged", "unchanged at `catmull-rom`" in raw))
    struct.append(("K24 failure disclosed", "K24 FAILED its registered bar" in raw))
    struct.append(("arm 7 correction disclosed", "9.902" in raw and "1.78" in raw))
    struct.append(("eye-refutes-metric disclosed", "The eye refuted my own metric" in raw))
    struct.append(("b-spline non-ship disclosed", "does not ship" in raw))
    struct.append(("corpus_lint disclosure", "M107-chroma.md" in raw))
    struct.append(("merge_cmd untouched stated", "reported and stopped" in raw.lower()))
    struct.append(("pre-registration deviation disclosed", "Deviation from pre-registration" in raw))
    for lbl, ok in struct:
        print(f"  {lbl:<44} {'yes' if ok else 'NO'}")
    spass = sum(1 for _, ok in struct if ok)
    print(f"\n  {spass}/{len(struct)} structural claims verified")

    green = npass == ntot and spass == len(struct)
    print(f"\n{'GREEN' if green else 'RED'}")
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
