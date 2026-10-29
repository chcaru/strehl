#!/usr/bin/env python3
"""Root-scheduled UI completion controls. No RAW/render work without --permit-render.
Uses only scripts/strehl-control.py; screenshots are the actual offscreen GPU UI.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
HELPER = ROOT / "scripts/strehl-control.py"

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

class Control:
    def __init__(self, args):
        self.args = args
        self.count = 0
        self.records = []
        args.evidence.mkdir(parents=True, exist_ok=True)
    def run(self, tail, expected=0):
        self.count += 1
        command = [sys.executable, "-X", "utf8", str(HELPER), "--exe", str(self.args.exe)]
        if self.args.session_file:
            command += ["--session-file", str(self.args.session_file)]
        command += tail
        started = time.time()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        record = {"command": command, "started_unix": started, "exit_code": result.returncode,
                  "stdout": result.stdout, "stderr": result.stderr}
        write(self.args.evidence / f"{self.count:03}-command.json", record)
        self.records.append(record)
        if result.returncode != expected:
            raise RuntimeError(f"Expected exit {expected}, got {result.returncode}: {result.stdout} {result.stderr}")
        return json.loads(result.stdout)
    def snapshot(self):
        reply = self.run(["snapshot"])
        return reply["data"]["revision"], reply["data"]["result"]
    def mutate(self, command, expected=0):
        revision, _ = self.snapshot()
        request = self.args.evidence / f"{self.count+1:03}-request.json"
        write(request, {"expected_revision": revision, "command": command})
        # Never retry a mutation or fill a changed revision after failure.
        return self.run(["call", "--request", str(request)], expected)
    def wait(self, predicate, seconds=180):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            _, state = self.snapshot()
            if predicate(state):
                return state
            time.sleep(0.25)
        raise RuntimeError("State did not reach the requested boundary; no mutation was retried")
    def idle(self):
        return self.wait(lambda s: not any(s["busy"].values()))
    def finish(self, result):
        write(self.args.evidence / "result.json", {"result": result, "command_count": self.count,
              "scope": "Application controls and separately requested actual GPU screenshots; no photographic quality conclusion."})

def options(ctl, args):
    _, initial = ctl.snapshot()
    ids = args.stack_id
    if len(ids) < 2:
        raise ValueError("Options phase requires two explicitly selected imported source stack IDs")
    nodes = {n["id"]: n for n in initial["projects"]}
    assert all(i in nodes and nodes[i]["kind"] == "Stack" for i in ids)
    passes = [{"name": nodes[i]["name"], "stack_ids": [i]} for i in ids]
    base = {"operation": "create_session", "name": "Completion controls · repeat",
            "passes": passes, "mode": "repeat", "primary_pass": None,
            "memory_limit_gib": 2.0, "precision_weights": True,
            "contribution_maps": True, "focus_evidence": True, "reproducibility": True,
            "original_cfa_reconstruction": True}
    ctl.mutate(base)
    repeat = ctl.idle()
    assert repeat["session"]["primary_pass"] is None
    assert all(repeat["session"][k] for k in ("precision_weights", "contribution_maps", "focus_evidence", "reproducibility", "original_cfa_reconstruction"))
    repeat_id = repeat["active_stack"]
    write(args.evidence / "repeat-default-primary.json", repeat)
    invalid = dict(base, name="Must refuse", mode="mosaic", primary_pass=0,
                   precision_weights=False, contribution_maps=False, focus_evidence=False, reproducibility=False,
                   original_cfa_reconstruction=False)
    before = ctl.snapshot()[1]
    ctl.mutate(invalid, expected=1)
    after = ctl.snapshot()[1]
    assert before["projects"] == after["projects"] and before["settings"] == after["settings"]
    for mode in ("layers", "mosaic"):
        refused = dict(invalid, name="Must refuse reconstruction", mode=mode,
                       primary_pass=None, original_cfa_reconstruction=True)
        ctl.mutate(refused, expected=1)
        unchanged = ctl.snapshot()[1]
        assert unchanged["projects"] == before["projects"] and unchanged["settings"] == before["settings"]
    ctl.mutate(dict(invalid, name="Completion controls · mosaic", primary_pass=None))
    mosaic = ctl.idle()
    assert mosaic["session"]["mode"] == "mosaic" and mosaic["session"]["primary_pass"] is None
    assert all(not mosaic["session"][k] for k in ("precision_weights", "contribution_maps", "focus_evidence", "reproducibility", "original_cfa_reconstruction"))
    write(args.evidence / "mosaic-no-primary.json", mosaic)
    ctl.mutate({"operation": "select_stack", "id": repeat_id})
    reopened = ctl.idle()
    assert reopened["settings"]["session"] == repeat["settings"]["session"], "Creating a later mode changed the saved repeat draft"
    ctl.mutate(dict(base, name="Completion controls · primary repeat", primary_pass=0))
    preferred = ctl.idle()
    assert preferred["session"]["primary_pass"] == 0
    write(args.evidence / "repeat-explicit-primary.json", preferred)
    ctl.finish({"optional_primary": True, "mosaic_no_primary": True, "incompatible_no_mutation": True,
                "saved_draft_immutable": True, "reconstruction_option_and_refusals": True, "rendered": False, "selected_stack": preferred["active_stack"]})

def inspect(ctl, args):
    if len(args.stack_id) != 1:
        raise ValueError("Inspect phase requires one existing stack ID and --run-index")
    ctl.mutate({"operation": "select_run", "stack_id": args.stack_id[0], "run_index": args.run_index})
    state = ctl.wait(lambda s: not any(s["busy"].values()) and s["photo_ready"] and bool(s["saved_diagnostics"]["available"]) and not s["saved_diagnostics"]["loading"])
    available = state["saved_diagnostics"]["available"]
    write(args.evidence / "available-maps.json", {"available": available})
    chosen = []
    for fragment in args.map_contains:
        matching = [name for name in available if fragment.casefold() in name.casefold()]
        if not matching:
            raise RuntimeError(f"No saved map matched {fragment!r}; available names were saved, not guessed")
        name = matching[0]
        ctl.mutate({"operation": "inspect_session_diagnostic", "map": name,
                    "opacity": args.opacity, "sample_uv": args.sample})
        result = ctl.wait(lambda s: not s["saved_diagnostics"]["loading"] and s["saved_diagnostics"]["selected"] == name and s["saved_diagnostics"]["sample"] is not None and (s["saved_diagnostics"]["value"] is not None or s["saved_diagnostics"]["interpretation"] is not None))
        assert result["saved_diagnostics"]["error"] is None
        chosen.append({"label": name, "state": result["saved_diagnostics"]})
    before = ctl.snapshot()[1]
    ctl.mutate({"operation": "inspect_session_diagnostic", "map": "../not-a-saved-map.tiff"}, expected=1)
    after = ctl.snapshot()[1]
    assert before["saved_diagnostics"]["selected"] == after["saved_diagnostics"]["selected"]
    ctl.mutate({"operation": "set_view", "center": args.sample, "zoom": 8.0})
    native = ctl.snapshot()[1]
    # Headless photo_view may be null; this is accepted command state, not GPU evidence.
    write(args.evidence / "headless-native-request.json", native)
    ctl.finish({"maps": chosen, "unavailable_map_noop": True, "headless_only": True,
                "native_request_is_not_render_evidence": True})

def render(ctl, args):
    if not args.permit_render:
        raise ValueError("Root must explicitly schedule --permit-render; the preparation script never starts a render implicitly")
    ctl.mutate({"operation": "start_stack"})
    state = ctl.wait(lambda s: not s["busy"]["stack"] and "saved" in s["status"].casefold(), seconds=args.render_timeout)
    write(args.evidence / "saved-run.json", state)
    ctl.finish({"actual_worker_completed": True, "state": state})

def capture(ctl, args):
    if not args.run or not args.catalog:
        raise ValueError("Capture needs the actual completed catalog run and isolated catalog")
    inspection = json.loads(args.inspection.read_text(encoding="utf-8")) if args.inspection else None
    entries = inspection["result"]["maps"] if inspection else []
    if not entries and not args.capture_plain:
        raise ValueError("Capture requires an actual inspect-phase result or --capture-plain")
    if args.capture_plain:
        entries = [{"label": None}]
    results = []
    for i, entry in enumerate(entries):
        for zoom in args.zoom:
            png = args.evidence / f"map-{i:02}-zoom-{zoom:g}.png"
            command = ["screenshot", "--open-run", str(args.run), "--catalog", str(args.catalog),
                       "--png", str(png), "--size", "1440x940", "--photo-zoom", str(zoom),
                       "--photo-center", ",".join(map(str, args.sample))]
            if entry["label"]:
                command += ["--diagnostic-map", entry["label"], "--diagnostic-opacity", str(args.opacity),
                            "--diagnostic-sample", ",".join(map(str, args.sample))]
            reply = ctl.run(command)
            assert reply["data"]["state"] == "screenshot_saved" and reply["data"]["exit_code"] == 0
            results.append({"png": str(png), "map": entry["label"], "zoom": zoom, "reply": reply})
    ctl.finish({"actual_gpu": results, "requires_visual_inspection": True})

def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["options", "inspect", "render", "capture"])
    p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--session-file", type=Path)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--stack-id", type=int, action="append", default=[])
    p.add_argument("--run-index", type=int, default=0)
    p.add_argument("--map-contains", action="append", default=[])
    p.add_argument("--sample", type=float, nargs=2, default=[0.5, 0.5])
    p.add_argument("--opacity", type=float, default=0.6)
    p.add_argument("--permit-render", action="store_true")
    p.add_argument("--render-timeout", type=int, default=600)
    p.add_argument("--run", type=Path)
    p.add_argument("--catalog", type=Path)
    p.add_argument("--inspection", type=Path)
    p.add_argument("--capture-plain", action="store_true")
    p.add_argument("--zoom", type=float, action="append", default=[])
    args = p.parse_args()
    if not args.zoom: args.zoom = [1.0, 8.0]
    ctl = Control(args)
    {"options": options, "inspect": inspect, "render": render, "capture": capture}[args.phase](ctl, args)

if __name__ == "__main__":
    main()
