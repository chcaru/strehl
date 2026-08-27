"""Which build sealed which corpus -- and can this scan even SEE every build?

HISTORY. v1 of this script reported "066A87AB absent from all 160 copies of
strehl.exe under C:\\dev". ORCH refuted it by holding the file:

    066A87AB  C:\\dev\\strehl-out\\V-REVIEW\\bin\\strehl-pinned.exe

The scan filtered on `fn.lower() == "strehl.exe"`. The file is named
`strehl-pinned.exe`. The absence was a property of my QUERY, not of the disk:
162 files matched `strehl.exe` where 306 match `strehl*.exe`. I stated the
scope as the root when the binding scope was the filename pattern.

THE RULE THIS ENCODES. The population a query can reach is part of its claim,
and an absence result is a statement about the query until its reach is
measured. So this script does not merely widen the pattern -- widening is
unfalsifiable on its own, because a wider query that still misses something
looks exactly like a complete one. Instead it PLANTS DECOYS it is required to
find, under names chosen to fall on both sides of each pattern boundary, and
hard-fails if any decoy inside the pattern is missed. Reach is measured, and
the residual blind spot is reported as a number rather than assumed to be zero.

    python vn_seals.py                 # census over strehl*.exe
    python vn_seals.py --wide          # absence-grade reach: every *.exe
    python vn_seals.py --reach-only    # just the decoy commissioning table
"""
import argparse
import collections
import fnmatch
import hashlib
import os
import shutil
import sys

DEFAULT_ROOT = r"C:\dev"
OUTS = r"C:\dev\strehl-out"
DECOYS = r"C:\dev\strehl-out\V-NEVERWORSE\decoys"

# corpus -> the build its seals must carry. Established by measurement and kept
# here so a later drift is a FAILURE rather than a quietly-accepted new fact.
EXPECT = {
    r"C:\dev\strehl-out\acceptance\SHIP-V4": "44C2F2CD",
    r"C:\dev\strehl-out\acceptance\SHIP-V3": "15EA7346",
    r"C:\dev\strehl-out\SHIP-V2": "CF33AE08",
}
# Trees that deliberately hold inconsistent seals: fixtures for other lanes'
# pin-checking tools, not incidents. Anything OUTSIDE these that is
# inconsistent IS an incident.
FIXTURES = ("pincommission", "pinguard", "PINTEST")

# The build ORCH holds. Named so the census reports it by name when found,
# rather than leaving a reader to match hex by eye.
KNOWN = {
    "44C2F2CD": "seals SHIP-V4",
    "15EA7346": "seals SHIP-V3",
    "CF33AE08": "seals SHIP-V2",
    "B50EABC1": "seals nothing shipped; lives at strehl-out\\PIN-V3",
    "066A87AB": "ORCH's third build; matches neither shipping corpus",
}

# Decoy name -> the narrowest pattern that should reach it. Each pair
# straddles a boundary, so the table shows where reach actually ends.
DECOY_PLAN = [
    ("strehl.exe", "strehl.exe", "reached by every pattern"),
    ("strehl-pinned-decoy.exe", "strehl*.exe", "THE v1 MISS: renamed build"),
    ("strehl2.exe", "strehl*.exe", "digit suffix"),
    ("zz-renamed-build.exe", "*.exe", "renamed off the strehl prefix"),
    ("renamed-build-no-ext", None, "no .exe extension: reached by nothing"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def scan(root, pattern):
    """Hash every file under root whose NAME matches pattern.

    Returns (digest -> [paths], files_seen, bytes_hashed). files_seen counts
    every file walked, matching or not, so reach can be quoted as a fraction
    of the population rather than as a bare count of hits.
    """
    builds, seen, nbytes = collections.defaultdict(list), 0, 0
    for dp, _, fns in os.walk(root):
        for fn in fns:
            seen += 1
            if not fnmatch.fnmatch(fn.lower(), pattern.lower()):
                continue
            p = os.path.join(dp, fn)
            try:
                nbytes += os.path.getsize(p)
                builds[sha(p)].append(p)
            except OSError:
                pass
    return builds, seen, nbytes


def plant():
    """Write decoys with unique content so a hit is attributable to the decoy.

    A byte-copy of a real build would hash to that build, and 'found it' would
    be indistinguishable from 'found the original'. Each decoy therefore gets
    a unique trailing marker and so a unique digest.
    """
    src = None
    for c in (os.path.join(OUTS, "V-NEVERWORSE", "bin", "strehl.exe"),
              os.path.join(OUTS, "PIN-V3", "strehl.exe")):
        if os.path.exists(c):
            src = c
            break
    if src is None:
        raise SystemExit("FATAL: no binary to build decoys from")
    os.makedirs(DECOYS, exist_ok=True)
    out = {}
    for i, (name, _, _) in enumerate(DECOY_PLAN):
        p = os.path.join(DECOYS, name)
        shutil.copyfile(src, p)
        with open(p, "ab") as f:
            f.write(b"\n#VN-DECOY-%02d-DO-NOT-EXECUTE\n" % i)
        out[name] = sha(p)
    if len(set(out.values())) != len(out):
        raise SystemExit("FATAL: decoys collided; a miss would be invisible")
    return out


def reach(root):
    """Commissioning: which pattern reaches which decoy? Must match the plan."""
    planted = plant()
    pats = ["strehl.exe", "strehl*.exe", "*.exe"]
    found = {}
    for pat in pats:
        b, _, _ = scan(DECOYS, pat)
        found[pat] = set(d[:8] for d in b)

    print("REACH COMMISSIONING -- decoys planted in %s\n" % DECOYS)
    print("%-26s %-11s %-11s %-11s  %s"
          % ("decoy", "strehl.exe", "strehl*.exe", "*.exe", "note"))
    bad = []
    for name, need, note in DECOY_PLAN:
        cells = []
        for pat in pats:
            hit = planted[name][:8] in found[pat]
            # expected: reachable iff this pattern is at least as wide as need
            want = need is not None and fnmatch.fnmatch(name.lower(),
                                                        pat.lower())
            cells.append(("FOUND" if hit else "miss")
                         + ("" if hit == want else " !!"))
            if hit != want:
                bad.append((name, pat, hit, want))
        print("%-26s %-11s %-11s %-11s  %s"
              % (name, cells[0], cells[1], cells[2], note))
    shutil.rmtree(DECOYS, ignore_errors=True)

    narrow = sum(1 for n, _, _ in DECOY_PLAN
                 if planted[n][:8] not in found["strehl.exe"])
    print("\nv1's pattern `strehl.exe` missed %d of the %d planted builds."
          % (narrow, len(DECOY_PLAN)))
    print("`*.exe` reaches %d of %d; the last is unreachable BY DESIGN and is "
          "the\nmeasured residual blind spot -- a build renamed without an .exe"
          " extension." % (len(DECOY_PLAN) - 1, len(DECOY_PLAN)))
    if bad:
        for name, pat, hit, want in bad:
            print("  REACH DEFECT: %s under %s: found=%s expected=%s"
                  % (name, pat, hit, want))
        raise SystemExit("FATAL: reach does not match the plan; "
                         "no absence claim may be made")
    print("reach matches the plan on all %d decoys x %d patterns.\n"
          % (len(DECOY_PLAN), len(pats)))
    return True


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--pattern", default="strehl*.exe")
    ap.add_argument("--wide", action="store_true",
                    help="scan every *.exe: the reach needed for an absence")
    ap.add_argument("--reach-only", action="store_true")
    ap.add_argument("--skip-reach", action="store_true",
                    help="census only; forbids any absence claim")
    a = ap.parse_args(argv)
    if a.wide:
        a.pattern = "*.exe"

    commissioned = False
    if not a.skip_reach:
        commissioned = reach(a.root)
    if a.reach_only:
        return 0

    builds, seen, nbytes = scan(a.root, a.pattern)
    ncopies = sum(len(v) for v in builds.values())
    print("CENSUS  pattern %-12s root %s" % (a.pattern, a.root))
    print("  walked %d files; %d matched; %.1f GB hashed; %d distinct builds"
          % (seen, ncopies, nbytes / 2**30, len(builds)))
    by8 = {k[:8]: v for k, v in builds.items()}

    print("\nbuilds of interest:")
    for tag, what in sorted(KNOWN.items()):
        paths = by8.get(tag, [])
        print("  %-9s %-52s %s" % (tag, what,
                                   "%d cop%s" % (len(paths),
                                                 "y" if len(paths) == 1
                                                 else "ies")
                                   if paths else "ABSENT under this reach"))
        for p in sorted(paths)[:4]:
            print("      %s" % p)

    seals = collections.defaultdict(list)
    for dp, _, fns in os.walk(OUTS):
        for fn in fns:
            if fn.endswith(".tiff.ok"):
                with open(os.path.join(dp, fn)) as f:
                    seals[dp].append(f.read().strip().upper())

    print("\n%-56s %5s  %s" % ("corpus", "seals", "build(s)"))
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
                note += "  <- no binary within reach"
                incidents.append((d, "seal %s: no binary within reach" % s))
        print("%-56s %5d  %s%s%s"
              % (d.replace(OUTS, "..."), len(seals[d]), " + ".join(u),
                 "  [fixture]" if fixture else "", note))

    print("\nexpected seals:")
    for d, want in EXPECT.items():
        got = sorted(set(s[:8] for s in seals.get(d, [])))
        ok = got == [want] and len(seals.get(d, [])) == 26
        print("  %-46s %s  %d seals %s"
              % (d.replace(OUTS, "..."), "OK " if ok else "FAIL",
                 len(seals.get(d, [])), " + ".join(got) or "none"))
        if not ok:
            incidents.append((d, "expected 26x %s, got %s" % (want, got)))

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
    if not commissioned:
        print("\nREACH NOT COMMISSIONED -- census only. No absence claim may "
              "be drawn from this run.")
    return 1 if incidents else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
