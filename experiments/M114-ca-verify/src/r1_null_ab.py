"""M114 R1 -- independent re-run of M107's CA null and A/B, with my own binary.

BARS, REGISTERED BEFORE THE RUN (falsifiable, and each can go red):

  M1  My binary, CA UNSET, must reproduce the ORCH-kernel pre-wiring render
      byte for byte:  E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
      RED IF: any byte differs.  This is the cross-binary null, re-derived.
  M2  My own solved sidecar must have identical PLACEMENT RECORDS to the
      ORCH-kernel sidecar.  RED IF: any hex field differs.
  M3  CA=0, CA=off, CA=OFF, CA=false, CA=<empty>, CA=<spaces> all == M1 hash.
      RED IF: any differs.
  M4  CA=a7c2-fe100gm-2xtc-x4cpl must DIFFER from M1, and must equal M107's
      claimed E9580E8A2A85009494B2FE5A35441EBE5D5F9F7E6B80ADBD079B40130B7742E9
      RED IF: equal to off (silent no-op) or different from M107's hash.
  M5  A typo'd key must exit EXACTLY 1.  CA=1 / true / on must exit EXACTLY 1.
      RED IF: exit 0 (silently off) or any other code.

Exit codes are read from subprocess.run().returncode, never $LASTEXITCODE.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
DIR = Path(r"D:\personal\macro\bee-3-cpl")
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r1")
ORCH = Path(r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom.tif")
ORCH_SIDE = Path(r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom-warpmap.txt")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
OFF_HASH = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"
ON_HASH = "E9580E8A2A85009494B2FE5A35441EBE5D5F9F7E6B80ADBD079B40130B7742E9"

OUT.mkdir(parents=True, exist_ok=True)
SIDE = OUT / "m114-warpmap.txt"
LOG = OUT / "r1.log"


def log(msg):
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run(args, env_extra):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env.update({k: v for k, v in env_extra.items() if v is not None})
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t0, p.stdout + p.stderr


def main():
    log("=" * 78)
    log("M114 R1  binary=%s" % EXE)
    log("binary sha256 = %s" % sha(EXE))
    n = len(list(DIR.glob("*.ARW")))
    ref = n // 2
    log("frames=%d reference=%d" % (n, ref))

    if not SIDE.exists():
        code, sec, out = run([str(EXE), "align", str(DIR), "--out", str(SIDE),
                              "--reference", str(ref)], {})
        log("align EXIT=%d  %.1fs" % (code, sec))
        if code != 0:
            log(out[-3000:])
            sys.exit("ALIGN FAILED")

    mine = [l for l in SIDE.read_text().splitlines() if l and not l.startswith("#")]
    theirs = [l for l in ORCH_SIDE.read_text().splitlines() if l and not l.startswith("#")]
    m2 = mine == theirs
    log("M2 sidecar placements identical to ORCH-kernel : %s (%d vs %d records)"
        % ("PASS" if m2 else "FAIL", len(mine), len(theirs)))
    if not m2:
        for a, b in zip(mine, theirs):
            if a != b:
                log("   first diff:\n     mine   %s\n     theirs %s" % (a[:140], b[:140]))
                break

    os.environ["STREHL_WARPMAP"] = str(SIDE)

    arms = [
        ("unset", None),
        ("on", KEY),
        ("unset2", None),
        ("zero", "0"),
        ("off", "off"),
        ("OFF_UPPER", "OFF"),
        ("false", "false"),
        ("empty", ""),
        ("spaces", "   "),
    ]
    results = {}
    for label, val in arms:
        tif = OUT / ("%s.tif" % label)
        code, sec, out = run([str(EXE), "stack", str(DIR), "--srgb",
                              "--auto-exposure", "-o", str(tif)],
                             {"STREHL_WARPMAP": str(SIDE), "STREHL_FIX_CA": val})
        h = sha(tif) if tif.exists() else "NO-FILE"
        results[label] = {"exit": code, "sha": h, "sec": round(sec, 1)}
        log("  arm %-10s CA=%-26r EXIT=%d %6.1fs  %s"
            % (label, val, code, sec, h))
        if code != 0:
            log("     " + out.strip().splitlines()[-1] if out.strip() else "")

    log("")
    for label, val in [("typo", KEY + "-TYPO"), ("truthy1", "1"),
                       ("truthytrue", "true"), ("truthyon", "on")]:
        tif = OUT / ("bad_%s.tif" % label)
        code, sec, out = run([str(EXE), "stack", str(DIR), "--srgb",
                              "--auto-exposure", "-o", str(tif)],
                             {"STREHL_WARPMAP": str(SIDE), "STREHL_FIX_CA": val})
        tail = [l for l in out.splitlines() if "profile" in l.lower()]
        results["bad_" + label] = {"exit": code, "msg": tail[-1] if tail else ""}
        log("  refuse arm %-11s CA=%-30r EXIT=%d  %s"
            % (label, val, code, tail[-1].strip() if tail else "(no message)"))

    log("")
    log("=" * 78)
    orch = sha(ORCH)
    log("ORCH-kernel pre-wiring render sha256 = %s" % orch)
    m1 = results["unset"]["sha"] == orch == OFF_HASH
    log("M1 cross-binary null (mine==ORCH==claim) : %s" % ("PASS" if m1 else "FAIL"))
    offs = ["unset", "unset2", "zero", "off", "OFF_UPPER", "false", "empty", "spaces"]
    m3 = len({results[a]["sha"] for a in offs}) == 1 and results["unset"]["sha"] == OFF_HASH
    log("M3 every off-form byte-identical          : %s" % ("PASS" if m3 else "FAIL"))
    m4 = (results["on"]["sha"] != results["unset"]["sha"]
          and results["on"]["sha"] == ON_HASH)
    log("M4 on differs and matches M107's hash     : %s  (mine=%s)"
        % ("PASS" if m4 else "FAIL", results["on"]["sha"]))
    m5 = all(results["bad_" + k]["exit"] == 1
             for k in ["typo", "truthy1", "truthytrue", "truthyon"])
    log("M5 typo/truthy arms exit EXACTLY 1        : %s" % ("PASS" if m5 else "FAIL"))
    log("=" * 78)
    (OUT / "r1.json").write_text(json.dumps(
        {"results": results, "orch": orch, "M1": m1, "M2": m2, "M3": m3,
         "M4": m4, "M5": m5}, indent=2))
    log("VERDICT: %s" % ("ALL BARS PASS" if all([m1, m2, m3, m4, m5]) else "BARS FAILED"))


if __name__ == "__main__":
    main()
