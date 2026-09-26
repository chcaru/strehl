// Generated-only actual-consumer experiment. Existing production is unchanged.
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{LevelSize, AdmissionMode, BaseBand, Fallback, Hull, SelectMode,
    correction_variance_diagnostic as kernels, rb_own_guide_diagnostic as core,
    cross_scale_source_prior_diagnostic as invariant, fine_support_candidate as held};
use super::shared_source_field::{hash16, hash32};
use super::boundary_cfa_wavelet as source_probe;
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chromatic-source-evidence/operator.rs"));

fn same(a: &[f32], b: &[f32]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a,b)| a.to_bits() == b.to_bits())
}
fn same_planes(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a,b)| same(a,b))
}
fn hashes(planes: &[Vec<f32>]) -> Vec<String> { planes.iter().map(|p| hash32(p)).collect() }

/// The existing twelve-slot RGB reconstruction is checked against the actual
/// GPU known-four consumer. The check also runs for every injected noise draw.
pub(crate) fn gather_packed_verified(frame: &Frame, pull: Similarity,
    crop: align_cmd::CropRect, known4: Option<&[Vec<f32>]>) -> Result<Vec<Vec<f32>>> {
    ensure!(!frame.path.exists() && frame.active.width <= 512 && frame.active.height <= 512,
        "bounded generated original only");
    let packed = phase_packed_rgb::gather_patch(&phase_packed_rgb::CfaPatch::from_frame(frame),
        pull, frame.geometry(), crop, None)?;
    let gathered;
    let expected = match known4 {
        Some(expected) => expected,
        None => { gathered = source_probe::gather_known4(frame, pull, crop)?; &gathered }
    };
    ensure!(expected.len() == 4 && same_planes(&packed[..4], expected),
        "co-sited gather first four differs from actual consumed source");
    Ok(packed)
}

pub(crate) struct ProbeEvidence {
    pub energy: Vec<Vec<f32>>, pub seeds: [usize; 16], pub active_sha256: String,
    pub projected_draw_sha256: Vec<Vec<String>>, pub verified_draws: usize,
}
pub(crate) fn projected_noise(frame: &Frame, pull: Similarity, crop: align_cmd::CropRect,
    noise: &NoiseModel, sizes: &[LevelSize]) -> Result<ProbeEvidence> {
    let active_sha256 = super::rb_own_guide::active_hash(frame);
    let seeds = super::rb_own_guide::source_seeds(&active_sha256)?;
    let variance = source_probe::original_variances(frame, noise)?;
    let mut accumulator = PairedNoiseEnergy::new(sizes)?;
    let mut projected_draw_sha256 = Vec::with_capacity(16);
    for pair in 0..PROBE_PAIRS {
        let member = |draw: usize| -> Result<ColourBands> {
            let source = source_probe::noisy_source(frame, &variance, seeds[draw])?;
            let packed = gather_packed_verified(&source, pull, crop, None)?;
            projected_bands(&packed, source.wb_coeffs, sizes)
        };
        let a = member(2*pair)?;
        let b = member(2*pair+1)?;
        projected_draw_sha256.push(a.iter().flat_map(|p| hashes(p)).collect());
        projected_draw_sha256.push(b.iter().flat_map(|p| hashes(p)).collect());
        accumulator.add_pair(&a, &b)?;
    }
    Ok(ProbeEvidence { energy:accumulator.finish()?, seeds, active_sha256,
        projected_draw_sha256, verified_draws:16 })
}
struct ChromaticFrame {
    fields:core::Fields, packed_sha256:Vec<String>, projection_sha256:[String;2], probe:ProbeEvidence,
}
fn chromatic_frame(frame:&Frame, pull:Similarity, crop:align_cmd::CropRect,
    known4:&[Vec<f32>], noise:&NoiseModel, sizes:&[LevelSize], cfg:MergeConfig) -> Result<ChromaticFrame> {
    let packed = gather_packed_verified(frame, pull, crop, Some(known4))?;
    let packed_sha256 = hashes(&packed);
    let guides = project_co_sited(&packed, frame.wb_coeffs)?;
    let projection_sha256 = std::array::from_fn(|c| hash32(&guides[c]));
    let bands = projected_bands(&packed, frame.wb_coeffs, sizes)?;
    drop(packed);
    let energy = joint_energy(&bands, sizes)?;
    let probe = projected_noise(frame, pull, crop, noise, sizes)?;
    let floor = probe.energy.iter().map(|band| band.iter().map(|v| cfg.gate*v).collect()).collect();
    let fields = core::fields_from_energy(sizes, cfg, energy, floor);
    Ok(ChromaticFrame { fields, packed_sha256, projection_sha256, probe })
}

#[derive(serde::Serialize)]
pub(crate) struct FrameEvidence {
    pub source_sha256:String, pub active_sha256:String, pub known4_sha256:[String;4],
    pub guide_sha256:String, pub variance_sha256:String, pub beta:Vec<f32>,
    pub canonical_energy_sha256:Vec<String>, pub canonical_floor_sha256:Vec<String>,
    pub canonical_weight_sha256:Vec<String>, pub candidate_weight_sha256:Vec<String>,
    pub packed_sha256:Vec<String>, pub projection_sha256:[String;2],
    pub chromatic_energy_sha256:Vec<String>, pub chromatic_floor_sha256:Vec<String>,
    pub chromatic_weight_sha256:Vec<String>, pub projected_noise_energy_sha256:Vec<String>,
    pub probe_seeds:[usize;16], pub projected_draw_sha256:Vec<Vec<String>>, pub verified_probe_draws:usize,
    pub changes:WeightChanges, pub replay_exact:bool, pub source_unchanged:bool,
}
pub(crate) struct Comparison {
    pub baseline_planes4:Vec<Vec<f32>>, pub candidate_planes4:Vec<Vec<f32>>,
    pub baseline_rgb:Vec<f32>, pub candidate_rgb:Vec<f32>,
    pub native_width:usize, pub native_height:usize, pub level_sizes:Vec<[usize;2]>,
    pub frames:Vec<FrameEvidence>, pub admission:AdmissionUnion, pub held_state_bit_exact:bool,
    pub baseline_averaged_fraction:Vec<f64>, pub candidate_averaged_fraction:Vec<f64>,
    pub forced_source:Option<usize>,
}
pub(crate) fn compare_generated(frames:&[Frame], transforms:&[Similarity],
    crop:align_cmd::CropRect, noise:&NoiseModel, cfg:MergeConfig, mode:Mode) -> Result<Comparison> {
    compare_inner(frames, transforms, crop, noise, cfg, mode, None)
}
/// Independent commissioning destroyer only; never an image-quality candidate.
pub(crate) fn compare_generated_forced(frames:&[Frame], transforms:&[Similarity],
    crop:align_cmd::CropRect, noise:&NoiseModel, cfg:MergeConfig, mode:Mode,
    forced_source:usize) -> Result<Comparison> {
    ensure!(mode == Mode::Chromatic && forced_source < frames.len(), "invalid forced source control");
    compare_inner(frames, transforms, crop, noise, cfg, mode, Some(forced_source))
}
fn compare_inner(frames:&[Frame], transforms:&[Similarity], crop:align_cmd::CropRect,
    noise:&NoiseModel, cfg:MergeConfig, mode:Mode, forced_source:Option<usize>) -> Result<Comparison> {
    ensure!((2..=16).contains(&frames.len()) && frames.len() == transforms.len(), "bounded generated sources required");
    ensure!(cfg.select == SelectMode::SoftPower && cfg.admission == AdmissionMode::HardFloor
        && cfg.base == BaseBand::Mean && cfg.fallback == Fallback::Mean && cfg.hull == Hull::InputRange
        && cfg.mean_coarse == 0 && cfg.significance_scale == 0.0, "held native merge settings required");
    ensure!(held::environment_mode() == held::Mode::Off
        && align_cmd::native_gpu_integration::ca_stage::mode()? == align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "competing experiments must be disabled");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?, "actual GPU rounded/probed route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "current Malvar and no local placement required");
    let first = &frames[0]; let full = first.geometry(); let wb = first.wb_coeffs;
    ensure!(first.active.width <= 512 && first.active.height <= 512
        && wb[..3].iter().all(|v|v.is_finite() && *v>0.0), "bounded generated extent/WB required");
    for (i, frame) in frames.iter().enumerate() {
        ensure!(!frame.path.exists() && frame.geometry() == full && frame.active == first.active
            && frame.stride == first.stride && frame.buffer_height == first.buffer_height
            && frame.levels == first.levels && frame.camera == first.camera && frame.iso == first.iso
            && frame.wb_coeffs[..3] == wb[..3], "generated source metadata differs");
        validate_pyramid_frame(frame, full, i)?;
        let id = strehl_raw::identity(&frame.path);
        ensure!(strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)?.is_none(), "generated no-CA scope");
        ensure!(phase_packed_rgb::full_stack::full_source_supported(transforms[i],full,crop,None), "full source support required");
    }
    let domain = PyramidDomain::cropped(full,crop)?;
    let sizes = level_sizes(crop.width,crop.height,cfg.bands);
    let mut admission = AdmissionUnion::new(&sizes,frames.len())?;
    let entries = frames.iter().map(|f|(f.path.to_string_lossy(),f.allocated_bytes() as u64)).collect::<Vec<_>>();
    let map = WarpMap::new(strehl_core::warpmap::Provenance {
        stack:StackIdentity::from_entries("chromatic-source-evidence-generated",&entries),
        strategy:"independently supplied geometry".into(), heldout_px:None, cycle_floor_px:None,
        reference:0, note:"one shared own-band colour-difference source field".into(),
    },full,Resampler::CatmullRom,transforms.iter().copied().map(FrameWarp::Placed).collect());
    struct Source<'a>(&'a[Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self)->usize {self.0.len()}
        fn decode(&self,i:usize)->Result<Frame> {Ok(self.0[i].clone())}
    }
    let source = Source(frames);
    let mut baseline = BandWorker::new(domain,cfg); let mut evidence = Vec::new();
    for (i, frame) in frames.iter().enumerate() {
        let source_sha256 = hash16(&frame.data);
        ensure!(baseline.fold(&source,i,frame.levels,noise,Some(&map),None)?, "first pass refused source");
        let canonical = core::canonical_fields(&baseline.merge,&baseline.fws,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        let chromatic = chromatic_frame(frame,transforms[i],crop,&baseline.planes,noise,&sizes,cfg)?;
        admission.add(&chromatic.fields.weights)?;
        ensure!(source_sha256 == hash16(&frame.data), "first pass modified original CFA");
        evidence.push(FrameEvidence {
            source_sha256, active_sha256:chromatic.probe.active_sha256,
            known4_sha256:std::array::from_fn(|c|hash32(&baseline.planes[c])),
            guide_sha256:hash32(&baseline.luma),variance_sha256:hash32(&baseline.var),beta:baseline.beta.clone(),
            canonical_energy_sha256:hashes(&canonical.energy),canonical_floor_sha256:hashes(&canonical.floor),
            canonical_weight_sha256:hashes(&canonical.weights),candidate_weight_sha256:Vec::new(),
            packed_sha256:chromatic.packed_sha256,projection_sha256:chromatic.projection_sha256,
            chromatic_energy_sha256:hashes(&chromatic.fields.energy),chromatic_floor_sha256:hashes(&chromatic.fields.floor),
            chromatic_weight_sha256:hashes(&chromatic.fields.weights),projected_noise_energy_sha256:hashes(&chromatic.probe.energy),
            probe_seeds:chromatic.probe.seeds,projected_draw_sha256:chromatic.probe.projected_draw_sha256,
            verified_probe_draws:chromatic.probe.verified_draws,
            changes:WeightChanges {changed:vec![],chromatic_sites:vec![],fallback_sites:vec![]},
            replay_exact:false,source_unchanged:true,
        });
    }
    admission.complete()?;
    let baseline_averaged_fraction = baseline.merge.averaged_fraction();
    let baseline_planes4 = baseline.merge.finish(&mut Workspace::new(&sizes));
    let mut replay = BandWorker::new(domain,cfg);
    let mut candidate = BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws = FrameWorkspace::new(&sizes,4);
    for (i, frame) in frames.iter().enumerate() {
        ensure!(replay.fold(&source,i,frame.levels,noise,Some(&map),None)?, "second pass refused source");
        let ev = &mut evidence[i];
        ensure!(ev.known4_sha256 == std::array::from_fn(|c|hash32(&replay.planes[c]))
            && ev.guide_sha256 == hash32(&replay.luma) && ev.variance_sha256 == hash32(&replay.var)
            && same(&ev.beta,&replay.beta), "canonical source replay differs");
        let mut fields = core::canonical_fields(&replay.merge,&replay.fws,
            (!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        ensure!(ev.canonical_energy_sha256 == hashes(&fields.energy)
            && ev.canonical_floor_sha256 == hashes(&fields.floor)
            && ev.canonical_weight_sha256 == hashes(&fields.weights), "canonical field replay differs");
        let chromatic = chromatic_frame(frame,transforms[i],crop,&replay.planes,noise,&sizes,cfg)?;
        ensure!(ev.packed_sha256 == chromatic.packed_sha256 && ev.projection_sha256 == chromatic.projection_sha256
            && ev.chromatic_energy_sha256 == hashes(&chromatic.fields.energy)
            && ev.chromatic_floor_sha256 == hashes(&chromatic.fields.floor)
            && ev.chromatic_weight_sha256 == hashes(&chromatic.fields.weights)
            && ev.projected_noise_energy_sha256 == hashes(&chromatic.probe.energy)
            && ev.active_sha256 == chromatic.probe.active_sha256 && ev.probe_seeds == chromatic.probe.seeds
            && ev.projected_draw_sha256 == chromatic.probe.projected_draw_sha256
            && ev.verified_probe_draws == chromatic.probe.verified_draws, "chromatic/probe replay differs");
        ev.changes = admission.apply(&mut fields,&chromatic.fields,mode)?;
        if let Some(forced) = forced_source {
            for k in 1..fields.weights.len() {
                let new:f32 = if i == forced {1.0} else {0.0};
                ev.changes.changed[k] = fields.weights[k].iter().filter(|w|w.to_bits()!=new.to_bits()).count();
                fields.weights[k].fill(new);
            }
        }
        ev.candidate_weight_sha256 = hashes(&fields.weights);
        ensure!(ev.candidate_weight_sha256[0] == ev.canonical_weight_sha256[0], "finest changed");
        core::add_fields(&mut candidate,&replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut candidate_ws);
        ensure!(invariant::held_state_bit_exact(&replay.merge,&candidate), "held accumulator state changed");
        ensure!(ev.source_sha256 == hash16(&frame.data), "second pass modified original CFA");
        ev.replay_exact = true;
    }
    ensure!(same_planes(&baseline_planes4,&replay.merge.finish(&mut Workspace::new(&sizes))), "complete baseline replay differs");
    let held_state_bit_exact = invariant::held_state_bit_exact(&baseline.merge,&candidate);
    ensure!(held_state_bit_exact, "complete held accumulator state differs");
    let candidate_averaged_fraction = candidate.averaged_fraction();
    let candidate_planes4 = candidate.finish(&mut Workspace::new(&sizes));
    if mode != Mode::Chromatic { ensure!(same_planes(&baseline_planes4,&candidate_planes4), "off/no-chroma identity failed"); }
    let baseline_rgb = phase_packed_rgb::camera_rgb(&baseline_planes4,crop.width,crop.height,first.levels,wb)?;
    let candidate_rgb = phase_packed_rgb::camera_rgb(&candidate_planes4,crop.width,crop.height,first.levels,wb)?;
    ensure!(baseline_rgb.iter().chain(&candidate_rgb).all(|v|v.is_finite()), "nonfinite delivered RGB");
    Ok(Comparison { baseline_planes4,candidate_planes4,baseline_rgb,candidate_rgb,
        native_width:2*crop.width,native_height:2*crop.height,level_sizes:sizes.iter().map(|s|[s.width,s.height]).collect(),
        frames:evidence,admission,held_state_bit_exact,baseline_averaged_fraction,candidate_averaged_fraction,forced_source })
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chromatic-source-evidence/independent-controls.rs"));
}
