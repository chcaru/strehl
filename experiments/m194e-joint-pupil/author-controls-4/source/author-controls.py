"""Predeclared author checks. Independent commissioning is a separate lane."""
from __future__ import annotations

import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
import sys
import shutil
import traceback

import numpy as np

from model import Field, Frame, Scene, Similarity, Wave, evaluate_rays, primary_frames, primary_scene, sha256, strict_json_loads, write_json
from render import Integrator, Meter, NumericalFailure, cosine_radial, render_cell, render_frame, render_point
import render as renderer


HERE = Path(__file__).resolve().parent


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    sources = {p.name: sha256(p) for p in HERE.glob("*.py") if not p.name.startswith("independent")}
    record = dict(schema="m194e-author-controls-v1", started_utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                  sources_before=sources, checks=[], status="running")
    write_json(output / "result.json", record)
    snapshot = output / "source"
    snapshot.mkdir()
    for name in sources:
        shutil.copyfile(HERE / name, snapshot / name)

    def check(name, condition, **evidence):
        item = dict(name=name, pass_=bool(condition), **evidence)
        record["checks"].append(item)
        print(json.dumps(item, allow_nan=False), flush=True)
        write_json(output / "result.json", record)
        if not condition:
            raise AssertionError(name)

    def refuses(name, callback, error=(ValueError, NumericalFailure)):
        try:
            callback()
        except error as exc:
            check(name, True, refusal=str(exc))
        else:
            check(name, False)

    try:
        frame = Frame(0, .75, 12)
        edge = np.array((11., 7.))
        scene = Scene(Field(30), Field(15 - 5 * 11 / 3, (5 / 3, 0)), (1, 2), (1, 0), 11)
        rays = np.array(((-1., 0.), (1., 0.)))
        first = evaluate_rays(scene, frame, edge, rays)
        reverse = evaluate_rays(replace(scene, background=Field(15 + 5 * 11 / 3, (-5 / 3, 0))), frame, edge, rays)
        check("actual-two-ray-covariance", np.max(np.abs(first - [30, 20])) < 1e-10 and np.max(np.abs(reverse - [30, 10])) < 1e-10, first=first.tolist(), reversed=reverse.tolist())
        check("separate-ray-means-destroyer", abs(first.mean() - 22.5) > .004 and abs(reverse.mean() - 22.5) > .004)
        null = evaluate_rays(replace(scene, background=Field(15)), frame, edge, rays)
        check("constant-background-covariance-null", null.mean() == 22.5)
        affine = Scene(Field(12000), Field(10000 - 800 * 11, (800, 0)), (1, 2), (1, 0), 11)
        value, receipt = render_point(affine, frame, edge)
        expected = 11000 + 800 * 3 * 2 / (3 * math.pi)
        check("continuous-half-disc-affine", abs(value - expected) <= 1e-8, actual=value, expected=expected, receipt=receipt)
        check("separate-means-and-unsigned-defocus-destroyers", abs(value - 11000) > .004 and abs(value - (22000 - expected)) > .004)
        check("global-sign-pupil-permutation", np.array_equal(evaluate_rays(affine, frame, edge, rays).sum(), evaluate_rays(affine, frame, edge, -rays).sum()))
        check("layer-order-destroyer", abs(value - affine.background.evaluate(edge)) > .004)
        refuses("unordered-depth-refusal", lambda: replace(scene, depths=(2, 1)))
        check("focus-zero-and-relative-sign", primary_frames()[0].defocus(primary_scene())[1] == 0 and primary_frames()[-1].defocus(primary_scene())[0] == 0 and frame.defocus(scene) == (-3., 3.))

        maximum_dc = 0.
        for dc in (0, 10000, 20000):
            for f in primary_frames():
                for state in ("half-plane", "full", "absent"):
                    item = Scene(Field(dc), Field(dc), (1, 2), (1, -.15), 28.4, state)
                    actual, _ = render_point(item, f, (28.4, 0))
                    maximum_dc = max(maximum_dc, abs(actual - dc))
        check("all-dc-focus-mask-states", maximum_dc <= 1e-8, max_abs_e=maximum_dc)
        p = primary_scene()
        full = replace(p, mask_state="full")
        absent = replace(p, mask_state="absent")
        a = render_point(full, frame, edge)[0]
        b = render_point(replace(full, background=Field(19000)), frame, edge)[0]
        c = render_point(absent, frame, edge)[0]
        d = render_point(replace(absent, foreground=Field(19000)), frame, edge)[0]
        check("hidden-layer-mutation-inert", a == b and c == d)
        first = render_point(p, frame, (32., 24.))[0]
        second = render_point(replace(p, background=Field(19000)), frame, (32., 24.))[0]
        check("visible-texture-mutation-live", abs(first - second) > .004, delta_e=second - first)

        disc = Scene(Field(30), Field(10), (1, 2), (1, 0), 11)
        segment_results = []
        for cut in (0, .3, -.4):
            centre = edge + (3 * cut, 0)
            fraction = 1 - (math.acos(cut) - cut * math.sqrt(1 - cut * cut)) / math.pi
            expected = 10 + 20 * fraction
            value, _ = render_point(disc, frame, centre)
            segment_results.append(dict(cut=cut, value=value, expected=expected))
            check(f"disc-segment-{cut}", abs(value - expected) <= 1e-8, actual=value, expected=expected)
        radii = (np.arange(128) + .5) / 128
        angles = (np.arange(128) + .5) * 2 * np.pi / 128
        uv = radii[:, None, None] * np.stack((np.cos(angles), np.sin(angles)), axis=-1)
        uniform_radius = evaluate_rays(disc, frame, edge + (.9, 0), uv).mean()
        centre_only = float(evaluate_rays(disc, frame, edge + (.9, 0), (0, 0)))
        expected = segment_results[1]["expected"]
        check("uniform-radius-and-pupil-centre-destroyers", abs(uniform_radius - expected) > .004 and abs(centre_only - expected) > .004,
              uniform_radius=float(uniform_radius), pupil_centre=centre_only, expected=expected)

        cellscene = Scene(Field(30), Field(10, (4, 0)), (1, 2), (1, 0), .1)
        pinhole = replace(frame, K=0)
        value, r = render_cell(cellscene, pinhole, (0, 0))
        other, _ = render_cell(replace(cellscene, background=Field(10, (-4, 0))), pinhole, (0, 0))
        check("pinhole-joint-cell-moments", abs(value - 17.52) < 1e-10 and abs(other - 18.48) < 1e-10, values=[value, other], receipt=r)
        centre_only = float(evaluate_rays(cellscene, pinhole, (0, 0), (0, 0)))
        check("cell-centre-and-separate-cell-means-destroyers", abs(value - centre_only) > .004 and abs(value - 18) > .004)
        coarse = []
        for shift in (0., .21):
            xs = (np.arange(4) + .5) / 4 - .5 + shift / 4
            grid = np.stack(np.meshgrid(xs, xs), axis=-1)
            coarse.append(float(evaluate_rays(cellscene, pinhole, grid, (0, 0)).mean()))
        check("shifted-coarse-cell-grid-diagnostic", max(abs(x - 17.52) for x in coarse) > .004, coarse=coarse)

        sim = Similarity(1.13, .19, (3, -2), (.7, -.4))
        transformed = replace(frame, forward_similarity=sim)
        q0 = sim.inverse(edge)
        normal = np.array((.8, .6))
        gradient = np.array((300., -170.))
        mapped = Scene(Field(12000), Field(10000 - gradient @ q0, tuple(gradient)), (1, 2), tuple(normal), float(normal @ q0))
        native_n = sim.inverse_matrix().T @ normal
        native_n /= np.linalg.norm(native_n)
        mapped_expected = 11000 + 3 * (gradient @ sim.inverse_matrix() @ native_n) * 2 / (3 * np.pi)
        mapped_value, _ = render_point(mapped, transformed, edge)
        wrong_chief = 11000 + 3 * (gradient @ normal) * 2 / (3 * np.pi)
        check("inverse-similarity-pupil-and-cell-coordinate-contract", abs(mapped_value - mapped_expected) < 1e-8 and abs(mapped_value - wrong_chief) > .004,
              actual=mapped_value, expected=float(mapped_expected), chief_only=float(wrong_chief))
        wrong_inverse = replace(transformed, forward_similarity=Similarity(1 / 1.13, -.19, (3, -2), (-.7, .4)))
        wrong_value, _ = render_point(mapped, wrong_inverse, edge)
        check("forward-inverse-swap-destroyer", abs(mapped_value - wrong_value) > .004, wrong=wrong_value)

        # Amendment1's fixed formerly-refusing cell. This is an author regression
        # and causal ablation, not a replacement for the independent value check.
        centre = np.array((37.23, 24.61))
        normal = np.array((12 / 13, 5 / 13))
        a, theta = 1 / 1.037, -.071
        forward_matrix = a * np.array(((math.cos(theta), -math.sin(theta)), (math.sin(theta), math.cos(theta))))
        translation = -forward_matrix @ np.array((.31, -.27))
        formerly_refused = Scene(Field(12000), Field(10000 - 800 * normal @ centre, tuple(800 * normal)), (1.25, 2.5), tuple(normal), float(normal @ centre))
        formerly_frame = Frame(0, .53, 11, Similarity(a, theta, tuple(centre), tuple(translation)))
        revised_value, revised_receipt = render_cell(formerly_refused, formerly_frame, centre)
        check("amended-fixed-cell-returns-with-registered-indicator", np.isfinite(revised_value) and revised_receipt["value_error_indicator_e"] <= .001,
              value_e=revised_value, receipt=revised_receipt)
        original_cuts = renderer.angular_cuts
        try:
            renderer.angular_cuts = lambda h, r, alpha, state: original_cuts(h, r, alpha, state, include_ladder=False)
            refuses("same-height-without-ladder-retains-refusal", lambda: render_cell(formerly_refused, formerly_frame, centre), NumericalFailure)
        finally:
            renderer.angular_cuts = original_cuts

        nodes, weights = np.polynomial.legendre.leggauss(96)
        max_primitive = 0.
        for beta in (0., 1e-8, -1e-8, .01, -.01, .3, -.3, 3., -3., 9., -9.):
            for lo, hi in ((0., 1.), (.17, .81), (.5, .5)):
                r = (lo + hi) / 2 + (hi - lo) / 2 * nodes
                expected = (hi - lo) / 2 * np.dot(weights, 20000 * r * np.cos(.37 + beta * r))
                actual = 20000 * float(cosine_radial(.37, beta, lo, hi))
                max_primitive = max(max_primitive, abs(actual - expected))
                check(f"radial-primitive-{beta}-{lo}", abs(actual - expected) <= 1e-8, abs_error_e=abs(actual - expected))
        correct = 20000 * float(cosine_radial(.37, 0., 0., 1.))
        check("missing-radial-Jacobian-destroyer", abs(correct - 20000 * math.cos(.37)) > .004)

        legacy_path = HERE / "author-controls-3" / "source" / "render.py"
        check("zero-width-reference-source-bound", sha256(legacy_path) == "84790fb4b963ae863f21248108402fe077a21584868eeca53a06a16c8f0a75ff")
        spec = importlib.util.spec_from_file_location("m194e_pre_zero_width", legacy_path)
        old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = old
        spec.loader.exec_module(old)
        raw_comparisons = 0
        for scalar_case in (True, False):
            q = np.array((.2, -.7)) if scalar_case else np.array((((.2, -.7),), ((.9, .1),)))
            d = np.array((-.3, .4)) if scalar_case else np.array((((-.3, .4), (.5, -.6), (.1, .8)),))
            for lower in (0., .17, 1.):
                for dc in (12000., -12000., -0.):
                    rad = Field(dc, (31., -47.), (Wave(-1400, (.17, -.23), -1.7), Wave(900, (-.3, .7), 2.9)))
                    for displacement in (-3., 0., 2.):
                        original = old.field_radial(rad, q, d, displacement, lower, lower, old.Meter(old.Integrator()))
                        revised = renderer.field_radial(rad, q, d, displacement, lower, lower, Meter(Integrator()))
                        check(f"zero-width-bit-null-{raw_comparisons}", np.asarray(original).tobytes() == np.asarray(revised).tobytes(), shape=list(np.shape(revised)))
                        raw_comparisons += 1

        refuses("invalid-pupil-refusal", lambda: evaluate_rays(scene, frame, edge, (1.1, 0)))
        refuses("invalid-negative-scale-refusal", lambda: Similarity(-1))
        refuses("duplicate-json-refusal", lambda: strict_json_loads('{"x":1,"x":2}'))
        refuses("nonfinite-json-refusal", lambda: strict_json_loads('{"x":NaN}'))
        refuses("point-work-limit-refusal", lambda: render_cell(p, frame, (32, 24), replace(Integrator(), point_limit=1)))
        refuses("angular-work-limit-refusal", lambda: render_point(p, frame, (32, 24), replace(Integrator(), angular_limit=1)))
        expired_cpu = Meter(Integrator())
        expired_cpu.started_cpu -= 601
        refuses("expired-own-cpu-limit-refusal", lambda: render_point(p, frame, (32, 24), meter=expired_cpu))
        expired_wall = Meter(Integrator())
        expired_wall.started_wall -= 1201
        refuses("expired-own-wall-limit-refusal", lambda: render_point(p, frame, (32, 24), meter=expired_wall))
        refuses("array-byte-limit-refusal", lambda: render_point(p, frame, (32, 24), replace(Integrator(), array_limit=1)))
        refuses("depth-error-limit-refusal", lambda: render_point(p, frame, (32, 24), replace(Integrator(), angle_low=1, angle_high=2, angle_depth=0)))

        # Small live fixture exercises frame lifetime and optional event observer
        # before the declared complete frame commission; no quality claim.
        small_sensor = dict(width=3, height=2)
        hashes, events, hooks, peaks = [], [], [], []
        smallscene = replace(p, mask_offset=.7)
        for mode, tile in (("off", 8), ("count", 8), ("placebo", 8), ("count", 16)):
            dest = output / f"observer-{mode}-{tile}"
            meter = Meter(Integrator(), mode)
            result = render_frame(smallscene, frame, small_sensor, Integrator(), dest, meter=meter, tile=tile)
            hashes.append(result["expected_scalar"]["sha256"])
            events.append(meter.observer_events)
            hooks.append(meter.optional_hook_calls)
            peaks.append(meter.peak_frames)
        check("actual-frame-observer-tile-byte-null", len(set(hashes)) == 1 and events[0] == events[2] == 0 and events[1] > 0 and hooks[0] == 0 and hooks[1] > 0 and hooks[2] > 0,
              sha256=hashes, events=events, hook_calls=hooks, peak_live_frames=peaks)
        meter = Meter(Integrator())
        reordered = []
        for i in (2, 0, 1):
            item = render_frame(smallscene, primary_frames()[i], small_sensor, Integrator(), output / f"order-{i}", meter=meter)
            reordered.append((i, item["expected_scalar"]["sha256"]))
        ordered = []
        for i in (0, 1, 2):
            item = render_frame(smallscene, primary_frames()[i], small_sensor, Integrator(), output / f"ordered-{i}", meter=meter)
            ordered.append((i, item["expected_scalar"]["sha256"]))
        check("frame-enumeration-byte-null-and-lifetime", sorted(reordered) == ordered and meter.peak_frames == 1, peak_live_frames=meter.peak_frames)
        check("frame-focus-live", len({value for _, value in ordered}) > 1)
        extra = HERE / "emit-cfa.py"
        if extra.exists():
            spec = importlib.util.spec_from_file_location("m194e_emit", extra)
            emitter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(emitter)
            emitter.author_conversion_controls(check, refuses)
        record["status"] = "PASS"
    except Exception as exc:
        record["status"] = "INSTRUMENT_INVALID"
        record["error"] = repr(exc)
        record["traceback"] = traceback.format_exc()
        traceback.print_exc()
    record["sources_after"] = {name: sha256(HERE / name) for name in sources}
    if record["sources_before"] != record["sources_after"]:
        record["status"] = "INSTRUMENT_INVALID"
        record["source_changed"] = True
    record["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "result.json", record)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output))
