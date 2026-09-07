"""Independent prospective M193b verification, never a RAW/candidate run.

Choice points registered before reading the prospective implementation:
* A matching self-hash is not authority. Alter a denominator alone and jointly
  alter transforms, uncertainty, and the rectangle; re-hash and rebind the
  candidate descriptor while retaining the external input-constructor binding.
* Re-choose the texture, aspect ratio, and similarity; count retained lattice
  sites directly rather than importing the consumer's interval reduction.
* Preserve the frozen v1 identity PASS and cropped FAIL as live controls.
* Test duplicate paths, duplicate bytes at a different path, order, metadata-
  distinct bytes, and changed pixels. Input binding is about exact input bytes.
* Reject unknown schemas/fields, absent trust, foreign inputs/references,
  bool/float integer impostors, malformed/duplicate-key/nonfinite JSON.
* Observe actual decoded-array lifetimes through weakrefs while holding only
  registration constant in both arms. A fake registrar is not coverage evidence.
  Compare v1's N retention to bounded construction, not estimated/native RSS.

No production adapter, deep-focus coverage, or scorecard closure is tested.
"""
from __future__ import annotations

import copy
import gc
import hashlib
import importlib.util
import io
import json
import math
import shutil
import sys
import uuid
import weakref
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import tifffile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / "experiments/M193-cover-overlap"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def workspace_directory():
    # Normal workspace ACL inheritance; M192 found private tempfile directories
    # inaccessible to this host's restricted Windows token.
    path = HERE / ("independent-inputs-"+uuid.uuid4().hex)
    path.mkdir()
    try:
        yield path
    finally:
        assert path.resolve().parent == HERE.resolve()
        assert path.name.startswith("independent-inputs-")
        shutil.rmtree(path)


def reseal(manifest):
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    data = (json.dumps(body, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n").encode()
    manifest["manifest_sha256"] = sha(data)
    return manifest


def descriptor_for(v1, manifest, *, crop=False):
    return v1.make_output_grid(
        manifest, arm_id="independent-crop" if crop else "independent-identity",
        expected_width=manifest["native_width"] - (12 if crop else 0),
        expected_height=manifest["native_height"] - (10 if crop else 0),
        derivation_kind="predeclared_program_grid" if crop else "identity_reference_grid",
    )


def brute_retained(manifest, descriptor):
    """Direct integer site membership, independent of interval construction."""
    box = manifest["common_overlap"]
    q, xy = 1 << 32, 256
    m = descriptor["common_to_output_q32"]
    guard = descriptor["valid_center_guard_q8"]
    lower = guard*q
    xmax = ((descriptor["expected_width"]-1)*xy-guard)*q
    ymax = ((descriptor["expected_height"]-1)*xy-guard)*q
    count = 0
    for y in range(box["y"], box["y"]+box["height"]):
        for x in range(box["x"], box["x"]+box["width"]):
            mapped_x = xy*(m["a"]*x-m["b"]*y+m["tx"])
            mapped_y = xy*(m["b"]*x+m["a"]*y+m["ty"])
            count += lower <= mapped_x <= xmax and lower <= mapped_y <= ymax
    return count, box["width"]*box["height"]


def brute_overlap_rectangle(manifest):
    """Per-site exact inverse tests, then a histogram-stack maximum rectangle.

    This uses neither the v1 interval code nor its top/bottom rectangle search.
    """
    w, h, q = manifest["native_width"], manifest["native_height"], 1 << 32
    heights = [0]*w
    best, best_box = None, None
    for y in range(h):
        for x in range(w):
            inside = True
            for source in manifest["sources"]:
                m, guard = source["source_to_reference_q32"], source["valid_center_guard_q8"]
                determinant = m["a"]**2 + m["b"]**2
                u, v = x*q-m["tx"], y*q-m["ty"]
                source_x = 256*(m["a"]*u+m["b"]*v)
                source_y = 256*(-m["b"]*u+m["a"]*v)
                inside &= (guard*determinant <= source_x <= ((w-1)*256-guard)*determinant
                           and guard*determinant <= source_y <= ((h-1)*256-guard)*determinant)
            heights[x] = heights[x]+1 if inside else 0
        stack = []
        for x in range(w+1):
            current, start = (heights[x] if x < w else 0), x
            while stack and stack[-1][1] > current:
                left, height = stack.pop()
                width, top = x-left, y-height+1
                key = (-width*height,top,left,-height,-width)
                if best is None or key < best:
                    best = key
                    best_box = dict(x=left,y=top,width=width,height=height,area_pixels=width*height)
                start = left
            if current and (not stack or stack[-1][1] < current):
                stack.append((start,current))
    assert best_box is not None
    return best_box


def alternate_texture():
    """Independent seed, non-square extent, and blob arrangement."""
    rng = np.random.default_rng(761839)
    h, w = 232, 328
    noise = rng.integers(2000, 56000, (h, w, 3), dtype=np.uint16)
    result = cv2.GaussianBlur(noise, (3, 3), .65)
    for _ in range(64):
        x, y = rng.integers(9, w-9), rng.integers(9, h-9)
        radius = int(rng.integers(2, 9))
        colour = tuple(int(v) for v in rng.integers(1000, 64000, 3))
        cv2.circle(result, (int(x), int(y)), radius, colour, -1)
    angle = math.radians(-.18)
    a, b = 1.007*math.cos(angle), 1.007*math.sin(angle)
    # Explicit origin-based similarity differs from the frozen centre rotation.
    matrix = np.array([[a, -b, -2.75], [b, a, 1.625]], dtype=np.float64)
    warped = cv2.warpAffine(result, matrix, (w,h), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
    return [result, warped]


def write_tiff(path, pixels, description=None):
    tifffile.imwrite(path, pixels, photometric="rgb", compression=None,
                     metadata=None, byteorder="<", description=description)


def mutation_cases(manifest):
    """Every callable is applied to a fresh valid manifest then independently sealed."""
    def smaller(m):
        box = m["common_overlap"]
        box.update(x=box["x"]+2, y=box["y"]+2, width=20, height=20, area_pixels=400)
    def wrong_area(m): m["common_overlap"]["area_pixels"] -= 1
    def foreign_input(m): m["input_bundle_sha256"] = "e"*64
    def foreign_reference(m): m["reference_source_sha256"] = "d"*64
    def coherent_geometry(m):
        for source in m["sources"]:
            if not source["reference"]:
                source["source_to_reference_q32"]["tx"] += 3*(1 << 32)
                source["valid_center_guard_q8"] += 16
                source["registration"]["heldout_max_source_px_ceil_q8"] += 16
                source["registration"]["valid_support_continuous_margin_q8"] += 16
        # The final rectangle is recalculated by the runner after this mutation.
    return {
        "smaller_but_in_bounds": smaller,
        "area_disagrees": wrong_area,
        "foreign_input_bundle": foreign_input,
        "foreign_reference": foreign_reference,
        "coherent_geometry_uncertainty_rectangle": coherent_geometry,
        "unknown_schema": lambda m: m.update(schema="strehl.m193-cover-overlap.unknown"),
        "unknown_field": lambda m: m.update(candidate_override=True),
        "missing_sources": lambda m: m.pop("sources"),
        "bool_native_width": lambda m: m.update(native_width=True),
        "float_native_width": lambda m: m.update(native_width=float(m["native_width"])),
        "bool_rectangle_x": lambda m: m["common_overlap"].update(x=True),
        "float_rectangle_width": lambda m: m["common_overlap"].update(width=float(m["common_overlap"]["width"])),
        "negative_rectangle_x": lambda m: m["common_overlap"].update(x=-1),
        "zero_rectangle_width": lambda m: m["common_overlap"].update(width=0, area_pixels=0),
        "outside_rectangle": lambda m: m["common_overlap"].update(x=m["native_width"]+1),
        "bool_source_multiplicity": lambda m: m["sources"][0].update(multiplicity=True),
        "float_source_transform": lambda m: m["sources"][0]["source_to_reference_q32"].update(a=float(1 << 32)),
        "bool_source_guard": lambda m: m["sources"][0].update(valid_center_guard_q8=False),
        "bool_registration_count": lambda m: m["sources"][-1]["registration"].update(holdout_count=True),
        "nonfinite_registration_residual": lambda m: m["sources"][-1]["registration"].update(heldout_rms_reference_px="NaN"),
    }


def verify_retention(v1, consumer, manifest, binding, descriptor):
    observed = consumer.output_retention(manifest, descriptor, binding)
    numerator, denominator = brute_retained(manifest, descriptor)
    assert (observed["retained_pixels"], observed["denominator_pixels"]) == (numerator, denominator)
    expected = "PASS" if numerator*1000 >= denominator*990 else "FAIL_GEOMETRY_FIELD_OF_VIEW"
    assert observed["field_of_view_verdict"] == expected
    return observed


def expect_refusal(name, fn, results):
    try:
        fn()
    except Exception as error:
        code = getattr(error, "code", None)
        results.append({"name": name, "rejected": True, "code": code, "exception": type(error).__name__})
        assert isinstance(code, str) and code.startswith(("UNMEASURED_", "FAIL_")), (name, "unnamed crash", repr(error))
        return
    results.append({"name": name, "rejected": False})
    raise AssertionError(f"accepted adversarial input: {name}")


def registration_stub(v1):
    def fake(*args):
        return v1.IDENTITY_Q32, {
            "mutual_match_count": 32, "calibration_count": 16, "calibration_inlier_count": 16,
            "holdout_count": 16, "holdout_inlier_count": 16, "heldout_rms_reference_px": "0.000000000",
            "heldout_max_source_px_ceil_q8": 0, "coordinate_quantization_guard_q8": 1,
            "valid_support_continuous_margin_q8": 129,
        }, 1
    return fake


def lifetime_comparison(v1, consumer, directory):
    """Actual decodes and loops, fake registration in both arms; no RSS claim."""
    pixels = np.full((144,208,3), 13001, dtype=np.uint16)
    paths = []
    for index in range(12):
        path = directory / f"lifetime-{index:02d}.tiff"
        write_tiff(path, pixels, description=f"independent input {index:02d}")
        paths.append(path)
    assert len({sha(p.read_bytes()) for p in paths}) == 12
    payload = int(pixels.nbytes)
    del pixels
    observations = {}
    for arm in ("v1_retained", "prospective_bounded"):
        refs, peak = [], [0]
        decode = v1.decode_input_tiff if arm == "v1_retained" else consumer.decode_input_path
        def observe(*args, **kwargs):
            array = decode(*args, **kwargs)
            refs.append(weakref.ref(array))
            peak[0] = max(peak[0], sum(ref() is not None for ref in refs))
            return array
        target, symbol = (v1, "decode_input_tiff") if arm == "v1_retained" else (consumer, "decode_input_path")
        with patch.object(target, symbol, observe), patch.object(target, "extract_features", lambda image: object()), patch.object(target, "register_to_reference", registration_stub(v1)):
            if arm == "v1_retained":
                manifest = v1.construct_overlap([p.read_bytes() for p in paths])
            else:
                manifest, binding = consumer.construct_overlap_paths(paths)
                consumer.validate_overlap(manifest, binding)
        gc.collect()
        assert len(refs) == 12 and not any(ref() is not None for ref in refs)
        observations[arm] = {"decoded_count": len(refs), "peak_live_decoded_arrays": peak[0],
                             "peak_live_decoded_payload_bytes": peak[0]*payload,
                             "live_arrays_after_return": 0, "manifest_sha256": manifest["manifest_sha256"]}
    assert observations["v1_retained"]["peak_live_decoded_arrays"] == 12
    assert observations["prospective_bounded"]["peak_live_decoded_arrays"] == 1
    assert observations["v1_retained"]["manifest_sha256"] == observations["prospective_bounded"]["manifest_sha256"]
    return observations


def main():
    v1 = load_module("independent_m193_v1", FROZEN / "reference.py")
    consumer_before = sha((HERE / "consumer.py").read_bytes())
    consumer = load_module("independent_m193b_consumer", HERE / "consumer.py")
    frozen_paths = [FROZEN / name for name in ("reference.py", "fixtures.json", "contract-v1.json")]
    before = {p.name: sha(p.read_bytes()) for p in frozen_paths}
    assert before["reference.py"] == "c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790"
    fixtures = json.loads((FROZEN / "fixtures.json").read_text())
    rejections, controls = [], {}
    # Workspace temporary files only; deletion checks its resolved exact parent.
    with workspace_directory() as scratch:
        directory = Path(scratch)
        assert directory.resolve().parent == HERE.resolve()
        base = v1.synthetic_rgb()
        frames = [base, v1.warp_synthetic(base, scale=.985, rotation_degrees=.35, tx=3.25, ty=-2.5),
                  v1.warp_synthetic(base, scale=1.018, rotation_degrees=-.25, tx=-4., ty=3.)]
        paths = []
        for index, frame in enumerate(frames):
            path = directory / f"frozen-{index}.tiff"
            path.write_bytes(v1.encode_tiff(frame))
            paths.append(path)
        manifest, binding = consumer.construct_overlap_paths(paths)
        assert manifest == fixtures["synthetic_overlap"], "prospective constructor changes frozen supported result"
        assert brute_overlap_rectangle(manifest) == manifest["common_overlap"]
        controls["frozen_identity"] = verify_retention(v1, consumer, manifest, binding, descriptor_for(v1, manifest))
        controls["frozen_crop"] = verify_retention(v1, consumer, manifest, binding, descriptor_for(v1, manifest, crop=True))
        assert controls["frozen_identity"]["field_of_view_verdict"] == "PASS"
        assert controls["frozen_crop"]["field_of_view_verdict"] == "FAIL_GEOMETRY_FIELD_OF_VIEW"
        assert controls["frozen_crop"]["retained_pixels"] == 97188
        # Power control: this exact stale corruption fools the old consumer.
        stale = copy.deepcopy(manifest)
        mutation_cases(manifest)["smaller_but_in_bounds"](stale)
        old_result = v1.output_retention(stale, descriptor_for(v1, manifest, crop=True))
        assert old_result["field_of_view_verdict"] == "PASS"
        controls["v1_stale_denominator_false_pass"] = old_result
        expect_refusal("stale_smaller_rectangle", lambda: consumer.output_retention(stale, descriptor_for(v1, manifest, crop=True), binding), rejections)
        for name, mutate in mutation_cases(manifest).items():
            altered = copy.deepcopy(manifest)
            mutate(altered)
            if name == "coherent_geometry_uncertainty_rectangle":
                altered["common_overlap"] = brute_overlap_rectangle(altered)
                assert altered["common_overlap"] != manifest["common_overlap"]
            reseal(altered)
            desc = descriptor_for(v1, manifest, crop=True)
            desc["overlap_manifest_sha256"] = altered["manifest_sha256"]
            desc["input_bundle_sha256"] = altered["input_bundle_sha256"]
            expect_refusal("rehashed_"+name, lambda a=altered,d=desc: consumer.output_retention(a,d,binding), rejections)
        expect_refusal("absent_binding", lambda: consumer.output_retention(manifest, descriptor_for(v1, manifest), None), rejections)
        expect_refusal("dictionary_binding", lambda: consumer.output_retention(manifest, descriptor_for(v1, manifest), {"manifest_sha256": manifest["manifest_sha256"]}), rejections)
        saved = copy.deepcopy(manifest)
        validated = consumer.validate_overlap(manifest,binding)
        validated["common_overlap"]["width"] = 1
        assert manifest == saved
        controls["binding_survives_returned_snapshot_mutation"] = verify_retention(v1,consumer,manifest,binding,descriptor_for(v1,manifest))
        # JSON failures are tested before parsing can erase their evidence.
        encoded = json.dumps(manifest)
        bad_json = {"truncated": encoded[:-2], "duplicate_key": encoded[:-1]+', "native_width": 1}',
                    "NaN": '{"value":NaN}', "Infinity": '{"value":Infinity}', "root_list": '[]',
                    "invalid_utf8": b'{"value":"\xff"}'}
        for name, content in bad_json.items():
            expect_refusal("json_"+name, lambda c=content: consumer.strict_json_loads(c), rejections)
        assert consumer.strict_json_loads(encoded) == manifest
        descriptor_mutations = {
            "bool_width": lambda d: d.update(expected_width=True),
            "float_width": lambda d: d.update(expected_width=float(d["expected_width"])),
            "bool_guard": lambda d: d.update(valid_center_guard_q8=False),
            "bool_translation": lambda d: d["common_to_output_q32"].update(tx=False),
            "float_residual": lambda d: d.update(input_only_landmark_residual_micropixel_ceil=0.0),
            "unknown_schema": lambda d: d.update(schema="future-grid"),
            "unknown_field": lambda d: d.update(candidate_override=True),
            "list_derivation_kind": lambda d: d.update(derivation_kind=[]),
            "bool_arm_id": lambda d: d.update(arm_id=True),
            "singular_transform": lambda d: d["common_to_output_q32"].update(a=0,b=0),
            "negative_residual": lambda d: d.update(input_only_landmark_residual_micropixel_ceil=-1),
        }
        for name, mutate in descriptor_mutations.items():
            desc = descriptor_for(v1,manifest)
            mutate(desc)
            expect_refusal("descriptor_"+name,lambda d=desc:consumer.output_retention(manifest,d,binding),rejections)
        reversed_manifest, reverse_binding = consumer.construct_overlap_paths(list(reversed(paths)))
        assert reversed_manifest == manifest
        controls["order_invariant"] = True
        # Duplicates and a single changed pixel use one unique source, so their
        # binding checks do not depend on another SIFT fit being accepted.
        single, single_binding = consumer.construct_overlap_paths([paths[0]])
        copied = directory / "byte-identical-copy.tiff"
        copied.write_bytes(paths[0].read_bytes())
        duplicate, duplicate_binding = consumer.construct_overlap_paths([paths[0],copied,paths[0]])
        assert duplicate["unique_input_count"] == 1 and duplicate["input_count"] == 3
        assert duplicate["sources"][0]["multiplicity"] == 3
        assert duplicate["input_bundle_sha256"] == v1.bundle_hash([paths[0].read_bytes()]*3)
        assert duplicate["input_bundle_sha256"] != single["input_bundle_sha256"]
        expect_refusal("foreign_multiplicity_binding",lambda:consumer.output_retention(single,descriptor_for(v1,single),duplicate_binding),rejections)
        changed = base.copy()
        changed[41,27,1] ^= np.uint16(1)
        changed_path = directory / "one-pixel-changed.tiff"
        write_tiff(changed_path,changed)
        different, different_binding = consumer.construct_overlap_paths([changed_path])
        assert different["input_bundle_sha256"] != single["input_bundle_sha256"]
        assert different["reference_source_sha256"] != single["reference_source_sha256"]
        expect_refusal("foreign_content_binding",lambda:consumer.output_retention(single,descriptor_for(v1,single),different_binding),rejections)
        controls["duplicate_and_changed_content"] = {"single":single["input_bundle_sha256"],"triplicate":duplicate["input_bundle_sha256"],"one_pixel_changed":different["input_bundle_sha256"]}
        alternate_paths = []
        for i, frame in enumerate(alternate_texture()):
            p=directory/f"alternate-{i}.tiff"
            write_tiff(p,frame)
            alternate_paths.append(p)
        alternate, alternate_binding = consumer.construct_overlap_paths(alternate_paths)
        assert brute_overlap_rectangle(alternate) == alternate["common_overlap"]
        controls["alternate_identity"] = verify_retention(v1,consumer,alternate,alternate_binding,descriptor_for(v1,alternate))
        alt_desc = descriptor_for(v1,alternate,crop=True)
        alt_desc["common_to_output_q32"]["tx"] = 3*(1 << 30)
        alt_desc["common_to_output_q32"]["ty"] = -(1 << 30)
        controls["alternate_fractional_map_crop"] = verify_retention(v1,consumer,alternate,alternate_binding,alt_desc)
        controls["alternate_registration"] = {"input_hashes":[sha(p.read_bytes()) for p in alternate_paths],"overlap":alternate["common_overlap"],"sources":alternate["sources"]}
        assert controls["alternate_identity"]["field_of_view_verdict"] == "PASS"
        assert controls["alternate_fractional_map_crop"]["field_of_view_verdict"] == "FAIL_GEOMETRY_FIELD_OF_VIEW"
        # Regression of the previous takeover challenge, not new coverage data.
        rng = np.random.default_rng(731943)
        texture = cv2.GaussianBlur(rng.uniform(3000,62000,(288,384)).astype(np.float32),(0,0),.7)
        defocused = cv2.GaussianBlur(texture,(0,0),12.)
        left, right = defocused.copy(), defocused.copy()
        left[:,:184], right[:,200:] = texture[:,:184], texture[:,200:]
        rgb = lambda a: np.repeat(np.clip(np.rint(a),0,65535).astype(np.uint16)[...,None],3,axis=2)
        focus_frames = [rgb(left),rgb(right)]
        focus_paths = []
        for i, frame in enumerate(focus_frames):
            p=directory/f"complementary-focus-{i}.tiff"
            write_tiff(p,frame)
            focus_paths.append(p)
        reference_features = v1.extract_features(focus_frames[0])
        matched = v1.register_to_reference(reference_features,reference_features)[1]
        assert matched["mutual_match_count"] == 256 and matched["heldout_rms_reference_px"] == "0.000000000"
        controls["matched_focus_feature_control"] = matched
        expect_refusal("v1_complementary_focus",lambda:v1.construct_overlap([p.read_bytes() for p in focus_paths]),rejections)
        expect_refusal("prospective_complementary_focus",lambda:consumer.construct_overlap_paths(focus_paths),rejections)
        compressed = directory / "unsupported-compressed.tiff"
        tifffile.imwrite(compressed,base,photometric="rgb",compression="deflate",metadata=None)
        expect_refusal("v1_compressed_tiff",lambda:v1.construct_overlap([compressed.read_bytes()]),rejections)
        expect_refusal("prospective_compressed_tiff",lambda:consumer.construct_overlap_paths([compressed]),rejections)
        lifetimes = lifetime_comparison(v1,consumer,directory)
    assert before == {p.name:sha(p.read_bytes()) for p in frozen_paths}
    assert consumer_before == sha((HERE / "consumer.py").read_bytes()), "consumer changed during verification"
    result = {"status":"VERIFIED_SCOPED_CONSUMER_AND_BOUNDED_DECODE_LIFETIME", "controls":controls,
              "rejections":rejections, "decoded_lifetimes":lifetimes, "frozen_v1_unchanged":True,
              "source_sha256":{**before,"consumer.py":sha((HERE/"consumer.py").read_bytes()),"independent-verify.py":sha(Path(__file__).read_bytes())},
              "scope":"Synthetic and structural consumer verification; no real adapters, deep-focus coverage, RAW or scorecard closure."}
    (HERE/"independent-verification.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"rejection_count":len(rejections),"decoded_lifetimes":lifetimes,"source_sha256":result["source_sha256"]},indent=2))


if __name__ == "__main__":
    main()
