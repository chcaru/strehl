#!/usr/bin/env python3
"""Create the frozen M142 candidate from the post-M130 private snapshot.

The shared ``crates/`` tree and the frozen M136 evidence are never written.
Every source input is content-locked, every textual anchor must occur exactly
once, and the completed tree is rejected unless exactly the declared files
changed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


MappingLike = dict[str, Any]

SOURCE_COMMIT = "248178b921f98ec1f13ea4c07d30fa68ace787a0"
SOURCE_TREE = {
    "files": 9292,
    "bytes": 325020512,
    "manifest_sha256": "0F0EFD13D5EC0BB8825EBFEE40F7DCD93D7C99B804582A142F59685288CBF625",
}
APPROVED_CANDIDATE_TREE = {
    "files": 9293,
    "bytes": 325053057,
    "manifest_sha256": "CE83FD38466856BF0C526AF9137AEEE8C7670E3D886A13A8D896155D32E92E12",
}
SOURCE_EXPECTED = {
    "crates/strehl-core/src/align.rs": (
        "E1C906B28E4ED1FBD1610FB1D9770E14FCFC636D9658114EF60A6E314D3C499C"
    ),
    "crates/strehl-core/src/warpmap.rs": (
        "0CFA76CF3138B2341BD0179D7E2B650BD3B762419E8726E0150EE2D202B47CD0"
    ),
    "crates/strehl-core/src/restore.rs": (
        "075B92B371CAE561D5CF5BF4307EFD0FAC02C72413DC52C86FE3F70DD9796A0E"
    ),
    "crates/strehl-cli/src/main.rs": (
        "D41E5F073D7F699D7625FF5B8D71B753ADAE6FD5AC736942F130D1A238809B54"
    ),
    "crates/strehl-cli/src/align_cmd.rs": (
        "2531323ECFA1AE0B8FFBDC72485995EEACFA8A551616350AD3C50199C3BFC7C7"
    ),
    "crates/strehl-cli/src/merge_cmd.rs": (
        "ADA666711B0CD562799E446299294CC2C4C2D35169EB9B046AA2FCEBD5179574"
    ),
    "crates/strehl-cli/src/image_out.rs": (
        "A12FA1C4811D59CBA9811A291D7A1C0F1E529D7E34E14763957E5A0783E52532"
    ),
}
HOOK_SHA256 = "D1DCF4E69678F5843A2AF0EA3C0185B4C271B4F5449CD9BE76FA48485A690FB1"
ADDED = ("crates/strehl-cli/src/m8_trace_v3.rs",)
MODIFIED = tuple(SOURCE_EXPECTED)
CHANGED = MODIFIED + ADDED


CLAMPED_FUNCTION = """
/// Catmull-Rom followed by a clamp to the hull of the 4x4 source taps.
///
/// The raw gather is delegated to [`sample_catmull_rom`] rather than copied,
/// so every value that already lies in the hull is bit-identical to the
/// ordinary kernel. Only an excursion beyond a contributing tap is changed.
pub fn sample_clamped_catmull_rom(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
    let value = sample_catmull_rom(p, x, y);
    if p.width < 4 || p.height < 4 {
        return value;
    }
    let x = x.clamp(1.0, (p.width - 3) as f64);
    let y = y.clamp(1.0, (p.height - 3) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let mut lo = f32::INFINITY;
    let mut hi = f32::NEG_INFINITY;
    for dy in 0..4 {
        let row = (y0 + dy - 1) * p.width + x0 - 1;
        for dx in 0..4 {
            let tap = p.data[row + dx];
            lo = lo.min(tap);
            hi = hi.max(tap);
        }
    }
    value.clamp(lo, hi)
}
"""


TRACE_CONTEXT = """
/// Value-only context for the preregistered M8 trace-v3 measurement.
///
/// The primary pyramid fold constructs this from its full-plane/Crop domain
/// and the first frame's final output gains. Other warp callers pass no
/// context, so gate-floor probes, confidence passes, examples and tests cannot
/// emit duplicate target evidence.
#[derive(Clone, Copy, Debug)]
pub(crate) struct M8TraceContext {
    pub frame_order: usize,
    pub full_width: usize,
    pub full_height: usize,
    pub compact_width: usize,
    pub compact_height: usize,
    pub crop_x: usize,
    pub crop_y: usize,
    pub output_gains: [f32; 3],
}
"""


WARP_DISPATCH_OLD = """pub fn warp_frame_in_place(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<f64> {
    if fullres_gather_enabled() {
        warp_frame_in_place_fullres(frame, t, geom, resampler, scratch)
    } else {
        warp_frame_in_place_plane(frame, t, geom, resampler, scratch)
    }
}
"""


WARP_DISPATCH_NEW = """pub fn warp_frame_in_place(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<f64> {
    warp_frame_in_place_with_m8_trace(frame, t, geom, resampler, scratch, None)
}

/// The ordinary warp plus an optional value-only M8 trace context.
///
/// Only the registered primary pyramid fold supplies `Some`. Trace v3 records
/// the full-resolution demosaiced source domain, so asking for it through the
/// legacy phase-plane gather is an error rather than a silently different
/// measurement.
pub(crate) fn warp_frame_in_place_with_m8_trace(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
    trace: Option<&M8TraceContext>,
) -> Result<f64> {
    let fullres = fullres_gather_enabled();
    if trace.is_some() && !fullres {
        bail!(
            "M8 trace-v3 requires {FULLRES_ENV}=1 because its source domain is the \\
             full-resolution demosaiced channel plane"
        );
    }
    if fullres {
        warp_frame_in_place_fullres_traced(frame, t, geom, resampler, scratch, trace)
    } else {
        warp_frame_in_place_plane(frame, t, geom, resampler, scratch)
    }
}
"""


FULLRES_SIGNATURE_OLD = """pub fn warp_frame_in_place_fullres(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<f64> {
"""


FULLRES_SIGNATURE_NEW = """pub fn warp_frame_in_place_fullres(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<f64> {
    warp_frame_in_place_fullres_traced(frame, t, geom, resampler, scratch, None)
}

fn warp_frame_in_place_fullres_traced(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
    trace: Option<&M8TraceContext>,
) -> Result<f64> {
"""


TRACE_CALL = """            if let Some(trace) = trace {
                ensure!(
                    (trace.full_width, trace.full_height) == (gw, gh),
                    "M8 trace-v3 full geometry {}x{} differs from warp geometry {gw}x{gh}",
                    trace.full_width,
                    trace.full_height
                );
                crate::m8_trace_v3::trace_site(
                    resampler,
                    trace.frame_order,
                    fw,
                    fh,
                    trace.full_width,
                    trace.full_height,
                    trace.compact_width,
                    trace.compact_height,
                    trace.crop_x,
                    trace.crop_y,
                    dx,
                    dy,
                    ci,
                    crate::m8_trace_v3::ARITHMETIC_CONTRACT,
                    t_site,
                    cx,
                    cy,
                    black,
                    frame.levels.range(),
                    gain[ci],
                    trace.output_gains[ci],
                    &frame.path,
                    plane,
                    &scratch.dst,
                )?;
            }

"""

M136_DESCRIPTION_HELPER = """
fn m136_measurement_description(mut description: String, dev: &Develop) -> Result<String> {
    let Some(value) = std::env::var_os("STREHL_M8_FREEZE_SHA256") else {
        return Ok(description);
    };
    if dev.matrix.is_some() || dev.srgb || dev.tone.is_some() {
        anyhow::bail!(
            "STREHL_M8_FREEZE_SHA256 may only bind the linear camera-native measurement output"
        );
    }
    let mut freeze = value
        .into_string()
        .map_err(|_| anyhow::anyhow!("STREHL_M8_FREEZE_SHA256 is not Unicode"))?;
    if freeze.len() != 64 || !freeze.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        anyhow::bail!(
            "STREHL_M8_FREEZE_SHA256 must contain exactly 64 hexadecimal digits"
        );
    }
    freeze.make_ascii_uppercase();
    description.push_str(" M136 instrument freeze sha256: ");
    description.push_str(&freeze);
    description.push('.');
    Ok(description)
}

"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def tree_manifest(root: Path) -> dict[str, Any]:
    rows: list[tuple[str, int, str]] = []
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"source snapshot contains a symbolic link: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"source snapshot contains a non-file entry: {path}")
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        rows.append((relative, size, sha256(path)))
    digest = hashlib.sha256()
    for row in rows:
        encoded = (
            json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")
        digest.update(encoded)
    return {
        "files": len(rows),
        "bytes": total,
        "manifest_sha256": digest.hexdigest().upper(),
        "file_sha256": {relative: file_hash for relative, _, file_hash in rows},
    }


def read_normalized(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"{path}: source is not UTF-8") from error
    if "\r\n" in text:
        if text.replace("\r\n", "").find("\r") != -1:
            raise RuntimeError(f"{path}: source has mixed carriage returns")
        newline = "\r\n"
    else:
        if "\r" in text:
            raise RuntimeError(f"{path}: source has unsupported carriage returns")
        newline = "\n"
    return text.replace("\r\n", "\n"), newline


def write_normalized(path: Path, text: str, newline: str) -> None:
    if "\r" in text:
        raise RuntimeError(f"{path}: replacement text contains a carriage return")
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def replace_once(path: Path, anchor: str, replacement: str, label: str) -> None:
    text, newline = read_normalized(path)
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(
            f"{path}: {label} anchor occurred {count} times; required exactly once"
        )
    write_normalized(path, text.replace(anchor, replacement), newline)


def replace_exact(
    path: Path,
    anchor: str,
    replacement: str,
    expected_count: int,
    label: str,
) -> None:
    text, newline = read_normalized(path)
    count = text.count(anchor)
    if count != expected_count:
        raise RuntimeError(
            f"{path}: {label} anchor occurred {count} times; "
            f"required exactly {expected_count}"
        )
    write_normalized(path, text.replace(anchor, replacement), newline)


def write_json_atomic(path: Path, payload: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def build_source_manifest(root: Path, source_commit: str) -> MappingLike:
    paths: list[Path] = []
    for top_level in root.iterdir():
        # These are the protocol's only permitted build-output subtrees.  Do
        # not blanket-ignore generic or nested `target` directories: those may
        # be committed build inputs and belong in the frozen inventory.
        if top_level.name.lower() in {"target-m136", "target-m136-tests"}:
            continue
        if top_level.is_symlink():
            raise RuntimeError(
                f"source manifest refuses symbolic link: {top_level}"
            )
        if top_level.is_file():
            paths.append(top_level)
        elif top_level.is_dir():
            for path in top_level.rglob("*"):
                if path.is_symlink():
                    raise RuntimeError(
                        f"source manifest refuses symbolic link: {path}"
                    )
                if path.is_file():
                    paths.append(path)

    rows = []
    total_bytes = 0
    tree_digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        rows.append({"path": relative, "bytes": size, "sha256": digest})
        total_bytes += size
        tree_digest.update(
            (
                json.dumps(
                    [relative, size, digest],
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")
        )
    if not rows:
        raise RuntimeError("source manifest has no build-relevant files")
    return {
        "schema": "m136-source-snapshot-v1",
        "schema_version": 1,
        "source_commit": source_commit,
        "source_root": str(root),
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "tree_sha256": tree_digest.hexdigest().upper(),
        "files": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--hook", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    experiment = Path(__file__).resolve().parent
    allowed = (experiment / "out").resolve()
    source = args.source.resolve()
    destination = args.destination.resolve()
    hook = args.hook.resolve()
    record = args.record.resolve()
    source_manifest_path = args.source_manifest.resolve()
    repository = Path(__file__).resolve().parents[2]

    if args.source_commit.lower() != SOURCE_COMMIT:
        raise RuntimeError(
            f"source commit {args.source_commit!r} != frozen {SOURCE_COMMIT}"
        )
    if not source.is_dir():
        raise RuntimeError(f"source snapshot is absent: {source}")
    if not hook.is_file():
        raise RuntimeError(f"trace hook is absent: {hook}")
    if not path_is_within(source, allowed):
        raise RuntimeError(f"source must be below M142/out: {source}")
    if not path_is_within(destination, allowed) or destination == allowed:
        raise RuntimeError(f"destination must be below M142/out: {destination}")
    if (
        destination == source
        or path_is_within(source, destination)
        or path_is_within(destination, source)
    ):
        raise RuntimeError("destination would overwrite or contain the source snapshot")
    for label, output in (
        ("record", record),
        ("source manifest", source_manifest_path),
    ):
        if not path_is_within(output, allowed):
            raise RuntimeError(f"{label} must be below M142/out: {output}")
        if path_is_within(output, source) or path_is_within(output, destination):
            raise RuntimeError(
                f"{label} must be outside both source and destination trees"
            )
    if record == source_manifest_path:
        raise RuntimeError("record and source manifest paths must be distinct")
    if path_is_within(hook, source) or path_is_within(hook, destination):
        raise RuntimeError("canonical hook must be outside source and destination trees")
    if sha256(hook) != HOOK_SHA256:
        raise RuntimeError(
            f"{hook}: trace hook hash {sha256(hook)} != frozen {HOOK_SHA256}"
        )

    source_manifest = tree_manifest(source)
    source_summary = {
        key: source_manifest[key] for key in ("files", "bytes", "manifest_sha256")
    }
    if source_summary != SOURCE_TREE:
        raise RuntimeError(
            "private source snapshot differs from the frozen tree: "
            f"{source_summary!r} != {SOURCE_TREE!r}"
        )
    for relative, expected in SOURCE_EXPECTED.items():
        actual = source_manifest["file_sha256"].get(relative)
        if actual != expected:
            raise RuntimeError(
                f"{source / relative}: frozen hash {actual}, expected {expected}"
            )
    for relative in ADDED:
        if relative in source_manifest["file_sha256"]:
            raise RuntimeError(
                f"clean source snapshot unexpectedly contains added file {relative}"
            )

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    align = destination / "crates/strehl-core/src/align.rs"
    warpmap = destination / "crates/strehl-core/src/warpmap.rs"
    restore = destination / "crates/strehl-core/src/restore.rs"
    main_rs = destination / "crates/strehl-cli/src/main.rs"
    align_cmd = destination / "crates/strehl-cli/src/align_cmd.rs"
    merge_cmd = destination / "crates/strehl-cli/src/merge_cmd.rs"
    image_out = destination / "crates/strehl-cli/src/image_out.rs"
    hook_destination = destination / "crates/strehl-cli/src/m8_trace_v3.rs"

    replace_once(
        align,
        "\n/// Normalised sinc, `sin(pi x) / (pi x)`, with the removable singularity filled.\n",
        CLAMPED_FUNCTION
        + "\n/// Normalised sinc, `sin(pi x) / (pi x)`, with the removable singularity filled.\n",
        "clamped function insertion",
    )
    replace_once(
        align,
        "    CatmullRom,\n    Lanczos2,\n",
        "    CatmullRom,\n    ClampedCatmullRom,\n    Lanczos2,\n",
        "Resampler variant",
    )
    replace_once(
        align,
        "            Resampler::CatmullRom => sample_catmull_rom(p, x, y),\n",
        "            Resampler::CatmullRom => sample_catmull_rom(p, x, y),\n"
        "            Resampler::ClampedCatmullRom => sample_clamped_catmull_rom(p, x, y),\n",
        "sample dispatch",
    )
    replace_once(
        align,
        "            Resampler::CatmullRom => 2.0,\n",
        "            Resampler::CatmullRom | Resampler::ClampedCatmullRom => 2.0,\n",
        "support dispatch",
    )

    replace_once(
        warpmap,
        'pub const RESAMPLER_NAMES: [&str; 5] =\n'
        '    ["nearest", "bilinear", "catmull-rom", "lanczos2", "lanczos3"];\n',
        'pub const RESAMPLER_NAMES: [&str; 6] = [\n'
        '    "nearest",\n'
        '    "bilinear",\n'
        '    "catmull-rom",\n'
        '    "clamped-catmull",\n'
        '    "lanczos2",\n'
        '    "lanczos3",\n'
        '];\n',
        "resampler names",
    )
    replace_once(
        warpmap,
        '        Resampler::CatmullRom => "catmull-rom",\n',
        '        Resampler::CatmullRom => "catmull-rom",\n'
        '        Resampler::ClampedCatmullRom => "clamped-catmull",\n',
        "resampler name",
    )
    replace_once(
        warpmap,
        '        "catmull-rom" => Some(Resampler::CatmullRom),\n',
        '        "catmull-rom" => Some(Resampler::CatmullRom),\n'
        '        "clamped-catmull" => Some(Resampler::ClampedCatmullRom),\n',
        "resampler parser",
    )

    # Restoration is not invoked by the registered command. These two arms are
    # compile-only nominal Catmull-Rom models for the nonlinear clamped variant.
    replace_once(
        restore,
        "        Resampler::CatmullRom => {\n",
        "        Resampler::CatmullRom | Resampler::ClampedCatmullRom => {\n",
        "restore nominal tap model",
    )
    replace_once(
        restore,
        "        Resampler::CatmullRom | Resampler::Lanczos2 => 2,\n",
        "        Resampler::CatmullRom\n"
        "        | Resampler::ClampedCatmullRom\n"
        "        | Resampler::Lanczos2 => 2,\n",
        "restore nominal support",
    )

    # Deliberately retain the approved CE83... candidate identity. Four
    # development examples include align_cmd.rs directly and therefore do not
    # resolve this crate-root module; the registered measurement and verifier
    # both build only the strehl-cli binary target.
    replace_once(
        main_rs,
        "mod merge_cmd;\nmod stack;\n",
        "mod m8_trace_v3;\nmod merge_cmd;\nmod stack;\n",
        "trace module declaration",
    )

    replace_once(
        image_out,
        "\n/// Interleaved RGB, 16 bits per channel, with the colour space stated in the\n",
        M136_DESCRIPTION_HELPER
        + "\n/// Interleaved RGB, 16 bits per channel, with the colour space stated in the\n",
        "M136 measurement-description helper",
    )
    replace_once(
        image_out,
        "    let desc = color_description(dev);\n",
        "    let desc = m136_measurement_description(color_description(dev), dev)?;\n",
        "M136 measurement-description binding",
    )

    replace_once(
        align_cmd,
        "use anyhow::{Context, Result, bail};\n",
        "use anyhow::{Context, Result, bail, ensure};\n",
        "anyhow ensure import",
    )
    replace_once(
        align_cmd,
        "}\n\n/// Resample a decoded frame onto the reference grid, in place.\n",
        "}\n"
        + TRACE_CONTEXT
        + "\n/// Resample a decoded frame onto the reference grid, in place.\n",
        "M8 trace context insertion",
    )
    replace_once(
        align_cmd,
        WARP_DISPATCH_OLD,
        WARP_DISPATCH_NEW,
        "traced warp dispatcher",
    )
    replace_once(
        align_cmd,
        FULLRES_SIGNATURE_OLD,
        FULLRES_SIGNATURE_NEW,
        "full-resolution traced implementation",
    )
    replace_once(
        align_cmd,
        "            }\n\n            let inv = 1.0 / gain[ci];\n",
        "            }\n\n" + TRACE_CALL + "            let inv = 1.0 / gain[ci];\n",
        "trace call after gather",
    )

    replace_once(
        merge_cmd,
        "    floor: Option<gatefloor::Probe>,\n",
        "    floor: Option<gatefloor::Probe>,\n"
        "    /// Final writer gains from the first frame, recorded by trace v3.\n"
        "    output_gains: [f32; 3],\n"
        "    /// Frozen once per worker so auxiliary warp passes remain untraced.\n"
        "    trace_enabled: bool,\n",
        "BandWorker trace fields",
    )
    replace_once(
        merge_cmd,
        "    fn new(domain: PyramidDomain, cfg: MergeConfig) -> Self {\n",
        "    fn new(\n"
        "        domain: PyramidDomain,\n"
        "        cfg: MergeConfig,\n"
        "        output_gains: [f32; 3],\n"
        "    ) -> Self {\n",
        "BandWorker constructor signature",
    )
    replace_once(
        merge_cmd,
        "            floor: gatefloor::enabled().then(|| gatefloor::Probe::new(domain, cfg.bands)),\n"
        "            beta: Vec::new(),\n",
        "            floor: gatefloor::enabled().then(|| gatefloor::Probe::new(domain, cfg.bands)),\n"
        "            output_gains,\n"
        "            trace_enabled: crate::m8_trace_v3::enabled(),\n"
        "            beta: Vec::new(),\n",
        "BandWorker trace field initialization",
    )
    replace_once(
        merge_cmd,
        "        if let Some(p) = self.floor.as_mut() {\n"
        "            p.invalidate();\n"
        "        }\n"
        "        if !load_frame(\n",
        "        if let Some(p) = self.floor.as_mut() {\n"
        "            p.invalidate();\n"
        "        }\n"
        "        let trace = self.trace_enabled.then_some(align_cmd::M8TraceContext {\n"
        "            frame_order: index,\n"
        "            full_width: self.domain.full.width,\n"
        "            full_height: self.domain.full.height,\n"
        "            compact_width: self.domain.rect.width,\n"
        "            compact_height: self.domain.rect.height,\n"
        "            crop_x: self.domain.rect.x,\n"
        "            crop_y: self.domain.rect.y,\n"
        "            output_gains: self.output_gains,\n"
        "        });\n"
        "        if !load_frame(\n",
        "primary-fold trace context construction",
    )
    replace_once(
        merge_cmd,
        "            warps,\n"
        "            defect,\n"
        "            &mut self.warp,\n",
        "            warps,\n"
        "            defect,\n"
        "            trace.as_ref(),\n"
        "            &mut self.warp,\n",
        "primary-fold trace context argument",
    )
    replace_once(
        merge_cmd,
        "    warps: Option<&WarpMap>,\n"
        "    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,\n"
        "    scratch: &mut WarpScratch,\n",
        "    warps: Option<&WarpMap>,\n"
        "    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,\n"
        "    trace: Option<&align_cmd::M8TraceContext>,\n"
        "    scratch: &mut WarpScratch,\n",
        "load_frame trace parameter",
    )
    replace_once(
        merge_cmd,
        "                    align_cmd::warp_frame_in_place(\n"
        "                        &mut frame,\n"
        "                        *t,\n"
        "                        domain.full,\n"
        "                        map.resampler(),\n"
        "                        scratch,\n"
        "                    )?;\n",
        "                    align_cmd::warp_frame_in_place_with_m8_trace(\n"
        "                        &mut frame,\n"
        "                        *t,\n"
        "                        domain.full,\n"
        "                        map.resampler(),\n"
        "                        scratch,\n"
        "                        trace,\n"
        "                    )?;\n",
        "load_frame traced warp call",
    )
    replace_exact(
        merge_cmd,
        "                    p, *i, domain, levels, warps, defect, &mut scratch, None, &mut planes,\n"
        "                    &mut luma,\n",
        "                    p, *i, domain, levels, warps, defect, None, &mut scratch, None,\n"
        "                    &mut planes, &mut luma,\n",
        2,
        "confidence passes' untraced loads",
    )
    replace_once(
        merge_cmd,
        "    let wb = first.wb_gains();\n"
        "    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();\n",
        "    let wb = first.wb_gains();\n"
        "    let output_gains = wb.unwrap_or([1.0, 1.0, 1.0]);\n"
        "    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();\n",
        "final output gain capture",
    )
    replace_once(
        merge_cmd,
        "            let mut w = BandWorker::new(domain, cfg);\n",
        "            let mut w = BandWorker::new(domain, cfg, output_gains);\n",
        "BandWorker constructor",
    )

    shutil.copyfile(hook, hook_destination)
    if sha256(hook_destination) != HOOK_SHA256:
        raise RuntimeError("copied trace hook hash changed")

    destination_manifest = tree_manifest(destination)
    modified = sorted(
        relative
        for relative, digest in destination_manifest["file_sha256"].items()
        if relative in source_manifest["file_sha256"]
        and source_manifest["file_sha256"][relative] != digest
    )
    missing = sorted(set(source_manifest["file_sha256"]) - set(destination_manifest["file_sha256"]))
    added = sorted(set(destination_manifest["file_sha256"]) - set(source_manifest["file_sha256"]))
    changed = sorted(modified + added)
    if modified != sorted(MODIFIED) or added != sorted(ADDED) or missing:
        raise RuntimeError(
            "patched tree changed an undeclared file set: "
            f"modified={modified}, missing={missing}, added={added}"
        )

    changed_rows = []
    for relative in changed:
        before = source / relative
        after = destination / relative
        changed_rows.append(
            {
                "path": relative,
                "kind": "added" if relative in ADDED else "modified",
                "base_git_blob_sha1": (
                    None if relative in ADDED else git_blob_sha1(before)
                ),
                "base_sha256": None if relative in ADDED else sha256(before),
                "snapshot_git_blob_sha1": git_blob_sha1(after),
                "snapshot_sha256": sha256(after),
            }
        )

    payload: MappingLike = {
        "schema": "m136-source-patch-v1",
        "schema_version": 1,
        "protocol": "M136 clamped-Catmull-Rom representable-domain M8-O v1",
        "source_commit": SOURCE_COMMIT,
        "source_root": str(destination),
        "repository": str(repository),
        "source": str(source),
        "destination": str(destination),
        "manifest_algorithm": (
            "SHA-256 over sorted UTF-8 JSON lines [relative_posix_path,bytes,file_sha256]"
        ),
        "source_tree": source_summary,
        "patched_tree": {
            key: destination_manifest[key]
            for key in ("files", "bytes", "manifest_sha256")
        },
        "frozen_before_sha256": {
            relative: source_manifest["file_sha256"][relative]
            for relative in MODIFIED
        },
        "after_sha256": {
            relative: destination_manifest["file_sha256"][relative]
            for relative in CHANGED
        },
        "changed_files": changed_rows,
        "changed_paths": changed,
        "trace_hook": {
            "source": str(hook),
            "sha256": HOOK_SHA256,
        },
        "patch_script": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "candidate_divergences": [
            {
                "file": "crates/strehl-core/src/align.rs",
                "change": (
                    "add ClampedCatmullRom; evaluate unchanged raw Catmull-Rom once, "
                    "then clamp to the exact 4x4 source-tap min/max"
                ),
            },
            {
                "file": "crates/strehl-core/src/warpmap.rs",
                "change": "add the clamped-catmull command/sidecar spelling",
            },
            {
                "file": "crates/strehl-core/src/restore.rs",
                "change": (
                    "compile-only nominal Catmull-Rom model/support for the new "
                    "variant; the registered command does not enable restoration"
                ),
            },
            {
                "file": "crates/strehl-cli/src/main.rs",
                "change": (
                    "declare the value-only m8_trace_v3 module for the registered "
                    "bin-only build; consciously retain the approved CE83 private-"
                    "snapshot example-module limitation"
                ),
            },
            {
                "file": "crates/strehl-cli/src/align_cmd.rs",
                "change": (
                    "emit one value-only trace block after each primary full-resolution "
                    "site gather and before inverse gain, pedestal restore, rounding or writeback"
                ),
            },
            {
                "file": "crates/strehl-cli/src/merge_cmd.rs",
                "change": (
                    "thread frame order, full/Crop geometry and first-frame final "
                    "output gains only through the registered primary pyramid fold"
                ),
            },
            {
                "file": "crates/strehl-cli/src/image_out.rs",
                "change": (
                    "when and only when the frozen measurement environment is "
                    "present, append its SHA-256 binding to the TIFF "
                    "ImageDescription without changing pixel arithmetic"
                ),
            },
            {
                "file": "crates/strehl-cli/src/m8_trace_v3.rs",
                "change": (
                    "copy the frozen trace-v3 value producer; no hull, contributor "
                    "mask, crop verdict or pass/fail value is produced"
                ),
            },
        ],
        "trace_scope": {
            "source_domain": "full-resolution demosaiced channel plane",
            "fullres_required": True,
            "primary_pyramid_fold_only": True,
            "auxiliary_warps_traced": False,
        },
    }
    candidate_manifest = build_source_manifest(destination, SOURCE_COMMIT)
    candidate_tree = {
        "files": candidate_manifest["file_count"],
        "bytes": candidate_manifest["total_bytes"],
        "manifest_sha256": candidate_manifest["tree_sha256"],
    }
    if candidate_tree != APPROVED_CANDIDATE_TREE:
        raise RuntimeError(
            "candidate source tree differs from the prospectively approved identity: "
            f"expected {APPROVED_CANDIDATE_TREE}, observed {candidate_tree}"
        )
    if candidate_tree != payload["patched_tree"]:
        raise RuntimeError(
            "exhaustive source manifest disagrees with source-patch tree identity"
        )
    write_json_atomic(source_manifest_path, candidate_manifest)
    write_json_atomic(record, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"patch_snapshot_m142: {error}", file=sys.stderr)
        raise SystemExit(1)
