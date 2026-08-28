"""Render the hull ladder: InputRange (shipping default) / PerLevel / Unclamped.

Every arm comes from ONE pinned copy of `blend-render`, hashed before and after
the whole run, because `crates/` is shared and the build lane can land at any
moment. Two pins built hours apart have already been mistaken for an A/B in
this project twice.

Why `blend-render` and not `strehl stack`: the hull modes are only reachable
from this example. Its two declared gaps -- no photometric normalisation and no
clip handling -- cancel exactly in a WITHIN-blend-render difference, because
both arms are missing the same two stages. That cancellation is the only reason
this instrument is admissible, and it is void the moment a number from here is
put beside a `strehl stack` number. Nothing in this lane does that.

`--camera-linear` is the output space: camera-native primaries, linear, no
matrix and no transfer curve. A tone curve fitted per image would put two arms
on two different nonlinear curves, which is the defect that invalidated every
master/source ratio this project published before it was caught.
"""
import hashlib, json, os, subprocess, sys, time

PIN = r"C:\dev\strehl-out\V-GATHER\hull\bin\blend-render-pin.exe"
OUT = r"C:\dev\strehl-out\V-GATHER\hull"
SRC = r"D:\personal\macro"

# arm name -> extra flags. "inputrange" is the shipping default: no flag.
ARMS = {
    "inputrange": [],
    "perlevel":   ["--per-level"],
    "unclamped":  ["--unclamped"],
}

# (subject, prior ceiling excess from the exponent ladder, is_negative_control)
SUBJECTS = [
    ("112MSDCF",               +0.170, False),
    ("coffee-bubbles",         -0.016, True),
    ("119MSDCF",               -0.013, True),
    ("109MSDCF",               -0.055, True),
    ("foam",                   +0.232, False),
    ("wrapped-text-1",         +0.283, False),
    ("flower-inner-edge-cpl",  +0.694, False),
    ("pencil-steep-angle-cpl", +0.964, False),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def render(subject, arm, flags):
    dst = os.path.join(OUT, "%s-%s.tiff" % (subject, arm))
    if os.path.exists(dst):
        print("      %-11s exists, skipping" % arm, flush=True)
        return dst, None
    cmd = [PIN, os.path.join(SRC, subject), dst, "--camera-linear"] + flags
    t0 = time.time()
    pr = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    log = (pr.stdout or "") + (pr.stderr or "")
    # Capture the tool's OWN report of what the clamp did. This is independent
    # provenance that the arm actually differed, separate from my gauge.
    clamp = [l.strip() for l in log.splitlines() if l.startswith("hull clamp")]
    if pr.returncode != 0 or not os.path.exists(dst):
        named = [l for l in log.splitlines()
                 if any(k in l.lower() for k in ("error", "panic", "fail", "unknown", "usage"))]
        raise SystemExit("RENDER FAILED %s/%s rc=%d\n%s"
                         % (subject, arm, pr.returncode, "\n".join(named[-12:]) or log[-800:]))
    with open(os.path.join(OUT, "%s-%s.log" % (subject, arm)), "w", encoding="utf-8") as fh:
        fh.write(log)
    print("      %-11s %6.1f s   %s" % (arm, time.time() - t0, clamp[0] if clamp else "no clamp line"),
          flush=True)
    return dst, (clamp[0] if clamp else None)


def main():
    if not os.path.exists(PIN):
        raise SystemExit("pin missing: %s" % PIN)
    pin0 = sha(PIN)
    print("pin SHA256 %s" % pin0, flush=True)

    only = sys.argv[1:] or None
    meta = {}
    for subject, prior, ctrl in SUBJECTS:
        if only and subject not in only:
            continue
        if not os.path.isdir(os.path.join(SRC, subject)):
            print("== %-24s MISSING, skipped" % subject, flush=True)
            continue
        print("== %-24s prior excess %+.1f%%%s"
              % (subject, 100 * prior, "   [negative control]" if ctrl else ""), flush=True)
        meta[subject] = {"prior_excess": prior, "control": ctrl, "clamp": {}}
        for arm, flags in ARMS.items():
            _, clamp = render(subject, arm, flags)
            if clamp:
                meta[subject]["clamp"][arm] = clamp

    pin1 = sha(PIN)
    if pin0 != pin1:
        raise SystemExit("PIN CHANGED MID-RUN %s -> %s: the A/B is void" % (pin0, pin1))
    print("pin unchanged after run: %s" % pin1, flush=True)

    dst = os.path.join("experiments", "V-GATHER", "hull-render.json")
    prev = {}
    if os.path.exists(dst):
        prev = json.load(open(dst))
    prev.update(meta)
    prev["_pin"] = pin1
    json.dump(prev, open(dst, "w"), indent=1)
    print("wrote %s" % dst)


if __name__ == "__main__":
    main()
