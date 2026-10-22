"""Adversarial export-contract tests; synthetic pixels, no private photographs.

Run: python experiments/adaptive-distillation/test-native-reference.py
The generated ICC is LittleCMS's public sRGB profile, selected explicitly in
tests. No Adobe profile or model asset is embedded in these fixtures.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
import xml.etree.ElementTree as ET

import numpy as np
from PIL import ImageCms
import tifffile


SPEC = importlib.util.spec_from_file_location("native_reference", Path(__file__).with_name("validate-native-reference.py"))
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
ICC = PROFILE.tobytes()
PROFILE_NAME = ImageCms.getProfileDescription(PROFILE).strip()


def metadata(role):
    root = ET.Element("xmpmeta")
    rdf = ET.SubElement(root, f"{{{V.RDF}}}RDF")
    base = ET.SubElement(rdf, f"{{{V.RDF}}}Description")
    controls = {name: "0" for name in V.REQUIRED_CONTROLS}
    controls.update(RawFileName="capture.raw", Version="1", ProcessVersion="1",
                    CameraProfile="test base", WhiteBalance="As Shot", Temperature="5000",
                    Tint="2", Sharpness="40", SharpenRadius="1", ColorNoiseReduction="25",
                    CropBottom="1", CropRight="1", HasCrop="False", AlreadyApplied="True")
    base.attrib.update({f"{{{V.CRS}}}{key}": value for key, value in controls.items()})
    base.set(f"{{{V.XMP}}}CreatorTool", "Adobe Lightroom synthetic fixture")
    base.set(f"{{{V.XMP_MM}}}OriginalDocumentID", "fixture-source-identity")
    tone = ET.SubElement(base, f"{{{V.CRS}}}ToneCurvePV2012")
    seq = ET.SubElement(tone, f"{{{V.RDF}}}Seq")
    ET.SubElement(seq, f"{{{V.RDF}}}li").text = "0, 0"
    ET.SubElement(seq, f"{{{V.RDF}}}li").text = "255, 255"
    look_node = ET.SubElement(base, f"{{{V.CRS}}}Look")
    look = ET.SubElement(look_node, f"{{{V.RDF}}}Description")
    look.set(f"{{{V.CRS}}}Name", "Adobe Color" if role == "baseline" else "Adaptive Color")
    look.set(f"{{{V.CRS}}}Amount", "0" if role == "adaptive_zero" else "1")
    look.set(f"{{{V.CRS}}}UUID", "baseline-profile" if role == "baseline" else "adaptive-profile")
    if role != "baseline":
        ai = ET.SubElement(base, f"{{{V.CRS}}}AILook")
        ai.set(f"{{{V.CRS}}}Active", "true")
        for name in V.AI_FIELDS:
            ai.set(f"{{{V.CRS}}}{name}", "synthetic-" + name)
    return root


def base_node(root):
    return root.find(".//rdf:Description", V.NS)


def set_control(root, key, value):
    base_node(root).set(f"{{{V.CRS}}}{key}", value)


def write_fixture(path, role, *, mutate=None, pixels=None, icc=ICC, xmp=True, orientation=1):
    root = metadata(role)
    if mutate:
        mutate(root)
    if pixels is None:
        value = {"baseline": 2000, "adaptive": 5000, "adaptive_zero": 2500}[role]
        pixels = np.full((12, 16, 3), value, dtype=np.uint16)
    tags = [(274, "H", 1, orientation, False)]
    if icc is not None:
        tags.append((34675, "B", len(icc), icc, False))
    if xmp is not False:
        data = ET.tostring(root) if xmp is True else xmp
        tags.append((700, "B", len(data), data, False))
    tifffile.imwrite(path, pixels, photometric="rgb", metadata=None, extratags=tags)


class NativeReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = {role: self.root / f"{role}.tif" for role in ("baseline", "adaptive", "adaptive_zero")}
        for role, path in self.paths.items():
            write_fixture(path, role)

    def validate(self, **kwargs):
        return V.validate_reference(**self.paths, expected_profile=PROFILE_NAME, **kwargs)

    def test_valid_three_arms_preserve_files_and_record_distinct_looks(self):
        before = {key: V.sha256_file(path) for key, path in self.paths.items()}
        result = self.validate()
        self.assertEqual(result["status"], "reference_contract_verified")
        self.assertEqual(result["arms"]["adaptive_zero"]["metadata"]["look"]["Amount"], "0")
        self.assertEqual(result["arms"]["baseline"]["metadata"]["look"]["Name"], "Adobe Color")
        self.assertEqual(result["arms"]["adaptive"]["metadata"]["look"]["Amount"], "1")
        self.assertNotEqual(result["arms"]["baseline"]["pixel_sha256_le_u16_yxc"], result["arms"]["adaptive_zero"]["pixel_sha256_le_u16_yxc"])
        self.assertEqual(before, {key: V.sha256_file(path) for key, path in self.paths.items()})

    def test_equal_zero_and_adobe_color_is_allowed_but_not_assumed(self):
        write_fixture(self.paths["adaptive_zero"], "adaptive_zero", pixels=np.full((12, 16, 3), 2000, np.uint16))
        self.validate()

    def test_identity_negative_controls(self):
        for role, value in (("baseline", 5000), ("adaptive_zero", 5000)):
            with self.subTest(role=role):
                write_fixture(self.paths[role], role, pixels=np.full((12, 16, 3), value, np.uint16))
                with self.assertRaisesRegex(V.ValidationError, "identical decoded pixels"):
                    self.validate()
                write_fixture(self.paths[role], role)

    def test_geometry_dtype_and_orientation_sabotage(self):
        cases = [({"pixels": np.ones((12, 17, 3), np.uint16)}, "geometry mismatch"),
                 ({"pixels": np.ones((12, 16, 3), np.uint8)}, "uint16"),
                 ({"orientation": 6}, "orientation")]
        for args, error in cases:
            with self.subTest(error=error):
                write_fixture(self.paths["adaptive"], "adaptive", **args)
                with self.assertRaisesRegex(V.ValidationError, error):
                    self.validate()

    def test_icc_sabotage(self):
        changed_icc = bytearray(ICC)
        changed_icc[84] ^= 1  # Valid ICC header profile-ID bytes; exact identity must still fail.
        cases = [(None, "missing ICC"), (b"not-an-icc", "ICC length"),
                 (bytes(changed_icc), "ICC bytes mismatch")]
        for profile, error in cases:
            with self.subTest(error=error):
                write_fixture(self.paths["adaptive"], "adaptive", icc=profile)
                with self.assertRaisesRegex(V.ValidationError, error):
                    self.validate()

    def test_declared_color_space_must_match_requested_profile(self):
        with self.assertRaisesRegex(V.ValidationError, "ICC description"):
            V.validate_reference(**self.paths)  # Default ProPhoto must reject the synthetic sRGB fixture.

    def test_xmp_absence_malformed_and_entities(self):
        for value, error in ((False, "missing ICC or XMP"), (b"<broken", "malformed XMP"),
                             ("<xmpmeta/>".encode("utf-16"), "XMP must be UTF-8"),
                             (b'<!DOCTYPE a [<!ENTITY x "data">]><a>&x;</a>', "DTD/entity")):
            with self.subTest(error=error):
                write_fixture(self.paths["adaptive"], "adaptive", xmp=value)
                with self.assertRaisesRegex(V.ValidationError, error):
                    self.validate()

    def test_basic_control_sabotage(self):
        for key, value, error in (("Exposure2012", "0.1", "must be zero"),
                                  ("Exposure2012", "NaN", "non-finite"),
                                  ("Exposure2012", "oops", "invalid number"),
                                  ("WhiteBalance", "Custom", "As Shot"),
                                  ("CropLeft", "0.1", "uncropped"),
                                  ("HasCrop", "True", "crop enabled"),
                                  ("AlreadyApplied", "False", "settings not marked baked")):
            with self.subTest(key=key, value=value):
                write_fixture(self.paths["adaptive"], "adaptive", mutate=lambda root: set_control(root, key, value))
                with self.assertRaisesRegex(V.ValidationError, error):
                    self.validate()

    def test_equal_nonneutral_controls_still_fail(self):
        for role, path in self.paths.items():
            write_fixture(path, role, mutate=lambda root: set_control(root, "Exposure2012", "1"))
        with self.assertRaisesRegex(V.ValidationError, "must be zero"):
            self.validate()

    def test_missing_control(self):
        write_fixture(self.paths["adaptive"], "adaptive",
                      mutate=lambda root: base_node(root).attrib.pop(f"{{{V.CRS}}}Tint"))
        with self.assertRaisesRegex(V.ValidationError, "missing required"):
            self.validate()

    def test_nonbasic_settings_must_match(self):
        write_fixture(self.paths["adaptive"], "adaptive", mutate=lambda root: set_control(root, "Sharpness", "41"))
        with self.assertRaisesRegex(V.ValidationError, "non_look_settings differs"):
            self.validate()

    def test_nested_curve_change_is_not_hidden_by_zero_sliders(self):
        def mutate(root):
            root.find(".//crs:ToneCurvePV2012/rdf:Seq/rdf:li", V.NS).text = "0, 10"
        write_fixture(self.paths["adaptive"], "adaptive", mutate=mutate)
        with self.assertRaisesRegex(V.ValidationError, "non_look_settings differs"):
            self.validate()

    def test_profile_name_amount_and_ai_activity(self):
        for field, value, error in (("Name", "Adobe Color", "expected Adaptive Color"),
                                    ("Amount", "0", "wrong profile Amount")):
            with self.subTest(field=field):
                def mutate(root):
                    root.find(".//crs:Look/rdf:Description", V.NS).set(f"{{{V.CRS}}}{field}", value)
                write_fixture(self.paths["adaptive"], "adaptive", mutate=mutate)
                with self.assertRaisesRegex(V.ValidationError, error):
                    self.validate()
        write_fixture(self.paths["adaptive"], "adaptive", mutate=lambda root: root.find(".//crs:AILook", V.NS).set(f"{{{V.CRS}}}Active", "false"))
        with self.assertRaisesRegex(V.ValidationError, "inactive"):
            self.validate()

    def test_zero_ai_identity_must_match_full_strength(self):
        write_fixture(self.paths["adaptive_zero"], "adaptive_zero", mutate=lambda root: root.find(".//crs:AILook", V.NS).set(f"{{{V.CRS}}}InputDigest", "different-input"))
        with self.assertRaisesRegex(V.ValidationError, "AI identity mismatch"):
            self.validate()

    def test_zero_look_changes_beyond_amount_fail(self):
        write_fixture(self.paths["adaptive_zero"], "adaptive_zero", mutate=lambda root: root.find(".//crs:Look/rdf:Description", V.NS).set(f"{{{V.CRS}}}UUID", "different-profile"))
        with self.assertRaisesRegex(V.ValidationError, "differs beyond Amount"):
            self.validate()

    def test_source_identity_mismatch(self):
        write_fixture(self.paths["adaptive"], "adaptive", mutate=lambda root: base_node(root).set(f"{{{V.XMP_MM}}}OriginalDocumentID", "different-capture"))
        with self.assertRaisesRegex(V.ValidationError, "original_document_id differs"):
            self.validate()

    def test_ambiguous_source_description(self):
        def mutate(root):
            root.find(f"{{{V.RDF}}}RDF").append(copy.deepcopy(base_node(root)))
        write_fixture(self.paths["adaptive"], "adaptive", mutate=mutate)
        with self.assertRaisesRegex(V.ValidationError, "one RAW settings description"):
            self.validate()

    def test_raw_hashes_and_prior_record(self):
        original, copied = self.root / "capture.raw", self.root / "copy.raw"
        original.write_bytes(b"original synthetic bytes")
        copied.write_bytes(original.read_bytes())
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        result = self.validate(source_raw=original, copied_raw=copied, expected_raw_sha256=digest)
        self.assertTrue(result["raw_identity"]["matches_prior_hash"])
        with self.assertRaisesRegex(V.ValidationError, "prior record"):
            self.validate(source_raw=original, copied_raw=copied, expected_raw_sha256="0" * 64)
        copied.write_bytes(b"changed bytes")
        with self.assertRaisesRegex(V.ValidationError, "hashes differ"):
            self.validate(source_raw=original, copied_raw=copied)

    def test_unrelated_raw_filename_is_rejected(self):
        original, copied = self.root / "different.raw", self.root / "copy.raw"
        original.write_bytes(b"synthetic bytes")
        copied.write_bytes(original.read_bytes())
        with self.assertRaisesRegex(V.ValidationError, "filename does not match"):
            self.validate(source_raw=original, copied_raw=copied)

    def test_cli_refuses_existing_output_including_input(self):
        digest = V.sha256_file(self.paths["baseline"])
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            status = V.main(["--baseline", str(self.paths["baseline"]), "--adaptive", str(self.paths["adaptive"]),
                             "--output", str(self.paths["baseline"]), "--expected-profile", PROFILE_NAME])
        self.assertEqual(status, 1)
        self.assertEqual(digest, V.sha256_file(self.paths["baseline"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
