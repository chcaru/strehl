"""Build a measurement bundle for one subject and stop.

`vn_commission.py`'s main() builds the bundle and then runs its whole damage
ladder. For the plateau work only the bundle is wanted, so this calls
`build_bundle` directly.
"""
import sys

import vn_commission as C


def main(argv):
    if not argv:
        raise SystemExit("usage: vn_bundle.py <subject> [<subject> ...]")
    for subj in argv:
        print("BUNDLE %s" % subj)
        sys.stdout.flush()
        meta, arrs = C.build_bundle(subj)
        ok = [r["frame"] for r in meta["rows"] if r["state"] == "OK"]
        ok = [k for k in ok if "b%04d" % k in arrs]
        print("  %s: %d/%d frames registered and kept"
              % (subj, len(ok), len(meta["rows"])))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
