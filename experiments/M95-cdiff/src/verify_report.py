"""Verify every number in docs/research/M95-cdiff.md against the JSON the
instruments wrote this session, and prove each check discriminates.

Two passes:
  PRESENT      the string appears in the report
  DISCRIMINATE perturbing the value makes the check fail

A check that passes PRESENT but not DISCRIMINATE is matching something else in
the document. Arm 6 hit that with a ladder row silently matching the
per-channel table, so anchors here carry surrounding context.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-cdiff.md"
OUT = Path(__file__).resolve().parents[1] / "out"
COV = ROOT / "experiments" / "M95-coverage" / "out"
RES = ROOT / "experiments" / "M95-resample" / "out"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def norm(s):
    """Canonicalise typography so a check compares data, not glyphs.

    The report uses U+2212 MINUS, U+00D7 TIMES and U+2013 EN DASH where the JSON
    emits ASCII. Folding those is not a weakening: digits are untouched, so the
    mutation pass still has to discriminate on value.
    """
    s = (s.replace("\u2212", "-").replace("\u00d7", "x")
          .replace("\u00a0", " ").replace("\u2013", "-"))
    return re.sub(r"\s+", " ", s)


def main():
    c1 = load(OUT / "c1_ladder.json")
    c2 = load(OUT / "c2_refine.json")
    fx = load(COV / "x8_fix.json")
    kn = load(RES / "x3_kernel.json")
    flat = norm(REPORT.read_text(encoding="utf-8"))

    checks = []

    def add(label, s):
        checks.append((label, norm(s)))

    # ---------------------------------------------------------- headline table
    add("NOW cost", f"| **+{fx['NOW']['cost_dex']:.4f} dex** |")
    add("FIX cost", f"| **+{fx['FIX']['cost_dex']:.4f} dex** |")
    add("SNAP cost", f"| **{fx['SNAP']['cost_dex']:+.4f} dex** |")
    add("fix recovery", f"recovers **{fx['fix_recovery_dex']:+.4f} dex**")
    add("K1 null", f"| **{fx['K1_null']:+.6f} dex** |")
    add("K6 cover alone", f"| **+{fx['K6_cover_alone']:.4f} dex** |")

    # ------------------------------------------------------------- the kernels
    KR = kn["results"]
    # lanczos3 is the recommended kernel and is bolded in the table; the others
    # are not. Arm 6's lesson was that ignoring bold markers causes silent
    # mismatches, so the anchors carry the exact markup rather than stripping it.
    for k in ("catmullrom", "mitchell", "bspline"):
        add(f"kernel {k} phase-avg",
            f"| {k} | {KR[k]['phase_avg']:+.4f} |")
    add("kernel lanczos3 phase-avg",
        f"| lanczos3 | **{KR['lanczos3']['phase_avg']:+.4f}** |")
    add("mitchell identity", f"reads `{KR['mitchell']['identity']:+.6f}`")
    gl = KR["lanczos3"]["phase_avg"] - KR["catmullrom"]["phase_avg"]
    gb = KR["bspline"]["phase_avg"] - KR["catmullrom"]["phase_avg"]
    add("lanczos gain", f"**lanczos3 vs catmullrom: {gl:+.4f} dex**")
    add("bspline gain", f"bspline vs catmullrom: {gb:+.4f} dex")

    # ---------------------------------------------------------- demosaic ladder
    L1, L2 = c1["ladder_luma"], c2["ladder"]
    for arm in ("MHC", "CDIFF"):
        s = L1[arm]
        add(f"ladder {arm} Y",
            f"| {arm} | Y | {s['power']:+.4f} | {s['signal']:+.4f} |"
            f" {s['artifact']:+.4f} | {s['artifact_share']:.4f} |")
    for arm in ("MHC", "CDIFF", "CDIFF2"):
        for ch in "RGB":
            s = c2["ladder"][arm][ch]
            add(f"ladder {arm} {ch}",
                f"| {arm} | {ch} | {s['power']:+.4f} | {s['signal']:+.4f} |"
                f" {s['artifact']:+.4f} | {s['artifact_share']:.4f} |")
    s = L2["CDIFF2"]["luma"]
    add("ladder CDIFF2 Y",
        f"| CDIFF2 | Y | {s['power']:+.4f} | {s['signal']:+.4f} |"
        f" {s['artifact']:+.4f} | {s['artifact_share']:.4f} |")

    # -------------------------------------------------------------------- bars
    b1, b2 = c1["bars"], c2["bars"]
    add("CDIFF gain", f"Luma signal gain **{b1['gain_dex']:+.4f} dex**")
    add("CDIFF dshare", f"artifact share\n**{b1['dshare']:+.4f}**")
    add("CDIFF channels",
        f"**R {b1['channel_gain']['R']:+.4f} / G {b1['channel_gain']['G']:+.4f}"
        f" / B {b1['channel_gain']['B']:+.4f}**")
    add("CDIFF2 gain", f"Luma signal gain\n**{b2['cdiff2_gain']:+.4f} dex**")
    add("CDIFF2 dshare", f"artifact share rises\n**{b2['dshare']:+.4f}**")
    add("CDIFF2 green", f"Green signal moved\n**{b2['channel_gain']['G']:+.4f}**")

    # ---------------------------------------------------------------- controls
    k11 = c1["controls"]["K11"]
    add("K11 CDIFF", f"CDIFF **{k11['CDIFF']['err']:.3e}**")
    add("K11 badnorm", f"`CDIFF_BADNORM` **{k11['CDIFF_BADNORM']['err']:.3e}**")
    add("K11 badparity",
        f"`CDIFF_BADPARITY`\n**{k11['CDIFF_BADPARITY']['err']:.3e}**")
    add("badparity share",
        f"artifact share **{c1['ladder_luma']['CDIFF_BADPARITY']['artifact_share']:.4f}**")
    add("badnorm share",
        f"share\n{c1['ladder_luma']['CDIFF_BADNORM']['artifact_share']:.4f}")

    # --------------------------------------------------------------- run passes
    present = [(lab, s, s in flat) for lab, s in checks]
    npres = sum(1 for _, _, ok in present if ok)
    print(f"PRESENT       {npres}/{len(present)}")
    for lab, s, ok in present:
        if not ok:
            print(f"  MISSING  {lab}: {s[:110]}")

    # A digit-perturbed anchor must NOT be found, or the check is matching
    # something other than the value it claims to check.
    ndisc = 0
    for lab, s, ok in present:
        if not ok:
            continue
        mut = re.sub(r"(\d)(?=\d*\s*(?:dex|\||\*|$))",
                     lambda m: str((int(m.group(1)) + 5) % 10), s, count=1)
        if mut == s:
            mut = s[:-1] + ("9" if s[-1] != "9" else "1")
        if mut not in flat:
            ndisc += 1
        else:
            print(f"  NON-DISCRIMINATING  {lab}")
    print(f"DISCRIMINATE  {ndisc}/{npres}")

    facts = len(re.findall(r"^- \*\*P\d+\.\*\*", REPORT.read_text(
        encoding="utf-8"), re.M))
    labels = len(re.findall(r"`(?:MEASURED|ARGUED|ASSUMED)`", REPORT.read_text(
        encoding="utf-8")))
    print(f"facts {facts} / labels {labels}")

    ok = (npres == len(present) and ndisc == npres and facts == labels
          and facts > 0)
    print("VERIFY PASSED" if ok else "VERIFY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
