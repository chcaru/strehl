//! Session consumer; original single-directory stacking never calls this path.
use super::{Merged, PyramidDomain, write_merged_observed};
use crate::align_cmd::CropRect;
use crate::session_align::SessionAlignment;
use crate::session_cache::{CachedSource, SourceCache};
use crate::session_cmd::{StackArgs, reserve_output_directory, write_json_new};
use crate::session_input::{
    ResolvedSession, SessionMode, SessionSpec, SourceIdentity, SourceMetadata,
};
use crate::session_sampling::{NativeSampler, ProbeConfig, SamplingDomain, measure_band_transfer};
use crate::session_sampling::{ProbeMemoryEstimate, sampling_bytes};
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::path::Path;
use std::time::Instant;
use strehl_core::CfaPlane;
use strehl_core::align::{Cx, Resampler};
use strehl_core::color::Exposure;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::optics::{OpticalProfile, cfa_site_channel, profile_for_capture_env};
use strehl_core::plane::QuadSource;
use strehl_core::pyramid::session_fusion::{
    GroupMode, GroupPolicy, GroupWorkspace, PreparedSource, SessionMerge, SourceKey,
    workspace_bytes,
};
use strehl_core::warpmap::{FrameWarp, WarpMap};

#[path = "session-transfer-cache.rs"]
mod transfer_cache;

#[path = "session-transfer-prefetch.rs"]
mod transfer_prefetch;

struct Calibration {
    camera: String,
    levels: Levels,
    iso: Option<f32>,
    wb: Option<[f32; 3]>,
    matrix: Option<([[f32; 3]; 3], String)>,
    metadata: crate::session_cache::CachedFrameMetadata,
    noise: NoiseModel,
    profile: Option<&'static OpticalProfile>,
    shutter: f64,
}

fn rational(value: Option<[u32; 2]>, label: &str) -> Result<f64> {
    let [a, b] = value.with_context(|| format!("missing {label} metadata"))?;
    ensure!(a > 0 && b > 0, "invalid {label} metadata");
    Ok(f64::from(a) / f64::from(b))
}
fn same_rational(a: Option<[u32; 2]>, b: Option<[u32; 2]>) -> bool {
    match (a, b) {
        (Some([an, ad]), Some([bn, bd])) => {
            ad > 0 && bd > 0 && u64::from(an) * u64::from(bd) == u64::from(bn) * u64::from(ad)
        }
        _ => false,
    }
}

fn validate_headers(session: &ResolvedSession, metadata: &[SourceMetadata]) -> Result<()> {
    ensure!(metadata.len() == session.len(), "metadata count differs");
    let first = &metadata[0];
    ensure!(
        first.camera_model.is_some(),
        "session needs camera model metadata"
    );
    for pass in &session.passes {
        let lead = &metadata[pass.global_range.start];
        ensure!(
            lead.camera_model == first.camera_model && lead.camera_make == first.camera_make,
            "mixed camera models are not supported in a session"
        );
        ensure!(
            lead.lens_type3 == first.lens_type3 && lead.lens_model == first.lens_model,
            "session lens identities differ"
        );
        for index in pass.global_range.clone() {
            let item = &metadata[index];
            ensure!(
                item.camera_model == lead.camera_model
                    && item.lens_type3 == lead.lens_type3
                    && item.lens_model == lead.lens_model
                    && item.iso == lead.iso
                    && same_rational(item.exposure_time, lead.exposure_time)
                    && same_rational(item.aperture, lead.aperture),
                "pass '{}' changes camera, ISO, exposure or aperture at frame {}; split captures into explicit passes",
                pass.name,
                index
            );
        }
        if session.spec.mode != SessionMode::Layers {
            ensure!(
                lead.iso == first.iso && lead.iso.is_some(),
                "combined passes currently require the same known ISO; use aligned layers for different ISO"
            );
            if session.spec.mode != SessionMode::Hdr {
                ensure!(
                    same_rational(lead.exposure_time, first.exposure_time),
                    "combined passes have different shutter times; use HDR or aligned layers"
                );
            }
            ensure!(
                same_rational(lead.aperture, first.aperture),
                "combined passes require equal aperture until measured photometric normalization is available; use aligned layers"
            );
        }
    }
    Ok(())
}

fn calibration(
    source: &CachedSource,
    metadata: &SourceMetadata,
    max_copy: usize,
) -> Result<Calibration> {
    let frame = source.to_frame(max_copy)?;
    Ok(Calibration {
        camera: source.camera().to_owned(),
        levels: source.levels(),
        iso: source.iso(),
        wb: frame.wb_gains(),
        matrix: frame.xyz_to_cam_rgb_with_source(),
        metadata: source.metadata.clone(),
        noise: strehl_core::profile::noise_model_for(
            source.camera(),
            source.iso(),
            source.levels(),
        ),
        profile: profile_for_capture_env(metadata.camera_model.as_deref(), metadata.lens_type3)?,
        shutter: rational(metadata.exposure_time, "shutter time")?,
    })
}

/// Crop is established from primary-pass coverage when explicitly selected.
/// An automatic reference is geometric only and never becomes a fusion priority.
fn domain(
    session: &ResolvedSession,
    alignment: &SessionAlignment,
    calibration: &[Calibration],
) -> Result<SamplingDomain> {
    let pass = session
        .primary_pass_index()
        .unwrap_or(alignment.report.reference_pass);
    let geometry = alignment.map.geometry();
    let mut warps = Vec::new();
    let selected: Vec<usize> = if session.spec.mode == SessionMode::Layers {
        (0..session.len()).collect()
    } else {
        session.passes[pass].global_range.clone().collect()
    };
    for index in selected {
        let Some(t) = alignment.map.warps()[index].placed() else {
            continue;
        };
        for color in CfaPlane::ALL {
            let (dx, dy) = color.rggb_offset();
            let mut transform = OpticalProfile::compose(
                calibration[session.frames[index].pass_index].profile,
                cfa_site_channel(dx, dy),
                t,
            );
            let delta = Cx::new(dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25);
            transform.b = transform.b + transform.a * delta - delta;
            warps.push(FrameWarp::Placed(transform));
        }
    }
    ensure!(!warps.is_empty(), "framing pass has no placed frames");
    let map = WarpMap::new(
        alignment.map.provenance().clone(),
        geometry,
        alignment.map.resampler(),
        warps,
    );
    let margin = if alignment.map.resampler() == Resampler::Lanczos3 {
        4.0
    } else {
        3.0
    };
    let scale = crate::align_cmd::cover_scale(&map, margin)
        .context("passes have no covered common canvas")?;
    let rect = crate::align_cmd::cover_rect(geometry, scale);
    ensure!(
        rect.width >= 128 && rect.height >= 128,
        "common canvas is too small for session stacking"
    );
    Ok(SamplingDomain {
        full: geometry,
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
    })
}

/// Form disjoint proposals with at most one acquisition from each pass.
/// The coefficient consumer, not this geometric proposal, decides local agreement.
fn groups(
    session: &ResolvedSession,
    alignment: &SessionAlignment,
    enabled: bool,
    only_pass: Option<usize>,
) -> Vec<Vec<usize>> {
    let allowed = |index: usize| {
        alignment.map.warps()[index].placed().is_some()
            && only_pass.is_none_or(|pass| session.frames[index].pass_index == pass)
    };
    let mut sets: Vec<BTreeSet<usize>> = (0..session.len()).map(|i| BTreeSet::from([i])).collect();
    let mut owner: Vec<usize> = (0..session.len()).collect();
    if enabled && only_pass.is_none() {
        let mut proposals: Vec<_> = alignment
            .pair_candidates
            .iter()
            .filter(|p| p.candidate_same_focus && p.mutual_nearest && allowed(p.i) && allowed(p.j))
            .collect();
        proposals.sort_by(|a, b| {
            a.log_scale_gap
                .total_cmp(&b.log_scale_gap)
                .then(a.i.cmp(&b.i))
                .then(a.j.cmp(&b.j))
        });
        for proposal in proposals {
            let (a, b) = (owner[proposal.i], owner[proposal.j]);
            if a == b {
                continue;
            }
            let passes: BTreeSet<_> = sets[a]
                .iter()
                .map(|&i| session.frames[i].pass_index)
                .collect();
            if sets[b]
                .iter()
                .any(|&i| passes.contains(&session.frames[i].pass_index))
            {
                continue;
            }
            let other = std::mem::take(&mut sets[b]);
            for index in other {
                sets[a].insert(index);
                owner[index] = a;
            }
        }
    }
    let mut result: Vec<Vec<usize>> = sets
        .into_iter()
        .filter_map(|group| {
            let members: Vec<_> = group.into_iter().filter(|&i| allowed(i)).collect();
            (!members.is_empty()).then_some(members)
        })
        .collect();
    result.sort_by_key(|g| g[0]);
    result
}

fn check_source(
    source: &CachedSource,
    expected: &Calibration,
    full: strehl_core::plane::PlaneGeometry,
) -> Result<()> {
    ensure!(source.geometry() == full, "source active geometry differs");
    ensure!(
        source.camera() == expected.camera
            && source.iso() == expected.iso
            && source.levels() == expected.levels,
        "decoded source calibration changes inside its pass"
    );
    ensure!(
        source.metadata.wb_bits == expected.metadata.wb_bits
            && source.metadata.xyz_to_cam_bits == expected.metadata.xyz_to_cam_bits
            && source.metadata.color_matrices_bits == expected.metadata.color_matrices_bits,
        "decoded white balance or color calibration changes inside its pass"
    );
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn render(
    args: &StackArgs,
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    metadata: &[SourceMetadata],
    alignment: &SessionAlignment,
    cache: &mut SourceCache,
    calibrations: &[Calibration],
    photometric_gains: &[f32],
    domain: SamplingDomain,
    only_pass: Option<usize>,
    destination: &Path,
) -> Result<Value> {
    let started = Instant::now();
    let cfg = args.merge_config()?;
    let primary = session.primary_pass_index();
    let grouped = !args.no_repeat_grouping
        && (matches!(session.spec.mode, SessionMode::Repeat | SessionMode::Hdr)
            || primary.is_some());
    let policy = GroupPolicy {
        mode: if grouped {
            GroupMode::Repeat
        } else {
            GroupMode::Combine
        },
        primary,
        agreement_sigma: args.agreement_sigma,
    };
    let plan = groups(session, alignment, grouped, only_pass);
    let probe = ProbeConfig {
        bands: cfg.bands,
        ..ProbeConfig::default()
    };
    // Explicit conservative extra allowance for sampler, its full-domain operator
    // probe, decoding, final RGB development, and allocator/collection overhead.
    let pixels = domain.pixels();
    let full_pixels = domain.full.pixels();
    let sampler_bytes = sampling_bytes(domain)?;
    let probe_bytes = ProbeMemoryEstimate::estimate(domain, cfg.bands)?.peak_bytes;
    let extra = full_pixels
        .checked_mul(32)
        .and_then(|n| n.checked_add(pixels.checked_mul(256)?))
        .and_then(|n| n.checked_add(sampler_bytes))
        .and_then(|n| n.checked_add(probe_bytes))
        .and_then(|n| n.checked_add(cache.budget_bytes()))
        .and_then(|n| n.checked_add(512 << 20))
        .context("session merge memory plan overflow")?;
    let merge_bytes = workspace_bytes(domain.width, domain.height, cfg, policy)?;
    let planned = merge_bytes
        .checked_add(extra)
        .context("session memory plan overflow")?;
    ensure!(
        planned <= args.resources.config()?.memory_limit_bytes,
        "session merge reservation needs {:.2} GiB, exceeds {:.2} GiB; increase --memory-limit-gib",
        planned as f64 / (1_u64 << 30) as f64,
        args.resources.memory_limit_gib
    );
    // Research single-pass controls retain the fused session color basis.
    // Exported layers intentionally develop using their own pass calibration.
    let anchor = if session.spec.mode == SessionMode::Layers {
        only_pass.or(primary)
    } else {
        primary
    }
    .unwrap_or(alignment.report.reference_pass);
    let phase_overhead = cache
        .budget_bytes()
        .checked_add(512 << 20)
        .context("transfer phase overhead overflow")?;
    let available_phase_bytes = args
        .resources
        .config()?
        .memory_limit_bytes
        .checked_sub(phase_overhead)
        .context("no memory remains for transfer probes")?;
    let progress = crate::ui_progress::Progress::new(session.len());
    progress.stage("merge");
    let jobs: Vec<_> = plan
        .iter()
        .flatten()
        .map(|&index| {
            Ok(transfer_prefetch::TransferJob {
                index,
                placement: alignment.map.warps()[index]
                    .placed()
                    .context("unplaced source reached transfer prefetch")?,
                profile: calibrations[session.frames[index].pass_index].profile,
            })
        })
        .collect::<Result<_>>()?;
    eprintln!(
        "session noise transfer: preparing {} bounded operator probes",
        jobs.len()
    );
    let mut transfers = transfer_prefetch::compute(
        cache.root(),
        domain,
        alignment.map.resampler(),
        probe,
        &jobs,
        available_phase_bytes,
        args.resources.threads,
    )?;
    drop(jobs);
    let planned = planned
        .checked_add(transfers.retained_result_bytes)
        .context("transfer receipt reservation overflow")?
        .max(
            transfers
                .reserved_bytes
                .checked_add(phase_overhead)
                .context("transfer phase reservation overflow")?,
        );
    ensure!(
        planned <= args.resources.config()?.memory_limit_bytes,
        "session including transfer receipts exceeds the memory budget"
    );
    eprintln!(
        "session noise transfer: {} lanes, {:.3}s, {} cache hits",
        transfers.lanes,
        transfers.elapsed_seconds,
        transfers
            .by_index
            .values()
            .filter(|receipt| receipt.cache_hit)
            .count()
    );
    let reference = &calibrations[anchor];
    let mut sampler = NativeSampler::new(domain)?;
    let mut prepared = PreparedSource::new(domain.width, domain.height, cfg)?;
    let mut group = GroupWorkspace::new(domain.width, domain.height, cfg, policy)?;
    let mut merge = SessionMerge::new(domain.width, domain.height, cfg)?;
    let mut receipts = Vec::new();
    eprintln!(
        "session fusion: {} sources in {} proposed groups; canvas {}x{} sensor pixels",
        plan.iter().map(Vec::len).sum::<usize>(),
        plan.len(),
        domain.width * 2,
        domain.height * 2
    );
    eprintln!(
        "session merge reservation: {:.2} GiB; {} CPU workers",
        planned as f64 / (1_u64 << 30) as f64,
        args.resources.threads
    );
    for (ordinal, members) in plan.iter().enumerate() {
        for &index in members {
            progress.frame_started(index);
            let pass = session.frames[index].pass_index;
            let source = cache.load_or_decode(&session.frames[index], &identities[index])?;
            let calibration = &calibrations[pass];
            check_source(&source, calibration, domain.full)?;
            let placement = alignment.map.warps()[index]
                .placed()
                .context("unplaced source reached fusion")?;
            let transfer_receipt = transfers
                .by_index
                .remove(&index)
                .context("prefetched transfer receipt missing")?;
            let transfer = transfer_receipt.transfer;
            let probe_cache_hit = transfer_receipt.cache_hit;
            let probe_seconds = transfer_receipt.seconds;
            let phase_started = Instant::now();
            let sampled = sampler.gather(
                source.as_ref(),
                source.levels(),
                placement,
                calibration.profile,
                alignment.map.resampler(),
            )?;
            let gain = photometric_gains[pass];
            let gather_seconds = phase_started.elapsed().as_secs_f64();
            let phase_started = Instant::now();
            prepared.prepare_with_masks(
                SourceKey {
                    acquisition: index as u64,
                    bracket: pass,
                },
                std::array::from_fn(|c| sampled.planes[c].as_slice()),
                &calibration.noise,
                Some(&transfer.luma_beta),
                Some(&transfer.max_color_beta),
                &sampled.coverage,
                &sampled.support,
                gain,
            )?;
            let prepare_seconds = phase_started.elapsed().as_secs_f64();
            let phase_started = Instant::now();
            merge.add_source(&mut group, &prepared)?;
            let accumulate_seconds = phase_started.elapsed().as_secs_f64();
            receipts.push(json!({
                "frame": index, "pass": pass, "path": metadata[index].path,
                "photometric_gain": gain, "covered_pixels": sampled.coverage.iter().filter(|&&v|v).count(),
                "clipped_pixels": sampled.clipped.iter().filter(|&&v|v).count(),
                "luma_beta": transfer.luma_beta, "color_beta": transfer.max_color_beta,
                "beta_samples": transfer.samples_per_band, "beta_realizations": transfer.realizations,
                "probe_seconds":probe_seconds,"probe_cache_hit":probe_cache_hit,"gather_seconds":gather_seconds,
                "prepare_seconds":prepare_seconds,"accumulate_seconds":accumulate_seconds,
            }));
            progress.frame_finished(index, true);
        }
        merge.fold_group(&mut group)?;
        if ordinal % 10 == 0 || ordinal + 1 == plan.len() {
            eprintln!("session groups {}/{}", ordinal + 1, plan.len());
        }
    }
    let result = merge.finish()?;
    let invalid = result.valid.iter().filter(|&&valid| !valid).count();
    let diagnostics: Vec<_> = result.diagnostics.iter().map(|d| json!({
        "averaged": d.averaged_coefficients, "single_source": d.single_source_coefficients,
        "primary_fallback": d.primary_fallback_coefficients, "ordinary_fallback": d.ordinary_fallback_coefficients,
        "uncovered": d.uncovered_coefficients, "independent_counts": d.averaged_independent_counts,
            "saturated_fallback": d.saturated_fallback_coefficients,
            "primary_saturated_fallback": d.primary_saturated_fallback_coefficients,
    })).collect();
    let report = json!({
           "schema": "strehl.session-render.v1",
           "build":crate::VERSION,"renderer_source_sha256":renderer_source_hash(),
           "recipe":{"bands":cfg.bands,"gate":cfg.gate,"exponent":cfg.exponent,
               "sharpen_per_octave":cfg.sharpen_per_octave,"select":format!("{:?}",cfg.select),
               "admission":format!("{:?}",cfg.admission),"base":format!("{:?}",cfg.base),
               "fallback":format!("{:?}",cfg.fallback),"hull":format!("{:?}",cfg.hull),
               "mean_coarse":cfg.mean_coarse,"significance_scale":cfg.significance_scale,
               "agreement_sigma":policy.agreement_sigma,"grouping_enabled":grouped,
               "exposure_ev":args.exposure,"resampler":format!("{:?}",alignment.map.resampler()),
               "workers":args.resources.threads,"memory_limit_gib":args.resources.memory_limit_gib,
               "noise_probe":{"bands":probe.bands,"realizations":probe.realizations,"seed":probe.seed,
                   "min_samples_per_band":probe.min_samples_per_band}},
    "primary_pass": primary, "reference_pass": alignment.report.reference_pass,
           "layer_pass": only_pass, "development_reference_pass": anchor, "mode": session.spec.mode, "canvas": [domain.x,domain.y,domain.width,domain.height],
           "sources": result.sources, "groups": result.groups, "proposed_groups": plan,
           "invalid_output_pixels": invalid, "diagnostics": diagnostics, "frames": receipts,
           "transfer_prefetch": {"lanes":transfers.lanes,"per_probe_bytes":transfers.per_probe_bytes,
               "retained_result_bytes":transfers.retained_result_bytes,"reserved_bytes":transfers.reserved_bytes,
               "elapsed_seconds":transfers.elapsed_seconds},
           "working_memory_reservation_bytes": planned, "sampler_bytes": sampler_bytes, "probe_bytes": probe_bytes, "elapsed_before_output_seconds": started.elapsed().as_secs_f64(),
           "limitations": [
               "Scale proximity proposes focus groups; local agreement does not establish identical focus or subject rigidity.",
               "Band noise transfer is a measured spatial average under stationary independent input noise, not exact spatial covariance.",
               "Camera model metadata does not establish physical body identity when serial metadata is absent.",
               "Primary preference applies to framing and disagreeing matched overlap, not arbitrary unmatched focus ranges.",
               "HDR requires equal ISO/aperture and a bounded exposure correction validated on spatial holdouts across proposed focus pairs; this does not calibrate a general camera response."
           ]
       });
    write_json_new(&destination.join("render-report.json"), &report)?;
    ensure!(
        invalid == 0,
        "session reconstruction has {invalid} unsupported pixels; report saved, photograph withheld"
    );
    drop(prepared);
    drop(group);
    drop(merge);
    drop(sampler);
    // Native API order R,G1,B,G2 -> existing writer order R,G1,G2,B.
    let [r, g1, b, g2] = result.planes;
    let planes = [r, g1, g2, b];
    let writer_domain = PyramidDomain::cropped(
        domain.full,
        CropRect {
            x: domain.x,
            y: domain.y,
            width: domain.width,
            height: domain.height,
        },
    )?;
    let photograph = destination.join("photograph.tiff");
    let master = destination.join("master.tiff");
    write_merged_observed(
        Merged::Bands {
            domain: writer_domain,
            planes: &planes,
        },
        reference.levels,
        reference.wb,
        reference.matrix.as_ref(),
        crate::image_out::OutputSpace::from_flags(true, false)?,
        !args.binned,
        Exposure::resolve(true, args.exposure, false)?,
        None,
        &photograph,
        Some(&progress),
        Some(&master),
        None,
    )?;
    Ok(report)
}

pub(crate) fn run(args: &StackArgs) -> Result<()> {
    args.merge_config()?;
    ensure!(
        !args.binned,
        "multi-pass sessions currently retain full-resolution linear masters; omit --binned"
    );
    let session = SessionSpec::load(&args.manifest)?.resolve(&args.manifest)?;
    let metadata = session.read_metadata()?;
    validate_headers(&session, &metadata)?;
    ensure!(
        args.only_pass
            .is_none_or(|pass| pass < session.passes.len()),
        "--only-pass lies outside this session"
    );
    ensure!(
        args.only_pass.is_none() || session.spec.mode != SessionMode::Layers,
        "--only-pass cannot combine with layer export"
    );
    let destination = reserve_output_directory(&session, &args.out_dir)?;
    write_json_new(&destination.join("session.json"), &session)?;
    let started = Instant::now();
    let progress = crate::ui_progress::Progress::new(session.len());
    progress.stage("read");
    eprintln!(
        "session: hashing {} original RAW acquisitions",
        session.len()
    );
    let identities = session.hash_sources(true)?;
    write_json_new(&destination.join("source-identities.json"), &identities)?;
    let config = args.resources.config()?;
    let cache_path = args
        .resources
        .cache
        .clone()
        .unwrap_or_else(|| destination.join("source-cache"));
    let mut cache = SourceCache::new(&cache_path, &session, args.resources.cache_budget()?)?;
    let resampler = crate::align_cmd::parse_resampler(&args.resources.resampler)?;
    ensure!(
        resampler != Resampler::ClampedCatmullRom,
        "session noise propagation requires a linear resampler"
    );
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(args.resources.threads)
        .build()?;
    pool.install(|| -> Result<()> {
        progress.stage("alignment");
        let alignment = if let Some(path) = &args.alignment {
            SessionAlignment::load(path, &session, &identities, &config, resampler)?
        } else {
            cached_alignment(&session, &identities, &mut cache, &config, resampler)?
        };
        alignment.save(&destination.join("alignment.json"), &session)?;
        ensure!(alignment.report.passes.iter().all(|pass| pass.placed > 0),
            "one or more passes could not join the measured alignment component; see alignment report");
        let mut calibrations = Vec::new();
        for pass in &session.passes {
            let index = pass.global_range.start;
            let first = cache.load_or_decode(&session.frames[index], &identities[index])?;
            calibrations.push(calibration(&first, &metadata[index], config.memory_limit_bytes / 8)?);
        }
        if session.spec.mode != SessionMode::Layers {
            let shared = &calibrations[0];
            for calibration in &calibrations[1..] {
                ensure!(calibration.levels == shared.levels && calibration.iso == shared.iso
                    && calibration.camera == shared.camera
                    && calibration.metadata.xyz_to_cam_bits == shared.metadata.xyz_to_cam_bits
                    && calibration.metadata.color_matrices_bits == shared.metadata.color_matrices_bits,
                    "combined passes have different decoded sensor or color calibration; use aligned layers");
            }
        }
        let calibration_report: Vec<_> = calibrations.iter().enumerate().map(|(pass, c)| json!({
            "pass":pass,"camera":c.camera,"iso":c.iso,"black":c.levels.black,"white":c.levels.white,
            "white_balance":c.wb,"color_matrix":c.matrix,"shutter_seconds":c.shutter,
            "optical_profile":c.profile.map(|p|json!({"key":p.key,"version":p.version,
                "eps_r":p.eps_r,"eps_b":p.eps_b,"applied_record":format!("{p:?}")})),
            "noise_model":format!("{:?}",c.noise),
            "noise_planes":CfaPlane::ALL.map(|plane|{let n=c.noise.plane(plane);json!({
                "plane":format!("{plane:?}"),"gain_dn_per_e":n.gain_dn_per_e,
                "read_noise_e":n.read_noise_e,"black":n.levels.black,"white":n.levels.white})}),
            "white_balance_policy":if session.spec.mode == SessionMode::Layers { "each layer uses its own pass after reconstruction" } else { "applied once after fusion from the explicit primary or automatic geometry reference" }
        })).collect();
        write_json_new(&destination.join("calibration.json"), &calibration_report)?;
        let domain = domain(&session, &alignment, &calibrations)?;
        let photometric_gains = if session.spec.mode == SessionMode::Hdr {
            let anchor = session.primary_pass_index().unwrap_or(alignment.report.reference_pass);
            let photometry_config = crate::session_photometry::PhotometryConfig::default();
            let phase_bytes = crate::session_photometry::workspace_bytes(domain.full, &photometry_config)?
                .checked_add(crate::session_photometry::report_bytes(session.passes.len(), &photometry_config)?)
                .and_then(|n| n.checked_add(cache.budget_bytes())).and_then(|n| n.checked_add(512 << 20))
                .context("HDR calibration memory reservation overflow")?;
            ensure!(phase_bytes <= config.memory_limit_bytes,
                "HDR calibration exceeds the session memory budget");
            let inputs: Vec<_> = calibrations.iter().map(|calibration| {
                crate::session_photometry::PassPhotometryInput {
                    nominal_gain: (calibrations[anchor].shutter / calibration.shutter) as f32,
                    noise: &calibration.noise, profile: calibration.profile,
                }
            }).collect();
            eprintln!("session HDR: validating exposure correction on held-out spatial patches");
            let photometry = crate::session_photometry::calibrate(
                &session, &identities, &alignment, &mut cache, anchor, &inputs, &photometry_config)?;
            write_json_new(&destination.join("photometry.json"), &photometry)?;
            photometry.require_gains()?.to_vec()
        } else { vec![1.0; session.passes.len()] };
        let mut outputs = Vec::new();
        if session.spec.mode == SessionMode::Layers {
            for pass in 0..session.passes.len() {
                let layer = destination.join(format!("layer-{:02}", pass + 1));
                std::fs::create_dir(&layer)?;
                outputs.push(render(args, &session, &identities, &metadata, &alignment, &mut cache, &calibrations, &photometric_gains, domain, Some(pass), &layer)?);
            }
        } else {
            outputs.push(render(args, &session, &identities, &metadata, &alignment, &mut cache, &calibrations, &photometric_gains, domain, args.only_pass, &destination)?);
        }
        write_json_new(&destination.join("completed.json"), &json!({
            "schema":"strehl.session-completion.v1", "elapsed_seconds":started.elapsed().as_secs_f64(),
            "outputs": outputs.len(), "frames": session.len(), "passes": session.passes.len(),
            "primary_pass":session.primary_pass_index()
        }))?;
        Ok(())
    })
}

fn cached_alignment(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    cache: &mut SourceCache,
    config: &crate::session_align::SessionAlignConfig,
    resampler: Resampler,
) -> Result<SessionAlignment> {
    let mut hash = Sha256::new();
    hash.update(serde_json::to_vec(&(
        &session.spec,
        identities,
        config,
        format!("{resampler:?}"),
    ))?);
    for bytes in [
        include_bytes!("session-align.rs").as_slice(),
        include_bytes!("session-cache.rs").as_slice(),
        include_bytes!("session-input.rs").as_slice(),
        include_bytes!("../../strehl-core/src/align.rs").as_slice(),
        include_bytes!("../../strehl-core/src/plane.rs").as_slice(),
        include_bytes!("../../strehl-core/src/warpmap.rs").as_slice(),
        include_bytes!("../../strehl-raw/src/lib.rs").as_slice(),
        include_bytes!("../../../Cargo.lock").as_slice(),
    ] {
        hash.update((bytes.len() as u64).to_le_bytes());
        hash.update(bytes);
    }
    let key = crate::session_input::hex(&hash.finalize());
    let path = cache.root().join(format!("alignment-{key}.json"));
    let path = session.ensure_output_outside_sources(&path)?;
    if std::fs::symlink_metadata(&path).is_ok() {
        match SessionAlignment::load(&path, session, identities, config, resampler) {
            Ok(alignment) => {
                eprintln!("session alignment: reusing verified geometry cache {key}");
                return Ok(alignment);
            }
            Err(error) => {
                eprintln!("session alignment: rejected derived cache ({error}); refitting");
                // Only this content-addressed derived cache entry is removed.
                // Unlinking a symlink/hardlink never changes its target contents.
                std::fs::remove_file(&path).with_context(|| {
                    format!("evicting invalid alignment cache {}", path.display())
                })?;
            }
        }
    }
    let alignment =
        crate::session_align::align_session(session, identities, cache, config, resampler)?;
    if let Err(error) = alignment.save(&path, session) {
        // Another process may have published the same complete binding first.
        // Its file must pass every normal envelope check before it is accepted.
        SessionAlignment::load(&path, session, identities, config, resampler)
            .with_context(|| format!("publishing alignment cache: {error}"))?;
    }
    Ok(alignment)
}

fn renderer_source_hash() -> String {
    let mut hash = Sha256::new();
    for bytes in [
        include_bytes!("session-consumer.rs").as_slice(),
        include_bytes!("session-sampling.rs").as_slice(),
        include_bytes!("session-transfer-cache.rs").as_slice(),
        include_bytes!("session-transfer-prefetch.rs").as_slice(),
        include_bytes!("session-photometry.rs").as_slice(),
        include_bytes!("session-cache.rs").as_slice(),
        include_bytes!("session-input.rs").as_slice(),
        include_bytes!("merge_cmd.rs").as_slice(),
        include_bytes!("image_out.rs").as_slice(),
        include_bytes!("../../strehl-core/src/session-fusion.rs").as_slice(),
        include_bytes!("../../strehl-core/src/pyramid.rs").as_slice(),
        include_bytes!("../../strehl-core/src/noise.rs").as_slice(),
        include_bytes!("../../strehl-core/src/profile.rs").as_slice(),
        include_bytes!("../../strehl-core/src/optics.rs").as_slice(),
        include_bytes!("../../strehl-core/src/color.rs").as_slice(),
        include_bytes!("../../../Cargo.lock").as_slice(),
    ] {
        hash.update((bytes.len() as u64).to_le_bytes());
        hash.update(bytes);
    }
    crate::session_input::hex(&hash.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exposure_ratios_compare_exact_rationals_without_float_rounding() {
        assert!(same_rational(Some([1, 10]), Some([100, 1000])));
        assert!(!same_rational(Some([1, 10]), Some([1, 11])));
        assert!(!same_rational(None, None));
        assert!(!same_rational(Some([1, 0]), Some([2, 0])));
        assert_eq!(rational(Some([5, 2]), "test").unwrap(), 2.5);
    }
}
