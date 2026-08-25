"""M113-spectral S1: render binned linear OFF/ON arms for the stack panel.

BINNED ONLY. M113-ca established that --srgb carries a non-diagonal colour matrix
and --demosaic carries a guided demosaic, and that both corrupt an inter-channel
geometry measurement in opposite directions (chain transfer 1.3073 and 0.6963
against 0.9399/0.9813 binned). Only the byte-frozen binned render is measured.

PRIVATE CACHE PER ARM. Corpus fact 1561: the warp cache was keyed on the capture
path alone and served differently-configured solves silently. Every arm here gets
its own STREHL_CACHE_DIR so no two arms can share a cache entry even in
principle.

S5, THE ALIGNMENT TEST. The reference frame of each stack is COPIED to a scratch
directory on C: and rendered alone with STREHL_ALIGN=0, so that arm has no align
and no merge in it at all. D:\ is never written to.

Exit codes come from subprocess.run().returncode.
"""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
ROOT = Path(r"C:\dev\strehl-out\M113-spectral")
MACRO = Path(r"D:\personal\macro")
KEY = "a7c2-fe100gm-2xtc-x4cpl"

PANEL = ["bee-1-cpl", "bee-2-cpl", "lavendar-cpl", "dry-erase-marker-head-cpl",
         "leaf-2-cpl", "tweezers-cpl"]
ONEFRAME = ["bee-3-cpl", "couch-fibers-cpl", "bee-1-cpl"]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def run(args, extra, tag):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    cache = ROOT / "cache" / tag
    cache.mkdir(parents=True, exist_ok=True)
    env["STREHL_CACHE_DIR"] = str(cache)
    env.update(extra)
    t = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t, (p.stdout or "") + (p.stderr or "")

def main():
    (ROOT / "arms").mkdir(parents=True, exist_ok=True)
    out = {}
    for name in PANEL:
        d = MACRO / name
        frames = sorted(d.glob("*.ARW"))
        ref = len(frames) // 2
        side = ROOT / ("%s-warpmap.txt" % name)
        print("\n%s  n=%d ref=%d" % (name, len(frames), ref), flush=True)
        if not side.exists():
            code, sec, msg = run([str(EXE), "align", str(d), "--out", str(side),
                                  "--reference", str(ref)], {}, name + "-align")
            if code != 0:
                print("  ALIGN REFUSED/FAILED exit=%d: %s"
                      % (code, (msg.strip().splitlines() or ["?"])[-1]), flush=True)
                side.unlink(missing_ok=True)
                continue
            print("  align %.1fs" % sec, flush=True)
        for arm, val in (("off", None), ("on", KEY)):
            tif = ROOT / "arms" / ("%s-binned-%s.tif" % (name, arm))
            if tif.exists():
                print("  %-3s exists %s" % (arm, sha(tif)[:16]), flush=True)
                out["%s|%s" % (name, arm)] = sha(tif); continue
            extra = {"STREHL_WARPMAP": str(side)}
            if val:
                extra["STREHL_FIX_CA"] = val
            code, sec, msg = run([str(EXE), "stack", str(d), "-o", str(tif)],
                                 extra, "%s-%s" % (name, arm))
            if code != 0:
                print(msg[-1500:]); sys.exit("STACK FAILED %s %s" % (name, arm))
            out["%s|%s" % (name, arm)] = sha(tif)
            print("  %-3s %.1fs %s" % (arm, sec, sha(tif)[:16]), flush=True)

    # ---------------- S5: single reference frame, no align, no merge -------------
    print("\n" + "=" * 70)
    print("S5 single-frame arms (STREHL_ALIGN=0, one frame, no merge)")
    print("=" * 70, flush=True)
    for name in ONEFRAME:
        frames = sorted((MACRO / name).glob("*.ARW"))
        ref = len(frames) // 2
        scratch = ROOT / "oneframe" / name
        scratch.mkdir(parents=True, exist_ok=True)
        dst = scratch / frames[ref].name
        if not dst.exists():
            shutil.copy2(frames[ref], dst)        # reads D:, writes C:
        for arm, val in (("off", None), ("on", KEY)):
            tif = ROOT / "arms" / ("%s-1frame-%s.tif" % (name, arm))
            if tif.exists():
                out["%s-1frame|%s" % (name, arm)] = sha(tif); continue
            extra = {"STREHL_ALIGN": "0"}
            if val:
                extra["STREHL_FIX_CA"] = val
            code, sec, msg = run([str(EXE), "stack", str(scratch), "-o", str(tif)],
                                 extra, "%s-1f-%s" % (name, arm))
            if code != 0:
                print(msg[-1500:]); sys.exit("1FRAME FAILED %s %s" % (name, arm))
            out["%s-1frame|%s" % (name, arm)] = sha(tif)
            print("  %-18s %-3s %.1fs %s" % (name, arm, sec, sha(tif)[:16]), flush=True)

    dup = {}
    for k, v in out.items():
        dup.setdefault(v, []).append(k)
    coll = {v: ks for v, ks in dup.items() if len(ks) > 1}
    print("\nidentical-output collisions (must be none): %s" % (coll if coll else "NONE"))
    with open(ROOT / "render.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote render.json  (%d arms)" % len(out))

if __name__ == "__main__":
    main()