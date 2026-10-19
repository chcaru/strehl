//! Evidence that the developed TIFF and the retained diagnostic maps share
//! one normalized aperture. This is a coordinate certificate, not an image
//! similarity test: matching aspect ratios alone cannot establish it.
//!
//! The writer consumes the compact analysis grid. Binning emits one RGB pixel
//! per quad; demosaicing interleaves that grid to exactly twice each dimension.
//! Crop is already applied before the merge, so its full-plane origin must not
//! be applied a second time to either the maps or the finished photograph.

use crate::pipeline::{CoveragePlan, PipelineProgress, Stage};

/// Start at the requested two-pixel detail scale, or the nearest observed
/// non-base level. Unknown output geometry uses two analysis-grid pixels.
/// The caller must preserve an explicit user choice and adopt at most once.
pub(crate) fn initial_detail_level(
    archive: &crate::process_provenance::AdmissionArchive,
    bands: usize,
    geometry: Option<OutputGeometry>,
) -> Option<usize> {
    let requested = usize::from(geometry.is_none_or(|value| value.pixels_per_quad == 1));
    archive
        .levels()
        .filter(|&level| level < bands)
        .filter(|&level| {
            archive.frames(level).any(|frame| {
                archive.cells(level, frame).is_some_and(|(meta, cells)| {
                    crate::process_sample_glyphs::SampleGeometry::new(level, meta).is_some()
                        && cells.len() > 0
                })
            })
        })
        // Equal distances keep the finer level, independently of mask content.
        .min_by_key(|&level| (level.abs_diff(requested), level))
}

/// The same physical sample spacing in every detail-scale control. A known
/// writer geometry converts analysis-grid samples to final photograph pixels.
pub(crate) fn detail_label(level: usize, geometry: Option<OutputGeometry>) -> String {
    let exponent =
        level as u128 + u128::from(geometry.is_some_and(|value| value.pixels_per_quad == 2));
    let unit = if geometry.is_some() { "photo" } else { "grid" };
    format!("{}px {unit}", detail_spacing(exponent))
}

pub(crate) fn detail_tooltip(level: usize, geometry: Option<OutputGeometry>) -> String {
    let grid = detail_spacing(level as u128);
    let spacing = if let Some(geometry) = geometry {
        let photo = detail_spacing(level as u128 + u128::from(geometry.pixels_per_quad == 2));
        format!("One sample every {photo} photograph pixels ({grid} analysis-grid pixels).")
    } else {
        format!(
            "One sample every {grid} analysis-grid pixels. Photograph pixel scale has not been reported yet."
        )
    };
    format!("{spacing} This is sample spacing, not exact feature width or filter support.")
}

fn detail_spacing(exponent: u128) -> String {
    if exponent < 64 {
        (1u64 << exponent as u32).to_string()
    } else {
        format!("2^{exponent}")
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct OutputGeometry {
    size: [usize; 2],
    pixels_per_quad: usize,
}

impl OutputGeometry {
    pub(crate) fn parse(value: &str) -> Option<Self> {
        let pixels_per_quad = if value.ends_with(", Malvar-He-Cutler demosaic)") {
            2
        } else if value.ends_with(", binned from one 2x2 quad per pixel)") {
            1
        } else {
            return None;
        };
        // A filename may contain parentheses, dimensions, or commas. Anchor
        // the final dimensions immediately before the writer's pixel format.
        let (prefix, _) = value.rsplit_once(", 16-bit RGB, ")?;
        let (_, dimensions) = prefix.rsplit_once(" (")?;
        let (width, height) = dimensions.split_once(" x ")?;
        Some(Self {
            size: [positive(width)?, positive(height)?],
            pixels_per_quad,
        })
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum OutputDomain {
    #[default]
    Unreported,
    Compact {
        size: [usize; 2],
        origin: [usize; 2],
    },
    /// An unfamiliar output-domain statement is not evidence of no crop.
    Unrecognized,
}

impl OutputDomain {
    pub(crate) fn parse(value: &str) -> Self {
        fn compact(value: &str) -> Option<OutputDomain> {
            let value = value
                .strip_prefix("compact Crop ")?
                .strip_suffix("; collapsed plane written directly (no second crop)")?;
            let (size, origin) = value.split_once(" from full-plane origin (")?;
            let (width, height) = size.split_once('x')?;
            let (x, y) = origin.strip_suffix(')')?.split_once(", ")?;
            Some(OutputDomain::Compact {
                size: [positive(width)?, positive(height)?],
                origin: [x.parse().ok()?, y.parse().ok()?],
            })
        }
        compact(value).unwrap_or(Self::Unrecognized)
    }
}

/// A successful certificate means output UV and analysis UV are identical.
/// The caller still owns session identity: only the owned, validated result
/// may be supplied, never an arbitrary image with matching dimensions.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct OutputSpace;

impl OutputSpace {
    /// `decoded_size` is the original TIFF extent, not the GPU texture size.
    /// An overview may have been reduced independently to the device limit.
    pub(crate) fn from_progress(
        progress: &PipelineProgress,
        decoded_size: [u32; 2],
    ) -> Option<Self> {
        if progress.stage != Stage::Complete || progress.bands.is_none_or(|bands| bands == 0) {
            return None;
        }
        let written = progress.output_geometry?;
        if written.size != decoded_size.map(|value| value as usize)
            || decoded_size
                .iter()
                .any(|&value| value == 0 || value > 32_768)
        {
            return None;
        }
        let full = progress.plane_size?;
        if full.contains(&0) {
            return None;
        }
        let (analysis, origin) = match (progress.analysis_size, progress.analysis_origin) {
            (Some(size), Some(origin)) => (size, origin),
            (None, None) => (full, [0, 0]),
            _ => return None,
        };
        if analysis.contains(&0)
            || origin[0].checked_add(analysis[0])? > full[0]
            || origin[1].checked_add(analysis[1])? > full[1]
            || analysis[0].checked_mul(written.pixels_per_quad)? != written.size[0]
            || analysis[1].checked_mul(written.pixels_per_quad)? != written.size[1]
        {
            return None;
        }
        let cropped = analysis != full || origin != [0, 0];
        match progress.output_domain {
            OutputDomain::Unrecognized => return None,
            OutputDomain::Unreported if cropped => return None,
            OutputDomain::Compact { size, origin: at } if size != analysis || at != origin => {
                return None;
            }
            _ => {}
        }
        match progress.coverage_plan {
            Some(CoveragePlan::Cropped {
                width,
                height,
                x,
                y,
                grid_width,
                grid_height,
            }) if [width, height] == analysis
                && [x, y] == origin
                && [grid_width, grid_height] == full => {}
            Some(CoveragePlan::Cropped { .. }) => return None,
            _ if cropped => return None,
            Some(CoveragePlan::Scaled(scale))
                if !scale.is_finite() || scale <= 0.0 || scale > 1.0 =>
            {
                return None;
            }
            _ => {}
        }
        Some(Self)
    }
}

fn positive(value: &str) -> Option<usize> {
    let value = value.parse().ok()?;
    (value > 0).then_some(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mask(
        archive: &mut crate::process_provenance::AdmissionArchive,
        level: usize,
        frame: usize,
        pixels: [u8; 8],
    ) {
        archive.ingest(
            &crate::pipeline::DiagnosticSurface {
                sequence: 1 + level as u64 * 10 + frame as u64,
                frame,
                level,
                kind: crate::pipeline::DiagnosticKind::GateSupport,
                scope: crate::pipeline::DiagnosticScope::Frame,
                scale: crate::pipeline::DiagnosticScale::Linear,
                width: 4,
                height: 2,
                min: 0.0,
                max: 1.0,
                pixels: pixels.to_vec().into(),
                folded: 1,
            },
            [131, 99],
        );
        let (meta, retained) = archive
            .cells(level, frame)
            .expect("fixture mask was retained");
        assert_eq!(meta.samples, [4, 2]);
        assert_eq!(meta.extent, [131, 99]);
        assert_eq!(
            retained.collect::<Vec<_>>(),
            pixels.map(|value| value == 255)
        );
    }

    #[test]
    fn initial_scale_prefers_two_pixels_even_when_another_level_has_more_disagreement() {
        let mut archive = Default::default();
        mask(&mut archive, 0, 0, [255, 0, 0, 0, 0, 0, 0, 0]);
        mask(&mut archive, 0, 1, [0, 0, 0, 0, 0, 0, 0, 255]);
        mask(&mut archive, 1, 0, [0, 255, 255, 255, 255, 255, 255, 255]);
        mask(&mut archive, 1, 1, [255, 255, 255, 255, 255, 255, 255, 0]);
        mask(&mut archive, 2, 0, [255, 255, 255, 255, 0, 0, 0, 0]);
        mask(&mut archive, 2, 1, [0, 0, 0, 0, 255, 255, 255, 255]);
        assert_eq!(archive.len(), 6);
        assert_eq!(
            initial_detail_level(&archive, 3, whole(true).output_geometry),
            Some(0)
        );
        assert_eq!(
            initial_detail_level(&archive, 3, whole(false).output_geometry),
            Some(1)
        );
        assert_eq!(initial_detail_level(&archive, 3, None), Some(1));
        // Making the preferred grid level the base excludes it from election.
        assert_eq!(initial_detail_level(&archive, 1, None), Some(0));
        // More unobserved declared levels cannot manufacture another winner.
        assert_eq!(initial_detail_level(&archive, 20, None), Some(1));
    }

    #[test]
    fn identical_masks_and_single_observations_are_usable_without_claiming_quality() {
        let mut archive = Default::default();
        for frame in 0..2 {
            mask(&mut archive, 0, frame, [255; 8]);
            mask(&mut archive, 1, frame, [0; 8]);
            mask(&mut archive, 2, frame, [255, 255, 255, 255, 0, 0, 0, 0]);
        }
        // A display default does not rank masks by visual interest or density.
        mask(&mut archive, 3, 0, [255, 0, 255, 0, 255, 0, 255, 0]);
        assert_eq!(archive.len(), 7);
        assert_eq!(initial_detail_level(&archive, 4, None), Some(1));
        assert_eq!(initial_detail_level(&Default::default(), 8, None), None);
        let mut single = Default::default();
        mask(&mut single, 1, 9, [0; 8]);
        assert_eq!(initial_detail_level(&single, 4, None), Some(1));
    }

    #[test]
    fn initial_scale_uses_the_nearest_observed_detail_and_never_the_base() {
        let mut archive = Default::default();
        mask(&mut archive, 4, 0, [255; 8]);
        assert_eq!(initial_detail_level(&archive, 4, None), None);
        assert_eq!(initial_detail_level(&archive, 0, None), None);
        assert_eq!(initial_detail_level(&archive, 5, None), Some(4));
        mask(&mut archive, 2, 0, [0; 8]);
        assert_eq!(initial_detail_level(&archive, 4, None), Some(2));
        mask(&mut archive, 0, 0, [0; 8]);
        assert_eq!(initial_detail_level(&archive, 4, None), Some(0));
        assert_eq!(
            initial_detail_level(&archive, 4, whole(true).output_geometry),
            Some(0)
        );
    }

    #[test]
    fn detail_labels_name_photo_or_unknown_grid_units_and_match_writer_geometry() {
        let demosaic = whole(true).output_geometry;
        let binned = whole(false).output_geometry;
        assert_eq!(detail_label(0, demosaic), "2px photo");
        assert_eq!(detail_label(1, demosaic), "4px photo");
        assert_eq!(detail_label(7, demosaic), "256px photo");
        assert_eq!(detail_label(0, binned), "1px photo");
        assert_eq!(detail_label(1, binned), "2px photo");
        assert_eq!(detail_label(7, binned), "128px photo");
        assert_eq!(detail_label(0, None), "1px grid");
        assert_eq!(detail_label(1, None), "2px grid");
        assert_eq!(detail_label(7, None), "128px grid");
        assert!(
            detail_tooltip(1, demosaic).contains("4 photograph pixels (2 analysis-grid pixels)")
        );
        assert!(detail_tooltip(1, binned).contains("2 photograph pixels (2 analysis-grid pixels)"));
        assert!(detail_tooltip(1, None).contains("Photograph pixel scale has not been reported"));
        assert_eq!(detail_label(64, demosaic), "2^65px photo");
    }

    #[test]
    fn initial_scale_rejects_unrenderable_preferred_lattices_and_oversized_domains() {
        for (preferred, extent, geometry) in [
            (1, [4, 2], None),
            (1, [70_000, 99], None),
            (0, [3, 2], whole(true).output_geometry),
            (0, [131, 70_000], whole(true).output_geometry),
        ] {
            let mut archive = crate::process_provenance::AdmissionArchive::default();
            archive.ingest(
                &crate::pipeline::DiagnosticSurface {
                    sequence: 1,
                    frame: 0,
                    level: preferred,
                    kind: crate::pipeline::DiagnosticKind::GateSupport,
                    scope: crate::pipeline::DiagnosticScope::Frame,
                    scale: crate::pipeline::DiagnosticScale::Linear,
                    width: 4,
                    height: 2,
                    min: 0.0,
                    max: 1.0,
                    pixels: vec![255; 8].into(),
                    folded: 1,
                },
                extent,
            );
            let meta = archive
                .metadata(preferred, 0)
                .expect("archive retained the receipt");
            assert!(crate::process_sample_glyphs::SampleGeometry::new(preferred, meta).is_none());
            assert_eq!(initial_detail_level(&archive, 4, geometry), None);
            let fallback = preferred + 1;
            mask(&mut archive, fallback, 0, [255; 8]);
            assert_eq!(initial_detail_level(&archive, 4, geometry), Some(fallback));
            assert_eq!(
                initial_detail_level(&archive, fallback, geometry),
                None,
                "an otherwise usable fallback is excluded when it is the base"
            );
        }
    }

    fn whole(demosaic: bool) -> PipelineProgress {
        let mut progress = PipelineProgress::default();
        progress.ingest("planes : 131 x 99 per CFA plane\nbands : 7 Laplacian levels + 1 base, coarsest 2 x 1\n");
        progress.ingest(if demosaic {
            "wrote : C:\\results\\stack.tiff (262 x 198, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n"
        } else {
            "wrote : C:\\results\\stack.tiff (131 x 99, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, binned from one 2x2 quad per pixel)\n"
        });
        progress.mark_complete();
        progress
    }

    fn cropped(demosaic: bool) -> PipelineProgress {
        let mut progress = whole(demosaic);
        progress.ingest("analysis domain : 105 x 81 at full-plane origin (9, 7) -- Crop is applied before the merge\ncoverage : CROPPED to the region EVERY frame covers -- 105 x 81 plane px at (9, 7) of 131 x 99, emitted at UNITY SCALE.\noutput domain : compact Crop 105x81 from full-plane origin (9, 7); collapsed plane written directly (no second crop)\n");
        progress.ingest(if demosaic {
            "wrote : crop.tiff (210 x 162, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)\n"
        } else {
            "wrote : crop.tiff (105 x 81, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)\n"
        });
        progress
    }

    #[test]
    fn exact_writer_geometry_supports_bin_and_demosaic_but_not_a_gpu_overview() {
        assert!(OutputSpace::from_progress(&whole(false), [131, 99]).is_some());
        assert!(OutputSpace::from_progress(&whole(true), [262, 198]).is_some());
        assert!(OutputSpace::from_progress(&whole(true), [83, 63]).is_none());
        assert!(OutputSpace::from_progress(&whole(false), [262, 198]).is_none());
        // Same aspect ratio alone would wrongly admit this unrelated extent.
        assert!(OutputSpace::from_progress(&whole(true), [524, 396]).is_none());
    }

    #[test]
    fn fitted_coverage_scale_does_not_shrink_the_final_uv_a_second_time() {
        let mut progress = whole(true);
        progress.ingest(
            "coverage : field of view scaled to 0.7312 so that EVERY frame covers every pixel\n",
        );
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_some());
        assert!(OutputSpace::from_progress(&progress, [192, 145]).is_none());
    }

    #[test]
    fn compact_crop_uses_the_analysis_aperture_without_a_second_origin_offset() {
        for (demosaic, extent) in [(false, [105, 81]), (true, [210, 162])] {
            let progress = cropped(demosaic);
            assert_eq!(progress.analysis_origin, Some([9, 7]));
            assert_eq!(progress.analysis_size, Some([105, 81]));
            assert!(OutputSpace::from_progress(&progress, extent).is_some());
            assert!(OutputSpace::from_progress(&progress, [262, 198]).is_none());
        }
    }

    #[test]
    fn incomplete_or_conflicting_crop_evidence_never_enables_a_guess() {
        for defect in 0..7 {
            let mut progress = cropped(true);
            match defect {
                0 => progress.analysis_origin = None,
                1 => progress.output_domain = OutputDomain::Unreported,
                2 => progress.coverage_plan = Some(CoveragePlan::Whole),
                3 => progress.analysis_origin = Some([27, 7]), // exceeds full width
                4 => progress.analysis_size = None,
                5 => progress.analysis_origin = Some([8, 7]), // in bounds, wrong crop
                _ => {
                    progress.output_domain = OutputDomain::Compact {
                        size: [105, 81],
                        origin: [8, 7],
                    }
                }
            }
            assert!(
                OutputSpace::from_progress(&progress, [210, 162]).is_none(),
                "defect {defect}"
            );
        }
    }

    #[test]
    fn an_unrecognized_writer_or_domain_clears_previous_evidence() {
        let mut progress = whole(true);
        progress.ingest("wrote : other.tiff (262 x 198, 16-bit RGB)\n");
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_none());
        let mut progress = whole(true);
        progress.ingest("output domain : late crop without an origin\n");
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_none());
    }

    #[test]
    fn completion_and_supported_pyramid_metadata_are_required() {
        let mut progress = whole(true);
        progress.stage = Stage::Rendering;
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_none());
        progress.mark_complete();
        progress.bands = None;
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_none());
    }

    #[test]
    fn writer_parser_cannot_take_dimensions_from_the_filename() {
        let parsed = OutputGeometry::parse("C:\\capture (999 x 333, 16-bit RGB, camera)\\stack (demo).tiff (262 x 198, 16-bit RGB, sRGB (BT.709), Malvar-He-Cutler demosaic)").unwrap();
        assert_eq!(parsed.size, [262, 198]);
        assert_eq!(parsed.pixels_per_quad, 2);
        assert!(
            OutputGeometry::parse(
                "result.tiff (0 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)"
            )
            .is_none()
        );
        assert!(
            OutputGeometry::parse("result.tiff (262 x 198, 16-bit RGB, sRGB, unknown renderer)")
                .is_none()
        );
    }

    #[test]
    fn writer_geometry_survives_single_character_delivery() {
        let mut progress = whole(true);
        progress.output_geometry = None;
        let line = "wrote : done.tiff (262 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)\r\n";
        for character in line.chars() {
            progress.ingest(&character.to_string());
        }
        assert!(OutputSpace::from_progress(&progress, [262, 198]).is_some());
    }

    /// Manual receipt check, deliberately not a silent optional fixture. The
    /// caller names an existing owned render log and its TIFF; corpus RAWs are
    /// neither read nor processed. Run with `--ignored --exact` and both envs.
    #[test]
    #[ignore = "requires STREHL_UI_GEOMETRY_LOG and STREHL_UI_GEOMETRY_TIFF"]
    fn retained_writer_receipt_matches_its_decoded_tiff() {
        let log = std::env::var_os("STREHL_UI_GEOMETRY_LOG").expect("fixture log path");
        let tiff = std::env::var_os("STREHL_UI_GEOMETRY_TIFF").expect("fixture TIFF path");
        let mut progress = PipelineProgress::default();
        progress.ingest(&std::fs::read_to_string(log).expect("read existing render log"));
        progress.mark_complete();
        let (width, height) = image::ImageReader::open(tiff)
            .expect("open existing TIFF")
            .with_guessed_format()
            .expect("TIFF format")
            .into_dimensions()
            .expect("TIFF dimensions");
        assert!(OutputSpace::from_progress(&progress, [width, height]).is_some());
        // The same log must reject another image extent, even at the same
        // aspect ratio. This is the fail input for the receipt's scope check.
        assert!(OutputSpace::from_progress(&progress, [width / 2, height / 2]).is_none());
        eprintln!("Verified retained TIFF geometry: {width} x {height}");
    }
}
