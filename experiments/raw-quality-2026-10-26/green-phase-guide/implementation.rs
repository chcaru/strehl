// Generated-only comparison seam. Root owns inclusion, independent controls and runs.
// Source storage/gather/synthesis/development remain the existing native consumer.
use super::shared_source_field::{hash16, hash32};
use super::*;
use strehl_core::align::Similarity;
use strehl_core::pyramid::{
    LevelSize, correction_variance_diagnostic as kernels, rb_own_guide_diagnostic as consumer,
};

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

/// Same ordinary Laplacian operator, retaining only its first two AC bands.
/// Triple semantics are G1, mean(G1,G2), G2; NoiseEnergy itself is channel agnostic.
fn green_laplacians(
    known4: &[Vec<f32>],
    sizes: &[LevelSize],
    shift_g2: bool,
) -> Result<rb_own_guide::GuideBands> {
    ensure!(
        sizes.len() >= 3
            && known4.len() == 4
            && known4
                .iter()
                .all(|p| p.len() == sizes[0].pixels() && p.iter().all(|v| v.is_finite())),
        "green guide shape/values"
    );
    let shifted;
    let g2 = if shift_g2 {
        // Deliberately wrong physical phase: one quad right with row wrap.
        // Control only; never used by the candidate/full photograph.
        shifted = (0..known4[2].len())
            .map(|i| {
                let x = i % sizes[0].width;
                let y = i / sizes[0].width;
                known4[2][y * sizes[0].width + (x + 1) % sizes[0].width]
            })
            .collect::<Vec<_>>();
        &shifted
    } else {
        &known4[2]
    };
    let mean = known4[1]
        .iter()
        .zip(g2)
        .map(|(a, b)| 0.5 * (a + b))
        .collect::<Vec<_>>();
    Ok([&known4[1], &mean, g2].map(|p| kernels::laplacian(p, &sizes[..3])))
}

fn probe_green(
    frame: &Frame,
    noise: &NoiseModel,
    sizes: &[LevelSize],
    shift_g2: bool,
    gather: impl Fn(&Frame) -> Result<Vec<Vec<f32>>>,
    diagnostics: bool,
) -> Result<(rb_own_guide::GuideBands, serde_json::Value)> {
    let active_sha = rb_own_guide::active_hash(frame);
    let seeds = rb_own_guide::source_seeds(&active_sha)?;
    let variance = boundary_cfa_wavelet::original_variances(frame, noise)?;
    let mut energy = rb_own_guide::NoiseEnergy::new(&sizes[..3]);
    let started = Instant::now();
    for pair in 0..8 {
        let member = |draw: usize| -> Result<_> {
            let noisy = boundary_cfa_wavelet::noisy_source(frame, &variance, seeds[draw])?;
            green_laplacians(&gather(&noisy)?, sizes, shift_g2)
        };
        let a = member(2 * pair)?;
        let b = member(2 * pair + 1)?;
        energy.add_pair(&a, &b)?;
    }
    let result = energy.finish()?;
    let evidence = if diagnostics {
        serde_json::json!({"active_sha256":active_sha,"seeds":seeds,
        "pairs":8,"draws":16,"channels":["G1","mean-G","G2"],"fine_bands":[0,1],
        "original_variance_sha256":hash32(&variance),"seconds":started.elapsed().as_secs_f64(),
        "variance3_sha256":result.iter().map(|v|v.iter().map(|p|hash32(p)).collect::<Vec<_>>()).collect::<Vec<_>>()})
    } else {
        serde_json::Value::Null
    };
    Ok((result, evidence))
}

fn fields_from_green(
    canonical: &consumer::Fields,
    signal: &rb_own_guide::GuideBands,
    variance: &rb_own_guide::GuideBands,
    sizes: &[LevelSize],
    cfg: MergeConfig,
    separate: bool,
) -> Result<consumer::Fields> {
    ensure!(
        sizes.len() >= 3 && cfg.gate == 2.0 && cfg.significance_scale == 0.0,
        "fixed phase guide contract"
    );
    let mut energy = canonical.energy.clone();
    let mut floor = canonical.floor.clone();
    for k in 0..2 {
        if separate {
            let e1 = kernels::energy(&signal[0][k], sizes[k]);
            let e2 = kernels::energy(&signal[2][k], sizes[k]);
            energy[k] = e1.iter().zip(&e2).map(|(a, b)| 0.5 * (a + b)).collect();
            floor[k] = variance[0][k]
                .iter()
                .zip(&variance[2][k])
                .map(|(a, b)| cfg.gate * (0.5 * (a + b)))
                .collect();
        } else {
            energy[k] = kernels::energy(&signal[1][k], sizes[k]);
            floor[k] = variance[1][k].iter().map(|v| cfg.gate * v).collect();
        }
    }
    let result = consumer::fields_from_energy(sizes, cfg, energy, floor);
    ensure!(
        (2..sizes.len() - 1).all(|k| same(&result.energy[k], &canonical.energy[k])
            && same(&result.floor[k], &canonical.floor[k])
            && same(&result.weights[k], &canonical.weights[k])),
        "coarse fields changed"
    );
    Ok(result)
}

fn fields_with_gather(
    frame: &Frame,
    noise: &NoiseModel,
    sizes: &[LevelSize],
    cfg: MergeConfig,
    planes: &[Vec<f32>],
    canonical: &consumer::Fields,
    shift_g2: bool,
    gather: impl Fn(&Frame) -> Result<Vec<Vec<f32>>>,
    diagnostics: bool,
) -> Result<([consumer::Fields; 2], serde_json::Value)> {
    let (variance, evidence) = probe_green(frame, noise, sizes, shift_g2, gather, diagnostics)?;
    let signal = green_laplacians(planes, sizes, shift_g2)?;
    Ok((
        [
            fields_from_green(canonical, &signal, &variance, sizes, cfg, false)?,
            fields_from_green(canonical, &signal, &variance, sizes, cfg, true)?,
        ],
        evidence,
    ))
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum GuideFoil {
    None,
    NextSource,
    ShiftG2OneQuad,
}

/// Compatibility seam for the fixed next-source guide foil.
pub(crate) fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
    rotate_joint_weights: bool,
    diagnostics: bool,
) -> Result<Comparison> {
    compare_generated_with_foil(
        frames,
        transforms,
        crop,
        noise,
        cfg,
        if rotate_joint_weights {
            GuideFoil::NextSource
        } else {
            GuideFoil::None
        },
        diagnostics,
    )
}

pub(crate) fn compare_generated_with_foil(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
    foil: GuideFoil,
    diagnostics: bool,
) -> Result<Comparison> {
    ensure!(
        (1..=16).contains(&frames.len()) && frames.len() == transforms.len(),
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
            stack: StackIdentity::from_entries("green-phase-energy-generated", &entries),
            strategy: "fixed supplied generated similarities".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "separate green Laplacian energy, fine2 only; no photographic inference".into(),
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
        let (own, probe_evidence) = fields_with_gather(
            frame,
            noise,
            &sizes,
            cfg,
            &baseline.planes,
            &canonical,
            false,
            |f| boundary_cfa_wavelet::gather_known4(f, transforms[index], crop),
            diagnostics,
        )?;
        let joint = match foil {
            GuideFoil::None => None,
            GuideFoil::NextSource => {
                let next = (index + 1) % frames.len();
                let donor_planes =
                    boundary_cfa_wavelet::gather_known4(&frames[next], transforms[next], crop)?;
                let (mut donor, _) = fields_with_gather(
                    &frames[next],
                    noise,
                    &sizes,
                    cfg,
                    &donor_planes,
                    &canonical,
                    false,
                    |f| boundary_cfa_wavelet::gather_known4(f, transforms[next], crop),
                    diagnostics,
                )?;
                Some(std::mem::replace(&mut donor[1], empty_fields()))
            }
            GuideFoil::ShiftG2OneQuad => {
                let (mut shifted, _) = fields_with_gather(
                    frame,
                    noise,
                    &sizes,
                    cfg,
                    &baseline.planes,
                    &canonical,
                    true,
                    |f| boundary_cfa_wavelet::gather_known4(f, transforms[index], crop),
                    diagnostics,
                )?;
                Some(std::mem::replace(&mut shifted[1], empty_fields()))
            }
        };
        let joint = joint.as_ref().unwrap_or(&own[1]);
        let planes = baseline
            .planes
            .iter()
            .map(Vec::as_slice)
            .collect::<Vec<_>>();
        for (arm, fields) in [&canonical, &own[0], joint, &uniform]
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
                "joint_weight_source":if foil==GuideFoil::NextSource {(index+1)%frames.len()} else {index},
                "canonical_weight_sha256":canonical.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "matched_green_weight_sha256":own[0].weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_weight_sha256":joint.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_energy_sha256":joint.energy.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_floor_sha256":joint.floor.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
                "joint_positive_counts":joint.weights.iter().map(|v|v.iter().filter(|&&w|w>0.0).count()).collect::<Vec<_>>(),
                "reconstruction_planes_per_shared_field":4,"coarse_fields_exact":true,"foil":format!("{foil:?}")}));
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
        joint_uses_next_source_weights: foil == GuideFoil::NextSource,
    })
}

fn empty_fields() -> consumer::Fields {
    consumer::Fields {
        energy: vec![],
        floor: vec![],
        weights: vec![],
    }
}
mod independent_controls {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/green-phase-guide/independent-controls.rs"
    ));
}
mod full {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/green-phase-guide/full-adapter.rs"
    ));
}
