"""Controls for CPU attribution and isolated native-audit inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "display_performance", Path(__file__).with_name("check-display-performance.py")
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def observations(rows):
    return {"frame_performance": {
        "columns": ["frame", "update_ms", "previous_frame_cpu_ms"],
        "meaning": "One observation per egui frame",
        "samples": rows,
    }}


class FrameControls(unittest.TestCase):
    def test_previous_cpu_moves_to_its_own_frame_and_layout_passes_accumulate(self):
        trace = audit.FrameTrace()
        trace.add(observations([[10, 1, 999], [11, 2, 3]]))
        trace.add(observations([[10, 4, 999], [11, 2, 3], [12, 5, 6]]))
        trace.add(observations([[10, 1, 999]]))  # Older partial snapshot cannot erase work.
        measured = trace.summarize(10, 11)
        self.assertEqual(measured["samples"], [[10, 4, 3], [11, 2, 6]])
        self.assertEqual(measured["frames"], 2)
        self.assertEqual(measured["framework_cpu"]["max_ms"], 6)
        self.assertEqual(measured["framework_cpu_sum_ms"], 9)
        self.assertEqual(measured["update_sum_ms"], 6)

    def test_missing_interior_or_trailing_frame_cannot_produce_a_passing_trace(self):
        for rows in ([[10, 1, 1], [12, 2, 2]], [[10, 1, 1], [11, 2, 2]]):
            with self.subTest(rows=rows):
                trace = audit.FrameTrace()
                trace.add(observations(rows))
                with self.assertRaisesRegex(RuntimeError, "coverage incomplete"):
                    trace.summarize(10, 11)

    def test_overlapping_windows_retain_entire_trace_beyond_native_ring(self):
        trace = audit.FrameTrace()
        for end in (256, 400, 600):
            trace.add(observations([[frame, frame / 10, frame - 1]
                                    for frame in range(max(0, end - 256), end)]))
        measured = trace.summarize(0, 598)
        self.assertEqual(measured["frames"], 599)
        self.assertEqual(measured["samples"][0], [0, 0, 0])
        self.assertEqual(measured["samples"][-1], [598, 59.8, 598])

    def test_missing_cpu_and_legacy_layout_counter_are_rejected(self):
        trace = audit.FrameTrace()
        trace.add(observations([[2, 1, 4], [3, 1, -1], [4, 1, 6]]))
        with self.assertRaisesRegex(RuntimeError, "CPU unavailable"):
            trace.summarize(2, 3)
        legacy = observations([[2, 1, 4]])
        legacy["frame_performance"]["meaning"] = "One observation per App::update"
        with self.assertRaisesRegex(RuntimeError, "group repeated layout passes"):
            trace.add(legacy)

    def test_invalid_measurement_rows_cannot_enter_percentiles(self):
        for row in ([-1, 1, 3], [1, -2, 3], [1, 2], [1, 2, 3, 4],
                    [1, float("nan"), 2]):
            with self.subTest(row=row):
                with self.assertRaisesRegex(RuntimeError, "Invalid frame"):
                    audit.FrameTrace().add(observations([row]))

    def test_idle_or_hidden_view_is_not_accepted_as_successful_pan(self):
        current = {"photo_view": {"uv": [[0.25, 0.4], [0.375, 0.525]]}}
        self.assertEqual(audit.checked_aperture(current, [0.3125, 0.4625], 8),
                         current["photo_view"]["uv"])
        for changed, center in (
            (current, [0.6, 0.6]),  # Command accepted but actual view stayed still.
            ({"photo_view": None}, [0.3125, 0.4625]),
            ({"photo_view": {"uv": [[0, 0], [1, 1]]}}, [0.5, 0.5]),
        ):
            with self.subTest(changed=changed, center=center):
                with self.assertRaises(ValueError):
                    audit.checked_aperture(changed, center, 8)


class IsolationControls(unittest.TestCase):
    def test_edit_witness_requires_matching_owned_launch_and_visible_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "edit.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            request = {"nonce": "unique-launch", "pid": 123, "binary_sha256": "hash", "phase": "before"}
            valid = {**request, "visible_pane": "Edit", "observed_controls": ["Exposure", "Contrast"],
                     "screenshot": "edit.png"}
            path = directory / "witness.json"
            path.write_text(json.dumps(valid))
            checked = audit.checked_edit_witness(path, request)
            self.assertEqual(checked["screenshot_sha256"], audit.digest(directory / "edit.png"))
            (directory / "edit.jpg").write_bytes(b"\xff\xd8\xfffixture")
            path.write_text(json.dumps({**valid, "screenshot": "edit.jpg"}))
            self.assertEqual(audit.checked_edit_witness(path, request)["screenshot_sha256"],
                             audit.digest(directory / "edit.jpg"))
            for change in ({"pid": 124}, {"nonce": "other-launch"}, {"phase": "after"},
                           {"visible_pane": "Agent"}, {"observed_controls": []},
                           {"binary_sha256": "different-binary"}):
                path.write_text(json.dumps({**valid, **change}))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    audit.checked_edit_witness(path, request)

    def test_edit_witness_cannot_use_an_external_or_non_image_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output = directory / "owned"
            output.mkdir()
            (directory / "outside.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            (output / "not-image.txt").write_text("Edit")
            request = {"nonce": "nonce", "pid": 123, "binary_sha256": "hash", "phase": "before"}
            path = output / "witness.json"
            for image_path in ("../outside.png", "not-image.txt"):
                path.write_text(json.dumps({**request, "visible_pane": "Edit",
                                           "observed_controls": ["Exposure"], "screenshot": image_path}))
                with self.subTest(image_path=image_path), self.assertRaises(ValueError):
                    audit.checked_edit_witness(path, request)

    def test_copy_remaps_only_selected_run_and_never_rewrites_original_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            run = base / "run"
            run.mkdir()
            output = base / "audit"
            output.mkdir()
            for name in ("result.tiff", "render.log", "result.strehl-edits.json"):
                (run / name).write_bytes(("original " + name).encode())
            catalog = base / "projects.json"
            sibling = base / "run-extra"
            catalog.write_text(json.dumps({
                "layout": {"network": 0.18},
                "runs": [{
                    "directory": str(run), "output": str(run / "result.tiff"),
                    "log": str(run / "render.log"), "source": str(sibling),
                }, {"directory": str(base / "unrelated")}],
            }), encoding="utf-8")
            original = catalog.read_bytes()
            fixture, state, protected = audit.prepare_fixture(run, catalog, output)
            isolated = json.loads((state / "Strehl/projects.json").read_text())
            self.assertEqual(len(isolated["runs"]), 1)
            self.assertEqual(isolated["runs"][0]["directory"], str(fixture))
            self.assertEqual(isolated["runs"][0]["source"], str(sibling))
            self.assertEqual(catalog.read_bytes(), original)
            (fixture / "result.strehl-edits.json").write_text("owned app modification")
            for path, before in protected.items():
                self.assertEqual(audit.digest(Path(path)), before)

    def test_saved_run_cannot_reference_an_output_outside_its_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            run, output = base / "run", base / "audit"
            run.mkdir()
            output.mkdir()
            outside = base / "outside.tiff"
            outside.write_bytes(b"never copied")
            (run / "render.log").write_bytes(b"log")
            catalog = base / "projects.json"
            catalog.write_text(json.dumps({"runs": [{
                "directory": str(run), "output": str(outside),
                "log": str(run / "render.log"),
            }]}), encoding="utf-8")
            for argument in (run, run / ".." / "run"):
                with self.subTest(argument=argument), self.assertRaises(ValueError) as rejected:
                    audit.prepare_fixture(argument, catalog, output)
                # A path-containment refusal is required, not an earlier failure
                # to recognize the same saved run under its equivalent spelling.
                self.assertNotIn("exactly one record", str(rejected.exception))
            self.assertFalse((output / "fixture").exists())
            self.assertEqual(outside.read_bytes(), b"never copied")

    def test_equivalent_noncanonical_run_is_matched_and_remapped(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            run, output = base / "run", base / "audit"
            run.mkdir()
            output.mkdir()
            alias = run / ".." / "run"
            self.assertNotEqual(alias, alias.resolve())
            self.assertTrue(alias.is_dir())
            for name in ("result.tiff", "render.log"):
                (run / name).write_bytes(("original " + name).encode())
            catalog = base / "projects.json"
            catalog.write_text(json.dumps({"runs": [{
                "directory": str(run.resolve()), "output": str(run / "result.tiff"),
                "log": str(run / "render.log"),
            }]}), encoding="utf-8")
            original = catalog.read_bytes()
            fixture, state, protected = audit.prepare_fixture(alias, catalog, output)
            isolated = json.loads((state / "Strehl/projects.json").read_text())
            self.assertEqual(isolated["runs"][0]["directory"], str(fixture))
            self.assertEqual(isolated["runs"][0]["output"], str(fixture / "result.tiff"))
            self.assertEqual((fixture / "result.tiff").read_bytes(), b"original result.tiff")
            self.assertEqual(catalog.read_bytes(), original)
            self.assertEqual(len(protected), 2)
            for path, before in protected.items():
                self.assertEqual(audit.digest(Path(path)), before)


if __name__ == "__main__":
    unittest.main()
