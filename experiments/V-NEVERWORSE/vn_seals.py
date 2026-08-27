"""Which build sealed which corpus? Hash everything; trust no name.

ORCH broadcast that pin 740e7056 was "the wrong pin", then corrected it: it is
the wrong pin for SHIP-V4 and the RIGHT pin for SHIP-V3. The corrected rule is
that a build is identified by its hash checked against the seal of the corpus
you are comparing to -- never by name, size, path or recollection.

This script is that check, run exhaustively rather than asserted:

  * hash every strehl.exe under C:\\dev and group by digest;
  * read every <subject>.tiff.ok seal and group by the directory it seals;
  * report any corpus carrying more than one seal (not internally consistent),
    any seal with no matching binary on disk, and any binary whose PATH NAME
    claims a corpus its hash does not seal.

The last of those is the one that bites: `strehl-out\\PIN-V3\\strehl.exe` is not
the SHIP-V3 pin, and it is the same byte size as both real shipping pins.

  python vn_seals.py [--root C:\\dev]
"""
import argparse
import collections
import hashlib
import os
import sys

DEFAULT_ROOT = r"C:\dev"
OUTS = r"C:\dev\strehl-out"

# corpus -> the build its seals must carry, established by this script's own
# first run and kept here so a later drift is a FAILURE rather than a new fact.
EXPECT = {
    r"C:\dev\strehl-out\acceptance\SHIP-V4": "44C2F2CD",
    r"C:\dev\strehl-out\acceptance\SHIP-V3": "15EA7346",
    r"C:\dev\strehl-out\SHIP-V2": "CF33AE08",
}
# Trees that deliberately contain inconsistent seals: they are fixtures for
# other lanes' pin-checking tools, not incidents. Anything OUTSIDE these that
# is inconsistent is an incident.
FIXTURES = ("pincommission", "pinguard", "PINTEST")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    a = ap.parse_args(argv)

    builds, n = collections.defaultdict(list), 0
    for dp, _, fns in os.walk(a.root):
        for fn in fns:
            if fn.lower() == "strehl.exe":
                p = os.path.join(dp, fn)
                try:
                    builds[sha(p)].append(p)
                    n += 1
                except OSError:
                    pass
    print("hashed %d copies of strehl.exe under %s -> %d distinct builds\n"
          % (n, a.root, len(builds)))
    by8 = {k[:8]: v for k, v in builds.items()}

    seals = collections.defaultdict(list)
    for dp, _, fns in os.walk(OUTS):
        for fn in fns:
            if fn.endswith(".tiff.ok"):
                with open(os.path.join(dp, fn)) as f:
                    seals[dp].append(f.read().strip().upper())

    print("%-58s %5s  %s" % ("corpus", "seals", "build(s)"))
    incidents = []
    for d in sorted(seals):
        u = sorted(set(s[:8] for s in seals[d]))
        fixture = any(f in d for f in FIXTURES)
        note = ""
        if len(u) > 1 and not fixture:
            note = "  <- NOT INTERNALLY CONSISTENT"
            incidents.append((d, "multiple seals: " + " + ".join(u)))
        for s in u:
            if s not in by8 and not fixture:
                note += "  <- no binary on disk"
                incidents.append((d, "seal %s has no binary on disk" % s))
        print("%-58s %5d  %s%s%s"
              % (d.replace(OUTS, "..."), len(seals[d]), " + ".join(u),
                 "  [fixture]" if fixture else "", note))

    print("\nexpected seals:")
    for d, want in EXPECT.items():
        got = sorted(set(s[:8] for s in seals.get(d, [])))
        ok = got == [want] and len(seals.get(d, [])) == 26
        print("  %-46s %s  %s" % (d.replace(OUTS, "..."),
                                  "OK " if ok else "FAIL",
                                  "%d seals %s" % (len(seals.get(d, [])),
                                                   " + ".join(got) or "none")))
        if not ok:
            incidents.append((d, "expected 26x %s, got %s" % (want, got)))

    # a path that NAMES a corpus it does not seal
    print("\npaths whose name claims a corpus their hash does not seal:")
    named = 0
    for dig, paths in builds.items():
        for p in paths:
            for tag, want in (("PIN-V4", "44C2F2CD"), ("PIN-V3", "15EA7346"),
                              ("PIN-V2", "CF33AE08")):
                if tag.lower() in p.lower() and not dig.startswith(want):
                    named += 1
                    print("  %s  %s  (name says %s, which is %s)"
                          % (dig[:8], p, tag, want))
    if not named:
        print("  none")

    print("\n%d incident(s)" % len(incidents))
    for d, why in incidents:
        print("  %s: %s" % (d, why))
    return 1 if incidents else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
