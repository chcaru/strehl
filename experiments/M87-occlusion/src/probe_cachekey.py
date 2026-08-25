"""M87 -- record the evidence behind P144 as data, so the report is re-derivable.

Answers ORCH's fact 1446 warning with the four things that actually decide it:

  A. do any M87 measurement scripts invoke the strehl binary?
  B. do the four pinned gate TIFFs still hash to what was recorded?
  C. does the HEAD source key `reference` and `resampler` into the solve?
  D. does `STREHL_WARPMAP` bypass the discover-or-solve path the defect lives in?

Nothing here transcribes a number into prose by hand; `verify_s34` re-reads this
JSON.  Read-only: it hashes files and greps source, and writes one JSON under
`data/`.
"""
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
DATA = HERE / "data"
PINS = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
GATES = ["4.00", "2.00", "0.7078", "0.00"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    out = {}

    # A -- binary invocations across the measurement scripts.
    # The harness/measurement split has ONE owner; a private copy here is how
    # three instruments silently drifted apart (P145).
    import sys
    sys.path.insert(0, str(HERE / "src"))
    import fix_audit
    HARNESS = fix_audit.HARNESS
    scripts = sorted(p for p in (HERE / "src").glob("*.py"))
    meas = [p for p in scripts if not p.name.startswith(HARNESS)]
    invoke = [
        p.name
        for p in meas
        if "subprocess" in p.read_text(encoding="utf-8", errors="replace")
        and re.search(r"strehl[-\w]*\.exe", p.read_text(encoding="utf-8", errors="replace"))
    ]
    out["measurement_scripts"] = len(meas)
    out["scripts_invoking_binary"] = len(invoke)
    out["rawpy_decode_sites"] = len(
        re.findall(r"rawpy\.imread", (HERE / "src" / "m87lib.py").read_text(encoding="utf-8"))
    )

    # B -- the pinned TIFFs as they sit now, against what was recorded
    pins = {}
    for g in GATES:
        p = PINS / ("pin-bee-3-cpl-gate-%s.tif" % g)
        pins[g] = {"sha256": sha256(p), "bytes": p.stat().st_size} if p.exists() else None
    out["pins"] = pins
    live = [v["sha256"] for v in pins.values() if v]
    out["pins_distinct"] = len(set(live))
    out["pins_one_byte_length"] = len({v["bytes"] for v in pins.values() if v}) == 1

    ladder = json.loads((DATA / "100-gate-veildepth.json").read_text(encoding="utf-8"))
    recorded = ladder["provenance"]["gate_4_sha256"].upper()
    out["gate4_recorded_at_measurement_time"] = recorded
    out["gate4_on_disk_now"] = pins["4.00"]["sha256"] if pins["4.00"] else None
    out["gate4_matches"] = out["gate4_on_disk_now"] == recorded

    # C -- is the cache-key fix in HEAD, and what does it hash?
    rc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "69f7b4c", "HEAD"],
        cwd=ROOT, capture_output=True,
    ).returncode
    out["cachekey_fix_is_ancestor_of_head"] = rc == 0
    align = (ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    sig = re.search(r"fn solve_config_key\(([^)]*)\)", align)
    out["solve_config_key_signature"] = sig.group(1).strip() if sig else None
    body = align[align.index("fn solve_config_key") :][:700]
    out["solve_config_key_hashes"] = {
        "reference": "reference.hash(" in body,
        "spans": "spans.hash(" in body,
        "resampler": "resampler:?" in body,
        "solve_env": "SOLVE_ENV" in body,
    }

    # D -- does STREHL_WARPMAP bypass discover-or-solve?
    merge = (ROOT / "crates" / "strehl-cli" / "src" / "merge_cmd.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    out["warpmap_env_const"] = 'WARPMAP_ENV: &str = "STREHL_WARPMAP"' in merge
    out["warpmap_bypasses_solve"] = (
        "explicitly named sidecar" in merge and "otherwise the normal discover-or-solve" in merge
    )

    DATA.mkdir(exist_ok=True)
    (DATA / "cachekey-probe.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8"
    )

    print("A  measurement scripts %d, invoking the binary %d, rawpy decode sites %d"
          % (out["measurement_scripts"], out["scripts_invoking_binary"], out["rawpy_decode_sites"]))
    print("B  gate-4 recorded %s" % recorded)
    print("   gate-4 on disk  %s   match=%s" % (out["gate4_on_disk_now"], out["gate4_matches"]))
    print("   %d distinct hashes over %d arms, one byte length=%s"
          % (out["pins_distinct"], len(live), out["pins_one_byte_length"]))
    print("C  69f7b4c ancestor of HEAD=%s; solve_config_key hashes %s"
          % (out["cachekey_fix_is_ancestor_of_head"], out["solve_config_key_hashes"]))
    print("D  warpmap bypasses discover-or-solve=%s" % out["warpmap_bypasses_solve"])


if __name__ == "__main__":
    main()
