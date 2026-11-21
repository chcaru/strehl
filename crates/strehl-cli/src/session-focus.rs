//! Streaming per-pass focus evidence. This optional consumer never changes the
//! ordinary merge, stores no aligned volume, and retains original frame order.
use crate::focus_pass::{FocusFrames, FocusSource};
use crate::session_align::SessionAlignment;
use crate::session_cache::{CachedSource, SourceCache};
use crate::session_cmd::{Resources, reserve_output_directory, write_json_new};
use crate::session_input::{ResolvedSession, SessionSpec, SourceIdentity};
use crate::session_sampling::SamplingDomain;
use anyhow::{Context, Result, ensure};
use clap::Args;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::fs::OpenOptions;
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use strehl_core::align::Resampler;
use strehl_core::focus::{FINE_WINDOW_RADIUS, window_radius};
use strehl_core::focus_evidence::{FocusEvidence, FocusEvidencePolicy};
use strehl_core::merge::REGULARISER_RADIUS;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::optics::OpticalProfile;
use strehl_core::plane::QuadSource;
use strehl_core::warpmap::WarpMap;

#[derive(Args, Clone, Debug)]
pub(crate) struct EvidenceArgs {
    pub manifest: PathBuf,
    #[arg(long)]
    pub alignment: PathBuf,
    #[arg(long)]
    pub out_dir: PathBuf,
    /// Optional diagnostic rectangle x,y,width,height in full green-quad coordinates.
    #[arg(long, value_delimiter = ',', num_args = 4)]
    pub rect: Option<Vec<usize>>,
    #[arg(long)]
    pub pass: Option<usize>,
    #[command(flatten)]
    pub resources: Resources,
}

pub struct PassFocusEvidence {
    pub field: FocusEvidence,
    /// At least one original source covers the pixel, irrespective of clipping
    /// or focus-filter support. Distinct from field.covered and field.usable.
    pub raw_coverage: Vec<bool>,
    pub reservation_bytes: usize,
    pub elapsed_seconds: f64,
    pub resolved_parameters: serde_json::Value,
}

/// Actual per-pixel arrays plus source sampler, one source decode/copy allowance,
/// and the caller-owned original cache. The caller reserves its other live work.
pub fn reservation_bytes(domain: SamplingDomain, frames: usize) -> Result<usize> {
    crate::focus_pass::reservation_bytes(domain, frames)
}

/// A session's originals through its source cache.
struct SessionFrames<'a> {
    session: &'a ResolvedSession,
    identities: &'a [SourceIdentity],
    cache: &'a mut SourceCache,
}

impl FocusSource for Arc<CachedSource> {
    fn quad(&self) -> &dyn QuadSource {
        self.as_ref()
    }
    fn camera(&self) -> &str {
        CachedSource::camera(self)
    }
    fn iso(&self) -> Option<f32> {
        CachedSource::iso(self)
    }
    fn levels(&self) -> Levels {
        CachedSource::levels(self)
    }
}

impl FocusFrames for SessionFrames<'_> {
    type Source = Arc<CachedSource>;
    fn load(&mut self, global_index: usize) -> Result<Self::Source> {
        Ok(self.cache.load_or_decode(
            &self.session.frames[global_index],
            &self.identities[global_index],
        )?)
    }
}

/// Warp placements use the caller's full anchor grid. Per-pass ordinal zero is
/// always the first declared acquisition, including any unplaced acquisition.
#[allow(clippy::too_many_arguments)]
pub fn compute_pass(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    pass: usize,
    map: &WarpMap,
    cache: &mut SourceCache,
    domain: SamplingDomain,
    noise: &NoiseModel,
    profile: Option<&OpticalProfile>,
    budget: usize,
) -> Result<PassFocusEvidence> {
    let track = session
        .passes
        .get(pass)
        .context("focus pass outside session")?;
    ensure!(
        identities.len() == session.len() && map.len() == session.len(),
        "focus source census differs"
    );
    let sweep: Vec<usize> = track.global_range.clone().collect();
    let mut frames = SessionFrames {
        session,
        identities,
        cache,
    };
    let result = crate::focus_pass::compute(
        &mut frames,
        &sweep,
        map,
        domain,
        noise,
        profile,
        budget,
        &format!("session focus: pass {}", pass + 1),
    )?;
    Ok(PassFocusEvidence {
        field: result.field,
        raw_coverage: result.raw_coverage,
        reservation_bytes: result.reservation_bytes,
        elapsed_seconds: result.elapsed_seconds,
        resolved_parameters: resolved_parameters(noise, profile, map.resampler()),
    })
}

pub fn resolved_parameters(
    noise: &NoiseModel,
    profile: Option<&OpticalProfile>,
    resampler: Resampler,
) -> serde_json::Value {
    let policy = FocusEvidencePolicy::default();
    let planes: Vec<_> = strehl_core::CfaPlane::ALL.into_iter().map(|p| {
        let n=noise.plane(p);
        json!({"plane":format!("{p:?}"),"gain_dn_per_e":n.gain_dn_per_e,"read_noise_e":n.read_noise_e,"black":n.levels.black,"white":n.levels.white})
    }).collect();
    json!({"noise":{"iso":noise.iso,"provenance":format!("{:?}",noise.provenance),"planes":planes},
        "optical_profile":profile.map(|p| json!({"key":p.key,"version":p.version,"eps_r":p.eps_r,"eps_b":p.eps_b,"translation":p.translation,"support_r_max":p.support_r_max})),
        "resampler":format!("{resampler:?}"),"fine_radius":FINE_WINDOW_RADIUS,"normal_radius":window_radius(),"regularizer_radius":REGULARISER_RADIUS,
        "policy":{"minimum_prominence_sigma":policy.minimum_prominence_sigma,"maximum_perplexity_fraction":policy.maximum_perplexity_fraction,"competing_peak_ratio":policy.competing_peak_ratio},"algorithm_sha256":algorithm_sha256()})
}

pub fn algorithm_sha256() -> String {
    crate::session_input::hex(&Sha256::digest(
        [
            include_bytes!("session-focus.rs").as_slice(),
            include_bytes!("focus-pass.rs").as_slice(),
            include_bytes!("session-sampling.rs").as_slice(),
            include_bytes!("../../strehl-core/src/focus-evidence.rs").as_slice(),
            include_bytes!("../../strehl-core/src/focus.rs").as_slice(),
            include_bytes!("../../strehl-core/src/through_focus.rs").as_slice(),
            include_bytes!("../../strehl-core/src/merge.rs").as_slice(),
            include_bytes!("../../strehl-core/src/noise.rs").as_slice(),
            include_bytes!("../../strehl-core/src/profile.rs").as_slice(),
            include_bytes!("../../strehl-core/src/optics.rs").as_slice(),
        ]
        .concat(),
    ))
}

pub use crate::focus_pass::complete_support;

pub(crate) fn run(args: &EvidenceArgs) -> Result<()> {
    let session = SessionSpec::load(&args.manifest)?.resolve(&args.manifest)?;
    ensure!(
        session.spec.mode != crate::session_input::SessionMode::IndependentViews,
        "independent views have separate focus coordinates; use session stack to export each view"
    );
    ensure!(
        args.pass.is_none_or(|p| p < session.passes.len()),
        "focus pass outside session"
    );
    let destination = reserve_output_directory(&session, &args.out_dir)?;
    let identities = session.hash_sources(true)?;
    let config = args.resources.config()?;
    let resampler = crate::align_cmd::parse_resampler(&args.resources.resampler)?;
    ensure!(
        resampler != Resampler::ClampedCatmullRom,
        "focus evidence requires a linear resampler"
    );
    let alignment =
        SessionAlignment::load(&args.alignment, &session, &identities, &config, resampler)?;
    let full = alignment.map.geometry();
    let domain = if let Some(rect) = &args.rect {
        ensure!(rect.len() == 4, "rectangle needs four values");
        SamplingDomain {
            full,
            x: rect[0],
            y: rect[1],
            width: rect[2],
            height: rect[3],
        }
    } else {
        SamplingDomain::full(full)
    };
    domain.validate()?;
    let metadata = session.read_metadata()?;
    crate::merge_cmd::session_consumer::validate_capture_headers(&session, &metadata)?;
    let cache_path = args
        .resources
        .cache
        .clone()
        .unwrap_or_else(|| destination.join("source-cache"));
    let mut cache = SourceCache::new(&cache_path, &session, args.resources.cache_budget()?)?;
    let available = config
        .memory_limit_bytes
        .checked_sub(cache.budget_bytes())
        .and_then(|n| n.checked_sub(256 << 20))
        .context("focus memory limit too small")?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(args.resources.threads)
        .build()?;
    let mut reports = Vec::new();
    pool.install(|| -> Result<()> {
        for pass in 0..session.passes.len() {
            if args.pass.is_some_and(|p| p != pass) {
                continue;
            }
            let index = session.passes[pass].global_range.start;
            let source = cache.load_or_decode(&session.frames[index], &identities[index])?;
            let noise = strehl_core::profile::noise_model_for(
                source.camera(),
                source.iso(),
                source.levels(),
            );
            let profile = strehl_core::optics::profile_for_capture_env(
                metadata[index].camera_model.as_deref(),
                metadata[index].lens_type3,
            )?;
            drop(source);
            let result = compute_pass(
                &session,
                &identities,
                pass,
                &alignment.map,
                &mut cache,
                domain,
                &noise,
                profile,
                available,
            )?;
            let dir = destination.join(format!("pass-{:02}", pass + 1));
            std::fs::create_dir(&dir)?;
            reports.push(save(&dir, &result, domain, pass)?);
        }
        Ok(())
    })?;
    let current = session
        .spec
        .resolve_from(&session.passes[0].directories[0])?;
    ensure!(
        current.frames == session.frames && current.hash_sources(true)? == identities,
        "focus sources changed during processing"
    );
    write_json_new(
        &destination.join("focus-evidence.json"),
        &json!({"schema":"strehl.session-focus.v1","session":session,"sources":identities,"alignment_binding":alignment.report.binding_sha256,"algorithm_sha256":algorithm_sha256(),"passes":reports,"workers":args.resources.threads,"memory_limit_bytes":config.memory_limit_bytes,"noise_semantics":"Injected camera temporal model. Prominence uses the existing operator nominal noise unit, not calibrated warped-image probability; same-photon selection remains conditional.","coordinate_semantics":"Acquisition ordinal, not metric depth. Physical sensor coordinate is 2*(full green-quad coordinate)+0.5."}),
    )?;
    write_json_new(
        &destination.join("completed.json"),
        &json!({"schema":"strehl.focus-completion.v1","passes":reports.len()}),
    )
}

pub fn save(
    path: &Path,
    result: &PassFocusEvidence,
    domain: SamplingDomain,
    pass: usize,
) -> Result<serde_json::Value> {
    let f = &result.field;
    let mut files = Vec::new();
    for (name, data) in [
        ("ordinal", &f.ordinal),
        ("width-frames", &f.width_frames),
        ("prominence-nominal-sigma", &f.prominence_sigma),
        ("perplexity", &f.perplexity),
        (
            "unresolved-mode-prominence-nominal-sigma",
            &f.unresolved_mode_prominence_sigma,
        ),
    ] {
        let file = path.join(format!("{name}.tiff"));
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&file)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray32Float>(
                f.geometry.width.try_into()?,
                f.geometry.height.try_into()?,
                data,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(file_receipt(&file)?);
    }
    // Integer source IDs are exact up to the session's u16 acquisition limit.
    // Invalid slots retain NaN, never masquerade as acquisition zero.
    let mut write_extra = |name: &str, values: Vec<f32>| -> Result<()> {
        let file = path.join(format!("{name}.tiff"));
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&file)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray32Float>(
                f.geometry.width.try_into()?,
                f.geometry.height.try_into()?,
                &values,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(file_receipt(&file)?);
        Ok(())
    };
    write_extra(
        "supported-frames",
        f.supported_frames.iter().map(|&v| f32::from(v)).collect(),
    )?;
    for rank in 0..4 {
        write_extra(
            &format!("source-rank-{}", rank + 1),
            f.top_global_indices
                .iter()
                .map(|v| {
                    if v[rank] < crate::session_input::MAX_SESSION_FRAMES {
                        v[rank] as f32
                    } else {
                        f32::NAN
                    }
                })
                .collect(),
        )?;
    }
    for rank in 0..strehl_core::focus_evidence::MODE_CAPACITY {
        write_extra(
            &format!("mode-{}-ordinal", rank + 1),
            f.modes.iter().map(|v| v[rank].ordinal).collect(),
        )?;
        write_extra(
            &format!("mode-{}-prominence-nominal-sigma", rank + 1),
            f.modes
                .iter()
                .map(|v| {
                    if v[rank].ordinal.is_finite() {
                        v[rank].prominence_sigma
                    } else {
                        f32::NAN
                    }
                })
                .collect(),
        )?;
        write_extra(
            &format!("mode-{}-boundary", rank + 1),
            f.modes
                .iter()
                .map(|v| {
                    if v[rank].ordinal.is_finite() {
                        u8::from(v[rank].boundary) as f32
                    } else {
                        f32::NAN
                    }
                })
                .collect(),
        )?;
    }
    let raw: Vec<u8> = result.raw_coverage.iter().map(|&v| u8::from(v)).collect();
    let covered: Vec<u8> = f.covered.iter().map(|&v| u8::from(v)).collect();
    let usable: Vec<u8> = f.usable.iter().map(|&v| u8::from(v)).collect();
    for (name, data) in [
        ("flags", &f.flags),
        ("raw-coverage", &raw),
        ("focus-coverage", &covered),
        ("usable", &usable),
    ] {
        let file = path.join(format!("{name}.tiff"));
        let mut writer = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&file)?,
        );
        tiff::encoder::TiffEncoder::new(&mut writer)?
            .write_image::<tiff::encoder::colortype::Gray8>(
                f.geometry.width.try_into()?,
                f.geometry.height.try_into()?,
                data,
            )?;
        writer.flush()?;
        writer.get_ref().sync_all()?;
        files.push(file_receipt(&file)?);
    }
    let mapping:Vec<_>=f.frames.iter().enumerate().map(|(ordinal,frame)|json!({"ordinal":ordinal,"global_index":frame.global_index,"acquisition":frame.acquisition})).collect();
    let report = json!({"pass":pass,"full_quad_geometry":[domain.full.width,domain.full.height],"origin_quad":[domain.x,domain.y],"dimensions":[domain.width,domain.height],"step_quad":[1,1],"ordinal_mapping":mapping,"usable_pixels":f.usable.iter().filter(|&&v|v).count(),"focus_covered_pixels":f.covered.iter().filter(|&&v|v).count(),"raw_covered_pixels":result.raw_coverage.iter().filter(|&&v|v).count(),"reservation_bytes":result.reservation_bytes,"elapsed_seconds":result.elapsed_seconds,"files":files,"resolved_parameters":result.resolved_parameters,"width_semantics":"Local three-sample log-Gaussian shape width; not a depth uncertainty interval."});
    write_json_new(&path.join("geometry.json"), &report)?;
    Ok(report)
}

fn file_receipt(path: &Path) -> Result<serde_json::Value> {
    let mut reader = std::io::BufReader::new(std::fs::File::open(path)?);
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 65536];
    loop {
        let n = reader.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(
        json!({"file":path.file_name().context("focus output has no filename")?.to_string_lossy(),"bytes":std::fs::metadata(path)?.len(),"sha256":crate::session_input::hex(&hash.finalize())}),
    )
}
