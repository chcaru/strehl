//! Bounded, opt-in original-CFA reconstruction layered on the native result.
//! Full-sweep decisions are compact; original u16 handles are pinned per cohort.
//! Neither an aligned volume nor a second demosaic is constructed here.
use super::reconstruction_plan::{FocusSummary, Rect, Skip, Tile};
use super::*;
use crate::image_out::session_reconstruction_output::{NativeCameraImage, NativeNormalization};
use crate::session_focus::complete_support;
use crate::session_reconstruction_sampling::RegionSampler;
use rayon::prelude::*;
use std::{
    collections::BTreeMap,
    fs::OpenOptions,
    io::{BufWriter, Read, Write},
    sync::Arc,
};
use strehl_core::reconstruction::{registration, registration_global, registration_graph as graph};
use strehl_core::{boxfilter::box_mean, plane::PlaneGeometry, reconstruction::*};

const LABELS: [&str; 13] = [
    "All RGB channels reconstructed",
    "Too few independent acquisitions",
    "Sampling phases are ill-conditioned",
    "Focus, motion or source support refused",
    "Conditional variance limit",
    "Native fallback unavailable",
    "Local regression overshoot",
    "Local registration not supported",
    "Primary appearance retained",
    "No qualified focus",
    "Original-source memory budget",
    "No independent guide acquisition",
    "Guide support missing",
];
const MAX_TILE_WORKERS: usize = 16;
const GLOBAL_GEOMETRY_BUDGET: usize = 16 << 20;
#[path = "session-reconstruction-motion.rs"]
mod motion;

struct Fields {
    focus: Vec<f32>,
    motion: Vec<f32>,
    valid: Vec<bool>,
    bound: Vec<f32>,
}
struct Outcome {
    rect: Rect,
    rgb: Option<Vec<[f32; 3]>>,
    reason: Vec<u8>,
    registration_supported: bool,
    report: Value,
}
struct Contexts<'a> {
    session: &'a ResolvedSession,
    alignment: &'a SessionAlignment,
    calibrations: &'a [Calibration],
    gains: &'a [f32],
    domain: SamplingDomain,
    focus: &'a [FocusSummary],
    originals: &'a BTreeMap<usize, Arc<CachedSource>>,
    image: &'a NativeCameraImage,
    normalization: NativeNormalization,
}
fn err(s: String) -> anyhow::Error {
    anyhow::anyhow!(s)
}
fn interp(plane: &[f32], g: PlaneGeometry, x: f64, y: f64) -> f32 {
    let x = x.clamp(0., (g.width - 1) as f64);
    let y = y.clamp(0., (g.height - 1) as f64);
    let (ix, iy) = (x.floor() as usize, y.floor() as usize);
    let (jx, jy) = ((ix + 1).min(g.width - 1), (iy + 1).min(g.height - 1));
    let (dx, dy) = ((x - ix as f64) as f32, (y - iy as f64) as f32);
    (1. - dy) * ((1. - dx) * plane[iy * g.width + ix] + dx * plane[iy * g.width + jx])
        + dy * ((1. - dx) * plane[jy * g.width + ix] + dx * plane[jy * g.width + jx])
}
fn green(p: &[Vec<f32>; 4], out: &mut [f32]) {
    for (i, v) in out.iter_mut().enumerate() {
        *v = 0.5 * (p[1][i] + p[3][i]);
    }
}
fn skipped(tile: &Tile, code: u8) -> Outcome {
    Outcome {
        rect: tile.rect,
        rgb: None,
        reason: vec![code; tile.rect.width * tile.rect.height],
        registration_supported: false,
        report: json!({"rect":[tile.rect.x,tile.rect.y,tile.rect.width,tile.rect.height],
            "sources":tile.sources,"guides":tile.guides,"retained_native_reason":LABELS[usize::from(code)]}),
    }
}
fn window_fits(
    source: &registration::OriginalView<'_>,
    window: registration::Window,
    color: registration::PlaneKind,
) -> bool {
    let (channel, site) = match color {
        registration::PlaneKind::Red => (0, [0., 0.]),
        registration::PlaneKind::GreenLuma => (1, [0.5, 0.5]),
        registration::PlaneKind::Blue => (2, [1., 1.]),
    };
    let pull = registration::plane_pull(source.color_pulls[channel], color);
    let center = pull.apply_at(
        (window.center_sensor[0] - site[0]) * 0.5,
        (window.center_sensor[1] - site[1]) * 0.5,
        window.full.width as f64 * 0.5,
        window.full.height as f64 * 0.5,
    );
    let x = (center.0 - window.side_quad as f64 * 0.5).floor();
    let y = (center.1 - window.side_quad as f64 * 0.5).floor();
    x >= 0.
        && y >= 0.
        && x + window.side_quad as f64 <= window.full.width as f64
        && y + window.side_quad as f64 <= window.full.height as f64
}
fn registration_pairs(count: usize, anchor: usize) -> BTreeSet<(usize, usize)> {
    let mut pairs = BTreeSet::new();
    let others: Vec<_> = (0..count).filter(|&s| s != anchor).collect();
    for &s in &others {
        pairs.insert((s.min(anchor), s.max(anchor)));
    }
    // Connect the non-anchor list, including across an interior anchor index.
    // Every leaf then participates in a measured, independent anchor triangle.
    for edge in others.windows(2) {
        pairs.insert((edge[0], edge[1]));
    }
    pairs
}
fn original_cache_budget(available: usize, original_bytes: usize, sources: usize) -> Result<usize> {
    // MAX_SOURCES constrains one estimator, not the union of concurrent tiles.
    // Reserving only one tile's originals needlessly serializes cohorts and
    // repeatedly rereads the same u16 CFA on a machine with spare memory.
    let census = sources
        .checked_add(1)
        .and_then(|n| original_bytes.checked_mul(n))
        .context("original pin reservation overflow")?;
    Ok((available / 2).min(census))
}
fn process(tile: &Tile, c: &Contexts<'_>) -> Result<Outcome> {
    if let Some(skip) = tile.skip {
        return Ok(skipped(
            tile,
            match skip {
                Skip::NoFocus => 9,
                Skip::SourceBudget => 10,
                Skip::NoIndependentGuide => 11,
            },
        ));
    }
    if tile.sources.len() < 3 {
        return Ok(skipped(tile, 1));
    }
    let started = Instant::now();
    let r = tile.rect;
    let n = r.width * r.height;
    let lattice = OutputLattice {
        full: c.domain.full,
        origin_sensor: [(c.domain.x * 2 + r.x) as f64, (c.domain.y * 2 + r.y) as f64],
        step_sensor: [1., 1.],
        width: r.width,
        height: r.height,
    };
    // Guide plugin halo covers box blur, interpolation, derivative and mask.
    let x = (c.domain.x + r.x / 2).saturating_sub(8);
    let y = (c.domain.y + r.y / 2).saturating_sub(8);
    let endx = (c.domain.x + (r.x + r.width).div_ceil(2) + 8).min(c.domain.full.width);
    let endy = (c.domain.y + (r.y + r.height).div_ceil(2) + 8).min(c.domain.full.height);
    let domain = SamplingDomain {
        full: c.domain.full,
        x,
        y,
        width: endx - x,
        height: endy - y,
    };
    let g = PlaneGeometry {
        width: domain.width,
        height: domain.height,
    };
    let qn = g.pixels();
    let mut sampler = RegionSampler::new(domain, 32 << 20)?;
    let mut scratch = vec![0.; qn];
    let mut blur = vec![0.; qn];
    let mut green_buf = vec![0.; qn];
    let mut mask_scratch = vec![0u32; qn];
    let mut support = vec![false; qn];
    let mut guide: [Vec<f32>; 3] = std::array::from_fn(|_| vec![0.; qn]);
    let mut guide_valid = vec![true; qn];
    for &i in &tile.guides {
        let source = &c.originals[&i];
        let pass = c.session.frames[i].pass_index;
        let sampled = sampler.gather(
            source.as_ref(),
            source.levels(),
            c.alignment.map.placement(i)?,
            c.calibrations[pass].profile,
            c.alignment.map.resampler(),
        )?;
        green(&sampled.planes, &mut green_buf);
        for (channel, guide_plane) in guide.iter_mut().enumerate() {
            let values = match channel {
                0 => &sampled.planes[0],
                2 => &sampled.planes[2],
                _ => &green_buf,
            };
            box_mean(values, g, 3, &mut scratch, &mut blur);
            for p in 0..qn {
                guide_plane[p] += blur[p] * c.gains[pass] / tile.guides.len() as f32;
            }
        }
        complete_support(&sampled.support, g, 6, &mut mask_scratch, &mut support)?;
        for p in 0..qn {
            guide_valid[p] &= support[p];
        }
    }
    let coords: Vec<_> = (0..n)
        .map(|p| {
            let v = lattice.position(p % r.width, p / r.width);
            [
                (v[0] - 0.5) * 0.5 - domain.x as f64,
                (v[1] - 0.5) * 0.5 - domain.y as f64,
            ]
        })
        .collect();
    let nearest: Vec<_> = coords
        .iter()
        .map(|p| {
            p[1].round().clamp(0., (g.height - 1) as f64) as usize * g.width
                + p[0].round().clamp(0., (g.width - 1) as f64) as usize
        })
        .collect();
    if !nearest.iter().any(|&q| guide_valid[q]) {
        return Ok(skipped(tile, 12));
    }
    let expected: Vec<[f32; 3]> = coords
        .iter()
        .map(|p| std::array::from_fn(|channel| interp(&guide[channel], g, p[0], p[1])))
        .collect();
    let tensor: Vec<_> = coords
        .iter()
        .map(|p| {
            let dx = (interp(&guide[1], g, p[0] + 1., p[1])
                - interp(&guide[1], g, p[0] - 1., p[1]))
                * 0.25;
            let dy = (interp(&guide[1], g, p[0], p[1] + 1.)
                - interp(&guide[1], g, p[0], p[1] - 1.))
                * 0.25;
            let jitter = (dx * dx + dy * dy) * 1e-6 + 1e-6;
            [dx * dx + jitter, dx * dy, dy * dy + jitter]
        })
        .collect();
    let mean = std::array::from_fn(|channel| {
        expected
            .iter()
            .enumerate()
            .filter(|(p, _)| guide_valid[nearest[*p]])
            .map(|(_, rgb)| f64::from(rgb[channel]))
            .sum::<f64>()
            / nearest.iter().filter(|&&q| guide_valid[q]).count() as f64
    })
    .map(|v| v as f32);
    let pulls: Vec<_> = tile
        .sources
        .iter()
        .map(|&i| {
            Ok(channel_pulls(
                c.alignment.map.placement(i)?,
                c.calibrations[c.session.frames[i].pass_index].profile,
            ))
        })
        .collect::<Result<_>>()?;
    let originals: Vec<_> = tile
        .sources
        .iter()
        .enumerate()
        .map(|(s, &i)| {
            let pass = c.session.frames[i].pass_index;
            registration::OriginalView {
                acquisition_id: i as u64,
                source: c.originals[&i].as_ref(),
                color_pulls: pulls[s],
                noise: CfaPlane::ALL.map(|p| *c.calibrations[pass].noise.plane(p)),
                gain: c.gains[pass],
                frozen_expected_rgb: mean,
            }
        })
        .collect();
    // Anchor is a qualified focus source, preferring the explicitly selected
    // primary pass. Every other source has a direct edge plus measured triangles.
    let score = |s: usize| {
        let i = tile.sources[s];
        let pass = c.session.frames[i].pass_index;
        (0..n)
            .map(|p| {
                let q = ((r.y + p / r.width) / 2) * c.domain.width + (r.x + p % r.width) / 2;
                f64::from(c.focus[pass].response(i, q))
            })
            .sum::<f64>()
    };
    let primary = c.session.primary_pass_index();
    let scores: Vec<_> = (0..originals.len()).map(score).collect();
    let eligible: Vec<_> = (0..originals.len())
        .filter(|&s| primary.is_none_or(|p| c.session.frames[tile.sources[s]].pass_index == p))
        .collect();
    let anchor = eligible
        .into_iter()
        .max_by(|&a, &b| scores[a].total_cmp(&scores[b]))
        .unwrap_or_else(|| {
            (0..originals.len())
                .max_by(|&a, &b| scores[a].total_cmp(&scores[b]))
                .unwrap()
        });
    let pairs = registration_pairs(originals.len(), anchor);
    let window = registration::Window {
        full: lattice.full,
        center_sensor: [
            lattice.origin_sensor[0] + (r.width - 1) as f64 * 0.5,
            lattice.origin_sensor[1] + (r.height - 1) as f64 * 0.5,
        ],
        side_quad: 192,
    };
    let policy = registration::Policy {
        geometry_lowpass_sigma_quad: 1.2,
        tile_quad: 46,
        grid_axis: 3,
        budget_bytes: 4 << 20,
        ..Default::default()
    };
    let maximum_pairs = pairs
        .len()
        .checked_mul(3)
        .context("local pair count overflow")?;
    let geometry_reservation =
        registration_global::reservation_bytes(originals.len(), maximum_pairs, window.side_quad)?;
    ensure!(
        geometry_reservation <= GLOBAL_GEOMETRY_BUDGET,
        "local original-evidence graph exceeds its worker reservation"
    );
    let mut evidence = Vec::with_capacity(maximum_pairs);
    for (a, b) in pairs {
        for color in [
            registration::PlaneKind::Red,
            registration::PlaneKind::GreenLuma,
            registration::PlaneKind::Blue,
        ] {
            if !window_fits(&originals[a], window, color)
                || !window_fits(&originals[b], window, color)
            {
                continue;
            }
            evidence.push(
                registration::measure_pair_with_footprints(
                    &originals[a],
                    &originals[b],
                    window,
                    color,
                    policy,
                )
                .map_err(err)?,
            );
        }
    }
    let nodes: Vec<_> = originals
        .iter()
        .map(|o| graph::Node {
            acquisition: o.acquisition_id,
            color_pulls: o.color_pulls,
        })
        .collect();
    let origin = lattice.origin_sensor;
    let end = lattice.position(r.width - 1, r.height - 1);
    if evidence.is_empty() {
        return Ok(skipped(tile, 7));
    }
    let corrected = match registration_global::solve(
        &nodes,
        anchor,
        graph::Domain {
            full: lattice.full,
            corners_sensor: [origin, [end[0], origin[1]], [origin[0], end[1]], end],
        },
        &evidence,
        Default::default(),
        GLOBAL_GEOMETRY_BUDGET,
    ) {
        Ok(corrected) => corrected,
        Err(registration_global::CorrectionError::Refused(reason)) => {
            let mut result = skipped(tile, 7);
            result.report["registration_refusal"] = json!(format!("{reason:?}"));
            result.report["geometry_reservation_bytes"] = json!(geometry_reservation);
            result.report["seconds"] = json!(started.elapsed().as_secs_f64());
            return Ok(result);
        }
        Err(error) => return Err(error.into()),
    };
    // The same returned pulls drive motion support and final original sampling.
    // Holdouts score those pulls, never the saved-map approximation.
    let certificate = corrected.certificate;
    drop(evidence);
    drop(corrected.pairs);
    let admitted = certificate
        .sources
        .iter()
        .filter(|s| s.admitted_rgb.iter().all(|&v| v))
        .count();
    let mut report = json!({"rect":[r.x,r.y,r.width,r.height],"sources":tile.sources,"guides":tile.guides,
        "anchor_acquisition":certificate.anchor_acquisition,"registration_admitted_sources":admitted,
        "passed_edges_rgb":certificate.passed_edges_rgb,"cycle_rank_rgb":certificate.cycle_rank_rgb,
        "passed_anchor_triangles_rgb":certificate.passed_anchor_triangles_rgb,
        "maximum_cycle_error_sensor_rgb":certificate.maximum_cycle_error_sensor_rgb,
        "geometry_reservation_bytes":geometry_reservation,
        "training_edges_rgb":corrected.training_edges_rgb,
        "training_cycle_rank_rgb":corrected.training_cycle_rank_rgb,
        "training_policy":"direct global unit-weight solve, one IRLS iteration, no smoothness prior",
        "graph_wide_original_train_heldout_disjoint":true,
        "window_center_sensor":window.center_sensor,"window_side_quad":window.side_quad,
        "certificates":certificate.sources.iter().map(|source|json!({"acquisition":source.acquisition,
            "admitted_rgb":source.admitted_rgb,"direct_anchor_max_error_sensor":source.direct_anchor_max_error_sensor,
            "passed_anchor_triangles_rgb":source.passed_anchor_triangles_rgb,
            "consuming_pull_bits":source.consuming_color_pulls.map(|p|[p.a.re.to_bits(),p.a.im.to_bits(),p.b.re.to_bits(),p.b.im.to_bits()])})).collect::<Vec<_>>()});
    if admitted < 3 {
        let mut result = skipped(tile, 7);
        report["seconds"] = json!(started.elapsed().as_secs_f64());
        result.report = report;
        return Ok(result);
    }
    let mut fields = Vec::new();
    let guide_calibrations: Vec<_> = tile
        .guides
        .iter()
        .map(|&i| {
            let pass = c.session.frames[i].pass_index;
            motion::Calibration {
                noise: CfaPlane::ALL.map(|p| *c.calibrations[pass].noise.plane(p)),
                gain: c.gains[pass],
            }
        })
        .collect();
    for (s, &i) in tile.sources.iter().enumerate() {
        let pass = c.session.frames[i].pass_index;
        let source = &c.originals[&i];
        let cert = &certificate.sources[s];
        let certified = cert.admitted_rgb.iter().all(|&v| v);
        let bound = if certified {
            cert.direct_anchor_max_error_sensor
                .iter()
                .copied()
                .fold(0., f64::max) as f32
        } else {
            1.
        };
        let mut f = Fields {
            focus: vec![0.; n],
            motion: vec![0.; n],
            valid: vec![false; n],
            bound: vec![bound; n],
        };
        if certified {
            let sampled = sampler.gather_pulls(
                source.as_ref(),
                source.levels(),
                cert.consuming_color_pulls,
                c.alignment.map.resampler(),
            )?;
            f.motion = motion::confidences(
                &sampled.planes,
                motion::Calibration {
                    noise: CfaPlane::ALL.map(|p| *c.calibrations[pass].noise.plane(p)),
                    gain: c.gains[pass],
                },
                motion::Guide {
                    geometry: g,
                    planes: &guide,
                    coords: &coords,
                    expected: &expected,
                    calibrations: &guide_calibrations,
                },
            );
            complete_support(&sampled.support, g, 4, &mut mask_scratch, &mut support)?;
            for p in 0..n {
                let q = ((r.y + p / r.width) / 2) * c.domain.width + (r.x + p % r.width) / 2;
                f.focus[p] = c.focus[pass].response(i, q);
                f.valid[p] = guide_valid[nearest[p]] && support[nearest[p]] && f.focus[p] > 0.;
            }
        }
        fields.push(f);
    }
    let fallback: Vec<[f32; 3]> = (0..n)
        .map(|p| {
            let index = (r.y + p / r.width) * c.image.width + r.x + p % r.width;
            std::array::from_fn(|channel| {
                c.normalization
                    .camera_units(c.image.pixels[index * 3 + channel], channel)
            })
        })
        .collect();
    let fallback_valid = vec![true; n];
    let views: Vec<_> = tile
        .sources
        .iter()
        .enumerate()
        .map(|(s, &i)| {
            let pass = c.session.frames[i].pass_index;
            let f = &fields[s];
            SourceView {
                acquisition_id: i as u64,
                source: c.originals[&i].as_ref(),
                source_pull: certificate.sources[s].consuming_color_pulls,
                noise: CfaPlane::ALL.map(|p| *c.calibrations[pass].noise.plane(p)),
                gain: c.gains[pass],
                admission: Admission {
                    focus: &f.focus,
                    motion: &f.motion,
                    valid: &f.valid,
                    registration_sigma_sensor: &f.bound,
                },
            }
        })
        .collect();
    let result = reconstruct_tile(
        lattice,
        &views,
        FrozenGuide {
            expected_rgb: &expected,
            tensor: &tensor,
            fallback_rgb: &fallback,
            fallback_variance: None,
            fallback_valid: &fallback_valid,
        },
        Config::default(),
    )
    .map_err(err)?;
    let mut reasons = vec![0_u8; n];
    for (p, reason) in reasons.iter_mut().enumerate() {
        if let Some(refusal) = result.reason[p]
            .iter()
            .find(|&&v| v != Reason::Reconstructed)
        {
            *reason = *refusal as u8;
        }
        if let Some(primary) = primary {
            let q = ((r.y + p / r.width) / 2) * c.domain.width + (r.x + p % r.width) / 2;
            let has_primary = tile.sources.iter().any(|&i| {
                c.session.frames[i].pass_index == primary && c.focus[primary].response(i, q) > 0.
            });
            let supported_primary = tile.sources.iter().enumerate().any(|(s, &i)| {
                c.session.frames[i].pass_index == primary
                    && fields[s].valid[p]
                    && fields[s].motion[p] > 0.
                    && fields[s].bound[p] <= 0.15
            });
            if has_primary && !supported_primary {
                *reason = 8;
            }
        }
    }
    report["seconds"] = json!(started.elapsed().as_secs_f64());
    report["region_sampler_peak_bytes"] = json!(sampler.peak_reserved_bytes());
    report["replaced_rgb_pixels"] = json!(reasons.iter().filter(|&&v| v == 0).count());
    Ok(Outcome {
        rect: r,
        rgb: Some(result.rgb),
        reason: reasons,
        registration_supported: true,
        report,
    })
}

fn receipt(path: &Path) -> Result<Value> {
    let mut f = std::fs::File::open(path)?;
    let mut hash = Sha256::new();
    let mut buf = [0_u8; 65536];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hash.update(&buf[..n]);
    }
    Ok(
        json!({"path":path.file_name().context("missing map name")?.to_string_lossy(),
        "sha256":crate::session_input::hex(&hash.finalize()),"bytes":f.metadata()?.len()}),
    )
}
#[allow(clippy::too_many_arguments)]
pub(super) fn run(
    args: &StackArgs,
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    alignment: &SessionAlignment,
    cache: &mut SourceCache,
    calibrations: &[Calibration],
    gains: &[f32],
    domain: SamplingDomain,
    focus: &[FocusSummary],
    destination: &Path,
    image: &mut NativeCameraImage,
    normalization: NativeNormalization,
) -> Result<Value> {
    let started = Instant::now();
    let limit = args.resources.config()?.memory_limit_bytes;
    ensure!(
        focus.len() == session.passes.len()
            && image.width == domain.width * 2
            && image.height == domain.height * 2,
        "reconstruction inputs differ from the native output canvas"
    );
    let original_bytes = domain
        .full
        .pixels()
        .checked_mul(8)
        .context("original CFA bytes overflow")?;
    let plan_bytes = reconstruction_plan::plan_bytes(domain, session.passes.len(), session.len())?;
    let fixed = domain
        .pixels()
        .checked_mul(128)
        .and_then(|n| n.checked_add(cache.budget_bytes()))
        .and_then(|n| n.checked_add(512 << 20))
        .and_then(|n| n.checked_add(reconstruction_plan::summary_bytes(domain, focus.len()).ok()?))
        .and_then(|n| n.checked_add(plan_bytes))
        .context("reconstruction fixed reservation overflow")?;
    // Includes32MiB bounded sampler +64MiB reconstruction +16MiB witnessed
    // global geometry and4MiB active pair measurement,
    // guide/admission arrays, one tile receipt and thread/allocator allowance.
    let per_worker = 160 << 20;
    let available = limit
        .checked_sub(fixed)
        .context("no memory for original-CFA reconstruction")?;
    let cache_budget = original_cache_budget(available, original_bytes, session.len())?;
    let pin_limit = (cache_budget / original_bytes).saturating_sub(1);
    ensure!(
        pin_limit >= 5,
        "reconstruction needs at least five original CFA handles; increase --memory-limit-gib"
    );
    let workers = args
        .resources
        .threads
        .min(MAX_TILE_WORKERS)
        .min((available - cache_budget) / per_worker);
    ensure!(
        workers > 0,
        "no memory for a reconstruction worker; increase --memory-limit-gib"
    );
    let reservation = fixed + cache_budget + workers * per_worker;
    let placed: Vec<_> = alignment
        .map
        .warps()
        .iter()
        .map(|w| w.placed().is_some())
        .collect();
    let tiles = reconstruction_plan::tiles(domain, focus, &placed, pin_limit)?;
    let mut originals_cache = SourceCache::new(cache.root(), session, cache_budget)?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(workers)
        .build()?;
    let mut support = vec![0_f32; image.width * image.height];
    let mut reasons = vec![0_f32; support.len()];
    let root = destination.join("reconstruction");
    std::fs::create_dir(&root)?;
    let mut reports = BufWriter::with_capacity(
        256 << 10,
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(root.join("tiles.json"))?,
    );
    reports.write_all(b"{\"schema\":\"strehl.original-cfa-tiles.v1\",\"tiles\":[\n")?;
    let mut report_count = 0;
    let mut counts = [0_usize; 13];
    let mut registration_supported = 0;
    let mut cohort_sizes = BTreeMap::<usize, usize>::new();
    let mut load_seconds = 0.;
    let mut compute_seconds = 0.;
    let mut publication_seconds = 0.;
    let mut cursor = 0;
    while cursor < tiles.len() {
        let start = cursor;
        let mut union = BTreeSet::new();
        while cursor < tiles.len() && cursor - start < workers {
            let tile = &tiles[cursor];
            let mut next = union.clone();
            next.extend(tile.sources.iter().chain(&tile.guides).copied());
            if !union.is_empty() && next.len() > pin_limit {
                break;
            }
            ensure!(
                next.len() <= pin_limit,
                "tile pin planner exceeded its memory reservation"
            );
            union = next;
            cursor += 1;
        }
        *cohort_sizes.entry(cursor - start).or_default() += 1;
        let load_started = Instant::now();
        let mut originals = BTreeMap::new();
        for i in union {
            let source = originals_cache
                .load(&identities[i])?
                .context("original CFA cache missing after native fusion")?;
            check_source(
                &source,
                &calibrations[session.frames[i].pass_index],
                domain.full,
            )?;
            originals.insert(i, source);
        }
        load_seconds += load_started.elapsed().as_secs_f64();
        let context = Contexts {
            session,
            alignment,
            calibrations,
            gains,
            domain,
            focus,
            originals: &originals,
            image,
            normalization,
        };
        let compute_started = Instant::now();
        let results: Vec<_> = pool.install(|| {
            tiles[start..cursor]
                .par_iter()
                .map(|tile| process(tile, &context))
                .collect::<Result<_>>()
        })?;
        compute_seconds += compute_started.elapsed().as_secs_f64();
        let publication_started = Instant::now();
        for result in results {
            registration_supported += usize::from(result.registration_supported);
            let r = result.rect;
            for p in 0..r.width * r.height {
                let index = (r.y + p / r.width) * image.width + r.x + p % r.width;
                let reason = result.reason[p];
                reasons[index] = f32::from(reason);
                counts[usize::from(reason)] += 1;
                if reason == 0 {
                    let rgb = result
                        .rgb
                        .as_ref()
                        .context("reconstructed tile has no candidate")?[p];
                    for (channel, value) in rgb.into_iter().enumerate() {
                        image.pixels[index * 3 + channel] = normalization.normalize(value, channel);
                    }
                    support[index] = 1.;
                }
            }
            if report_count > 0 {
                reports.write_all(b",\n")?;
            }
            serde_json::to_writer(&mut reports, &result.report)?;
            report_count += 1;
        }
        publication_seconds += publication_started.elapsed().as_secs_f64();
        if start == 0 || cursor == tiles.len() || cursor / 100 != start / 100 {
            eprintln!(
                "original-CFA reconstruction: {cursor}/{} tiles, {} coherent RGB pixels",
                tiles.len(),
                counts[0]
            );
        }
    }
    reports.write_all(b"\n]}\n")?;
    reports.flush()?;
    reports.get_ref().sync_all()?;
    drop(reports);
    let mut files = Vec::new();
    for (name, values) in [
        ("support.tiff", &support),
        ("fallback-reason.tiff", &reasons),
    ] {
        let path = root.join(name);
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray32Float>(
                image.width.try_into()?,
                image.height.try_into()?,
                values,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(receipt(&path)?);
    }
    let labels: BTreeMap<_, _> = LABELS
        .iter()
        .enumerate()
        .map(|(i, &s)| (i.to_string(), s))
        .collect();
    write_json_new(
        &root.join("geometry.json"),
        &json!({"schema":"strehl.original-cfa-reconstruction.v1",
        "full_quad_geometry":[domain.full.width,domain.full.height],"origin_sensor":[domain.x*2,domain.y*2],
        "dimensions":[image.width,image.height],"step_sensor":[1,1],"files":files,"fallback_reasons":labels}),
    )?;
    let reason_counts: BTreeMap<_, _> = LABELS.iter().zip(counts).map(|(&s, n)| (s, n)).collect();
    let cache_stats = originals_cache.stats();
    Ok(
        json!({"requested":true,"enabled":true,"total_rgb_pixels":support.len(),"replaced_rgb_pixels":counts[0],
        "native_fallback_pixels":support.len()-counts[0],"registration_supported_tiles":registration_supported,
        "reason_counts":reason_counts,"geometry_sha256":receipt(&root.join("geometry.json"))?["sha256"],
        "tiles_receipt":receipt(&root.join("tiles.json"))?,"working_memory_reservation_bytes":reservation,
        "workers":workers,"original_pin_limit":pin_limit,"tiles":tiles.len(),"elapsed_seconds":started.elapsed().as_secs_f64(),
        "tile_plan_reservation_bytes":plan_bytes,"per_worker_reservation_bytes":per_worker,
        "original_cache_reservation_bytes":cache_budget,"original_cache":{
            "peak_resident_cfa_bytes":cache_stats.peak_resident_cfa_bytes,
            "memory_hits":cache_stats.memory_hits,"disk_hits":cache_stats.disk_hits,"decodes":cache_stats.decodes},
        "cohort_sizes":cohort_sizes,"original_load_seconds":load_seconds,
        "tile_compute_seconds":compute_seconds,"tile_publication_seconds":publication_seconds,
        "appearance_admission":"minimum independent-guide confidence across red, green and blue",
        "kernel_sigma_sensor":Config::default().sigma_sensor,"geometry_lowpass_sigma_quad":1.2,
        "registration_maximum_error_sensor":0.15,"regression_model":"local-constant",
        "registration_tile_quad":46,"registration_grid_axis":3,
        "registration_correction":"direct global training fit with graph-wide original-site holdouts",
        "limitations":["All channels replace together; refused pixels preserve the exact native camera RGB before the common development.",
            "The output retains native dimensions. Phase support does not establish increased optical resolution.",
            "Local geometry is direct-anchor heldout pair and cycle consistency, not a calibrated statistical uncertainty.",
            "The0.15-sensor-pixel threshold is observed consistency, not a guaranteed absolute placement bound.",
            "Guide photons are withheld from the tile's targets. Focus and motion remain adaptive and do not give unconditional variance.",
            "Native fallback variance is unknown; no native-relative noise reduction is claimed."]}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn session_reconstruction_cache_uses_session_census_within_fixed_half_budget() {
        let original = 64 << 20;
        // Two neighboring64-source estimators may use different originals.
        assert_eq!(
            original_cache_budget(40 << 30, original, 126).unwrap(),
            127 * original
        );
        assert_eq!(
            original_cache_budget(6 << 30, original, 126).unwrap(),
            3 << 30
        );
        assert_eq!(
            original_cache_budget(40 << 30, original, 8).unwrap(),
            9 * original
        );
        assert!(original_cache_budget(usize::MAX, original, usize::MAX).is_err());
        assert!(original_cache_budget(usize::MAX, usize::MAX, 4).is_err());
    }
    #[test]
    fn session_reconstruction_witnessed_graph_fits_every_planned_source_count() {
        for count in 3..=MAX_SOURCES {
            let pairs = registration_pairs(count, count / 2).len() * 3;
            let bytes = registration_global::reservation_bytes(count, pairs, 192).unwrap();
            assert!(bytes <= GLOBAL_GEOMETRY_BUDGET);
            assert!(
                bytes >= registration::OriginalFootprints::reservation_bytes(192).unwrap() * pairs
            );
        }
    }
    #[test]
    fn session_reconstruction_pair_plan_gives_every_anchor_and_source_a_triangle() {
        for count in 3..=64 {
            for anchor in 0..count {
                let pairs = registration_pairs(count, anchor);
                let edge = |a: usize, b: usize| pairs.contains(&(a.min(b), a.max(b)));
                assert!(pairs.len() <= 2 * count - 3);
                for source in 0..count {
                    if source != anchor {
                        assert!(edge(source, anchor));
                        assert!(
                            (0..count).any(|other| other != anchor
                                && other != source
                                && edge(anchor, other)
                                && edge(source, other)),
                            "source{source} lacks a closed triangle for anchor{anchor} in{count} sources"
                        );
                    }
                }
            }
        }
    }
}
