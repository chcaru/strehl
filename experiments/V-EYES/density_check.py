"""How much of the corpus ratio is the sampled ceiling rather than the master?

The reference is the best of a SAMPLED bracket. Sample 13 frames out of 299 and
most sites have no in-focus frame among them, so the ceiling is weak and the
ratio inflates; sample 13 out of 22 and the ceiling is nearly the true one. The
first six corpus rows showed exactly that ordering, which means sampling density
is a rival explanation for the whole corpus result and has to be bounded rather
than argued about.

This sweeps the sample size on a few subjects chosen to span stack depth, holding
the tile, block, instrument and binary fixed, and reports how the ratio moves as
the ceiling gets denser. The bias runs one way by construction -- adding frames
can only raise a max, so the ratio can only fall -- so the sweep gives an upper
bound on the true value and shows whether it has converged.

A subject whose ratio stops moving as n doubles has a bounded bias. A subject
still falling at the largest n affordable is reported as still falling, and its
corpus row is an upper bound, stated as one.

Usage:
  python density_check.py <out.tsv> <subject>:<n1,n2,n3> [<subject>:<ns> ...]
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from corpus_softness import COLS, TILE, measure  # noqa: E402


def main():
    outp = pathlib.Path(sys.argv[1])
    # Tile size is an argument because the high-n arms are memory-bound: the
    # instrument holds every reference tile at once, and all seven commissioning
    # arms build two more full sets of blurred copies. At 2048 px a 205-frame
    # reference needs ~21 GB and does not run; at 1024 px it fits. Size is held
    # constant WITHIN a subject's sweep so the density trend is not confounded by
    # a change of tile, and stated in the row so it is never compared across.
    size = int(sys.argv[2])
    outp.parent.mkdir(parents=True, exist_ok=True)
    if not outp.exists():
        outp.write_text("\t".join(COLS) + "\n", encoding="utf-8")

    for spec in sys.argv[3:]:
        subject, ns = spec.split(":")
        for n in (int(v) for v in ns.split(",")):
            # keep=True: renders are reused across the sweep, so doubling n costs
            # only the frames that were not already developed.
            row = measure(subject, size, None, n, None, keep=True)
            with outp.open("a", encoding="utf-8") as fh:
                fh.write("\t".join(str(row[c]) for c in COLS) + "\n")
            print(f"{subject:<30} n={row['n_sampled']:<5} size={size} "
                  f"{row['state']:<9} ratio={row['ratio']} sites={row['n_sites']} "
                  f"{row['secs']}s", flush=True)


if __name__ == "__main__":
    main()
