"""Detail-SNR normalisation of the M93 gate fire rates.

Reads the `gate` mode outputs and reweights each stack's per-bin election-change
rate by a single common reference detail distribution (the placebo stack,
`flowers-cpl`). Without this, a stack is ranked by how much texture it contains
rather than by how contaminated it is -- fact 1187 measured ~8x of raw
disagreement to be detail composition.
"""

import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "out"
EDGES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0]
ARMS = ["H hard gate", "S soft demote", "G5 shuffled-z"]


def parse(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in txt.splitlines() if not re.match(r"\s+pass\d frame", ln)]
    out = {"path": path.name}
    for ln in lines:
        if ln.startswith("frames "):
            out["n"] = int(re.search(r":\s*(\d+)", ln).group(1))
        if ln.startswith("iso / black"):
            out["iso"] = re.search(r"Some\(([\d.]+)\)", ln).group(1)
        m = re.match(r"^n\s+((?:\s*[\d.]+e-?\d+)+)$", ln)
        if m:
            out["nbin"] = [float(v) for v in ln.split()[1:]]
        for a in ARMS:
            if ln.startswith(a):
                vals = ln[len(a):].split()
                out.setdefault("rate", {})[a] = [
                    None if v == "-" else float(v) for v in vals
                ]
        m = re.match(r"^arm (\S+) .*changed\s+([\d.]+)%.*speckle\s+(\S+)\s+\(\s*([-+][\d.]+)%\).*mean response\s+([\d.]+)\s+\(([-+][\d.]+)%\)", ln)
        if m:
            out.setdefault("chg", {})[m.group(1)] = (
                float(m.group(2)), float(m.group(3)), float(m.group(4)),
                float(m.group(5)), float(m.group(6)),
            )
        m = re.match(
            r"^arm (\S+) .*\bH ([\d.]+) \(\s*([-+][\d.]+)%\)\s+med ([\d.]+)"
            r"\s+p99\s+([\d.]+)\s+p999\s+([\d.]+)\s+adm\s+([\d.]+) \(\s*([-+][\d.]+)%\)",
            ln,
        )
        if m:
            out.setdefault("h", {})[m.group(1)] = (
                float(m.group(2)),  # H mean
                float(m.group(4)),  # median
                float(m.group(5)),  # p99
                float(m.group(6)),  # p999
                float(m.group(3)),  # dH %
                float(m.group(7)),  # adm
                float(m.group(8)),  # dadm %
            )
        if "violations (" in ln:
            out["inv"] = out.get("inv", "") + ln.strip().split("--")[-1].strip() + " "
        m = re.search(r"discrepant samples:\s*([\d.]+)%", ln)
        if m:
            out["disc"] = float(m.group(1))
        m = re.match(r"^arm (\S+)[^\d]*?(\d+) pixels \(([\d.]+)%\)", ln)
        if m:
            out.setdefault("hot", {})[m.group(1)] = (int(m.group(2)), float(m.group(3)))
    return out


def reweight(rate, ref_n):
    """Rate the gate would fire at if this stack had the reference stack's
    detail composition. Bins where the reference is empty contribute nothing;
    bins where this stack is empty but the reference is not are treated as the
    nearest populated lower bin, which is conservative (it cannot invent firing).
    """
    num = 0.0
    den = 0.0
    last = 0.0
    for j, w in enumerate(ref_n):
        if w <= 0:
            continue
        r = rate[j]
        if r is None:
            r = last
        else:
            last = r
        num += w * r
        den += w
    return num / den if den else float("nan")


def main():
    files = {
        "flowers-cpl": "gate-flowers-cpl.txt",
        "lead-1-cpl": "gate-lead-1-cpl.txt",
        "foam": "gate-foam.txt",
        "coffee-bean": "gate-coffee-bean.txt",
        "coffee-bean+pn": "gate-coffee-bean-photonorm.txt",
    }
    data = {}
    for k, v in files.items():
        p = OUT / v
        if p.exists():
            data[k] = parse(p)
        else:
            print(f"(missing {v})", file=sys.stderr)
    ref = data["flowers-cpl"]["nbin"]

    print("Reference detail distribution = flowers-cpl (the measured-cleanest stack).")
    print()
    hdr = f"{'stack':<16}{'n':>5}{'iso':>8}{'|z|>8 %':>9}{'raw fire %':>12}{'norm fire %':>13}{'x placebo':>11}{'dH %':>9}"
    print(hdr)
    print("-" * len(hdr))
    base = None
    rows = []
    for k, d in data.items():
        if "rate" not in d or "h" not in d or "chg" not in d or "S" not in d["h"]:
            continue
        raw = d["chg"]["S"][0]
        norm = 100.0 * reweight(d["rate"]["S soft demote"], ref)
        if k == "flowers-cpl":
            base = norm
        dh = d["h"]["S"][4]
        rows.append((k, d, raw, norm, dh))
    for k, d, raw, norm, dh in rows:
        print(
            f"{k:<16}{d['n']:>5}{d['iso']:>8}{d['disc']:>9.4f}"
            f"{raw:>12.4f}{norm:>13.4f}{norm / base:>11.1f}{dh:>9.2f}"
        )
    print()
    for k, d in data.items():
        if "inv" in d:
            print(f"{k:<16} invariant: {d['inv'].strip()}")
    print()
    print("Per-arm summary, all stacks (MEASURED):")
    hdr2 = (
        f"{'stack':<16}{'arm':<4}{'changed %':>11}{'resp %':>9}{'speckle %':>11}"
        f"{'hot %':>9}{'dHmean %':>10}{'dp99 %':>9}{'dp999 %':>9}{'dadm %':>9}"
    )
    print(hdr2)
    print("-" * len(hdr2))
    for k, d in data.items():
        if "h" not in d or "hot" not in d or len(d["h"]) < 4:
            continue
        h0 = d["h"]["0"]
        for a in ["0", "H", "S", "G5"]:
            c = d["chg"][a]
            h = d["h"][a]
            hot = d["hot"][a][1]
            print(
                f"{k:<16}{a:<4}{c[0]:>11.4f}{c[4]:>9.3f}{c[2]:>11.2f}{hot:>9.4f}"
                f"{h[4]:>10.2f}{100.0 * (h[2] / h0[2] - 1.0):>9.2f}"
                f"{100.0 * (h[3] / h0[3] - 1.0):>9.2f}{h[6]:>9.3f}"
            )
    print()
    print("Benefit normalised by the admitted-frame increase it buys. The gate lowers the")
    print("tolerance band centre, which admits more frames, which lowers H by smoothing")
    print("alone. G5 (shuffled z) raises `adm` the same way with no spatial contamination")
    print("information, so it bounds how much of the benefit that artefact can explain.")
    hdr4 = (
        f"{'stack':<16}{'S dH/dadm':>11}{'G5 dH/dadm':>12}{'ratio':>8}"
        f"{'S dH/dchg':>11}{'G5 dH/dchg':>12}{'ratio':>8}"
    )
    print(hdr4)
    print("-" * len(hdr4))
    for k, d in data.items():
        if "h" not in d or len(d["h"]) < 4:
            continue
        s, g = d["h"]["S"], d["h"]["G5"]
        cs, cg = d["chg"]["S"][0], d["chg"]["G5"][0]
        if abs(g[6]) < 1e-4 or abs(cg) < 1e-6:
            print(f"{k:<16}{'(placebo denominators are ~0)':>62}")
            continue
        a, b = s[4] / s[6], g[4] / g[6]
        c, e = s[4] / cs, g[4] / cg
        print(f"{k:<16}{a:>11.3f}{b:>12.3f}{a / b:>8.2f}{c:>11.3f}{e:>12.3f}{c / e:>8.2f}")
    print()
    print("Speckle generated per point of election changed (lower = more spatially")
    print("coherent). The G5 column is the placebo: a z field with the same marginal")
    print("distribution but no spatial correspondence to the image.")
    hdr3 = f"{'stack':<16}{'arm S':>10}{'arm G5':>10}{'ratio G5/S':>12}"
    print(hdr3)
    print("-" * len(hdr3))
    for k, d in data.items():
        if "chg" not in d:
            continue
        s = d["chg"]["S"]
        g = d["chg"]["G5"]
        if s[0] > 0 and g[0] > 0:
            rs = s[2] / s[0]
            rg = g[2] / g[0]
            print(f"{k:<16}{rs:>10.2f}{rg:>10.2f}{rg / rs:>12.2f}")


if __name__ == "__main__":
    main()
