"""Private quality/TIFF instruments. No candidate-output scoring in this stage."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import hashlib
import importlib.util
import math
from pathlib import Path
import struct
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OLD = ROOT / "experiments/m194f-production-bridge/independent-reader.py"
OLD_SHA = "3fbaf526776fc85042861e1e7a90c06664c43519cef20d12310a67efd8eaff2d"


class Checks:
    def __init__(self): self.rows = []

    def add(self, name, passed, **details):
        if any(row["id"] == name for row in self.rows): raise ValueError("duplicate control ID")
        self.rows.append({"id": name, "passed": bool(passed), "details": details})
        if not passed: raise ValueError("quality instrument: " + name)

    def refuses(self, name, call, exception, contains):
        try: call()
        except exception as error:
            self.add(name, contains in str(error), exception_type=type(error).__name__, message=str(error))
        else: self.add(name, False, exception_type=None)


def metric_controls(m, fixture, budget, check):
    np = m.np
    masks = m.regions((240, 320), (0, 0), budget)
    check.add("endpoint-mask-positive-negative", not bool(masks["endpoint-background"][110, 150])
              and bool(masks["endpoint-background"][106, 149]))
    check.refuses("fixed-guard-live", lambda: m.regions((200, 300), (10, 31), budget), m.Refusal, "guard")
    image = budget.empty((240, 320), "<f8", "private metric signal")
    changed = budget.empty(image.shape, "<f8", "private metric changed signal")
    extra = budget.empty(image.shape, "<f8", "private extra frequency")
    for y in range(240):
        for x in range(320): extra[y, x] = 20. * math.cos(2 * math.pi * (.117 * x + .053 * y) + .29)
    for layer in ("background", "foreground"):
        mask = masks["surface-" + layer]
        frequencies = [wave["frequency"] for wave in fixture["scene"][layer]["waves"]]
        fit = m.WaveFit(mask, (0, 0), frequencies, budget)
        image.fill(3000.)
        flat = fit.read(image)  # Flat control is deliberately first on each actual mask.
        check.add(layer + "-flat-first", max(w["amplitude_dn"] for w in flat["waves"]) <= 1e-7
                  and flat["residual_rms_dn"] <= 1e-7, readout=flat)
        def signal(destination, scale=1., shift=0.):
            for y in range(240):
                for x in range(320):
                    destination[y, x] = 3000. + sum(amplitude * scale * math.cos(
                        2 * math.pi * (f[0] * x + f[1] * y) + phase + shift)
                        for f, amplitude, phase in zip(frequencies, (40., 25.), (.31, -.47), strict=True))
            budget.check()
        signal(image)
        original_hash = hashlib.sha256(image.tobytes(order="C")).hexdigest()
        reference = fit.read(image)
        max_error = max(abs(reference["intercept_dn"] - 3000.), *(math.hypot(
            row["real_dn"] - amplitude * math.cos(phase), row["imaginary_dn"] - amplitude * math.sin(phase))
            for row, amplitude, phase in zip(reference["waves"], (40., 25.), (.31, -.47), strict=True)))
        check.add(layer + "-known-complex-coefficients", max_error <= 1e-7, maximum_error_dn=max_error, readout=reference)
        for label, scale, shift in (("half-amplitude", .5, 0.), ("phase-shift", 1., .4), ("inflated-amplitude", 1.5, 0.)):
            signal(changed, scale, shift)
            measured = fit.read(changed)
            differences = m.wave_difference(measured, reference)
            error = m.errors(changed, image, mask, budget)
            powered = error["rmse_dn"] > 1.
            if label == "inflated-amplitude": powered &= all(row["amplitude_difference_dn"] > 1. for row in differences)
            if label == "half-amplitude": powered &= all(row["amplitude_difference_dn"] < -1. for row in differences)
            if label == "phase-shift": powered &= all(abs(row["phase_error_radians"] - .4) <= 1e-7 for row in differences)
            check.add(layer + "-" + label, powered, error=error, wave_differences=differences)
            signal(changed)
            restored_hash = hashlib.sha256(changed.tobytes(order="C")).hexdigest()
            check.add(layer + "-" + label + "-restored", restored_hash == original_hash,
                      original_sha256=original_hash, restored_sha256=restored_hash)
        np.add(image, extra, out=changed)
        measured = fit.read(changed)
        check.add(layer + "-extra-wave", measured["residual_rms_dn"] > 1.
                  and m.errors(changed, image, mask, budget)["rmse_dn"] > 1., readout=measured)
        selected = m.selected(extra, mask, budget, "extra-wave selected private vector")
        coefficients = budget.empty((5,), "<f8", "extra-wave projection coefficients")
        projection = budget.empty(selected.shape, "<f8", "extra-wave projection")
        np.matmul(fit.inverse, selected, out=coefficients)
        np.matmul(fit.x, coefficients, out=projection)
        np.subtract(selected, projection, out=selected)
        rms = math.sqrt(float(np.dot(selected, selected)) / selected.size)
        check.add(layer + "-projected-residual-nonzero", rms > 1e-6, residual_rms_dn=rms)
        np.copyto(changed, image)
        # Explicit row-order scatter into the same selected sites.
        k = 0
        for y in range(240):
            for x in range(320):
                if mask[y, x]: changed[y, x] += selected[k]; k += 1
        measured = fit.read(changed)
        differences = m.wave_difference(measured, reference)
        check.add(layer + "-coefficient-only-blindness", max(row["complex_error_dn"] for row in differences) <= 1e-7
                  and measured["residual_rms_dn"] > 1. and m.errors(changed, image, mask, budget)["rmse_dn"] > 1.,
                  wave_differences=differences, residual_rms_dn=measured["residual_rms_dn"])
        check.refuses(layer + "-rank-refusal", lambda: m.WaveFit(mask, (0, 0), [frequencies[0]] * 2, budget),
                      m.Refusal, "rank/condition")
        # Same data with a false native offset changes coefficients on the actual solver.
        false_fit = m.WaveFit(mask, (7, 11), frequencies, budget)
        differences = m.wave_difference(false_fit.read(image), reference)
        check.add(layer + "-native-phase-live", max(row["complex_error_dn"] for row in differences) > 1.,
                  wave_differences=differences)
        del fit, false_fit, selected, coefficients, projection
    image.fill(3000.); np.copyto(changed, image)
    changed[19, 23] += 64.
    report = m.sparse_pair(image, changed, image, masks["whole"], (0, 0), budget)
    window = m.sparse_pair(image, changed, image, masks["window"], (0, 0), budget)
    check.add("full-site-spike-outside-window", report["after_maximum_absolute_error_dn"] == 64.
              and report["after_worst_site"]["native_xy"] == [23, 19]
              and report["worsening_gt10_dn_count"] == 1 and window["after_maximum_absolute_error_dn"] == 0.,
              whole=report, window=window)
    changed[19, 24] -= 64.
    err = m.errors(changed, image, masks["whole"], budget)
    check.add("opposing-bias-cancellation", err["bias_dn"] == 0. and err["mse_dn2"] > 0., error=err)
    changed.fill(3000.); changed[0, 0] += 10.; changed[0, 1] -= 10.
    report = m.sparse_pair(image, changed, image, masks["whole"], (0, 0), budget)
    check.add("threshold-strict-and-tie-order", report["worsening_gt10_dn_count"] == 0
              and report["after_worst_site"]["native_xy"] == [0, 0], report=report)
    del image, changed, extra, masks

    shape = (3, 5)
    mask = budget.empty(shape, "|b1", "temporal private mask"); mask.fill(True)
    truth = budget.empty(shape, "<f8", "temporal private target")
    for y in range(3):
        for x in range(5): truth[y, x] = 3000. + x * 31. + y * 19.
    image = budget.empty(shape, "<f8", "temporal private repeat")
    scratch = tuple(budget.empty(shape, "<f8", "temporal scratch" + str(j)) for j in range(2))
    temporal, constant = m.Temporal(shape, budget), m.Temporal(shape, budget)
    offsets, mses = (-7., -5., -3., -1., 1., 3., 5., 7.), []
    for a in offsets:
        np.add(truth, a, out=image); temporal.add(image, scratch)
        mses.append(m.errors(image, truth, mask, budget)["mse_dn2"])
        np.add(truth, 9., out=image); constant.add(image, scratch)
    check.add("temporal-versus-spatial", temporal.variance_region(mask) == 24.
              and constant.variance_region(mask) == 0., variance_dn2=temporal.variance_region(mask),
              constant_variance_dn2=constant.variance_region(mask))
    decomposition = m.decomposition(temporal, truth, mask, 21.)
    check.add("negative-squared-bias-retained", decomposition["unbiased_squared_bias_dn2"] == -3., result=decomposition)
    leaves = []
    for a in offsets:
        np.add(truth, a, out=image)
        value = temporal.leave_one(image, scratch, mask)
        expected = 28. - 4. * a * a / 21.
        check.add("delete-repeat-" + str(int(a)), abs(value - expected) <= 1e-10, actual=value, expected=expected)
        leaves.append(value)
    jack = m.jackknife(leaves)
    expected_mean = math.fsum(28. - 4. * a * a / 21. for a in offsets) / 8
    expected_se = math.sqrt(7. / 8. * sum((28. - 4. * a * a / 21. - expected_mean)**2 for a in offsets))
    check.add("whole-repeat-jackknife", abs(jack["jackknife_standard_error"] - expected_se) <= 1e-10, result=jack, expected_se=expected_se)
    summary = m.repeat_summary([2. * a + 1. for a in offsets])
    check.add("paired-mse-repeat-uncertainty", abs(summary["mean"] - 1.) <= 1e-12
              and abs(summary["sample_sd"] - math.sqrt(96.)) <= 1e-12
              and abs(summary["standard_error"] - math.sqrt(12.)) <= 1e-12, result=summary)
    check.refuses("ninth-repeat-refusal", lambda: temporal.add(image, scratch), m.Refusal, "eight-repeat")
    incomplete = m.Temporal(shape, budget)
    check.refuses("incomplete-variance-refusal", lambda: incomplete.variance_region(mask), m.Refusal, "incomplete")
    check.refuses("temporal-alias-refusal", lambda: incomplete.add(image, (image, scratch[1])), m.Refusal, "alias")


def tiff_fixture(width, height, endian="<", strip_rows=3):
    """Small independent encoder uses scalar struct packing, not the parser."""
    description = ("Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. "
                   "THIS IS NOT sRGB -- do not treat it as such. This is the measurement output. "
                   "White balance: as-shot per-channel gains, green = 1, applied AFTER black subtraction "
                   "and normalisation by (white - black), and AFTER the noise model, which is calibrated "
                   "in raw DN before any gain.\0").encode("ascii")
    pixels = [1000 + 301 * c + 17 * y + 3 * x for y in range(height) for x in range(width) for c in range(3)]
    strips = [struct.pack(endian + "H" * (min(strip_rows, height - y) * width * 3),
                          *pixels[y * width * 3:min(y + strip_rows, height) * width * 3])
              for y in range(0, height, strip_rows)]
    def payload(typ, values):
        return values if typ == 2 else struct.pack(endian + ("H" if typ == 3 else "I") * len(values), *values)
    tags = {256: (4, [width]), 257: (4, [height]), 258: (3, [16] * 3), 259: (3, [1]),
            262: (3, [2]), 270: (2, description), 273: (4, [0] * len(strips)), 274: (3, [1]),
            277: (3, [3]), 278: (4, [strip_rows]), 279: (4, [len(s) for s in strips]),
            284: (3, [1]), 305: (2, b"strehl 0.0.0\0"), 317: (3, [1]), 339: (3, [1] * 3)}
    ifd_end = 8 + 2 + 12 * len(tags) + 4
    cursor = ifd_end
    locations = {}
    for tag, (typ, values) in sorted(tags.items()):
        raw = payload(typ, values)
        if len(raw) > 4: locations[tag], cursor = cursor, cursor + len(raw)
    offsets = []
    for strip in strips: offsets.append(cursor); cursor += len(strip)
    tags[273] = (4, offsets)
    raw = bytearray(cursor)
    raw[:8] = (b"II" if endian == "<" else b"MM") + struct.pack(endian + "HI", 42, 8)
    struct.pack_into(endian + "H", raw, 8, len(tags))
    entries = {}
    for i, (tag, (typ, values)) in enumerate(sorted(tags.items())):
        at = 10 + i * 12; entries[tag] = at
        data = payload(typ, values)
        struct.pack_into(endian + "HHI", raw, at, tag, typ, len(values))
        if len(data) <= 4: raw[at + 8:at + 8 + len(data)] = data
        else:
            struct.pack_into(endian + "I", raw, at + 8, locations[tag])
            raw[locations[tag]:locations[tag] + len(data)] = data
    for offset, strip in zip(offsets, strips, strict=True): raw[offset:offset + len(strip)] = strip
    return bytes(raw), {"entries": entries, "locations": locations, "strip_offsets": offsets,
                        "pixels": pixels, "shape": (height, width, 3)}


def tiff_controls(tiff, old, store, budget, check):
    def write(label, raw): return store.raw("tiff/" + label + ".tiff", raw)
    def decode(ref, shape):
        budget.tiff_decodes += 1; budget.check()
        return tiff.read_rgb_tiff(store.root / ref["path"], shape, ref["sha256"], budget)
    for endian in ("<", ">"):
        raw, info = tiff_fixture(11, 7, endian, 3)
        name = "little" if endian == "<" else "big"
        ref = write(name, raw)
        pixels, evidence = decode(ref, info["shape"])
        expected_sha = hashlib.sha256(struct.pack("<" + "H" * len(info["pixels"]), *info["pixels"])).hexdigest()
        check.add("tiff-" + name + "-actual-strips", evidence["pixel_sha256"] == expected_sha
                  and evidence["strip_count"] == 3 and pixels.dtype.str == "<u2"
                  and all(int(v) == wanted for v, wanted in zip(pixels.flat, info["pixels"], strict=True)),
                  pixel_sha256=evidence["pixel_sha256"], expected_sha256=expected_sha)
        del pixels
    raw, info = tiff_fixture(193, 17, "<", 5)
    ref = write("larger-than-old-bound", raw)
    pixels, evidence = decode(ref, info["shape"])
    check.add("tiff-larger-live-companion", pixels.shape == (17, 193, 3)
              and int(pixels[16, 192, 2]) == 1000 + 301 * 2 + 17 * 16 + 3 * 192)
    del pixels
    budget.tiff_decodes += 1; budget.check()
    check.refuses("tiff-old128-bound-live", lambda: old.read_tiff(store.root / ref["path"], "rgb", info["shape"], ref["sha256"]),
                  old.Refusal, "bounded")
    raw, info = tiff_fixture(11, 7)
    base = write("baseline-restored", raw)
    entries, locations = info["entries"], info["locations"]
    def mutate(tag, field, value, fmt):
        changed = bytearray(raw)
        struct.pack_into("<" + fmt, changed, entries[tag] + field, value)
        return bytes(changed)
    cases = [
        ("compression", mutate(259, 8, 2, "H"), "compression"),
        ("sample-type", raw[:locations[339]] + struct.pack("<HHH", 3, 3, 3) + raw[locations[339] + 6:], "unsigned"),
        ("duplicate-tag", mutate(257, 0, 256, "H"), "duplicate"),
        ("unknown-tag", mutate(257, 0, 65000, "H"), "unknown"),
        ("huge-width", mutate(256, 8, 321, "I"), "bounded native"),
        ("wrong-dimensions", mutate(256, 8, 12, "I"), "expected TIFF"),
        ("wrong-short-type", mutate(258, 2, 4, "H"), "SHORT"),
        ("zero-strip-rows", mutate(278, 8, 0, "I"), "zero rows"),
        ("truncated", raw[:-1], "strip outside"),
        ("trailing", raw + b"x", "trailing"),
    ]
    overlap = bytearray(raw); struct.pack_into("<I", overlap, locations[273] + 4, info["strip_offsets"][0])
    cases.append(("overlapping-strips", bytes(overlap), "overlap"))
    wrong_count = bytearray(raw); struct.pack_into("<I", wrong_count, locations[279], 1)
    cases.append(("strip-extent", bytes(wrong_count), "strip byte count"))
    bad_description = bytearray(raw); bad_description[locations[270]] = ord("X")
    cases.append(("description", bytes(bad_description), "description"))
    for label, changed, reason in cases:
        ref = write("bad-" + label, changed)
        check.refuses("tiff-" + label, lambda r=ref: decode(r, (7, 11, 3)), tiff.Refusal, reason)
    for label, shape, reason in (("bool-shape", (7, True, 3), "typed"),
                                 ("float-shape", (7., 11, 3), "typed"),
                                 ("wrong-channel-shape", (7, 11, 4), "typed")):
        check.refuses("tiff-" + label, lambda s=shape: decode(base, s), tiff.Refusal, reason)
    check.refuses("tiff-external-hash", lambda: decode({**base, "sha256": "0" * 64}, (7, 11, 3)), tiff.Refusal, "SHA mismatch")
    changed = bytearray(raw)
    changed_at = info["strip_offsets"][0] + 2 * (11 * 2 * 3 + 4 * 3 + 1)
    old_value = struct.unpack_from("<H", raw, changed_at)[0]
    struct.pack_into("<H", changed, changed_at, old_value + 1)
    changed_ref = write("changed-green-valid-hash", bytes(changed))
    pixels, evidence = decode(changed_ref, (7, 11, 3))
    check.add("tiff-changed-code-pixel-oracle", int(pixels[2, 4, 1]) == old_value + 1
              and int(pixels[2, 4, 1]) != info["pixels"][(2 * 11 + 4) * 3 + 1],
              actual_code=int(pixels[2, 4, 1]), expected_original_code=old_value,
              scope="valid file hash/parser; original actual-pixel oracle deliberately fails")
    del pixels
    pixels, evidence = decode(base, (7, 11, 3))
    check.add("tiff-original-restored", all(int(v) == wanted for v, wanted in zip(pixels.flat, info["pixels"], strict=True)))


def main():
    spec = importlib.util.spec_from_file_location("m194g_quality_io", HERE / "independent-quality-io.py")
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_paths = (Path(__file__), HERE / "independent-quality-io.py", HERE / "independent-quality-metrics.py",
                    HERE / "independent-rgb-tiff.py", OLD)
    names = {p.resolve().relative_to(ROOT).as_posix() for p in source_paths}
    inputs = [(HERE / name).resolve() for name in ("fixture.json", "next-quality-reader-preregister.md", "next-rgb-tiff-reader-design.md")]
    release, reads = io.verify_release(args.release, args.release_sha256, "instruments", names, inputs)
    sources = release["source_bindings"]
    io.need(sources[OLD.relative_to(ROOT).as_posix()]["sha256"] == OLD_SHA, "held historical TIFF reader")
    m = io.load_bound(HERE / "independent-quality-metrics.py", "m194g_quality_metrics", sources)
    io.np = m.np
    budget = m.Budget("instruments", start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    reads.budget = budget
    store = io.Store(args.output, budget)
    result = {"schema": "m194g-quality-instruments-v1", "status": "UNCOMMISSIONED_QUALITY_STAGE",
              "checks": [], "sources_before": sources, "sources_after": None, "runtime": None, "work": None,
              "error": None, "finalization_errors": [], "execution_release": io.file_ref(args.release),
              "invocation": io.invocation(), "fixture": io.file_ref(HERE / "fixture.json"), "artifacts": []}
    check = Checks()
    def check_inputs():
        reads.finish()
        result["sources_after"] = {name: io.file_binding(ROOT / name) for name in sources}
        io.need(result["sources_after"] == sources, "quality instrument source changed")
    try:
        store.snapshots(sources)
        tiff = io.load_bound(HERE / "independent-rgb-tiff.py", "m194g_independent_tiff", sources)
        old = io.load_bound(OLD, "m194f_frozen_independent_tiff", sources)
        fixture = io.strict_json(reads.raw(HERE / "fixture.json", result["fixture"]["sha256"], result["fixture"]["bytes"]))
        result["runtime"] = io.runtime()
        metric_controls(m, fixture, budget, check)
        io.need(len(check.rows) == 46 and budget.tiff_decodes == 0, "exact private metric control population")
        tiff_controls(tiff, old, store, budget, check)
        io.need(len(check.rows) == 69 and budget.tiff_decodes == 23
                and budget.target_cells == 0, "exact metric/TIFF control population")
        result["status"] = "PASS_QUALITY_INSTRUMENTS_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    result["checks"] = check.rows
    result["artifacts"] = [ref for name, ref in sorted(store.files.items()) if name.startswith("tiff/")]
    success = io.finish_terminal(store, "result.json", result, "PASS_QUALITY_INSTRUMENTS_ONLY", check_inputs)
    print(io.canonical_bytes({"status": result["status"], "result": str(store.root / "result.json"),
                             "checks": len(check.rows), "error": result["error"],
                             "finalization_errors": result["finalization_errors"]}).decode(), flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
