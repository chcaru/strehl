// Independent literal-port qualification. Source only until root schedules it.
use super::*;
use crate::merge_cmd::dual_tree_cfa as cpu;
use anyhow::{Context, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    cell::RefCell,
    fs::OpenOptions,
    io::Write,
    path::{Path, PathBuf},
    sync::OnceLock,
};
use strehl_core::pyramid::{LevelSize, correction_variance_diagnostic as kernels};

static OUTPUT: OnceLock<PathBuf> = OnceLock::new();
#[derive(Default)]
struct Observations {
    worker: Option<(usize, usize, DebugWorker)>,
    transforms: Vec<Value>,
    inverses: Vec<Value>,
    terminals: Vec<Value>,
    cases: Vec<Value>,
    bank_foil: Option<Value>,
}
thread_local! { static OBS:RefCell<Observations>=RefCell::new(Observations::default()); }
fn out() -> &'static Path {
    OUTPUT.get().expect("control output initialized").as_path()
}
fn digest(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn floats_hash(values: &[f32]) -> String {
    digest(
        &values
            .iter()
            .flat_map(|v| v.to_le_bytes())
            .collect::<Vec<_>>(),
    )
}
fn save(path: &Path, value: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}
fn save_floats(path: &Path, values: &[f32]) -> Result<Value> {
    ensure!(
        values.iter().all(|v| v.is_finite()),
        "nonfinite saved controls"
    );
    let bytes = values
        .iter()
        .flat_map(|v| v.to_le_bytes())
        .collect::<Vec<_>>();
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?
        .write_all(&bytes)?;
    Ok(
        json!({"path":path,"sha256":digest(&bytes),"bytes":bytes.len(),"floats":values.len(),"format":"f32le"}),
    )
}
#[derive(Clone, Copy, Debug)]
enum Guard {
    Coefficients,
    Fields,
    Weights,
    Output,
}
fn agreement(reference: &[f32], actual: &[f32], guard: Guard) -> Result<Value> {
    ensure!(
        !reference.is_empty() && reference.len() == actual.len(),
        "comparison shape"
    );
    ensure!(
        reference.iter().chain(actual).all(|v| v.is_finite()),
        "comparison nonfinite"
    );
    let mut max = 0.0f64;
    let mut sum = 0.0f64;
    let mut ref_sum = 0.0f64;
    let mut max_excess = 0.0f64;
    let mut positive = 0usize;
    for (&r, &a) in reference.iter().zip(actual) {
        let (r, a) = if matches!(guard, Guard::Weights) {
            ensure!(r >= 0. && a >= 0., "negative weight");
            positive += usize::from(r > 0. && a > 0.);
            ((r as f64).ln_1p(), (a as f64).ln_1p())
        } else {
            (r as f64, a as f64)
        };
        let difference = (r - a).abs();
        max = max.max(difference);
        sum += difference * difference;
        ref_sum += r * r;
        let bound = match guard {
            Guard::Coefficients => 0.05 + 1e-5 * r.abs().max(a.abs()),
            Guard::Fields => 0.01 + 1e-3 * r.abs().max(a.abs()),
            Guard::Weights => 0.02,
            Guard::Output => 0.10,
        };
        max_excess = max_excess.max(difference / bound);
    }
    let rms = (sum / reference.len() as f64).sqrt();
    let reference_rms = (ref_sum / reference.len() as f64).sqrt();
    let rms_bound = match guard {
        Guard::Coefficients => Some(0.01 + 1e-6 * reference_rms),
        Guard::Weights => Some(0.002),
        Guard::Output => Some(0.02),
        Guard::Fields => None,
    };
    let pass = max_excess <= 1. && rms_bound.is_none_or(|limit| rms <= limit);
    Ok(
        json!({"guard":format!("{guard:?}"),"count":reference.len(),"max_error":max,"rms_error":rms,
        "reference_rms":reference_rms,"max_pointwise_tolerance_ratio":max_excess,"rms_limit":rms_bound,
        "positive_in_both":positive,"pass":pass}),
    )
}
fn pass(value: &Value) -> bool {
    value["pass"] == true
}
fn shapes(plan: &Plan) -> Vec<usize> {
    plan.band_shapes()
        .into_iter()
        .flat_map(|(w, h)| (0..6).map(move |_| w * h))
        .collect()
}
fn coefficients_flat(c: &Coefficients) -> Vec<f32> {
    let mut result = c
        .bands
        .iter()
        .flat_map(|b| b.values.iter().flat_map(|z| [z.re, z.im]))
        .collect::<Vec<_>>();
    for low in &c.low {
        result.extend_from_slice(low);
    }
    result
}
fn coefficient_agreement(a: &Coefficients, b: &Coefficients) -> Result<Value> {
    ensure!(a.bands.len() == b.bands.len(), "coefficient bands");
    let mut rows = Vec::new();
    for (i, (x, y)) in a.bands.iter().zip(&b.bands).enumerate() {
        ensure!(
            (x.level, x.direction, x.width, x.height) == (y.level, y.direction, y.width, y.height),
            "coefficient layout"
        );
        let x = x
            .values
            .iter()
            .flat_map(|z| [z.re, z.im])
            .collect::<Vec<_>>();
        let y = y
            .values
            .iter()
            .flat_map(|z| [z.re, z.im])
            .collect::<Vec<_>>();
        rows.push(json!({"band":i,"comparison":agreement(&x,&y,Guard::Coefficients)?}));
    }
    for (i, (x, y)) in a.low.iter().zip(&b.low).enumerate() {
        rows.push(json!({"LL_tree":i,"comparison":agreement(x,y,Guard::Coefficients)?}));
    }
    Ok(json!({"pass":rows.iter().all(|r|pass(&r["comparison"])),"bands_and_lowpasses":rows}))
}
fn plane_agreement(a: &[Vec<f32>], b: &[Vec<f32>]) -> Result<Value> {
    ensure!(a.len() == 4 && b.len() == 4, "four physical phases");
    let rows = a
        .iter()
        .zip(b)
        .map(|(x, y)| agreement(x, y, Guard::Output))
        .collect::<Result<Vec<_>>>()?;
    Ok(json!({"pass":rows.iter().all(pass),"phases":rows}))
}
fn close_debug() -> Result<()> {
    let worker = OBS.with(|s| s.borrow_mut().worker.take());
    if let Some((_, _, worker)) = worker {
        let terminal = worker.close()?;
        OBS.with(|s| s.borrow_mut().terminals.push(terminal));
    }
    Ok(())
}
fn with_debug<T>(plan: &Plan, call: impl FnOnce(&mut DebugWorker) -> Result<T>) -> Result<T> {
    let needs_new = OBS.with(|s| {
        s.borrow()
            .worker
            .as_ref()
            .is_none_or(|(w, h, _)| *w != plan.input_width || *h != plan.input_height)
    });
    if needs_new {
        close_debug()?;
        let worker = DebugWorker::new(
            plan.clone(),
            MergeConfig::default(),
            [1.6, 1., 2., f32::NAN],
            false,
        )?;
        OBS.with(|s| s.borrow_mut().worker = Some((plan.input_width, plan.input_height, worker)));
    }
    OBS.with(|s| call(&mut s.borrow_mut().worker.as_mut().unwrap().2))
}

// These wrappers are the transform consumed by the inherited, unmodified CPU
// controls. Reference calls always name the frozen CPU module explicitly.
fn forward_phase(input: &[f32], plan: &Plan) -> Result<Coefficients> {
    let reference = cpu::forward_phase(input, plan)?;
    let (actual, inverse, response) = with_debug(plan, |w| w.transform(input, false))?;
    let comparison = coefficient_agreement(&reference, &actual)?;
    let cpu_inverse = cpu::inverse_phase(&reference, plan)?;
    let inverse_comparison = agreement(&cpu_inverse, &inverse, Guard::Output)?;
    let record = json!({"input_dimensions":[plan.input_width,plan.input_height],"input_sha256":floats_hash(input),
        "coefficients":comparison,"inverse":inverse_comparison,"response":response});
    OBS.with(|s| s.borrow_mut().transforms.push(record));
    if OBS.with(|s| s.borrow().bank_foil.is_none()) {
        let (bad, bad_inverse, response) = with_debug(plan, |w| w.transform(input, true))?;
        let bad_coefficients = coefficient_agreement(&reference, &bad)?;
        let bad_output = agreement(&cpu_inverse, &bad_inverse, Guard::Output)?;
        let record = json!({"kind":"first aLow tap3 multiplied by1.01 in actual GPU transform/inverse only",
            "coefficients":bad_coefficients,"inverse":bad_output,"response":response,
            "pass":!pass(&bad_coefficients) || !pass(&bad_output)});
        OBS.with(|s| s.borrow_mut().bank_foil = Some(record));
    }
    Ok(actual)
}
fn inverse_phase(coefficients: &Coefficients, plan: &Plan) -> Result<Vec<f32>> {
    let reference = cpu::inverse_phase(coefficients, plan)?;
    let (actual, response) = with_debug(plan, |w| w.inverse(coefficients))?;
    let comparison = agreement(&reference, &actual, Guard::Output)?;
    OBS.with(|s| {
        s.borrow_mut()
            .inverses
            .push(json!({"comparison":comparison,"response":response}))
    });
    Ok(actual)
}

struct CpuStages {
    energy: Vec<Vec<f32>>,
    floor: Vec<Vec<f32>>,
    weights: Vec<Vec<f32>>,
    signal0: Coefficients,
}
fn cpu_stages(
    frame: &Frame,
    index: usize,
    warp: Similarity,
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
    actual_receipt: &Value,
) -> Result<CpuStages> {
    let plan = Plan::new(crop.width, crop.height)?;
    let known = super::generated_gather(frame, warp, crop)?;
    ensure!(
        json!(known.iter().map(|p| floats_hash(p)).collect::<Vec<_>>())
            == actual_receipt["known4_sha256"],
        "reference actual gather hash"
    );
    let gains = [
        frame.wb_coeffs[0] / frame.wb_coeffs[1],
        1.,
        1.,
        frame.wb_coeffs[2] / frame.wb_coeffs[1],
    ]
    .map(|v| v * v);
    let mut energy = shapes(&plan)
        .iter()
        .map(|&n| vec![0.0f32; n])
        .collect::<Vec<_>>();
    let mut variance = energy.clone();
    let mut signal0 = None;
    for p in 0..4 {
        let wave = cpu::forward_phase(&known[p], &plan)?;
        for (sum, band) in energy.iter_mut().zip(&wave.bands) {
            for (e, z) in sum.iter_mut().zip(&band.values) {
                *e += gains[p] * (z.re * z.re + z.im * z.im);
            }
        }
        if p == 0 {
            signal0 = Some(wave);
        }
    }
    let original_variance = boundary_cfa_wavelet::original_variances(frame, noise)?;
    ensure!(
        floats_hash(&original_variance)
            == actual_receipt["original_variance_sha256"]
                .as_str()
                .context("variance reference hash")?,
        "reference original variance hash"
    );
    for pair in 0..8 {
        let first = boundary_cfa_wavelet::noisy_source(
            frame,
            &original_variance,
            boundary_cfa_wavelet::probe_seed(index, 2 * pair),
        )?;
        let first = super::generated_gather(&first, warp, crop)?;
        let second = boundary_cfa_wavelet::noisy_source(
            frame,
            &original_variance,
            boundary_cfa_wavelet::probe_seed(index, 2 * pair + 1),
        )?;
        let second = super::generated_gather(&second, warp, crop)?;
        for p in 0..4 {
            let a = cpu::forward_phase(&first[p], &plan)?;
            let b = cpu::forward_phase(&second[p], &plan)?;
            for ((sum, a), b) in variance.iter_mut().zip(&a.bands).zip(&b.bands) {
                for ((v, a), b) in sum.iter_mut().zip(&a.values).zip(&b.values) {
                    let re = a.re - b.re;
                    let im = a.im - b.im;
                    let q = gains[p] * (re * re + im * im);
                    *v += q / 16.;
                }
            }
        }
    }
    let mut floors = Vec::new();
    let mut weights = Vec::new();
    for b in 0..energy.len() {
        let k = b / 6;
        let size = LevelSize {
            width: plan.padded_width >> (k + 1),
            height: plan.padded_height >> (k + 1),
        };
        energy[b] = kernels::smooth(&energy[b], size);
        let floor = kernels::smooth(&variance[b], size)
            .iter()
            .map(|v| 2. * v)
            .collect::<Vec<_>>();
        let weight = energy[b]
            .iter()
            .zip(&floor)
            .map(|(&e, &v)| kernels::soft_weight((e - v).max(0.), v, cfg.exponent_at(k, 7)))
            .collect::<Vec<_>>();
        ensure!(
            floats_hash(&energy[b])
                == actual_receipt["energy_sha256"][b]
                    .as_str()
                    .context("CPU energy hash")?,
            "replayed CPU energy is not actual consumer"
        );
        ensure!(
            floats_hash(&floor)
                == actual_receipt["floor_sha256"][b]
                    .as_str()
                    .context("CPU floor hash")?,
            "replayed CPU floor is not actual consumer"
        );
        ensure!(
            floats_hash(&weight)
                == actual_receipt["raw_weight_sha256"][b]
                    .as_str()
                    .context("CPU weight hash")?,
            "replayed CPU weights are not actual consumer"
        );
        floors.push(floor);
        weights.push(weight);
    }
    Ok(CpuStages {
        energy,
        floor: floors,
        weights,
        signal0: signal0.context("phase0 coefficients")?,
    })
}
fn read_array(record: &Value) -> Result<Vec<f32>> {
    let path = PathBuf::from(record["path"].as_str().context("debug file path")?);
    let bytes = std::fs::read(path)?;
    ensure!(
        digest(&bytes) == record["sha256"] && bytes.len() % 4 == 0,
        "debug file identity"
    );
    let values = bytes
        .chunks_exact(4)
        .map(|p| f32::from_le_bytes(p.try_into().unwrap()))
        .collect::<Vec<_>>();
    ensure!(
        values.len() == record["floats"].as_u64().context("debug count")? as usize,
        "debug file count"
    );
    Ok(values)
}
fn stage_agreement(
    reference: &CpuStages,
    arrays: &[DebugArray],
    plan: &Plan,
    directory: &Path,
) -> Result<Value> {
    std::fs::create_dir(directory)?;
    let sizes = shapes(plan);
    let mut rows = Vec::new();
    for (name, reference, guard) in [
        ("energy", &reference.energy, Guard::Fields),
        ("floor", &reference.floor, Guard::Fields),
        ("raw_weights", &reference.weights, Guard::Weights),
    ] {
        let actual = &arrays
            .iter()
            .find(|v| v.name == name)
            .context("GPU debug named stage")?
            .values;
        ensure!(
            actual.len() == sizes.iter().sum::<usize>(),
            "stage flat extent"
        );
        let mut at = 0;
        let mut bands = Vec::new();
        for (i, (&n, r)) in sizes.iter().zip(reference).enumerate() {
            bands.push(json!({"band":i,"comparison":agreement(r,&actual[at..at+n],guard)?}));
            at += n;
        }
        let reference = reference.iter().flatten().copied().collect::<Vec<_>>();
        let reference_file = save_floats(&directory.join(format!("cpu-{name}.f32le")), &reference)?;
        let actual_file = save_floats(&directory.join(format!("gpu-{name}.f32le")), actual)?;
        rows.push(json!({"name":name,"pass":bands.iter().all(|b|pass(&b["comparison"])),"bands":bands,
            "reference":reference_file,"actual":actual_file,"literal_cpu_stage_hashes_verified":true}));
    }
    let flat = coefficients_flat(&reference.signal0);
    let actual = &arrays
        .iter()
        .find(|v| v.name == "signal_coefficients_phase0")
        .context("GPU signal stage")?
        .values;
    ensure!(flat.len() == actual.len(), "signal coefficient extent");
    let mut signal_rows = Vec::new();
    let mut at = 0;
    for n in sizes
        .iter()
        .map(|n| 2 * n)
        .chain(reference.signal0.low.iter().map(Vec::len))
    {
        signal_rows.push(agreement(
            &flat[at..at + n],
            &actual[at..at + n],
            Guard::Coefficients,
        )?);
        at += n;
    }
    let signal_reference = save_floats(&directory.join("cpu-signal0.f32le"), &flat)?;
    let signal_actual = save_floats(&directory.join("gpu-signal0.f32le"), actual)?;
    let signal = json!({"pass":signal_rows.iter().all(pass),"bands_and_LL":signal_rows,"reference":signal_reference,"actual":signal_actual});
    Ok(
        json!({"pass":rows.iter().all(pass) && pass(&signal),"fields":rows,"signal_coefficients_phase0":signal}),
    )
}
fn read_historical() -> Result<Value> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let bytes = std::fs::read(
        root.join("outputs/raw-quality-2026-10-27/dual-tree-cfa-screen-1/output/screen.json"),
    )?;
    ensure!(
        digest(&bytes) == "17f4191626bf378a2520590de37933ca13003d6ac6b77dab244158a600fd9fd6",
        "held CPU screen identity"
    );
    Ok(serde_json::from_slice(&bytes)?)
}
fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
) -> Result<Comparison> {
    close_debug()?;
    let index = OBS.with(|s| s.borrow().cases.len());
    let directory = out().join(format!("agreement-case-{index}"));
    std::fs::create_dir(&directory)?;
    let reference = cpu::compare_generated(frames, transforms, crop, noise, cfg)?;
    let actual = super::compare_generated(frames, transforms, crop, noise, cfg)?;
    let pre_hull = plane_agreement(&reference.pre_hull_planes4, &actual.pre_hull_planes4)?;
    let delivered = plane_agreement(&reference.candidate.planes4, &actual.candidate.planes4)?;
    let uniform = plane_agreement(&reference.uniform.planes4, &actual.uniform.planes4)?;
    let canonical_exact = reference
        .canonical
        .planes4
        .iter()
        .flatten()
        .map(|v| v.to_bits())
        .eq(actual
            .canonical
            .planes4
            .iter()
            .flatten()
            .map(|v| v.to_bits()))
        && reference
            .canonical
            .rgb
            .iter()
            .map(|v| v.to_bits())
            .eq(actual.canonical.rgb.iter().map(|v| v.to_bits()));
    let historical = read_historical()?;
    let historical_exact = if index < 8 {
        floats_hash(&reference.candidate.rgb)
            == historical["cases"][index]["panels"]["candidate"]["float"]["sha256"]
            && floats_hash(&reference.canonical.rgb)
                == historical["cases"][index]["panels"]["canonical"]["float"]["sha256"]
    } else {
        true
    };
    let mut stages = Vec::new();
    for (i, frame) in frames.iter().enumerate() {
        let reference_stage = cpu_stages(
            frame,
            i,
            transforms[i],
            crop,
            noise,
            cfg,
            &reference.evidence["frames"][i],
        )?;
        let array_records = actual.evidence["frames"][i]["debug_arrays"]
            .as_array()
            .context("GPU generated stage records")?;
        let arrays = array_records
            .iter()
            .map(|r| {
                Ok(DebugArray {
                    name: r["name"].as_str().context("debug stage name")?.into(),
                    values: read_array(r)?,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        stages.push(stage_agreement(
            &reference_stage,
            &arrays,
            &Plan::new(crop.width, crop.height)?,
            &directory.join(format!("source-{i}")),
        )?);
    }
    let rgb_delta = reference
        .candidate
        .rgb
        .iter()
        .zip(&actual.candidate.rgb)
        .map(|(a, b)| a - b)
        .collect::<Vec<_>>();
    let rgb_max = rgb_delta.iter().map(|v| v.abs()).fold(0.0f32, f32::max);
    let rgb_rms = (rgb_delta.iter().map(|v| (*v as f64).powi(2)).sum::<f64>()
        / rgb_delta.len() as f64)
        .sqrt();
    let files = json!({"cpu_rgb":save_floats(&directory.join("cpu-camera-rgb.f32le"),&reference.candidate.rgb)?,
        "gpu_rgb":save_floats(&directory.join("gpu-camera-rgb.f32le"),&actual.candidate.rgb)?});
    let positive_selected = actual.evidence["frames"]
        .as_array()
        .context("GPU source census")?
        .iter()
        .any(|frame| {
            frame["positive_weight_coefficients"]
                .as_array()
                .is_some_and(|counts| counts.iter().any(|n| n.as_u64().unwrap_or(0) > 0))
        });
    let selected_required = (2..8).contains(&index) || index == 9;
    let result = json!({"case_index":index,"source_count":frames.len(),"pass":pass(&pre_hull)&&pass(&delivered)&&pass(&uniform)&&canonical_exact&&historical_exact&&stages.iter().all(pass)&&(!selected_required||positive_selected),
        "positive_selected_coefficients":positive_selected,"positive_selection_required":selected_required,
        "pre_hull":pre_hull,"delivered":delivered,"uniform":uniform,"canonical_pixel_exact":canonical_exact,
        "historical_CPU_generated_RGB_exact":historical_exact,"source_stages":stages,"complete_rgb":files,
        "camera_rgb_difference_observed":{"max_normalized":rgb_max,"rms_normalized":rgb_rms},
        "cpu_evidence":reference.evidence,"gpu_evidence":actual.evidence});
    save(&directory.join("agreement.json"), &result)?;
    OBS.with(|s| s.borrow_mut().cases.push(result));
    Ok(actual)
}

// Source reuse, not a fixture rewrite. Local wrappers above supply the actual
// GPU transform/consumer. All original truth, seeds, guards and foils persist.
mod inherited {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/dual-tree-cfa/controls.rs"
    ));
    pub(super) fn run_frozen() -> Result<()> {
        run()
    }
    pub(super) fn floor_fixture() -> (
        Vec<Frame>,
        Vec<Similarity>,
        crate::align_cmd::CropRect,
        NoiseModel,
        MergeConfig,
    ) {
        let ts = transforms();
        let noise = profile::noise_model_for("ILCE-7CM2", Some(100.), levels());
        let frames = ts
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(Scene::Colour, k, t, 100., &noise, true))
            .collect();
        (frames, ts, crop(), noise, MergeConfig::default())
    }
    pub(super) fn panel(dir: &Path, name: &str, rgb: &[f32], w: usize, h: usize) -> Result<Value> {
        image(dir, name, rgb, w, h)
    }
}
fn floor_foil() -> Result<Value> {
    let (frames, transforms, crop, noise, cfg) = inherited::floor_fixture();
    let reference = cpu::compare_generated(&frames, &transforms, crop, &noise, cfg)?;
    let plan = Plan::new(crop.width, crop.height)?;
    let directory = out().join("wrong-floor");
    std::fs::create_dir(&directory)?;
    let mut accumulator = Accumulator::new_debug(plan.clone(), cfg, frames[0].wb_coeffs, true)?;
    let mut stages = Vec::new();
    let mut rows = Vec::new();
    for (i, frame) in frames.iter().enumerate() {
        let known = super::generated_gather(frame, transforms[i], crop)?;
        rows.push(accumulator.add_source(frame, i, &known, &noise, |f| {
            super::generated_gather(f, transforms[i], crop)
        })?);
        let arrays = accumulator.take_debug_arrays()?;
        let cpu = cpu_stages(
            frame,
            i,
            transforms[i],
            crop,
            &noise,
            cfg,
            &reference.evidence["frames"][i],
        )?;
        stages.push(stage_agreement(
            &cpu,
            &arrays,
            &plan,
            &directory.join(format!("source-{i}")),
        )?);
    }
    let finished = accumulator.finish()?;
    let rgb = camera_rgb(
        &finished.planes4,
        crop.width,
        crop.height,
        frames[0].levels,
        frames[0].wb_coeffs,
    )?;
    let panels = json!({"cpu":inherited::panel(&directory,"cpu",&reference.candidate.rgb,2*crop.width,2*crop.height)?,
        "wrong_floor":inherited::panel(&directory,"wrong-floor",&rgb,2*crop.width,2*crop.height)?});
    let field_fails = |name: &str| {
        stages.iter().any(|s| {
            s["fields"]
                .as_array()
                .unwrap()
                .iter()
                .any(|r| r["name"] == name && !pass(r))
        })
    };
    let selected = stages.iter().any(|s| {
        s["fields"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|r| r["name"] == "raw_weights")
            .any(|r| {
                r["bands"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|b| b["comparison"]["positive_in_both"].as_u64().unwrap_or(0) > 0)
            })
    });
    let result = json!({"pass":field_fails("floor")&&field_fails("raw_weights")&&selected,
        "actual_floor_and_nonzero_weight_guards_reject":field_fails("floor")&&field_fails("raw_weights"),
        "positive_selected_coefficients":selected,"stages":stages,"frames":rows,"finish":finished.evidence,
        "delivered_output_observation":plane_agreement(&reference.candidate.planes4,&finished.planes4)?,"complete_panels":panels});
    save(&directory.join("result.json"), &result)?;
    Ok(result)
}
fn run() -> Result<()> {
    let directory = PathBuf::from(
        std::env::var_os("STREHL_DUAL_TREE_CFA_GPU_CONTROL_OUT").context("GPU control output")?,
    );
    ensure!(!directory.exists(), "fresh output required");
    std::fs::create_dir_all(&directory)?;
    OUTPUT
        .set(directory.clone())
        .map_err(|_| anyhow::anyhow!("one fixed control execution"))?;
    let inherited_out = directory.join("inherited");
    let previous = std::env::var_os("STREHL_DUAL_TREE_CFA_CONTROL_OUT");
    // Root runs this single exact test with one test thread; no concurrent env use.
    unsafe {
        std::env::set_var("STREHL_DUAL_TREE_CFA_CONTROL_OUT", &inherited_out);
    }
    let inherited_result = inherited::run_frozen();
    unsafe {
        match previous {
            Some(v) => std::env::set_var("STREHL_DUAL_TREE_CFA_CONTROL_OUT", v),
            None => std::env::remove_var("STREHL_DUAL_TREE_CFA_CONTROL_OUT"),
        }
    }
    let closing = close_debug();
    let inherited = if inherited_out.join("screen.json").is_file() {
        serde_json::from_slice::<Value>(&std::fs::read(inherited_out.join("screen.json"))?)?
    } else {
        Value::Null
    };
    let floor_result = if inherited_result.is_ok() && closing.is_ok() {
        Some(floor_foil())
    } else {
        None
    };
    let floor_error = floor_result
        .as_ref()
        .and_then(|r| r.as_ref().err())
        .map(|e| format!("{e:#}"));
    let floor = floor_result.and_then(Result::ok);
    let observed=OBS.with(|s| {let s=s.borrow();json!({"transforms":s.transforms,"inverses":s.inverses,"worker_terminals":s.terminals,"cases":s.cases,"bank_foil":s.bank_foil})});
    let transform_pass = observed["transforms"]
        .as_array()
        .unwrap()
        .iter()
        .all(|r| pass(&r["coefficients"]) && pass(&r["inverse"]))
        && observed["inverses"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| pass(&r["comparison"]));
    let all_cases = inherited["all_cases_completed"] == true
        && observed["cases"].as_array().unwrap().len() == 10;
    let historical = read_historical()?;
    let flags_retained = inherited["cases"].as_array().is_some_and(|rows| {
        rows.len() == 8
            && rows
                .iter()
                .zip(historical["cases"].as_array().unwrap())
                .all(|(a, b)| a["quality_pass"] == b["quality_pass"])
    });
    let mechanical = inherited_result.is_ok()
        && closing.is_ok()
        && all_cases
        && inherited["mechanical_pass"] == true
        && transform_pass
        && observed["cases"].as_array().unwrap().iter().all(pass)
        && pass(&observed["bank_foil"])
        && floor.as_ref().is_some_and(pass)
        && flags_retained;
    let record = json!({"status":if all_cases&&floor.is_some(){"COMPLETE_DUAL_TREE_GPU_GENERATED_DIAGNOSTIC"}else{"GPU_MECHANICAL_REFUSAL"},
        "all_cases_completed":all_cases&&floor.is_some(),"mechanical_pass":mechanical,"quality_pass":inherited["quality_pass"]==true,
        "admission":false,"photographic_admission":false,"RAW_reads":0,"observations":observed,"wrong_floor_foil":floor,
        "inherited_screen":inherited,"historical_CPU_quality_flags_retained":flags_retained,
        "inherited_error":inherited_result.as_ref().err().map(|e|format!("{e:#}")),"close_error":closing.as_ref().err().map(|e|format!("{e:#}")),"floor_foil_error":floor_error,
        "numerical_tolerances":"independent-plan.md frozen before execution; individualPR.05/.01DN, cross-backend output.10/.02DN",
        "basis_only_comparison":false,"CPU_historical_screen_sha256":"17f4191626bf378a2520590de37933ca13003d6ac6b77dab244158a600fd9fd6"});
    save(&directory.join("screen.json"), &record)?;
    ensure!(
        mechanical,
        "GPU literal-port qualification refused; evidence retained"
    );
    Ok(())
}
#[test]
#[ignore]
fn generated_controls() {
    run().unwrap();
}
