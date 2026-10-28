// Test-only whole-CFA-tuple fusion with unchanged current finest-band weights.
use super::shared_source_field::{hash16, hash32};
use super::*;
use serde_json::{Value, json};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{Fallback, Hull, rb_own_guide_diagnostic as core};

pub(crate) struct Accumulator {
    first: Vec<Vec<f32>>,
    equal: Vec<bool>,
    weighted: Vec<Vec<f32>>,
    mean: Vec<Vec<f32>>,
    denominator: Vec<f32>,
    count: usize,
}
impl Accumulator {
    pub(crate) fn new(pixels: usize) -> Self {
        Self {
            first: vec![vec![0.; pixels]; 4],
            equal: vec![true; pixels],
            weighted: vec![vec![0.; pixels]; 4],
            mean: vec![vec![0.; pixels]; 4],
            denominator: vec![0.; pixels],
            count: 0,
        }
    }
    pub(crate) fn add(&mut self, planes: &[Vec<f32>], weights: &[f32]) -> Result<()> {
        let n = self.denominator.len();
        ensure!(
            planes.len() == 4
                && planes
                    .iter()
                    .all(|p| p.len() == n && p.iter().all(|v| v.is_finite()))
                && weights.len() == n
                && weights.iter().all(|v| v.is_finite() && *v >= 0.),
            "invalid native tuple/weight"
        );
        ensure!(self.count < 299, "bounded original source count");
        for j in 0..n {
            let w = weights[j];
            self.denominator[j] += w;
            for p in 0..4 {
                let v = planes[p][j];
                if self.count == 0 {
                    self.first[p][j] = v;
                    self.mean[p][j] = v;
                } else {
                    self.equal[j] &= self.first[p][j].to_bits() == v.to_bits();
                    self.mean[p][j] += v;
                }
                // Same exact power-of-two numerator scale as production SoftPower.
                self.weighted[p][j] += w * (v / 65536.0);
                ensure!(
                    self.weighted[p][j].is_finite() && self.mean[p][j].is_finite(),
                    "pixel numerator overflow"
                );
            }
        }
        self.count += 1;
        Ok(())
    }
    pub(crate) fn finish(self) -> Result<Vec<Vec<f32>>> {
        ensure!(self.count > 0, "no sources accumulated");
        let n = self.denominator.len();
        let mut result = self.weighted;
        for j in 0..n {
            ensure!(self.denominator[j].is_finite(), "weight sum overflow");
            for p in 0..4 {
                result[p][j] = if self.equal[j] {
                    self.first[p][j]
                } else if self.denominator[j] > 0. {
                    (result[p][j] / self.denominator[j]) * 65536.0
                } else {
                    self.mean[p][j] / self.count as f32
                };
                ensure!(result[p][j].is_finite(), "nonfinite pixel fusion");
            }
        }
        Ok(result)
    }
    pub(crate) fn evidence(&self) -> Value {
        json!({"sources":self.count,"denominator_sha256":hash32(&self.denominator),
            "unsupported_pixels":self.denominator.iter().filter(|&&w|w==0.).count(),
            "equal_tuple_pixels":self.equal.iter().filter(|&&v|v).count(),
            "equal_tuple_exact_copy":true,"shared_reconstruction_planes":4,
            "soft_numerator_scale":65536.0,"association":"original-source-order f32 numerator and denominator; no candidate chunk reduction"})
    }
}

pub(crate) struct Arm {
    pub planes4: Vec<Vec<f32>>,
    pub rgb: Vec<f32>,
}
pub(crate) struct Comparison {
    pub baseline: Arm,
    pub native: Arm,
    pub uniform: Arm,
    pub forced: Arm,
    pub gathered_source0: Arm,
    pub native_width: usize,
    pub native_height: usize,
    pub evidence: Value,
}
fn arm(
    planes4: Vec<Vec<f32>>,
    crop: align_cmd::CropRect,
    levels: Levels,
    wb: [f32; 4],
) -> Result<Arm> {
    let rgb = phase_packed_rgb::camera_rgb(&planes4, crop.width, crop.height, levels, wb)?;
    Ok(Arm { planes4, rgb })
}
fn route() -> Result<()> {
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded
            && align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "actual rounded GPU/probe route required"
    );
    ensure!(
        strehl_core::pyramid::fine_support_candidate::environment_mode()
            == strehl_core::pyramid::fine_support_candidate::Mode::Off
            && align_cmd::native_gpu_integration::ca_stage::mode()?
                == align_cmd::native_gpu_integration::ca_stage::Mode::Current,
        "competing treatment must be off"
    );
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && std::env::var_os("STREHL_ONLY_FRAME").is_none()
            && matches!(
                std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("malvar")
            ),
        "held MHC/placement/source support"
    );
    Ok(())
}
fn config_guard(cfg: MergeConfig) -> Result<()> {
    ensure!(
        cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.fallback == Fallback::Mean
            && cfg.hull == Hull::InputRange
            && cfg.mean_coarse == 0
            && cfg.significance_scale == 0.0,
        "canonical merge settings required"
    );
    Ok(())
}
pub(crate) fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
) -> Result<Comparison> {
    route()?;
    config_guard(cfg)?;
    ensure!(
        !frames.is_empty() && frames.len() <= 70 && frames.len() == transforms.len(),
        "bounded generated source count"
    );
    let first = &frames[0];
    let full = first.geometry();
    let wb = first.wb_coeffs;
    ensure!(
        first.active.width <= 1152 && first.active.height <= 1152,
        "bounded generated extent"
    );
    for (index, f) in frames.iter().enumerate() {
        ensure!(
            !f.path.exists()
                && f.geometry() == full
                && f.active == first.active
                && f.stride == first.stride
                && f.levels == first.levels
                && f.camera == first.camera
                && f.iso == first.iso
                && f.wb_coeffs[..3] == wb[..3],
            "generated metadata/support"
        );
        validate_pyramid_frame(f, full, index)?;
        let id = strehl_raw::identity(&f.path);
        ensure!(
            strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?
                .is_none()
                && phase_packed_rgb::full_stack::full_source_supported(
                    transforms[index],
                    full,
                    crop,
                    None
                ),
            "generated no-CA pull support"
        );
    }
    let entries = frames
        .iter()
        .map(|f| (f.path.to_string_lossy(), f.allocated_bytes() as u64))
        .collect::<Vec<_>>();
    let map = WarpMap::new(
        strehl_core::warpmap::Provenance {
            stack: StackIdentity::from_entries("native-pixel-generated", &entries),
            strategy: "supplied generated geometry".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "one unchanged canonical finest field".into(),
        },
        full,
        Resampler::CatmullRom,
        transforms.iter().copied().map(FrameWarp::Placed).collect(),
    );
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self) -> usize {
            self.0.len()
        }
        fn decode(&self, i: usize) -> Result<Frame> {
            Ok(self.0[i].clone())
        }
    }
    let source = Source(frames);
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let mut baseline = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let n = crop.width * crop.height;
    let mut native = Accumulator::new(n);
    let mut uniform = Accumulator::new(n);
    let mut forced = Accumulator::new(n);
    let ones = vec![1.; n];
    let zeros = vec![0.; n];
    let mut gathered = None;
    let mut receipts = Vec::new();
    for (index, f) in frames.iter().enumerate() {
        let before = hash16(&f.data);
        ensure!(
            baseline.fold(&source, index, f.levels, noise, Some(&map), None)?,
            "canonical source refused"
        );
        let fields = core::canonical_fields(
            &baseline.merge,
            &baseline.fws,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()),
        );
        native.add(&baseline.planes, &fields.weights[0])?;
        uniform.add(&baseline.planes, &ones)?;
        forced.add(&baseline.planes, if index == 0 { &ones } else { &zeros })?;
        if index == 0 {
            gathered = Some(baseline.planes.clone());
        }
        ensure!(hash16(&f.data) == before, "original generated CFA changed");
        receipts.push(json!({"index":index,"source_sha256":before,"known4_sha256":baseline.planes.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
            "guide_sha256":hash32(&baseline.luma),"variance_sha256":hash32(&baseline.var),"beta":baseline.beta,
            "canonical_weight_sha256":fields.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),"source_unchanged":true}));
    }
    let evidence = json!({"frames":receipts,"native":native.evidence(),"uniform":uniform.evidence(),"forced":forced.evidence(),
        "forced_source":0,"one_actual_gather_per_source":true,"known4_shared_with_canonical":true,
        "causal_baseline":"unchanged canonical Pyramid alongside the direct-pixel candidate; no amount knob or zero-amount identity claim",
        "resolved_config":format!("{cfg:?}"),"level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "exponents":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1)).collect::<Vec<_>>()});
    Ok(Comparison {
        baseline: arm(
            baseline.merge.finish(&mut Workspace::new(&sizes)),
            crop,
            first.levels,
            wb,
        )?,
        native: arm(native.finish()?, crop, first.levels, wb)?,
        uniform: arm(uniform.finish()?, crop, first.levels, wb)?,
        forced: arm(forced.finish()?, crop, first.levels, wb)?,
        gathered_source0: arm(gathered.context("source0 absent")?, crop, first.levels, wb)?,
        native_width: 2 * crop.width,
        native_height: 2 * crop.height,
        evidence,
    })
}
mod independent_controls {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/native-pixel-fusion/independent-controls.rs"
    ));
}
mod full {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/native-pixel-fusion/full-adapter.rs"
    ));
}
