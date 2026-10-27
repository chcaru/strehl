//! Metadata-only Sony focus inspection and non-mutating bracket diagnostics.
//!
//! The hidden tag decoder establishes byte layout, not calibrated distance or
//! measurement freshness. This consumer preserves filename order and reports
//! changes in raw metadata units; it never changes frame admission or geometry.

use std::collections::{BTreeMap, BTreeSet};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use anyhow::{Context, Result, ensure};
use clap::Args;
use serde::Serialize;
use sha2::{Digest, Sha256};
use strehl_raw::sony_focus::{self, SonyFocusError, SonyFocusMetadata};

#[path = "sony-optical-report.rs"]
mod sony_optical_report;

const LARGE_DELTA_MULTIPLIER: u64 = 3;
const LIMITS: &[&str] = &[
    "Scalar differences are raw metadata units, not calibrated physical focus steps or distance.",
    "Grid values are preserved as raw bits; signed int16 is a display interpretation.",
    "Grid coordinates and flags do not establish sharpness, valid depth, or spatial coverage.",
    "Matching section sequence identifiers do not prove fresh measurements; firmware can reuse a prior buffer.",
    "No metadata changes frame order, image samples, merge admission, or alignment.",
];

#[derive(Args, Debug)]
pub(crate) struct InspectArgs {
    /// An ARW file or a bracket directory (non-recursive filename order).
    pub input: PathBuf,
    /// Inspect at most this many files in filename order.
    #[arg(long, value_parser = clap::value_parser!(usize))]
    pub limit: Option<usize>,
    /// Write a new JSON report. Existing files are never overwritten.
    #[arg(long, value_name = "REPORT.JSON")]
    pub out: Option<PathBuf>,
    /// Write a new self-contained HTML viewer, including all grid records.
    #[arg(long, value_name = "REPORT.HTML")]
    pub html: Option<PathBuf>,
    /// Include all raw value/flag records in the JSON report.
    #[arg(long, requires = "out")]
    pub records: bool,
    /// Include exact optical settings, signed tables, and header provenance.
    #[arg(long)]
    pub optical: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
enum ReadStatus {
    Present,
    Absent,
    Unsupported,
    Malformed,
    IoError,
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
struct OpticalIdentity {
    lens_model: Option<String>,
    lens_type3: Option<u16>,
    focal_length_mm: Option<f32>,
    f_number: Option<f32>,
}

impl OpticalIdentity {
    fn read(path: &Path) -> Self {
        let id = strehl_raw::identity(path);
        Self {
            lens_model: id.lens_model,
            lens_type3: id.lens_type3,
            focal_length_mm: id.focal_len_mm.filter(|x| x.is_finite() && *x > 0.0),
            f_number: id.f_number.filter(|x| x.is_finite() && *x > 0.0),
        }
    }

    fn comparable(&self) -> bool {
        (self.lens_model.is_some() || self.lens_type3.is_some())
            && self.focal_length_mm.is_some()
            && self.f_number.is_some()
    }
}

#[derive(Debug, Serialize)]
struct FileIdentity {
    byte_length: Option<u64>,
    modified_unix_ns: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
struct GridReport {
    width: u16,
    height: u16,
    roi_raw: [u16; 4],
    origin_raw: [u16; 2],
    extent_raw: [u16; 2],
    record_count: usize,
    records_sha256: String,
    signed_display_range: Option<[i16; 2]>,
    signed_display_extreme_32000_count: usize,
    last_flag_bit_0x20_count: usize,
    extreme_flag_association_mismatches: usize,
    flag_pairs: Vec<FlagCount>,
    #[serde(skip_serializing_if = "Option::is_none")]
    records: Option<Vec<RecordReport>>,
}

#[derive(Clone, Debug, Serialize)]
struct FlagCount {
    bytes: [u8; 2],
    count: usize,
}

#[derive(Clone, Debug, Serialize)]
struct RecordReport {
    value_bits: u16,
    signed_display: i16,
    flags: [u8; 2],
}

#[derive(Clone, Debug, Serialize)]
struct TailReport {
    length: usize,
    nonzero_bytes: usize,
    sha256: String,
}

#[derive(Clone, Debug, Serialize)]
struct FrameMetadata {
    model: String,
    software: String,
    optical_identity: OpticalIdentity,
    source_offset: u64,
    source_length: u32,
    encoded_payload_sha256: String,
    coarse_focus_position: Option<u8>,
    focus_mode_raw: Option<u8>,
    section_sequences: [u16; 3],
    section_sequences_agree: bool,
    section0_u16: [u16; 20],
    scalar_status_raw: u16,
    scalars_raw: [u32; 3],
    grid: GridReport,
    unknown_tail: TailReport,
}

#[derive(Debug, Serialize)]
struct FrameReport {
    index: usize,
    path: PathBuf,
    file_identity: FileIdentity,
    status: ReadStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    metadata: Option<FrameMetadata>,
    #[serde(skip_serializing_if = "Option::is_none")]
    optical: Option<sony_optical_report::OpticalReport>,
}

#[derive(Debug, Default, Serialize)]
struct StatusCounts {
    present: usize,
    absent: usize,
    unsupported: usize,
    malformed: usize,
    io_error: usize,
}

#[derive(Debug, Serialize)]
struct DeltaReport {
    from_index: usize,
    to_index: usize,
    scalar_b_delta: i64,
    sequence_raw_delta: i32,
    sequence_modulo_65536_delta: u16,
    sequence_observation: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    coarse_delta: Option<i16>,
    direction_change: bool,
    larger_than_three_median_deltas: bool,
}

#[derive(Debug, Serialize)]
struct ComparisonBreak {
    from_index: usize,
    to_index: usize,
    reason: &'static str,
}

#[derive(Debug, Serialize)]
struct SegmentReport {
    first_index: usize,
    last_index: usize,
    first_scalar_b: u32,
    last_scalar_b: u32,
    comparable_pairs: usize,
    increasing_pairs: usize,
    decreasing_pairs: usize,
    repeated_pairs: usize,
    direction_changes: usize,
    sequence_non_unit_pairs: usize,
    sequence_decreasing_pairs: usize,
    median_absolute_nonzero_delta: Option<f64>,
    large_delta_pairs: usize,
    direction: &'static str,
    deltas: Vec<DeltaReport>,
}

#[derive(Debug, Serialize)]
pub(crate) struct AuditReport {
    schema: &'static str,
    strehl_version: &'static str,
    input_order: &'static str,
    records_included: bool,
    limits: &'static [&'static str],
    file_count: usize,
    counts: StatusCounts,
    section_sequence_disagreement_indices: Vec<usize>,
    comparison_breaks: Vec<ComparisonBreak>,
    scalar_b_segments: Vec<SegmentReport>,
    frames: Vec<FrameReport>,
}

fn hex_bytes(bytes: impl AsRef<[u8]>) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let bytes = bytes.as_ref();
    let mut text = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        text.push(char::from(HEX[usize::from(byte >> 4)]));
        text.push(char::from(HEX[usize::from(byte & 15)]));
    }
    text
}

fn metadata_report(
    meta: SonyFocusMetadata,
    mut lens: OpticalIdentity,
    records: bool,
) -> FrameMetadata {
    lens.lens_model = meta.lens_model.clone().or(lens.lens_model);
    let mut flag_pairs = BTreeMap::new();
    let mut hash = Sha256::new();
    let mut low = i16::MAX;
    let mut high = i16::MIN;
    let mut extremes = 0;
    let mut flagged = 0;
    let mut mismatches = 0;
    for r in &meta.grid.records {
        *flag_pairs.entry(r.flags).or_insert(0) += 1;
        hash.update(r.value_bits.to_le_bytes());
        hash.update(r.flags);
        let signed = r.signed_display();
        low = low.min(signed);
        high = high.max(signed);
        let extreme = signed == -32000 || signed == 32000;
        let bit = r.flags[1] & 0x20 != 0;
        extremes += usize::from(extreme);
        flagged += usize::from(bit);
        mismatches += usize::from(extreme != bit);
    }
    let sequences = meta.sequence_fields();
    let grid = GridReport {
        width: meta.grid.width,
        height: meta.grid.height,
        roi_raw: meta.grid.roi_raw,
        origin_raw: meta.grid.origin_raw,
        extent_raw: meta.grid.extent_raw,
        record_count: meta.grid.records.len(),
        records_sha256: hex_bytes(hash.finalize()),
        signed_display_range: (!meta.grid.records.is_empty()).then_some([low, high]),
        signed_display_extreme_32000_count: extremes,
        last_flag_bit_0x20_count: flagged,
        extreme_flag_association_mismatches: mismatches,
        flag_pairs: flag_pairs
            .into_iter()
            .map(|(bytes, count)| FlagCount { bytes, count })
            .collect(),
        records: records.then(|| {
            meta.grid
                .records
                .iter()
                .map(|r| RecordReport {
                    value_bits: r.value_bits,
                    signed_display: r.signed_display(),
                    flags: r.flags,
                })
                .collect()
        }),
    };
    FrameMetadata {
        model: meta.model,
        software: meta.software,
        optical_identity: lens,
        source_offset: meta.source_offset,
        source_length: meta.source_length,
        encoded_payload_sha256: hex_bytes(Sha256::digest(&meta.encoded_payload)),
        coarse_focus_position: meta.coarse_focus_position,
        focus_mode_raw: meta.focus_mode,
        section_sequences: sequences,
        section_sequences_agree: sequences[0] == sequences[1] && sequences[1] == sequences[2],
        section0_u16: meta.section0,
        scalar_status_raw: meta.section2.status,
        scalars_raw: meta.section2.values_raw,
        grid,
        unknown_tail: TailReport {
            length: meta.unknown_tail.len(),
            nonzero_bytes: meta.unknown_tail.iter().filter(|&&v| v != 0).count(),
            sha256: hex_bytes(Sha256::digest(&meta.unknown_tail)),
        },
    }
}

fn inspect_path(index: usize, path: &Path, records: bool) -> FrameReport {
    let file = std::fs::metadata(path).ok();
    let file_identity = FileIdentity {
        byte_length: file.as_ref().map(|m| m.len()),
        modified_unix_ns: file
            .as_ref()
            .and_then(|m| m.modified().ok())
            .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
            .map(|d| d.as_nanos().to_string()),
    };
    let (status, reason, metadata) = match sony_focus::read(path) {
        Ok(Some(meta)) => (
            ReadStatus::Present,
            None,
            Some(metadata_report(meta, OpticalIdentity::read(path), records)),
        ),
        Ok(None) => (ReadStatus::Absent, None, None),
        Err(e) => {
            let status = match &e {
                SonyFocusError::Io(_) => ReadStatus::IoError,
                SonyFocusError::Unsupported(_) => ReadStatus::Unsupported,
                SonyFocusError::Malformed(_) => ReadStatus::Malformed,
            };
            (status, Some(e.to_string()), None)
        }
    };
    FrameReport {
        index,
        path: path.to_owned(),
        file_identity,
        status,
        reason,
        metadata,
        optical: None,
    }
}

fn incompatibility(a: &FrameMetadata, b: &FrameMetadata) -> Option<&'static str> {
    if a.model != b.model || a.software != b.software {
        Some("camera_or_firmware_changed")
    } else if !a.optical_identity.comparable() || !b.optical_identity.comparable() {
        Some("incomplete_optical_identity")
    } else if a.optical_identity != b.optical_identity {
        Some("lens_focal_length_or_aperture_changed")
    } else if a.focus_mode_raw != b.focus_mode_raw {
        Some("focus_mode_changed")
    } else if a.section0_u16[2..10] != b.section0_u16[2..10]
        || a.grid.width != b.grid.width
        || a.grid.height != b.grid.height
        || a.grid.roi_raw != b.grid.roi_raw
        || a.grid.origin_raw != b.grid.origin_raw
        || a.grid.extent_raw != b.grid.extent_raw
    {
        Some("image_or_grid_geometry_changed")
    } else if a.scalar_status_raw != 3 || b.scalar_status_raw != 3 {
        Some("scalar_status_not_observed_layout")
    } else if !a.section_sequences_agree || !b.section_sequences_agree {
        Some("section_sequence_disagreement")
    } else {
        None
    }
}

fn segment(frames: &[FrameReport], first: usize, last: usize) -> SegmentReport {
    let mut deltas = Vec::with_capacity(last - first);
    let mut magnitudes = Vec::new();
    let mut positive = 0;
    let mut negative = 0;
    let mut repeated = 0;
    let mut changes = 0;
    let mut previous_sign = 0;
    for i in first..last {
        let a = frames[i]
            .metadata
            .as_ref()
            .expect("segment contains metadata");
        let b = frames[i + 1]
            .metadata
            .as_ref()
            .expect("segment contains metadata");
        let delta = i64::from(b.scalars_raw[1]) - i64::from(a.scalars_raw[1]);
        let sign = delta.signum();
        let direction_change = sign != 0 && previous_sign != 0 && sign != previous_sign;
        changes += usize::from(direction_change);
        match sign {
            1 => positive += 1,
            -1 => negative += 1,
            _ => repeated += 1,
        }
        if sign != 0 {
            previous_sign = sign;
            magnitudes.push(delta.unsigned_abs());
        }
        let previous_sequence = a.section_sequences[0];
        let sequence = b.section_sequences[0];
        let sequence_delta = sequence.wrapping_sub(previous_sequence);
        deltas.push(DeltaReport {
            from_index: i,
            to_index: i + 1,
            scalar_b_delta: delta,
            sequence_raw_delta: i32::from(sequence) - i32::from(previous_sequence),
            sequence_modulo_65536_delta: sequence_delta,
            sequence_observation: match sequence_delta {
                0 => "repeat",
                1 if sequence < previous_sequence => "unit_increment_modulo_65536",
                1 => "unit_increment",
                _ if sequence < previous_sequence => "decrease_or_wrap",
                _ => "forward_nonunit",
            },
            coarse_delta: a
                .coarse_focus_position
                .zip(b.coarse_focus_position)
                .map(|(a, b)| i16::from(b) - i16::from(a)),
            direction_change,
            larger_than_three_median_deltas: false,
        });
    }
    magnitudes.sort_unstable();
    let median_twice = if magnitudes.is_empty() {
        None
    } else {
        Some(magnitudes[(magnitudes.len() - 1) / 2] + magnitudes[magnitudes.len() / 2])
    };
    // The heuristic needs at least three nonzero differences. It reports a
    // relative metadata jump, never a dropped capture or a physical gap.
    if magnitudes.len() >= 3 {
        let median_twice = median_twice.expect("nonempty magnitudes");
        for d in &mut deltas {
            d.larger_than_three_median_deltas =
                d.scalar_b_delta.unsigned_abs() * 2 > LARGE_DELTA_MULTIPLIER * median_twice;
        }
    }
    SegmentReport {
        first_index: first,
        last_index: last,
        first_scalar_b: frames[first].metadata.as_ref().unwrap().scalars_raw[1],
        last_scalar_b: frames[last].metadata.as_ref().unwrap().scalars_raw[1],
        comparable_pairs: last - first,
        increasing_pairs: positive,
        decreasing_pairs: negative,
        repeated_pairs: repeated,
        direction_changes: changes,
        sequence_non_unit_pairs: deltas
            .iter()
            .filter(|d| d.sequence_modulo_65536_delta != 1)
            .count(),
        sequence_decreasing_pairs: deltas.iter().filter(|d| d.sequence_raw_delta < 0).count(),
        median_absolute_nonzero_delta: median_twice.map(|x| x as f64 / 2.0),
        large_delta_pairs: deltas
            .iter()
            .filter(|d| d.larger_than_three_median_deltas)
            .count(),
        direction: match (positive > 0, negative > 0) {
            (true, true) => "mixed",
            (true, false) => "increasing",
            (false, true) => "decreasing",
            (false, false) => "constant",
        },
        deltas,
    }
}

fn report(frames: Vec<FrameReport>, records: bool) -> AuditReport {
    let mut counts = StatusCounts::default();
    let mut sequence_disagreements = Vec::new();
    for f in &frames {
        match f.status {
            ReadStatus::Present => counts.present += 1,
            ReadStatus::Absent => counts.absent += 1,
            ReadStatus::Unsupported => counts.unsupported += 1,
            ReadStatus::Malformed => counts.malformed += 1,
            ReadStatus::IoError => counts.io_error += 1,
        }
        if f.metadata
            .as_ref()
            .is_some_and(|m| !m.section_sequences_agree)
        {
            sequence_disagreements.push(f.index);
        }
    }
    let mut breaks = Vec::new();
    let mut segments = Vec::new();
    let mut start = None;
    for i in 0..frames.len().saturating_sub(1) {
        let problem = match (&frames[i].metadata, &frames[i + 1].metadata) {
            (Some(a), Some(b)) => incompatibility(a, b),
            _ => Some("metadata_unavailable"),
        };
        if let Some(reason) = problem {
            if let Some(first) = start.take() {
                segments.push(segment(&frames, first, i));
            }
            breaks.push(ComparisonBreak {
                from_index: i,
                to_index: i + 1,
                reason,
            });
        } else if start.is_none() {
            start = Some(i);
        }
    }
    if let Some(first) = start {
        segments.push(segment(&frames, first, frames.len() - 1));
    }
    AuditReport {
        schema: "strehl-sony-focus-audit-v1",
        strehl_version: super::VERSION,
        input_order: "caller order; focus inspect uses non-recursive filename order; never sorted by metadata values",
        records_included: records,
        limits: LIMITS,
        file_count: frames.len(),
        counts,
        section_sequence_disagreement_indices: sequence_disagreements,
        comparison_breaks: breaks,
        scalar_b_segments: segments,
        frames,
    }
}

/// Inspect exactly the caller's input order. Metadata failures are per-file
/// outcomes, never reasons to exclude a RAW from a stack.
pub(crate) fn audit_paths(paths: &[PathBuf], records: bool) -> AuditReport {
    audit_paths_with_optical(paths, records, false)
}

fn audit_paths_with_optical(paths: &[PathBuf], records: bool, optical: bool) -> AuditReport {
    report(
        paths
            .iter()
            .enumerate()
            .map(|(i, p)| {
                let mut frame = inspect_path(i, p, records);
                // Optical facts have their own status even when hidden focus
                // data are absent or malformed. Normal preflight stays unchanged.
                frame.optical = optical.then(|| sony_optical_report::read(p));
                frame
            })
            .collect(),
        records,
    )
}

fn summary_line(report: &AuditReport) -> String {
    let compared: usize = report
        .scalar_b_segments
        .iter()
        .map(|s| s.comparable_pairs)
        .sum();
    let repeated: usize = report
        .scalar_b_segments
        .iter()
        .map(|s| s.repeated_pairs)
        .sum();
    let changes: usize = report
        .scalar_b_segments
        .iter()
        .map(|s| s.direction_changes)
        .sum();
    let jumps: usize = report
        .scalar_b_segments
        .iter()
        .map(|s| s.large_delta_pairs)
        .sum();
    format!(
        "{}/{} decoded; scalar B across {} comparable pairs: {} repeated pairs, {} direction changes, {} large deltas (raw units)",
        report.counts.present, report.file_count, compared, repeated, changes, jumps
    )
}

/// Nonfatal read-only preflight for the normal stack path.
pub(crate) fn print_preflight(paths: &[PathBuf]) {
    if !preflight_enabled(std::env::var_os("STREHL_SONY_FOCUS_AUDIT").as_deref()) {
        return;
    }
    let report = audit_paths(paths, false);
    if report.counts.present > 0 {
        tracing::info!(
            "focus metadata: {}; use `strehl focus inspect` for details; freshness and depth units unvalidated",
            summary_line(&report)
        );
        if !report.comparison_breaks.is_empty() {
            tracing::info!(
                "focus metadata: {} adjacent pairs not compared (missing or incompatible metadata)",
                report.comparison_breaks.len()
            );
        }
    }
    let failed = report.counts.malformed + report.counts.io_error;
    if failed > 0 {
        tracing::warn!(
            "focus metadata: {failed} files could not be inspected; pixel decoding and frame selection continue unchanged"
        );
    }
}

/// Only the explicit value 0 disables normal-stack metadata preflight.
/// Explicit `focus inspect` and `probe` remain available independently.
fn preflight_enabled(setting: Option<&std::ffi::OsStr>) -> bool {
    setting != Some(std::ffi::OsStr::new("0"))
}

/// Concise addition to the existing pixel probe; absence does not fail it.
pub(crate) fn probe_summary(path: &Path) -> String {
    let f = inspect_path(0, path, false);
    match f.metadata {
        Some(m) => format!(
            "{} x {} records; coarse {}; scalar B {} (raw, freshness unvalidated)",
            m.grid.width,
            m.grid.height,
            m.coarse_focus_position
                .map_or_else(|| "unknown".into(), |v| v.to_string()),
            m.scalars_raw[1]
        ),
        None => match f.status {
            ReadStatus::Absent => "absent".into(),
            _ => format!("{:?}: {}", f.status, f.reason.unwrap_or_default()),
        },
    }
}

fn input_paths(input: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>> {
    ensure!(limit != Some(0), "--limit must be at least 1");
    if input.is_file() {
        ensure!(
            input
                .extension()
                .and_then(|x| x.to_str())
                .is_some_and(|x| x.eq_ignore_ascii_case("arw")),
            "expected an ARW file or bracket directory"
        );
        Ok(vec![input.to_owned()])
    } else {
        super::raw_paths(input, limit)
    }
}

fn print_report(report: &AuditReport) {
    println!("Sony focus metadata: {}", summary_line(report));
    println!(
        "Status: {} absent, {} unsupported, {} malformed, {} I/O errors",
        report.counts.absent,
        report.counts.unsupported,
        report.counts.malformed,
        report.counts.io_error
    );
    println!(
        "Order: filename order, not reordered by metadata. Frame indices are zero-based. No image pixels decoded."
    );
    if let Some(m) = report.frames.iter().find_map(|f| f.metadata.as_ref()) {
        let positions: BTreeSet<_> = report
            .frames
            .iter()
            .filter_map(|f| f.metadata.as_ref().and_then(|m| m.coarse_focus_position))
            .collect();
        println!(
            "First metadata: {} / {}; grid {} x {}; coarse focus codes {} distinct",
            m.model,
            m.software,
            m.grid.width,
            m.grid.height,
            positions.len()
        );
        println!(
            "First raw scalars: {:?}; section sequences {:?}",
            m.scalars_raw, m.section_sequences
        );
    }
    for s in &report.scalar_b_segments {
        println!(
            "Frames {}..{}: scalar B {} -> {}, {}, {} repeated pairs, {} direction changes; median |nonzero delta| {:?}, {} deltas > 3 x median",
            s.first_index,
            s.last_index,
            s.first_scalar_b,
            s.last_scalar_b,
            s.direction,
            s.repeated_pairs,
            s.direction_changes,
            s.median_absolute_nonzero_delta,
            s.large_delta_pairs
        );
        if s.sequence_non_unit_pairs > 0 || s.sequence_decreasing_pairs > 0 {
            println!(
                "  Raw sequence observations: {} non-unit modulo increments, {} decreasing values (may wrap or reset; not proof of missing exposures).",
                s.sequence_non_unit_pairs, s.sequence_decreasing_pairs
            );
        }
    }
    for f in report.frames.iter().filter(|f| f.reason.is_some()).take(10) {
        println!(
            "  [{}] {}: {}",
            f.index,
            f.path.display(),
            f.reason.as_deref().unwrap_or_default()
        );
    }
    if !report.comparison_breaks.is_empty() {
        println!(
            "{} adjacent pairs not compared because metadata were missing or incompatible.",
            report.comparison_breaks.len()
        );
    }
    if !report.section_sequence_disagreement_indices.is_empty() {
        println!(
            "Section sequence disagreement at indices {:?}.",
            report.section_sequence_disagreement_indices
        );
    }
    println!(
        "Large deltas are a descriptive heuristic, not proof of missing frames or physical focus gaps."
    );
    println!("Depth units, spatial mapping, flags, and measurement freshness remain unvalidated.");
    if report.frames.iter().any(|frame| frame.optical.is_some()) {
        let present = report
            .frames
            .iter()
            .filter(|frame| {
                frame
                    .optical
                    .as_ref()
                    .is_some_and(|optical| optical.status == ReadStatus::Present)
            })
            .count();
        println!(
            "Optical header facts: {present}/{} present; raw settings and signed tables, no correction activated.",
            report.file_count
        );
        for frame in &report.frames {
            if let Some(optical) = &frame.optical
                && let Some(reason) = &optical.reason
            {
                println!(
                    "  Optical [{}] {}: {reason}",
                    frame.index,
                    frame.path.display()
                );
            }
        }
        println!("Use --out or --html to inspect exact optical fields and provenance.");
    }
}

pub(crate) fn run(args: &InspectArgs) -> Result<()> {
    let paths = input_paths(&args.input, args.limit)?;
    validate_outputs(args)?;
    let report =
        audit_paths_with_optical(&paths, args.records || args.html.is_some(), args.optical);
    print_report(&report);
    if let Some(out) = &args.out {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out)
            .with_context(|| format!("creating new focus report {}", out.display()))?;
        let mut writer = BufWriter::new(file);
        serde_json::to_writer_pretty(&mut writer, &report)
            .context("writing focus metadata JSON")?;
        writer.write_all(b"\n")?;
        writer.flush()?;
        println!("Report: {}", out.display());
    }
    if let Some(out) = &args.html {
        let html = super::sony_focus_report::render(&serde_json::to_value(&report)?);
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(out)
            .with_context(|| format!("creating new focus HTML report {}", out.display()))?;
        file.write_all(html.as_bytes())
            .context("writing focus metadata HTML")?;
        file.flush()?;
        println!("Viewer: {}", out.display());
    }
    Ok(())
}

fn validate_outputs(args: &InspectArgs) -> Result<()> {
    let mut resolved = Vec::new();
    for path in [&args.out, &args.html].into_iter().flatten() {
        ensure!(
            !path.exists(),
            "report destination already exists: {}",
            path.display()
        );
        let parent = path
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        let parent = std::fs::canonicalize(parent)
            .with_context(|| format!("resolving report directory {}", parent.display()))?;
        let name = path
            .file_name()
            .context("report destination needs a file name")?;
        let key = parent.join(name).to_string_lossy().into_owned();
        let key = if cfg!(windows) {
            key.to_lowercase()
        } else {
            key
        };
        ensure!(
            !resolved.contains(&key),
            "JSON and HTML reports need different destinations"
        );
        resolved.push(key);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(index: usize, scalar: u32) -> FrameReport {
        let metadata = FrameMetadata {
            model: "ILCE-7CM2".into(),
            software: "ILCE-7CM2 v2.00".into(),
            optical_identity: OpticalIdentity {
                lens_model: Some("test lens".into()),
                lens_type3: Some(1),
                focal_length_mm: Some(100.0),
                f_number: Some(5.6),
            },
            source_offset: 100,
            source_length: 8192,
            encoded_payload_sha256: "fixture".into(),
            coarse_focus_position: Some(56),
            focus_mode_raw: Some(0),
            section_sequences: [index as u16; 3],
            section_sequences_agree: true,
            section0_u16: [0; 20],
            scalar_status_raw: 3,
            scalars_raw: [0, scalar, 0],
            grid: GridReport {
                width: 33,
                height: 23,
                roi_raw: [0; 4],
                origin_raw: [0; 2],
                extent_raw: [33, 23],
                record_count: 759,
                records_sha256: "fixture".into(),
                signed_display_range: Some([-32000, 32000]),
                signed_display_extreme_32000_count: 0,
                last_flag_bit_0x20_count: 0,
                extreme_flag_association_mismatches: 0,
                flag_pairs: vec![],
                records: None,
            },
            unknown_tail: TailReport {
                length: 0,
                nonzero_bytes: 0,
                sha256: "fixture".into(),
            },
        };
        FrameReport {
            index,
            path: PathBuf::from(format!("{index:03}.ARW")),
            file_identity: FileIdentity {
                byte_length: None,
                modified_unix_ns: None,
            },
            status: ReadStatus::Present,
            reason: None,
            metadata: Some(metadata),
            optical: None,
        }
    }

    fn frames(values: &[u32]) -> Vec<FrameReport> {
        values
            .iter()
            .enumerate()
            .map(|(i, &value)| frame(i, value))
            .collect()
    }

    #[test]
    fn audit_preserves_order_and_detects_plateau_reversal_and_large_delta() {
        let result = report(frames(&[100, 101, 101, 102, 101, 102, 112]), false);
        let s = &result.scalar_b_segments[0];
        assert_eq!(s.direction, "mixed");
        assert_eq!(s.repeated_pairs, 1);
        assert_eq!(s.direction_changes, 2);
        assert_eq!(s.median_absolute_nonzero_delta, Some(1.0));
        assert_eq!(s.large_delta_pairs, 1);
        assert_eq!(
            s.deltas
                .iter()
                .map(|d| d.scalar_b_delta)
                .collect::<Vec<_>>(),
            [1, 0, 1, -1, 1, 10]
        );
        assert_eq!(
            result.frames[6].metadata.as_ref().unwrap().scalars_raw[1],
            112
        );
    }

    #[test]
    fn reversed_monotonic_and_constant_controls_are_not_bad_sweeps() {
        let reversed = report(frames(&[105, 104, 103, 102, 101]), false);
        let s = &reversed.scalar_b_segments[0];
        assert_eq!(
            (s.direction, s.direction_changes, s.large_delta_pairs),
            ("decreasing", 0, 0)
        );
        let null = report(frames(&[100; 5]), false);
        let s = &null.scalar_b_segments[0];
        assert_eq!(
            (s.direction, s.repeated_pairs, s.large_delta_pairs),
            ("constant", 4, 0)
        );
        assert_eq!(s.median_absolute_nonzero_delta, None);
    }

    #[test]
    fn missing_metadata_breaks_adjacency_instead_of_inventing_a_step() {
        let mut rows = frames(&[100, 101, 999, 200, 201]);
        rows[2].status = ReadStatus::Absent;
        rows[2].metadata = None;
        let r = report(rows, false);
        assert_eq!(r.counts.absent, 1);
        assert_eq!(r.scalar_b_segments.len(), 2);
        assert_eq!(r.comparison_breaks.len(), 2);
        assert!(r.scalar_b_segments.iter().all(|s| s.comparable_pairs == 1));
    }

    #[test]
    fn mixed_lens_and_unknown_lens_are_not_pooled() {
        let mut rows = frames(&[100, 101, 10000, 10001, 10002]);
        rows[2]
            .metadata
            .as_mut()
            .unwrap()
            .optical_identity
            .lens_model = Some("different".into());
        rows[4].metadata.as_mut().unwrap().optical_identity = OpticalIdentity::default();
        let r = report(rows, false);
        assert_eq!(r.scalar_b_segments.len(), 1);
        assert_eq!(r.scalar_b_segments[0].comparable_pairs, 1);
        assert_eq!(
            r.comparison_breaks
                .iter()
                .map(|b| b.reason)
                .collect::<Vec<_>>(),
            [
                "lens_focal_length_or_aperture_changed",
                "lens_focal_length_or_aperture_changed",
                "incomplete_optical_identity"
            ]
        );
    }

    #[test]
    fn status_failures_and_sequence_mismatch_are_visible_without_failing_audit() {
        let mut rows = frames(&[1, 2, 3, 4, 5, 6]);
        for (index, status) in [
            (0, ReadStatus::Unsupported),
            (1, ReadStatus::Malformed),
            (2, ReadStatus::IoError),
        ] {
            rows[index].status = status;
            rows[index].metadata = None;
        }
        rows[4].metadata.as_mut().unwrap().section_sequences_agree = false;
        rows[4].metadata.as_mut().unwrap().section_sequences = [4, 3, 4];
        let r = report(rows, false);
        assert_eq!(
            (
                r.counts.present,
                r.counts.unsupported,
                r.counts.malformed,
                r.counts.io_error
            ),
            (3, 1, 1, 1)
        );
        assert_eq!(r.section_sequence_disagreement_indices, [4]);
        assert!(r.scalar_b_segments.is_empty());
    }

    #[test]
    fn large_delta_gate_is_strict_and_requires_a_nontrivial_baseline() {
        let r = report(frames(&[0, 1, 2, 5]), false);
        assert_eq!(r.scalar_b_segments[0].large_delta_pairs, 0); // exactly 3x is not greater
        let r = report(frames(&[0, 1, 2, 6]), false);
        assert_eq!(r.scalar_b_segments[0].large_delta_pairs, 1);
        let r = report(frames(&[0, 1, 100]), false);
        assert_eq!(r.scalar_b_segments[0].large_delta_pairs, 0); // only two nonzero deltas
    }

    #[test]
    fn geometry_camera_firmware_mode_and_status_changes_break_comparisons() {
        let original = frame(0, 100).metadata.unwrap();
        for (reason, change) in [
            ("camera_or_firmware_changed", 0),
            ("camera_or_firmware_changed", 1),
            ("image_or_grid_geometry_changed", 2),
            ("image_or_grid_geometry_changed", 3),
            ("image_or_grid_geometry_changed", 4),
            ("focus_mode_changed", 5),
            ("scalar_status_not_observed_layout", 6),
        ] {
            let mut changed = original.clone();
            match change {
                0 => changed.model = "another body".into(),
                1 => changed.software = "another firmware".into(),
                2 => changed.grid.width = 31,
                3 => changed.grid.roi_raw[0] = 1,
                4 => changed.section0_u16[6] = 1,
                5 => changed.focus_mode_raw = Some(1),
                6 => changed.scalar_status_raw = 4,
                _ => unreachable!(),
            }
            assert_eq!(incompatibility(&original, &changed), Some(reason));
        }
    }

    struct TestDirectory(PathBuf);

    impl TestDirectory {
        fn new() -> Self {
            static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
            let path = std::env::temp_dir().join(format!(
                "strehl-focus-test-{}-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos(),
                NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed),
            ));
            std::fs::create_dir(&path).unwrap();
            Self(path)
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    // Minimal classic TIFF identity, deliberately with no EXIF or pixel payload.
    // The consumer must report absent without invoking the image decoder.
    fn absent_fixture() -> Vec<u8> {
        let mut bytes = vec![0_u8; 96];
        bytes[..8].copy_from_slice(b"II*\0\x08\0\0\0");
        bytes[8..10].copy_from_slice(&2_u16.to_le_bytes());
        for (at, tag, length, offset) in [(10, 0x010f_u16, 5_u32, 64_u32), (22, 0x0110, 10, 80)] {
            bytes[at..at + 2].copy_from_slice(&tag.to_le_bytes());
            bytes[at + 2..at + 4].copy_from_slice(&2_u16.to_le_bytes());
            bytes[at + 4..at + 8].copy_from_slice(&length.to_le_bytes());
            bytes[at + 8..at + 12].copy_from_slice(&offset.to_le_bytes());
        }
        bytes[64..69].copy_from_slice(b"SONY\0");
        bytes[80..90].copy_from_slice(b"ILCE-7CM2\0");
        bytes
    }

    #[test]
    fn real_reader_classifies_absent_unsupported_malformed_and_missing_without_reordering() {
        let dir = TestDirectory::new();
        let absent = absent_fixture();
        let mut unsupported = absent.clone();
        unsupported[67] = b'X';
        std::fs::write(dir.0.join("b.ARW"), &absent).unwrap();
        std::fs::write(dir.0.join("a.arw"), &unsupported).unwrap();
        std::fs::write(dir.0.join("c.ARW"), b"II*\0\x08\0\0\0").unwrap();
        std::fs::write(dir.0.join("ignored.txt"), []).unwrap();
        std::fs::create_dir(dir.0.join("nested")).unwrap();
        std::fs::write(dir.0.join("nested/ignored.ARW"), &absent).unwrap();
        let mut paths = input_paths(&dir.0, None).unwrap();
        assert_eq!(
            paths
                .iter()
                .map(|p| p.file_name().unwrap().to_str().unwrap())
                .collect::<Vec<_>>(),
            ["a.arw", "b.ARW", "c.ARW"]
        );
        assert_eq!(input_paths(&dir.0, Some(2)).unwrap(), paths[..2]);
        assert!(input_paths(&dir.0, Some(0)).is_err());
        paths.reverse();
        paths.push(dir.0.join("missing.ARW"));
        let report = audit_paths(&paths, false);
        assert_eq!(
            (
                report.counts.absent,
                report.counts.unsupported,
                report.counts.malformed,
                report.counts.io_error
            ),
            (1, 1, 1, 1)
        );
        assert_eq!(
            report
                .frames
                .iter()
                .map(|f| f.path.clone())
                .collect::<Vec<_>>(),
            paths
        );
        assert!(report.scalar_b_segments.is_empty());
        assert_eq!(probe_summary(&dir.0.join("b.ARW")), "absent");
        assert_eq!(std::fs::read(dir.0.join("b.ARW")).unwrap(), absent);
    }

    #[test]
    fn inspect_writes_reports_and_refuses_existing_or_colliding_destinations() {
        let dir = TestDirectory::new();
        let input = dir.0.join("source.ARW");
        let source = absent_fixture();
        std::fs::write(&input, &source).unwrap();
        let mut args = InspectArgs {
            input: input.clone(),
            limit: None,
            out: Some(dir.0.join("report.json")),
            html: Some(dir.0.join("report.html")),
            records: false,
            optical: false,
        };
        run(&args).unwrap();
        let json: serde_json::Value =
            serde_json::from_slice(&std::fs::read(args.out.as_ref().unwrap()).unwrap()).unwrap();
        assert_eq!(json["schema"], "strehl-sony-focus-audit-v1");
        assert_eq!(json["counts"]["absent"], 1);
        assert_eq!(json["records_included"], true);
        let html = std::fs::read_to_string(args.html.as_ref().unwrap()).unwrap();
        assert!(html.contains("<!doctype html>") || html.contains("<!DOCTYPE html>"));
        assert!(run(&args).is_err());
        args.out = Some(input.clone());
        args.html = None;
        assert!(run(&args).is_err());
        assert_eq!(std::fs::read(&input).unwrap(), source);
        let collision = dir.0.join("same-output");
        args.out = Some(collision.clone());
        args.html = Some(dir.0.join("./same-output"));
        assert!(run(&args).is_err());
        assert!(!collision.exists());
    }

    #[test]
    fn focus_inspect_is_reachable_through_cli_with_html_or_json() {
        use super::super::{Cli, Command, FocusAction};
        use clap::Parser;
        let cli = Cli::try_parse_from([
            "strehl",
            "focus",
            "inspect",
            "bracket",
            "--html",
            "report.html",
            "--limit",
            "3",
            "--optical",
        ])
        .unwrap();
        let Command::Focus {
            action: FocusAction::Inspect(args),
        } = cli.command
        else {
            panic!("focus inspect was not routed");
        };
        assert_eq!(args.html, Some(PathBuf::from("report.html")));
        assert_eq!(args.limit, Some(3));
        assert!(args.optical);
        assert!(
            Cli::try_parse_from(["strehl", "focus", "inspect", "bracket", "--records"]).is_err()
        );
        assert!(
            Cli::try_parse_from([
                "strehl",
                "focus",
                "inspect",
                "bracket",
                "--out",
                "report.json",
                "--records"
            ])
            .is_ok()
        );
    }

    #[test]
    fn sequence_discontinuities_are_observations_without_invented_capture_gaps() {
        let mut rows = frames(&[100, 101, 102, 103, 104, 105]);
        for (row, sequence) in rows.iter_mut().zip([65534, 65535, 0, 0, 5, 3]) {
            row.metadata.as_mut().unwrap().section_sequences = [sequence; 3];
        }
        let r = report(rows, false);
        let s = &r.scalar_b_segments[0];
        assert_eq!(s.direction_changes, 0);
        assert_eq!(s.large_delta_pairs, 0);
        assert_eq!(s.sequence_non_unit_pairs, 3);
        assert_eq!(s.sequence_decreasing_pairs, 2);
        assert_eq!(
            s.deltas
                .iter()
                .map(|d| d.sequence_observation)
                .collect::<Vec<_>>(),
            [
                "unit_increment",
                "unit_increment_modulo_65536",
                "repeat",
                "forward_nonunit",
                "decrease_or_wrap"
            ]
        );
        assert_eq!(
            s.deltas
                .iter()
                .map(|d| d.sequence_modulo_65536_delta)
                .collect::<Vec<_>>(),
            [1, 1, 0, 5, 65534]
        );
    }

    #[test]
    fn normal_stack_preflight_is_on_unless_explicitly_disabled() {
        use std::ffi::OsStr;
        assert!(preflight_enabled(None));
        assert!(!preflight_enabled(Some(OsStr::new("0"))));
        assert!(preflight_enabled(Some(OsStr::new("1"))));
        assert!(preflight_enabled(Some(OsStr::new("false"))));
        assert!(preflight_enabled(Some(OsStr::new(""))));
    }

    #[test]
    fn export_preserves_record_bits_flags_and_whole_payload_hash() {
        use strehl_raw::sony_focus::{FocusGrid, FocusRecord, FocusScalars};
        let raw = SonyFocusMetadata {
            model: "ILCE-7CM2".into(),
            software: "ILCE-7CM2 v2.00".into(),
            lens_model: Some("test lens".into()),
            coarse_focus_position: Some(56),
            focus_mode: Some(0),
            source_offset: 100,
            source_length: 8192,
            encoded_payload: vec![0; 8192],
            section0: [0; 20],
            grid: FocusGrid {
                sequence: 0,
                roi_raw: [0; 4],
                width: 2,
                height: 1,
                origin_raw: [0; 2],
                extent_raw: [2, 1],
                records: vec![
                    FocusRecord {
                        value_bits: 33536,
                        flags: [1, 32],
                    },
                    FocusRecord {
                        value_bits: 123,
                        flags: [2, 0],
                    },
                ],
            },
            section2: FocusScalars {
                sequence: 0,
                status: 3,
                values_raw: [123, 18543, 0],
            },
            unknown_tail: vec![0; 5036],
        };
        let exported = metadata_report(raw.clone(), OpticalIdentity::default(), true);
        let records = exported.grid.records.unwrap();
        assert_eq!(records.len(), 2);
        assert_eq!(
            (
                records[0].value_bits,
                records[0].signed_display,
                records[0].flags
            ),
            (33536, -32000, [1, 32])
        );
        assert_eq!(
            (
                records[1].value_bits,
                records[1].signed_display,
                records[1].flags
            ),
            (123, 123, [2, 0])
        );
        assert_eq!(exported.grid.last_flag_bit_0x20_count, 1);
        assert_eq!(exported.grid.extreme_flag_association_mismatches, 0);
        let mut changed = raw;
        changed.encoded_payload[3144] = 1; // outside the grid and tail hashes
        let changed = metadata_report(changed, OpticalIdentity::default(), false);
        assert_ne!(
            changed.encoded_payload_sha256,
            exported.encoded_payload_sha256
        );
        assert_eq!(changed.grid.records_sha256, exported.grid.records_sha256);
        assert!(changed.grid.records.is_none());
    }

    #[test]
    fn payload_hash_is_standard_lowercase_sha256() {
        assert_eq!(hex_bytes([0, 15, 16, 255]), "000f10ff");
        assert_eq!(
            hex_bytes(Sha256::digest(b"abc")),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }
}

#[cfg(test)]
#[path = "sony-optical-inspect-tests.rs"]
mod optical_inspection_tests;
