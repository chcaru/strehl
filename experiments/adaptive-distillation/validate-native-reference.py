"""Validate a native SDR reference export pair, optionally with a zero arm.

Requires numpy, tifffile, and Pillow (LittleCMS). No photographs or profiles ship
with this tool. Inputs are read-only; the JSON receipt is created exclusively.

Example:
  python validate-native-reference.py --baseline baseline.tif \
      --adaptive adaptive.tif --adaptive-zero zero.tif --output receipt.json

The contract is deliberately narrow: one uncompressed uint16 RGB TIFF per arm,
the same embedded RGB ICC, full crop, As Shot white balance, neutral basic tone
controls, and embedded Adobe Color / Adaptive Color metadata. Amount is stored
as 1 for 100 percent. This validates an export record, NOT image quality, model
fidelity, authenticity of metadata, or equivalence to a scene-linear input.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import ImageCms
import tifffile


CRS = "http://ns.adobe.com/camera-raw-settings/1.0/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
XMP = "http://ns.adobe.com/xap/1.0/"
XMP_MM = "http://ns.adobe.com/xap/1.0/mm/"
NS = {"crs": CRS, "rdf": RDF}
ZERO_CONTROLS = (
    "Exposure2012", "Contrast2012", "Highlights2012", "Shadows2012",
    "Whites2012", "Blacks2012", "Texture", "Clarity2012", "Dehaze",
    "Vibrance", "Saturation", "HDREditMode",
)
REQUIRED_CONTROLS = (
    "RawFileName", "Version", "ProcessVersion", "CameraProfile",
    "WhiteBalance", "Temperature", "Tint", "Sharpness", "SharpenRadius",
    "SharpenDetail", "SharpenEdgeMasking", "LuminanceSmoothing",
    "ColorNoiseReduction", "ColorNoiseReductionDetail", "ColorNoiseReductionSmoothness",
    "CropTop", "CropLeft", "CropBottom", "CropRight", "CropAngle",
    "HasCrop", "AlreadyApplied",
) + ZERO_CONTROLS
AI_FIELDS = ("Version", "ModelVersion", "InputDigest", "InputDigestVersion", "AILookData")


class ValidationError(ValueError):
    """An input does not meet the documented reference contract."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_stamp(path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def numeric(value, name):
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValidationError(f"{name}: missing or invalid number") from error
    require(math.isfinite(result), f"{name}: non-finite number")
    return result


def canonical(element):
    """Keep tree structure and values; ignore XML prefix and attribute ordering."""
    return [element.tag, sorted(element.attrib.items()), (element.text or "").strip(),
            [canonical(child) for child in element]]


def crs_attributes(element):
    prefix = "{" + CRS + "}"
    return {key[len(prefix):]: value for key, value in element.attrib.items()
            if key.startswith(prefix)}


def parse_xmp(blob, role):
    require(len(blob) <= 16 * 1024 * 1024, f"{role}: XMP exceeds 16 MiB limit")
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError(f"{role}: XMP must be UTF-8") from error
    require("\x00" not in text, f"{role}: XMP must be UTF-8 without NUL characters")
    require("<!DOCTYPE" not in text.upper() and "<!ENTITY" not in text.upper(),
            f"{role}: DTD/entity declarations are unsupported")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ValidationError(f"{role}: malformed XMP") from error
    candidates = [node for node in root.findall(".//rdf:Description", NS)
                  if f"{{{CRS}}}RawFileName" in node.attrib]
    require(len(candidates) == 1, f"{role}: expected one RAW settings description")
    base = candidates[0]
    controls = crs_attributes(base)
    require(all(key in controls and controls[key] != "" for key in REQUIRED_CONTROLS),
            f"{role}: missing required edit controls")
    for key in ZERO_CONTROLS:
        require(numeric(controls[key], key) == 0, f"{role}: {key} must be zero")
    require(controls["WhiteBalance"] == "As Shot", f"{role}: white balance must be As Shot")
    for key in ("Temperature", "Tint", "Sharpness", "SharpenRadius", "SharpenDetail",
                "SharpenEdgeMasking", "LuminanceSmoothing", "ColorNoiseReduction",
                "ColorNoiseReductionDetail", "ColorNoiseReductionSmoothness"):
        numeric(controls[key], key)
    for key, value in {"CropTop": 0, "CropLeft": 0, "CropBottom": 1,
                       "CropRight": 1, "CropAngle": 0}.items():
        require(numeric(controls[key], key) == value, f"{role}: full uncropped image required")
    require(controls["HasCrop"].lower() == "false", f"{role}: crop enabled")
    require(controls["AlreadyApplied"].lower() == "true", f"{role}: settings not marked baked")
    creator = base.attrib.get(f"{{{XMP}}}CreatorTool", "")
    require("Adobe Lightroom" in creator, f"{role}: missing Lightroom producer declaration")
    original_id = base.attrib.get(f"{{{XMP_MM}}}OriginalDocumentID", "")
    require(bool(original_id), f"{role}: missing original document identity")
    looks = base.findall("crs:Look/rdf:Description", NS)
    require(len(looks) == 1, f"{role}: expected one profile look")
    look = crs_attributes(looks[0])
    expected_name = "Adobe Color" if role == "baseline" else "Adaptive Color"
    expected_amount = 0 if role == "adaptive_zero" else 1
    require(look.get("Name") == expected_name, f"{role}: expected {expected_name} look")
    require(numeric(look.get("Amount"), "look Amount") == expected_amount,
            f"{role}: wrong profile Amount, expected {expected_amount}")
    ai_nodes = base.findall("crs:AILook", NS)
    require(len(ai_nodes) <= 1, f"{role}: ambiguous AI look")
    ai = crs_attributes(ai_nodes[0]) if ai_nodes else {}
    if role != "baseline":
        require(ai.get("Active", "").lower() == "true", f"{role}: Adaptive AI look is inactive")
        require(all(ai.get(key) for key in AI_FIELDS), f"{role}: missing AI look identity fields")
    else:
        require(ai.get("Active", "false").lower() == "false", f"{role}: baseline carries active AI look")
    # Compare every represented setting outside the complete look/AI payload.
    # CompatibleVersion is a profile capability field, not a tone adjustment.
    comparable = {key: value for key, value in controls.items() if key != "CompatibleVersion"}
    children = [canonical(child) for child in base
                if child.tag.startswith("{" + CRS + "}")
                and child.tag not in {f"{{{CRS}}}Look", f"{{{CRS}}}AILook"}]
    look_without_amount = ET.fromstring(ET.tostring(looks[0]))
    look_without_amount.attrib.pop(f"{{{CRS}}}Amount", None)
    return {
        "creator": creator, "original_document_id": original_id,
        "controls": controls, "look": look, "ai_look": ai,
        "non_look_settings": [comparable, children],
        "look_without_amount": canonical(look_without_amount),
    }


def inspect_tiff(path, role, expected_profile):
    path = path.resolve(strict=True)
    before = file_stamp(path)
    with tifffile.TiffFile(path) as source:
        require(len(source.pages) == 1, f"{role}: expected one TIFF page")
        page = source.pages[0]
        require(len(page.shape) == 3 and page.shape[-1] == 3 and min(page.shape[:2]) > 0,
                f"{role}: expected H x W x 3 image")
        require(page.dtype.kind == "u" and page.dtype.itemsize == 2,
                f"{role}: expected uint16 samples")
        require(int(page.photometric) == 2 and int(page.planarconfig) == 1,
                f"{role}: expected contiguous RGB")
        require(int(page.compression) == 1, f"{role}: expected uncompressed TIFF")
        require(not page.extrasamples, f"{role}: extra image channels unsupported")
        orientation = page.tags.get(274)
        require(orientation is None or orientation.value == 1, f"{role}: orientation must be baked")
        require(34675 in page.tags and 700 in page.tags, f"{role}: missing ICC or XMP")
        icc = bytes(page.tags[34675].value)
        require(len(icc) >= 128 and int.from_bytes(icc[:4], "big") == len(icc),
                f"{role}: invalid ICC length")
        require(icc[36:40] == b"acsp" and icc[16:20] == b"RGB ", f"{role}: invalid RGB ICC header")
        try:
            cms_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            description = ImageCms.getProfileDescription(cms_profile).strip()
        except (OSError, ValueError, ImageCms.PyCMSError) as error:
            raise ValidationError(f"{role}: ICC cannot be parsed") from error
        require(description == expected_profile, f"{role}: ICC description {description!r} != {expected_profile!r}")
        xmp = bytes(page.tags[700].value)
        metadata = parse_xmp(xmp, role)
        shape = list(page.shape)
    # The uncompressed contract permits read-only mapping, avoiding full-image
    # copies or temporary decompression files. Canonical hash is little endian.
    pixel_hash = hashlib.sha256()
    pixels = tifffile.memmap(path, mode="r")
    try:
        for y in range(0, shape[0], 64):
            pixel_hash.update(np.asarray(pixels[y:y + 64], dtype="<u2").tobytes(order="C"))
    finally:
        pixels._mmap.close()
    result = {
        "path": str(path), "bytes": before[0], "file_sha256": sha256_file(path),
        "pixel_sha256_le_u16_yxc": pixel_hash.hexdigest(), "shape_yxc": shape,
        "dtype": "uint16", "compression": "none", "orientation": "baked",
        "icc_description": description, "icc_sha256": hashlib.sha256(icc).hexdigest(),
        "xmp_sha256": hashlib.sha256(xmp).hexdigest(), "metadata": metadata,
    }
    require(file_stamp(path) == before, f"{role}: input changed during validation")
    return result


def validate_reference(baseline, adaptive, adaptive_zero=None, *, expected_profile="ProPhoto RGB",
                       source_raw=None, copied_raw=None, expected_raw_sha256=None):
    paths = {"baseline": Path(baseline), "adaptive": Path(adaptive)}
    if adaptive_zero is not None:
        paths["adaptive_zero"] = Path(adaptive_zero)
    resolved = [path.resolve(strict=True) for path in paths.values()]
    require(len(set(resolved)) == len(resolved), "Reference arms must be distinct input files")
    initial_stamps = {path: file_stamp(path) for path in resolved}
    arms = {role: inspect_tiff(path, role, expected_profile) for role, path in paths.items()}
    first = arms["baseline"]
    for role, arm in arms.items():
        require(arm["shape_yxc"] == first["shape_yxc"], f"{role}: geometry mismatch")
        require(arm["icc_sha256"] == first["icc_sha256"], f"{role}: embedded ICC bytes mismatch")
        for key in ("creator", "original_document_id", "non_look_settings"):
            require(arm["metadata"][key] == first["metadata"][key], f"{role}: {key} differs")
    def require_changed(left, right):
        require(arms[left]["pixel_sha256_le_u16_yxc"] != arms[right]["pixel_sha256_le_u16_yxc"],
                f"{left}/{right}: identical decoded pixels; no observed treatment change")
    require_changed("baseline", "adaptive")
    if "adaptive_zero" in arms:
        zero, full = arms["adaptive_zero"]["metadata"], arms["adaptive"]["metadata"]
        require(zero["ai_look"] == full["ai_look"], "Zero/full Adaptive AI identity mismatch")
        require(zero["look_without_amount"] == full["look_without_amount"], "Zero/full look differs beyond Amount")
        require_changed("adaptive_zero", "adaptive")
    require((source_raw is None) == (copied_raw is None), "Provide both original and copied RAW paths")
    require(expected_raw_sha256 is None or source_raw is not None, "Expected RAW hash needs original/copy paths")
    raw = None
    if source_raw is not None:
        originals = [Path(source_raw).resolve(strict=True), Path(copied_raw).resolve(strict=True)]
        require(originals[0] != originals[1], "Original and copied RAW must be distinct files")
        recorded_name = first["metadata"]["controls"]["RawFileName"]
        require(recorded_name.casefold() in {path.name.casefold() for path in originals},
                "RAW filename does not match the TIFF source declaration")
        stamps = [file_stamp(path) for path in originals]
        hashes = [sha256_file(path) for path in originals]
        require(hashes[0] == hashes[1], "Original/copy RAW hashes differ")
        if expected_raw_sha256 is not None:
            require(len(expected_raw_sha256) == 64 and all(c in "0123456789abcdefABCDEF" for c in expected_raw_sha256),
                    "Expected RAW hash must be 64 hexadecimal characters")
            require(hashes[0] == expected_raw_sha256.lower(), "RAW hash differs from prior record")
        require([file_stamp(path) for path in originals] == stamps, "RAW input changed during validation")
        raw = {"original": str(originals[0]), "copy": str(originals[1]), "sha256": hashes[0],
               "matches_prior_hash": True if expected_raw_sha256 is not None else None}
    require(all(file_stamp(path) == stamp for path, stamp in initial_stamps.items()),
            "Reference input changed while other arms were validated")
    return {
        "schema": 1, "validated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "reference_contract_verified", "arms": arms, "raw_identity": raw,
        "unknowns_and_limits": [
            "Metadata is an export declaration, not authenticated proof of the originating application or physical pixel color encoding.",
            "Optional RAW hashes establish copy identity and optionally match a prior receipt; the TIFF filename declaration is not a cryptographic binding to those RAW bytes.",
            "ICC is parseable RGB with the requested description, and identical bytes across arms; this does not prove colorimetric accuracy.",
            "No geometry registration against another decoder or completed stack is established.",
            "Output sharpening and resize export switches are not independently established by these tags.",
            "Raw sharpening/noise reduction remain as recorded; zero basic tone controls do not mean no processing.",
            "Adobe Color and zero-strength Adaptive are different arms; equality is neither assumed nor required.",
            "These are output-referred SDR exports, not scene-linear model inputs or portable AI tensor assets.",
            "Pixel differences prove only a change; they do not measure photographic quality, training generalization, or production readiness.",
            "File stability uses size and timestamps plus hashes; coordinated hostile concurrent replacement is outside this local audit model.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--adaptive", type=Path, required=True)
    parser.add_argument("--adaptive-zero", type=Path)
    parser.add_argument("--expected-profile", default="ProPhoto RGB")
    parser.add_argument("--source-raw", type=Path)
    parser.add_argument("--copied-raw", type=Path)
    parser.add_argument("--expected-raw-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not args.output.exists(), "Output must be a new file; refusing to overwrite")
        result = validate_reference(args.baseline, args.adaptive, args.adaptive_zero,
                                    expected_profile=args.expected_profile, source_raw=args.source_raw,
                                    copied_raw=args.copied_raw, expected_raw_sha256=args.expected_raw_sha256)
        # Exclusive create also rejects a file created after the initial check.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except (ValidationError, OSError, tifffile.TiffFileError) as error:
        print(f"Reference rejected: {error}", file=sys.stderr)
        return 1
    print(f"Verified export contract: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
