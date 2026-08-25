"""M87 -- what the rank statistic prints on data with no effect in it.

ORCH's warning (facts 1457, 1463, 1468, 1472): four instruments returned
confident numbers while measuring the wrong thing, one of them a 2-bin Spearman
reading +1.0000 on random data.  §34 reports Spearman rho(gate, V) = -1.0000
over a FOUR-arm ladder, which is the same family.

This enumerates the exact null rather than sampling it: for n distinct points
every one of the n! rank permutations is equally likely under the null, so
P(rho = -1) is countable exactly.  No simulation, no seed, no tolerance.
"""
import itertools
import json
import pathlib

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


def rho(a, b):
    n = len(a)
    ra = {v: i for i, v in enumerate(sorted(a))}
    rb = {v: i for i, v in enumerate(sorted(b))}
    d2 = sum((ra[x] - rb[y]) ** 2 for x, y in zip(a, b))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    out = {}
    for n in (4, 5, 6, 7, 8):
        base = list(range(n))
        perms = list(itertools.permutations(base))
        both = sum(1 for p in perms if abs(rho(base, list(p))) == 1.0)
        neg = sum(1 for p in perms if rho(base, list(p)) == -1.0)
        out[str(n)] = {
            "permutations": len(perms),
            "p_abs_one": both / len(perms),
            "p_minus_one": neg / len(perms),
        }
        print("n=%d  perms=%-6d  P(|rho|=1)=%.4f  P(rho=-1)=%.4f"
              % (n, len(perms), both / len(perms), neg / len(perms)))

    # The ladder actually reported in section 34 has four arms.
    out["ladder_n"] = 4
    out["ladder_p_minus_one"] = out["4"]["p_minus_one"]
    # How many arms would be needed for a perfect reversal to clear 1 in 100?
    need = min(n for n in (4, 5, 6, 7, 8) if out[str(n)]["p_minus_one"] < 0.01)
    out["arms_for_p_below_0_01"] = need
    print("the section 34 ladder has %d arms; P(rho=-1) there is %.4f"
          % (out["ladder_n"], out["ladder_p_minus_one"]))
    print("a perfect reversal first clears p<0.01 at n=%d" % need)

    (DATA / "rho-null.json").write_text(json.dumps(out, indent=2, sort_keys=True),
                                        encoding="utf-8")


if __name__ == "__main__":
    main()
