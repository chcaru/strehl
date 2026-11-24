"""Plan S4 engine gate: compare the base and new engines' outputs.

Usage: python -I s4-gate.py <out-root>

<out-root> holds base/ (engine at 7b786abae), new/ (this branch, no
subject) and subj/ (this branch, with outlines from `strehl subject`), as
written by run-base.ps1 and run-new.ps1. Prints text only.
"""
import glob
import hashlib
import json
import os
import sys

root = sys.argv[1]
base, new, subj = (os.path.join(root, d) for d in ("base", "new", "subj"))


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


print("== Without a subject: base against new ==")
for name in sorted(os.listdir(base)):
    if not name.endswith(".json"):
        continue
    a, b = os.path.join(base, name), os.path.join(new, name)
    same = sha(a) == sha(b)
    note = ""
    if not same and name.startswith("subject-"):
        x, y = load(a), load(b)
        extra = sorted(set(y) - set(x))
        y = {k: v for k, v in y.items() if k != "bounds"}
        note = f"; equal without `bounds`: {x == y}; keys added: {extra}"
    print(f"{name:32s} bytes identical: {same}{note}")


def follow_lines(cache):
    out = {}
    for p in glob.glob(os.path.join(cache, "follow", "*.jsonl")):
        with open(p, encoding="utf-8") as f:
            for line in f:
                v = json.loads(line)
                for k in ("seconds", "align_seconds"):
                    v.pop(k, None)
                out[v["group_id"]] = v
    return out


fa, fb = follow_lines(os.path.join(root, "cache-base")), follow_lines(os.path.join(root, "cache-new"))
print(f"follow journal (seconds removed): {len(fa)} groups base, {len(fb)} new, equal: {fa == fb}")


def group_journal(cache):
    rows = []
    for p in glob.glob(os.path.join(cache, "groups", "*.jsonl")):
        with open(p, encoding="utf-8") as f:
            rows += sorted(f.read().splitlines())
    return rows


ga, gb = group_journal(os.path.join(root, "cache-base")), group_journal(os.path.join(root, "cache-new"))
print(f"group journal (render's measurements): {len(ga)} records base, {len(gb)} new, equal as sets: {sorted(ga) == sorted(gb)}")

print("\n== Focus step: whole frame against the subject ==")
for k in ("weevil", "scarab", "tile4", "tile1"):
    p = os.path.join(subj, f"focus-step-{k}.json")
    if not os.path.exists(p):
        print(k, "missing")
        continue
    v = load(p)
    w = v.get("whole_frame") or {}
    b = load(os.path.join(base, f"focus-step-{k}.json"))
    fmt = lambda x: "-" if x is None else f"{x:.1f}"
    print(
        f"{k:7s} subject={v.get('subject')} tiles touching {v.get('subject_tiles')} of {v['tiles']}; "
        f"whole frame: {w.get('tiles_measured')} measured, width {fmt(w.get('width'))} (p10 {fmt(w.get('width_p10'))}), step {w.get('suggested_step')}; "
        f"subject: {v['tiles_measured']} measured, width {fmt(v['width'])} (p10 {fmt(v['width_p10'])}, p90 {fmt(v['width_p90'])}), step {v['suggested_step']}; "
        f"base whole-frame width {fmt(b['width'])} step {b['suggested_step']} (same as new whole frame: {b['width'] == w.get('width') and b['suggested_step'] == w.get('suggested_step')})"
    )

print("\n== Plane checker: retake with and without the subject ==")
for k in ("tile1", "tile4"):
    p = os.path.join(subj, f"pixel-shift-{k}.json")
    if not os.path.exists(p):
        print(k, "missing")
        continue
    groups = load(p)["groups"]
    nb = {(g["plane"], g["group_id"]): g for g in load(os.path.join(base, f"pixel-shift-{k}.json"))["groups"]}
    demoted = [g for g in groups if g.get("gate", {}).get("reason")]
    changes, backdrop, kinds = [], [], {}
    same_gate = all(
        nb[(g["plane"], g["group_id"])].get("gate", {}).get("reason") == g.get("gate", {}).get("reason")
        and nb[(g["plane"], g["group_id"])].get("verdict") == g.get("verdict")
        for g in groups
    )
    for g in demoted:
        gate = g["gate"]
        before, after = gate.get("retake_without_subject"), gate.get("retake")
        kind = gate["reason"].split(" by ")[0].split(" [")[0][:40]
        kinds.setdefault(kind, [0, 0, 0])
        kinds[kind][0] += 1
        kinds[kind][1] += bool(before)
        kinds[kind][2] += bool(after)
        if gate.get("backdrop_only"):
            backdrop.append(g["plane"])
        if before != after:
            s = gate["subject"]
            changes.append(
                f"  plane {g['plane']:>3} {g['group_id'][-8:]}: retake {before} -> {after}"
                f"{' (backdrop only)' if gate.get('backdrop_only') else ''}; frame: {gate['reason'][:70]}"
                f" | subject: local {s['local_px']}, backdrop {s['backdrop_local_px']}, {s['tiles_measured']}/{s['tiles']} tiles,"
                f" reason {s['reason']}"
            )
    disagree = [
        (g["plane"], g["offsets"][1:], g["gate"]["subject"]["registration"]["offsets"][1:],
         g["gate"]["subject"]["registration"]["parities"])
        for g in groups
        if g.get("gate", {}).get("subject") and not g["gate"]["subject"]["registration"]["agrees"]
    ]
    print(
        f"{k}: {len(groups)} groups, stack verdicts and reasons unchanged from base: {same_gate}; demoted {len(demoted)}; "
        f"retakes without subject {sum(bool(g['gate'].get('retake_without_subject')) for g in demoted)}, "
        f"with subject {sum(bool(g['gate'].get('retake')) for g in demoted)}; backdrop only {len(backdrop)}"
    )
    for kind, (n, b0, b1) in sorted(kinds.items()):
        print(f"  {kind:40s} {n:3d} demoted, retake {b0} -> {b1}")
    print("\n".join(changes) if changes else "  no retake changed")
    passing = [g for g in groups if not g.get("gate", {}).get("reason") and g.get("gate", {}).get("subject")]
    over = [g["plane"] for g in passing if (g["gate"]["subject"].get("local_px") or 0) >= g["gate"]["local_tolerance_px"]]
    print(f"  passing groups whose subject tiles alone exceed the limit (reported, no retake): {over}")
    for g in demoted:
        if g["gate"]["reason"].startswith("witness tiles disagree locally"):
            s = g["gate"]["subject"]
            print(
                f"  local fault, plane {g['plane']:>3}: frame {g['gate']['local_px']:.3f} px, subject {s['local_px']:.3f} px"
                f" over {s['tiles_measured']}/{s['tiles']} tiles, backdrop {s['backdrop_local_px']:.3f} px; retake {g['gate']['retake']}"
            )
    print(f"  registration on the subject's box (reported, no vote): offsets differ from the stack's in {len(disagree)} groups")
    for plane, a, b, par in disagree:
        print(f"    plane {plane:>3}: stack {a}, subject box {b} (covers parities: {par})")

print("\n== follow with a subject (tile1) ==")
fs = follow_lines(os.path.join(root, "cache-subj"))
diff = []
for key, v in sorted(fs.items(), key=lambda kv: (kv[1]["plane"], kv[0])):
    b = fa.get(key)
    if b is None:
        continue
    if b.get("retake") != v.get("retake") or b.get("verdict") != v.get("verdict"):
        diff.append(f"  plane {v['plane']:>3}: verdict {b.get('verdict')} -> {v.get('verdict')}, retake {b.get('retake')} -> {v.get('retake')}, backdrop_only {v.get('backdrop_only')}")
checked = sum(1 for v in fs.values() if "subject_check" in v)
print(f"{len(fs)} groups, subject arm run on {checked} demoted groups; changes against base:")
print("\n".join(diff) if diff else "  none")

print("\n== Bounds ==")
for k in ("weevil", "scarab"):
    for tag in ("bounds13", "boundsall"):
        p = os.path.join(subj, f"{tag}-{k}.json")
        if not os.path.exists(p):
            continue
        v = load(p)
        d, b = v["depth"], v["bounds"]
        c = b.get("core") or {}
        print(
            f"{k} {tag}: planes used {len(v['provenance']['planes'])}; depth planes {d['first_plane']}-{d['last_plane']} (core {d['core_first_plane']}-{d['core_last_plane']}) of {b['run_planes']}; "
            f"width {b['sharp_width']:.1f} ({b['width_from']}); start {b['start']:.0f} end {b['end']:.0f} (run {b['run_start']:.0f}-{b['run_end']:.0f}); "
            f"{b['planes']} planes, {b['planes_saved']} saved, {100 * b['fraction']:.0f} % of the range; "
            f"core: {c.get('planes')} planes, {c.get('planes_saved')} saved, {100 * c.get('fraction', 0):.0f} %; "
            f"reaches start/end {b['reaches_run_start']}/{b['reaches_run_end']}"
        )
for k in ("tile1", "tile4"):
    v = load(os.path.join(subj, f"subject-{k}.json"))
    b = v.get("bounds") or {}
    print(f"{k}: depth {v['depth']['first_plane']}-{v['depth']['last_plane']}; reaches start/end {b.get('reaches_run_start')}/{b.get('reaches_run_end')}; {b.get('planes_saved')} saved")
