"""Offline failure/control tests; synthetic camera events are NOT photographic evidence."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("sony_control", Path(__file__).with_name("sony-control.py"))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@contextlib.contextmanager
def test_directory():
    root = (control.ROOT / "outputs/sony-control/test-temp").resolve()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="test-", dir=root) as directory:
        # Verify the recursive cleanup target before TemporaryDirectory cleans it.
        if not Path(directory).resolve().is_relative_to(root):
            raise RuntimeError("Test temporary directory escaped its workspace root")
        yield directory


class FakeBridge:
    def __init__(self, fail=None):
        self.commands = []
        self.fail = fail
        self.focus = 32768
        self.drive = 1
        self.bracket_count = 3
        self.bracket_order = 1
        self.destination = 1
        self.card_images = 0

    def call(self, *parts, **kwargs):
        self.commands.append(parts)
        if parts[0] == self.fail:
            raise RuntimeError("Planted camera failure")
        if parts[0] == "focus":
            self.focus = parts[1]
            return {"ok": True, "readback": self.focus, "requested": self.focus}
        if parts[0] == "set":
            _, name, value = parts
            if name == "StillImageStoreDestination":
                self.destination = value
            if name == "DriveMode":
                self.drive = value
            if name == "FocusBracketOrder":
                self.bracket_order = value
            if name == "FocusBracketShotNumber":
                if self.bracket_order != 2 and value != 3:
                    raise RuntimeError("Wrong bracket order for requested shot count")
                self.bracket_count = value
        if parts[0] == "capture":
            _, count, _ = parts  # Protocol intentionally has no host image path.
            assert self.destination == 2
            if count > 1:
                assert self.drive == 0x12001 and self.bracket_count == count
            else:
                assert self.drive == 1
            self.card_images += count
            return card_reply(count)
        return {"ok": True, "properties": {}}


def card_reply(count):
    return {"ok": True, "destination": "memory-card", "captured_events": count,
            "card_state": "not-writing", "bracket_idle": True,
            "completion": "camera-events-and-card-idle", "file_verification": "not-performed", "files": []}


def card_status(**overrides):
    values = {"StillImageStoreDestination": 2, "MediaSLOT1_Status": 0,
              "MediaSLOT1_WritingState": 1, "FocusBracketShootingStatus": 0,
              "MediaSLOT1_RemainingNumber": 1000}
    values.update(overrides)
    return {"properties": {k: {"readable": True, "value": v} for k, v in values.items()}}


class FocusControlTests(unittest.TestCase):
    def test_controls_precede_focus_sweep(self):
        plan = control.plan_test(32768)
        self.assertEqual([p["kind"] for p in plan[:5]], ["capture"] * 5)
        self.assertTrue(all(p["phase"] == "fixed-null" for p in plan[:5]))
        self.assertEqual(control.plan_summary(plan)["raw_count"], 73)
        captures = [p for p in plan if p["kind"] == "capture"]
        self.assertEqual(len(captures), 57)
        self.assertEqual(sum(p["count"] for p in captures if p["phase"] == "native-width-1"), 18)

    def test_same_sweep_repeated_without_clamping(self):
        plan = control.plan_test(32768, direction=-1)
        for repeat in range(3):
            offsets = [p["offset"] for p in plan if p["kind"] == "capture" and
                       p["phase"] == "fine-sweep" and p["repeat"] == repeat]
            self.assertEqual(offsets, [-x for x in control.OFFSETS])

    def test_both_return_directions_present(self):
        plan = control.plan_test(32768)
        approaches = [p["approach_side"] for p in plan if p["kind"] == "capture" and
                      p["phase"] == "return-repeatability"]
        self.assertEqual(approaches, [-1, 1] * 3)

    def test_range_failure_is_not_silently_clipped(self):
        for base in (0, 100, 65535, 65200):
            with self.assertRaises(ValueError):
                control.plan_test(base)

    def test_real_positive_control_is_not_a_fine_step(self):
        with self.assertRaises(ValueError):
            control.plan_test(32768, positive=16)

    def test_stack_can_exceed_native_299_limit(self):
        actions = control.plan_stack(10000, 2, 1000)
        self.assertEqual(control.plan_summary(actions)["raw_count"], 1000)
        self.assertEqual(actions[-2]["target"], 11998)
        self.assertTrue(all(a["count"] == 1 for a in actions if a["kind"] == "capture"))

    def test_stack_range_and_zero_step_fail(self):
        for args in ((5, -1, 10), (65534, 1, 3), (100, 0, 3), (100, 1, 0)):
            with self.assertRaises(ValueError):
                control.plan_stack(*args)

    def test_skip_native_changes_claimable_comparison(self):
        plan = control.plan_test(32768, native=False)
        self.assertEqual(control.plan_summary(plan)["raw_count"], 55)
        self.assertNotIn("native-width-1", control.plan_summary(plan)["phases"])

    def test_complete_protocol_sequence_and_manifest(self):
        with test_directory() as directory:
            out = Path(directory)
            manifest = {"captures": []}
            bridge = FakeBridge()
            control.configure(bridge)
            with contextlib.redirect_stdout(io.StringIO()):
                control.execute(bridge, control.plan_test(32768), out, 1000, 90, manifest)
            self.assertEqual(len(manifest["captures"]), 57)
            self.assertEqual(bridge.card_images, 73)
            self.assertEqual(sum(c["camera_report"]["captured_events"] for c in manifest["captures"]), 73)
            ordinals = [i for c in manifest["captures"] for i in range(c["image_range"][0], c["image_range"][1] + 1)]
            self.assertEqual(ordinals, list(range(1, 74)))
            self.assertEqual([c["image_range"] for c in manifest["captures"][-2:]], [[56, 64], [65, 73]])
            self.assertEqual([p.name for p in out.iterdir()], ["manifest.json"])
            self.assertNotIn("active_capture", manifest)
            saved = json.loads((out / "manifest.json").read_text())
            self.assertEqual(saved, manifest)
            self.assertTrue(all(c["camera_report"]["files"] == [] for c in saved["captures"]))

    def test_capture_failure_does_not_retry_shutter_or_move_again(self):
        with test_directory() as directory:
            out = Path(directory)
            bridge = FakeBridge(fail="capture")
            control.configure(bridge)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                control.execute(bridge, control.plan_stack(1000, 1, 3), out, 1000, 90, {"captures": []})
            self.assertEqual([c[0] for c in bridge.commands].count("capture"), 1)
            self.assertEqual([c[0] for c in bridge.commands].count("focus"), 1)
            saved = json.loads((out / "manifest.json").read_text())
            self.assertEqual(saved["captures"], [])
            self.assertEqual(saved["active_capture"]["image_range"], [1, 1])
            self.assertEqual(saved["active_capture"]["sequence"], 1)

    def test_focus_failure_takes_no_exposure(self):
        bridge = FakeBridge(fail="focus")
        with self.assertRaises(RuntimeError):
            control.execute(bridge, control.plan_stack(1000, 1, 3), Path("unused"), 1000, 90, {"captures": []})
        self.assertNotIn("capture", [c[0] for c in bridge.commands])

    def test_configure_selects_card_first_and_never_host(self):
        bridge = FakeBridge()
        control.configure(bridge)
        self.assertEqual(bridge.commands[0], ("set", "StillImageStoreDestination", 2))
        self.assertEqual([c for c in bridge.commands if "StillImageStoreDestination" in c],
                         [("set", "StillImageStoreDestination", 2)])
        self.assertFalse(any("RAW_J_PC_Save_Image" in c for c in bridge.commands))

    def test_card_completion_rejects_wrong_destination_count_busy_and_download(self):
        control.validate_card_capture(card_reply(9), 9)
        changes = [{"destination": "host"}, {"captured_events": 8}, {"captured_events": 10},
                   {"card_state": "writing"}, {"bracket_idle": False}, {"files": ["image.ARW"]},
                   {"completion": "download"}, {"file_verification": "verified"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                control.validate_card_capture({**card_reply(9), **change}, 9)
        for key in card_reply(9):
            if key == "ok":
                continue
            incomplete = card_reply(9)
            incomplete.pop(key)
            with self.subTest(missing=key), self.assertRaises(RuntimeError):
                control.validate_card_capture(incomplete, 9)

    def test_card_preflight_rejects_missing_busy_full_and_host(self):
        control.card_preflight(card_status(MediaSLOT1_RemainingNumber=73), 73)
        for change in ({"StillImageStoreDestination": 1}, {"StillImageStoreDestination": 3},
                       {"MediaSLOT1_Status": 1}, {"MediaSLOT1_Status": 2},
                       {"MediaSLOT1_WritingState": 2}, {"FocusBracketShootingStatus": 1},
                       {"MediaSLOT1_RemainingNumber": 72}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                control.card_preflight(card_status(**change), 73)
        with self.assertRaises(RuntimeError):
            control.card_preflight({"properties": {}}, 73)

    def test_obsolete_host_destination_arguments_are_rejected(self):
        for destination in ("host", "both"):
            args = ["sony-control.py", "focus-test", "--out", "unused", "--destination", destination]
            with patch.object(control.sys, "argv", args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    control.main()
            self.assertEqual(error.exception.code, 2)

    def test_bad_completion_stops_before_next_focus_and_preserves_intent(self):
        with test_directory() as directory:
            bridge = FakeBridge()
            control.configure(bridge)
            original = bridge.call

            def bad_reply(*parts, **kwargs):
                response = original(*parts, **kwargs)
                if parts[0] == "capture":
                    response["captured_events"] = 0
                return response

            manifest = {"captures": []}
            with patch.object(bridge, "call", side_effect=bad_reply), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):
                    control.execute(bridge, control.plan_stack(1000, 1, 3), Path(directory), 1000, 90, manifest)
            self.assertEqual([c[0] for c in bridge.commands].count("focus"), 1)
            self.assertEqual([c[0] for c in bridge.commands].count("capture"), 1)
            self.assertEqual(manifest["captures"], [])
            self.assertEqual(manifest["active_capture"]["image_range"], [1, 1])

    def test_preflight_rejects_auto_exposure_bulb_and_bad_focus(self):
        def status(**overrides):
            values = {"FocusMode": 1, "ExposureProgramMode": 1, "IsoSensitivity": 100,
                      "ShutterSpeed": 6553601, "FocusPositionCurrentValue": 32768}
            values.update(overrides)
            return {"properties": {k: {"readable": True, "value": v} for k, v in values.items()}}
        self.assertEqual(control.preflight(status()), 32768)
        for change in ({"FocusMode": 2}, {"ExposureProgramMode": 2}, {"IsoSensitivity": 0xFFFFFF},
                       {"ShutterSpeed": 0}, {"FocusPositionCurrentValue": 65536}):
            with self.assertRaises(RuntimeError):
                control.preflight(status(**change))


if __name__ == "__main__":
    unittest.main(verbosity=2)
