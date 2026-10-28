// Generated-only comparison seam. Root owns inclusion, independent controls and runs.
// Source storage/gather/synthesis/development remain the existing native consumer.
use super::shared_source_field::{hash16, hash32};
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{
    LevelSize, correction_variance_diagnostic as kernels, rb_own_guide_diagnostic as consumer,
};

mod guide {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/insect-color/guide-fields.rs"
    ));
}

pub(crate) struct Arm {
    pub planes4: Vec<Vec<f32>>,
    pub rgb: Vec<f32>,
    pub averaged_fraction: Vec<f64>,
    pub terminal_base_exact: bool,
}

pub(crate) struct Comparison {
    pub canonical: Arm,
    pub canonical_replay: Arm,
    pub matched_green: Arm,
    pub joint: Arm,
    pub uniform: Arm,
    pub frames: Vec<serde_json::Value>,
    pub sizes: Vec<[usize; 2]>,
    pub joint_uses_next_source_weights: bool,
}

fn same(a: &[f32], b: &[f32]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
}

fn finish(
    merge: &BandMerge,
    base: &[Vec<f32>],
    sizes: &[LevelSize],
    levels: Levels,
    wb: [f32; 4],
) -> Result<Arm> {
    let planes4 = merge.finish(&mut Workspace::new(sizes));
    ensure!(
        planes4.iter().flatten().all(|v| v.is_finite()),
        "nonfinite reconstruction"
    );
    let terminal = consumer::terminal_means(merge);
    let terminal_base_exact =
        terminal.len() == base.len() && terminal.iter().zip(base).all(|(a, b)| same(a, b));
    ensure!(terminal_base_exact, "terminal mean changed");
    let rgb = phase_packed_rgb::camera_rgb(&planes4, sizes[0].width, sizes[0].height, levels, wb)?;
    Ok(Arm {
        planes4,
        rgb,
        averaged_fraction: merge.averaged_fraction(),
        terminal_base_exact,
    })
}

fn channel_fields(
    frame: &Frame,
    transform: Similarity,
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    sizes: &[LevelSize],
    cfg: MergeConfig,
    planes: &[Vec<f32>],
    diagnostics: bool,
) -> Result<([consumer::Fields; 3], serde_json::Value)> {
    let probe =
        super::rb_own_guide::probe_noise(frame, transform, crop, noise, sizes, diagnostics)?;
    let signal = super::rb_own_guide::guide_laplacians(planes, sizes)?;
    let fields = std::array::from_fn(|c| {
        let energy = signal[c]
            .iter()
            .enumerate()
            .map(|(k, values)| kernels::energy(values, sizes[k]))
            .collect();
        let floor = probe.energy3[c]
            .iter()
            .map(|values| values.iter().map(|value| cfg.gate * value).collect())
            .collect();
        consumer::fields_from_energy(sizes, cfg, energy, floor)
    });
    let evidence = if diagnostics {
        serde_json::json!({
            "active_sha256":probe.active_sha256,"seeds":probe.seeds,
            "pair_band_means3":probe.pair_band_means3,
            "variance3_sha256":probe.energy3.iter().map(|bands|bands.iter().map(|v|hash32(v)).collect::<Vec<_>>()).collect::<Vec<_>>()
        })
    } else {
        serde_json::Value::Null
    };
    Ok((fields, evidence))
}

/// The foil rotates only the joint guide's source identity. The current source
/// coefficients, canonical path and matched-green reference do not rotate.
/// It is for one frozen positive control, never an alternative candidate recipe.
pub(crate) fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
    rotate_joint_weights: bool,
    diagnostics: bool,
) -> Result<Comparison> {
    ensure!(
        (2..=16).contains(&frames.len()) && frames.len() == transforms.len(),
        "bounded generated source set required"
    );
    ensure!(
        cfg.bands == 4 && cfg.gate == 2.0 && cfg.significance_scale == 0.0,
        "fixed four-band gate2 screen required"
    );
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "single injected temporal model required"
    );
    ensure!(
        gatefloor::enabled()
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "canonical probe enabled and competing treatment disabled"
    );
    let first = &frames[0];
    let full = first.geometry();
    let wb = first.wb_coeffs;
    ensure!(
        first.active.width <= 512
            && first.active.height <= 512
            && wb[..3].iter().all(|v| v.is_finite() && *v > 0.0),
        "bounded geometry/WB required"
    );
    for (index, frame) in frames.iter().enumerate() {
        ensure!(
            !frame.path.exists()
                && frame.geometry() == full
                && frame.active == first.active
                && frame.stride == first.stride
                && frame.buffer_height == first.buffer_height
                && frame.levels == first.levels
                && frame.camera == first.camera
                && frame.iso == first.iso
                && frame.wb_coeffs[..3] == wb[..3],
            "generated identity/metadata differs"
        );
        validate_pyramid_frame(frame, full, index)?;
        let id = strehl_raw::identity(&frame.path);
        ensure!(
            strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?
                .is_none(),
            "generated no-CA screen required"
        );
        ensure!(
            phase_packed_rgb::full_stack::full_source_supported(
                transforms[index],
                full,
                crop,
                None
            ),
            "source pull lacks support"
        );
    }
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let entries = frames
        .iter()
        .map(|frame| (frame.path.to_string_lossy(), frame.allocated_bytes() as u64))
        .collect::<Vec<_>>();
    let map = WarpMap::new(
        strehl_core::warpmap::Provenance {
            stack: StackIdentity::from_entries("insect-shared-snr-generated", &entries),
            strategy: "fixed supplied generated similarities".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "shared channel-SNR guide; no photographic inference".into(),
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
        fn decode(&self, index: usize) -> Result<Frame> {
            Ok(self.0[index].clone())
        }
    }
    let source = Source(frames);
    let mut baseline = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut merges: [BandMerge; 4] =
        std::array::from_fn(|_| BandMerge::new(crop.width, crop.height, 4, cfg));
    let mut work: [FrameWorkspace; 4] = std::array::from_fn(|_| FrameWorkspace::new(&sizes, 4));
    let uniform = consumer::fields_from_energy(
        &sizes,
        cfg,
        sizes[..sizes.len() - 1]
            .iter()
            .map(|s| vec![0.0; s.pixels()])
            .collect(),
        sizes[..sizes.len() - 1]
            .iter()
            .map(|s| vec![1.0; s.pixels()])
            .collect(),
    );
    let mut evidence = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        let before = hash16(&frame.data);
        ensure!(
            baseline.fold(&source, index, first.levels, noise, Some(&map), None)?,
            "canonical source refused"
        );
        let canonical = consumer::canonical_fields(
            &baseline.merge,
            &baseline.fws,
            (!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()),
        );
        let (own, probe_evidence) = channel_fields(
            frame,
            transforms[index],
            crop,
            noise,
            &sizes,
            cfg,
            &baseline.planes,
            diagnostics,
        )?;
        let joint = if rotate_joint_weights {
            let next = (index + 1) % frames.len();
            let donor_planes =
                super::boundary_cfa_wavelet::gather_known4(&frames[next], transforms[next], crop)?;
            let (donor, _) = channel_fields(
                &frames[next],
                transforms[next],
                crop,
                noise,
                &sizes,
                cfg,
                &donor_planes,
                diagnostics,
            )?;
            guide::shared_snr_fields(&sizes, cfg, [&donor[0], &donor[1], &donor[2]])
                .map_err(anyhow::Error::msg)?
        } else {
            guide::shared_snr_fields(&sizes, cfg, [&own[0], &own[1], &own[2]])
                .map_err(anyhow::Error::msg)?
        };
        let planes = baseline
            .planes
            .iter()
            .map(Vec::as_slice)
            .collect::<Vec<_>>();
        for (arm, fields) in [&canonical, &own[1], &joint, &uniform]
            .into_iter()
            .enumerate()
        {
            // ONE common field, FOUR original linear planes, unchanged accumulator.
            consumer::add_fields(&mut merges[arm], &planes, fields, &mut work[arm]);
        }
        ensure!(
            hash16(&frame.data) == before,
            "original generated source changed"
        );
        if diagnostics {
            evidence.push(serde_json::json!({"source":index,"source_sha256":before,
                "probe":probe_evidence,
                "known4_sha256":baseline.planes.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_weight_source":if rotate_joint_weights {(index+1)%frames.len()} else {index},
                "canonical_weight_sha256":canonical.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "matched_green_weight_sha256":own[1].weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_weight_sha256":joint.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_energy_sha256":joint.energy.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_floor_sha256":joint.floor.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_positive_counts":joint.weights.iter().map(|v|v.iter().filter(|&&w|w>0.0).count()).collect::<Vec<_>>(),
                "reconstruction_planes_per_shared_field":4}));
        }
    }
    let base = consumer::terminal_means(&baseline.merge);
    let canonical = finish(&baseline.merge, &base, &sizes, first.levels, wb)?;
    let canonical_replay = finish(&merges[0], &base, &sizes, first.levels, wb)?;
    ensure!(
        canonical
            .planes4
            .iter()
            .zip(&canonical_replay.planes4)
            .all(|(a, b)| same(a, b))
            && same(&canonical.rgb, &canonical_replay.rgb),
        "canonical replay changed arithmetic"
    );
    Ok(Comparison {
        canonical,
        canonical_replay,
        matched_green: finish(&merges[1], &base, &sizes, first.levels, wb)?,
        joint: finish(&merges[2], &base, &sizes, first.levels, wb)?,
        uniform: finish(&merges[3], &base, &sizes, first.levels, wb)?,
        frames: evidence,
        sizes: sizes.iter().map(|s| [s.width, s.height]).collect(),
        joint_uses_next_source_weights: rotate_joint_weights,
    })
}

mod noise_controls {
    use super::super::rb_own_guide::{GuideBands, NoiseEnergy, guide_laplacians};
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/rb-own-guide/independent-noise-controls.rs"
    ));
}

mod controls {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/insect-color/controls.rs"
    ));
}
