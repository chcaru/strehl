//! Bounded original-CFA gathers through a mosaic's spatial backward map.
//! The output canvas and source geometry are deliberately separate. Nothing is
//! demosaiced or written to u16 after gathering. Unsupported numeric storage
//! remains a sentinel whose typed coverage must be carried by the consumer.

use anyhow::{Result, ensure};
use rayon::prelude::*;
use strehl_core::CfaPlane;
use strehl_core::align::{PlaneRef, Resampler, Similarity};
use strehl_core::mosaic::{BackwardMesh, MappedPoint, MosaicCanvas, PixelRect};
use strehl_core::noise::Levels;
use strehl_core::optics::{OpticalProfile, cfa_site_channel};
use strehl_core::plane::{PlaneGeometry, QuadSource};

use crate::session_sampling::{SampledCfa, footprint_clipped};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MappedSamplingDomain {
    pub canvas: MosaicCanvas,
    pub rect: PixelRect,
}
impl MappedSamplingDomain {
    pub fn validate(self) -> Result<()> {
        ensure!(
            self.canvas.width > 0
                && self.canvas.height > 0
                && self.rect.width > 0
                && self.rect.height > 0,
            "empty mapped sampling geometry"
        );
        ensure!(
            self.rect
                .x
                .checked_add(self.rect.width)
                .is_some_and(|n| n <= self.canvas.width)
                && self
                    .rect
                    .y
                    .checked_add(self.rect.height)
                    .is_some_and(|n| n <= self.canvas.height),
            "mapped sampling rectangle leaves canvas"
        );
        ensure!(
            self.rect.width.checked_mul(self.rect.height).is_some(),
            "mapped sampling pixel count overflow"
        );
        ensure!(
            self.canvas
                .origin
                .iter()
                .all(|&x| x.unsigned_abs() < 1_u64 << 50)
                && (self.canvas.width as u128) < 1_u128 << 50
                && (self.canvas.height as u128) < 1_u128 << 50,
            "mapped sampling coordinate exceeds exact integer range"
        );
        Ok(())
    }
    pub fn pixels(self) -> usize {
        self.rect.width * self.rect.height
    }
}

/// Pixel buffers only; allocation headers and scheduling overhead belong to the
/// caller's total reservation. Source CFA cache storage is counted separately.
pub fn mapped_sampling_bytes(source: PlaneGeometry, domain: MappedSamplingDomain) -> Result<usize> {
    domain.validate()?;
    ensure!(
        source.width >= 2 && source.height >= 2,
        "empty mapped source geometry"
    );
    let bytes = source
        .width
        .checked_mul(source.height)
        .and_then(|n| n.checked_mul(5))
        .and_then(|n| {
            domain
                .pixels()
                .checked_mul(20)
                .and_then(|m| n.checked_add(m))
        })
        .ok_or_else(|| anyhow::anyhow!("mapped sampling reservation overflow"))?;
    ensure!(
        bytes <= isize::MAX as usize,
        "mapped sampling exceeds addressable allocation"
    );
    Ok(bytes)
}

/// Geometry support is separate from source-code clipping and focus evidence.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum GeometrySupport {
    Supported,
    Uncovered,
    Rejected,
    Ambiguous,
}

pub struct NativeMappedSampler {
    source: PlaneGeometry,
    domain: MappedSamplingDomain,
    source_plane: Vec<f32>,
    source_clipped: Vec<bool>,
    output: SampledCfa,
    geometry_support: Vec<GeometrySupport>,
    working_bytes: usize,
}
impl NativeMappedSampler {
    pub fn new(
        source: PlaneGeometry,
        domain: MappedSamplingDomain,
        max_work_bytes: usize,
    ) -> Result<Self> {
        let working_bytes = mapped_sampling_bytes(source, domain)?;
        ensure!(
            working_bytes <= max_work_bytes,
            "mapped sampler exceeds explicit workspace budget"
        );
        Ok(Self {
            source,
            domain,
            source_plane: vec![0.0; source.pixels()],
            source_clipped: vec![false; source.pixels()],
            output: SampledCfa {
                planes: std::array::from_fn(|_| vec![0.0; domain.pixels()]),
                coverage: vec![false; domain.pixels()],
                clipped: vec![false; domain.pixels()],
                support: vec![false; domain.pixels()],
            },
            geometry_support: vec![GeometrySupport::Uncovered; domain.pixels()],
            working_bytes,
        })
    }
    pub fn working_bytes(&self) -> usize {
        self.working_bytes
    }
    pub fn domain(&self) -> MappedSamplingDomain {
        self.domain
    }
    pub fn output(&self) -> &SampledCfa {
        &self.output
    }
    pub fn geometry_support(&self) -> &[GeometrySupport] {
        &self.geometry_support
    }

    /// `pass_map` maps signed canvas coordinates to the pass-anchor guide.
    /// `frame_placement` then pulls that anchor into the individual frame.
    /// Optical correction uses the source's full centre, never the tile centre.
    pub fn gather<S: QuadSource + ?Sized>(
        &mut self,
        source: &S,
        levels: Levels,
        pass_map: &BackwardMesh,
        frame_placement: Similarity,
        profile: Option<&OpticalProfile>,
        resampler: Resampler,
    ) -> Result<&SampledCfa> {
        self.gather_with_mapping(
            source,
            levels,
            &|point| pass_map.map(point),
            frame_placement,
            profile,
            resampler,
        )
    }

    /// Compose an explicitly qualified local map with an original-view fallback
    /// before sampling. The mapping is evaluated independently at every physical
    /// CFA site; selecting a map never adds a second image resampling step.
    #[allow(clippy::too_many_arguments)]
    pub fn gather_with_mapping<S: QuadSource + ?Sized, F>(
        &mut self,
        source: &S,
        levels: Levels,
        mapping: &F,
        frame_placement: Similarity,
        profile: Option<&OpticalProfile>,
        resampler: Resampler,
    ) -> Result<&SampledCfa>
    where
        F: Fn([f64; 2]) -> MappedPoint + Sync,
    {
        ensure!(
            source.geometry() == self.source,
            "mapped source geometry changed"
        );
        ensure!(
            levels.black.is_finite()
                && levels.white.is_finite()
                && levels.white > levels.black
                && levels.white > 0.0
                && levels.white <= 65535.0,
            "invalid mapped source levels"
        );
        validate_placement(frame_placement)?;
        self.output.coverage.fill(true);
        self.output.clipped.fill(false);
        self.output.support.fill(false);
        self.geometry_support.fill(GeometrySupport::Supported);
        let geom = self.source;
        let center = (geom.width as f64 * 0.5, geom.height as f64 * 0.5);
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let (dx, dy) = color.rggb_offset();
            let transform =
                OpticalProfile::compose(profile, cfa_site_channel(dx, dy), frame_placement);
            validate_placement(transform)?;
            let mut any_clipped = false;
            for y in 0..geom.height {
                let (r0, r1) = source.quad_rows(y);
                let row = if dy == 0 { r0 } else { r1 };
                ensure!(row.len() >= 2 * geom.width, "short mapped active CFA row");
                for x in 0..geom.width {
                    let raw = row[2 * x + dx];
                    let i = y * geom.width + x;
                    self.source_plane[i] = f32::from(raw) - levels.black;
                    self.source_clipped[i] = f32::from(raw) >= levels.white;
                    any_clipped |= self.source_clipped[i];
                }
            }
            let plane = PlaneRef::from_geometry(&self.source_plane, geom)
                .expect("validated source geometry");
            let site = (dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25);
            let domain = self.domain;
            let source_clipped = &self.source_clipped;
            let SampledCfa {
                planes,
                coverage,
                clipped,
                ..
            } = &mut self.output;
            planes[ci]
                .par_chunks_mut(domain.rect.width)
                .zip(coverage.par_chunks_mut(domain.rect.width))
                .zip(clipped.par_chunks_mut(domain.rect.width))
                .zip(self.geometry_support.par_chunks_mut(domain.rect.width))
                .enumerate()
                .for_each(|(y, (((values, covered), clipped), geometry))| {
                    for (x, value) in values.iter_mut().enumerate() {
                        let world = domain.canvas.world(
                            (domain.rect.x + x) as f64 + site.0,
                            (domain.rect.y + y) as f64 + site.1,
                        );
                        let point = match mapping(world) {
                            MappedPoint::Supported { source, .. } => source,
                            failed => {
                                *value = 0.0;
                                covered[x] = false;
                                let reason = match failed {
                                    MappedPoint::Uncovered => GeometrySupport::Uncovered,
                                    MappedPoint::Rejected(_) => GeometrySupport::Rejected,
                                    MappedPoint::Ambiguous => GeometrySupport::Ambiguous,
                                    MappedPoint::Supported { .. } => unreachable!(),
                                };
                                geometry[x] = geometry[x].max(reason);
                                continue;
                            }
                        };
                        let (sx, sy) = transform.apply_at(point[0], point[1], center.0, center.1);
                        let (sx, sy) = (sx - site.0, sy - site.1);
                        if let Some(sample) = resampler.sample_checked(plane, sx, sy) {
                            *value = sample;
                            clipped[x] |= any_clipped
                                && footprint_clipped(source_clipped, geom, sx, sy, resampler);
                        } else {
                            *value = 0.0;
                            covered[x] = false;
                            geometry[x] = geometry[x].max(GeometrySupport::Uncovered);
                        }
                    }
                });
        }
        self.output
            .support
            .par_iter_mut()
            .zip(&self.output.coverage)
            .zip(&self.output.clipped)
            .for_each(|((support, &coverage), &clipped)| *support = coverage && !clipped);
        Ok(&self.output)
    }
}
fn validate_placement(t: Similarity) -> Result<()> {
    ensure!(
        [t.a.re, t.a.im, t.b.re, t.b.im]
            .into_iter()
            .all(f64::is_finite)
            && t.a.norm_sq().is_finite()
            && t.a.norm_sq() > 0.0,
        "nonfinite or singular mapped frame placement"
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::Cx;
    use strehl_core::mosaic::{
        FocusEvidence, ForwardMesh, IndexLimits, MeshValidation, Visibility,
    };

    struct Source {
        geom: PlaneGeometry,
        stride: usize,
        data: Vec<u16>,
    }
    impl Source {
        fn ramp(geom: PlaneGeometry) -> Self {
            let stride = 2 * geom.width + 13;
            let mut source = Self {
                geom,
                stride,
                data: vec![65535; stride * (2 * geom.height + 11)],
            };
            for y in 0..2 * geom.height {
                for x in 0..2 * geom.width {
                    source.data[(y + 5) * stride + x + 3] =
                        (1024 + 13 * (x + 3) + 7 * (y + 5)) as u16;
                }
            }
            source
        }
    }
    impl QuadSource for Source {
        fn geometry(&self) -> PlaneGeometry {
            self.geom
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let a = (2 * y + 5) * self.stride + 3;
            let b = a + self.stride;
            (
                &self.data[a..a + 2 * self.geom.width],
                &self.data[b..b + 2 * self.geom.width],
            )
        }
    }
    fn mesh(geom: PlaneGeometry, offset: [f64; 2], visibility: Visibility) -> BackwardMesh {
        let vertices = [
            [0.0, 0.0],
            [(geom.width - 1) as f64, 0.0],
            [0.0, (geom.height - 1) as f64],
            [(geom.width - 1) as f64, (geom.height - 1) as f64],
        ]
        .map(|p| [p[0] + offset[0], p[1] + offset[1]])
        .to_vec();
        let mesh = ForwardMesh::new(
            geom,
            2,
            2,
            vertices,
            vec![visibility],
            vec![
                FocusEvidence {
                    ordinal: 0.0,
                    width: 1.0,
                    usable: true
                };
                4
            ],
        )
        .unwrap();
        BackwardMesh::new(
            &mesh,
            MeshValidation::default(),
            IndexLimits {
                bin_side: 16,
                max_bins: 1000,
                max_entries: 10_000,
            },
        )
        .unwrap()
    }
    fn levels() -> Levels {
        Levels {
            black: 2500.0,
            white: 16000.0,
        }
    }

    #[test]
    fn mapped_gather_matches_absolute_sensor_oracle_with_signed_canvas_and_odd_active_origin() {
        let geom = PlaneGeometry {
            width: 64,
            height: 48,
        };
        let source = Source::ramp(geom);
        let offset = [-20.0, 7.0];
        let map = mesh(geom, offset, Visibility::SingleView);
        let domain = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [-30, -5],
                width: 120,
                height: 100,
            },
            rect: PixelRect {
                x: 25,
                y: 30,
                width: 13,
                height: 11,
            },
        };
        let transform = Similarity {
            a: Cx::new(1.07, 0.03),
            b: Cx::new(0.7, -0.9),
        };
        let mut sampler = NativeMappedSampler::new(geom, domain, 1_000_000).unwrap();
        let out = sampler
            .gather(
                &source,
                levels(),
                &map,
                transform,
                None,
                Resampler::Bilinear,
            )
            .unwrap();
        assert!(out.support.iter().all(|&v| v));
        let mut site_trap = 0.0_f64;
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let (dx, dy) = color.rggb_offset();
            for y in 0..domain.rect.height {
                for x in 0..domain.rect.width {
                    // Independent derivation in physical active sensor coordinates.
                    let world = domain
                        .canvas
                        .world((domain.rect.x + x) as f64, (domain.rect.y + y) as f64);
                    let sensor = [
                        2.0 * (world[0] - offset[0]) + dx as f64,
                        2.0 * (world[1] - offset[1]) + dy as f64,
                    ];
                    let centre = [geom.width as f64 + 0.5, geom.height as f64 + 0.5];
                    let ux = sensor[0] - centre[0];
                    let uy = sensor[1] - centre[1];
                    let sx = transform.a.re * ux - transform.a.im * uy
                        + centre[0]
                        + 2.0 * transform.b.re;
                    let sy = transform.a.im * ux
                        + transform.a.re * uy
                        + centre[1]
                        + 2.0 * transform.b.im;
                    let expected = 1024.0 + 13.0 * (sx + 3.0) + 7.0 * (sy + 5.0) - 2500.0;
                    assert!(
                        (f64::from(out.planes[ci][y * domain.rect.width + x]) - expected).abs()
                            < 0.0002
                    );
                    let wrong =
                        transform.apply_at(world[0] - offset[0], world[1] - offset[1], 32.0, 24.0);
                    let wrong_value = 1024.0
                        + 13.0 * (2.0 * wrong.0 + dx as f64 + 3.0)
                        + 7.0 * (2.0 * wrong.1 + dy as f64 + 5.0)
                        - 2500.0;
                    site_trap = site_trap.max((wrong_value - expected).abs());
                }
            }
        }
        assert!(
            site_trap > 0.2,
            "fixture must expose omitted per-color site coordinates"
        );
        assert!(out.planes.iter().flatten().any(|&v| v < 0.0));
    }

    #[test]
    fn mapped_negative_interpolation_tap_keeps_original_clipping() {
        let geom = PlaneGeometry {
            width: 32,
            height: 32,
        };
        let mut source = Source::ramp(geom);
        source.data[(2 * 10 + 5) * source.stride + 2 * 9 + 3] = 16000;
        let domain = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [0, 0],
                width: 32,
                height: 32,
            },
            rect: PixelRect {
                x: 10,
                y: 10,
                width: 1,
                height: 1,
            },
        };
        let map = mesh(geom, [-0.5, 0.0], Visibility::SingleView);
        let mut sampler = NativeMappedSampler::new(geom, domain, 100_000).unwrap();
        let out = sampler
            .gather(
                &source,
                levels(),
                &map,
                Similarity::IDENTITY,
                None,
                Resampler::CatmullRom,
            )
            .unwrap();
        assert!(out.coverage[0]);
        assert!(out.clipped[0]);
        assert!(!out.support[0]);
        assert!(out.planes[0][0] < 16000.0 - levels().black);
    }

    #[test]
    fn mapped_optical_pull_uses_source_centre_after_spatial_mapping() {
        use strehl_core::optics::A7C2_FE100GM_2XTC_X4CPL;
        let geom = PlaneGeometry {
            width: 64,
            height: 48,
        };
        let source = Source::ramp(geom);
        let profile = OpticalProfile {
            eps_r: 0.12,
            eps_b: Some(-0.08),
            translation: (0.4, -0.3),
            ..A7C2_FE100GM_2XTC_X4CPL
        };
        let domain = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [-100, -60],
                width: 300,
                height: 200,
            },
            rect: PixelRect {
                x: 112,
                y: 74,
                width: 8,
                height: 7,
            },
        };
        let map = mesh(geom, [0.0, 0.0], Visibility::SingleView);
        let mut sampler = NativeMappedSampler::new(geom, domain, 1_000_000).unwrap();
        let out = sampler
            .gather(
                &source,
                levels(),
                &map,
                Similarity::IDENTITY,
                Some(&profile),
                Resampler::Bilinear,
            )
            .unwrap();
        assert!(out.support.iter().all(|&v| v));
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let (dx, dy) = color.rggb_offset();
            let eps = [0.12, 0.0, -0.08, 0.0][ci];
            let offset = if ci == 0 || ci == 2 {
                [0.4, -0.3]
            } else {
                [0.0, 0.0]
            };
            for y in 0..domain.rect.height {
                for x in 0..domain.rect.width {
                    let px = 12.0 + x as f64 + dx as f64 * 0.5 - 0.25;
                    let py = 14.0 + y as f64 + dy as f64 * 0.5 - 0.25;
                    let sx = 2.0 * ((px - 32.0) * (1.0 + eps) + 32.0 + offset[0]) + 0.5;
                    let sy = 2.0 * ((py - 24.0) * (1.0 + eps) + 24.0 + offset[1]) + 0.5;
                    let expected = 1024.0 + 13.0 * (sx + 3.0) + 7.0 * (sy + 5.0) - 2500.0;
                    assert!(
                        (f64::from(out.planes[ci][y * domain.rect.width + x]) - expected).abs()
                            < 0.0002
                    );
                }
            }
        }
    }

    #[test]
    fn mapped_visibility_holes_are_typed_and_budgeted() {
        let geom = PlaneGeometry {
            width: 32,
            height: 32,
        };
        let source = Source::ramp(geom);
        let domain = MappedSamplingDomain {
            canvas: MosaicCanvas {
                origin: [0, 0],
                width: 32,
                height: 32,
            },
            rect: PixelRect {
                x: 10,
                y: 10,
                width: 4,
                height: 4,
            },
        };
        assert!(NativeMappedSampler::new(geom, domain, 1).is_err());
        let map = mesh(geom, [0.0, 0.0], Visibility::Disoccluded);
        let mut sampler = NativeMappedSampler::new(geom, domain, 100_000).unwrap();
        let out = sampler
            .gather(
                &source,
                levels(),
                &map,
                Similarity::IDENTITY,
                None,
                Resampler::Bilinear,
            )
            .unwrap();
        assert!(out.coverage.iter().all(|&v| !v));
        assert!(out.support.iter().all(|&v| !v));
        assert!(out.planes.iter().flatten().all(|&v| v == 0.0));
        assert!(
            sampler
                .geometry_support()
                .iter()
                .all(|&v| v == GeometrySupport::Rejected)
        );
    }
}
