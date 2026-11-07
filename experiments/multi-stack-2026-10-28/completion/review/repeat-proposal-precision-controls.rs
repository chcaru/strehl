//! Independent precision-mean causal control. Fixture copied from root consumer
//! SHA256 eb1935044226cff9345381d7ba8cec358fca02e918dcd41700e84f6f654d6748; photon equations/order retained except named noise/signal cases.
//! Identity image geometry is supplied, not estimated. No optical-resolution claim.
pub use strehl_cli::session_align;
#[path = "../../../../crates/strehl-cli/src/session-repeat-proposals.rs"]
mod proposals;
use anyhow::{Result, ensure};
use serde_json::{Value, json};
use std::path::Path;
use strehl_cli::session_sampling::{NativeSampler, SamplingDomain};
use strehl_core::{
    align::{Cx, Resampler, Similarity},
    noise::{Levels, NoiseModel, PlaneNoise, Provenance},
    plane::{PlaneGeometry, QuadSource},
    pyramid::{
        MergeConfig,
        session_fusion::{
            FrozenPrediction, GroupFocusReference, GroupPolicy, GroupWorkspace, PreparedSource,
            SessionMerge, SourceKey,
        },
    },
};
const W: usize = 128;
const FULL: usize = 134;
struct Raw(Vec<u16>);
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: FULL,
            height: FULL,
        }
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let i = y * FULL * 4;
        (
            &self.0[i..i + 2 * FULL],
            &self.0[i + 2 * FULL..i + 4 * FULL],
        )
    }
}
fn model(case: &str, pass: usize) -> NoiseModel {
    NoiseModel::new(
        [PlaneNoise {
            gain_dn_per_e: if case.starts_with("unequal-") && pass == 1 {
                0.8
            } else {
                0.2
            },
            read_noise_e: 5.,
            levels: Levels {
                black: 512.,
                white: 15360.,
            },
        }; 4],
        100.,
        Provenance::Measured,
    )
}
fn true_signal(case: &str, index: usize, c: usize, x: f32, y: f32) -> f32 {
    let case = case.strip_prefix("unequal-").unwrap_or(case);
    let pass = index / 4;
    let ordinal = index % 4;
    let dc = if case == "flat-low" {
        20.
    } else {
        1200. + c as f32 * 80.
    };
    if case.starts_with("flat") {
        return dc;
    }
    if case.starts_with("psf-") {
        let sigma = if case == "psf-focus-sweep" || case == "psf-fine-focus-offset" {
            let z = if x < 64. { 0.5 } else { 2.5 };
            let offset = if case == "psf-fine-focus-offset" && pass == 1 {
                0.25
            } else {
                0.
            };
            0.8 * (ordinal as f32 + offset - z).abs()
        } else if pass == 1 && (case == "psf-blur" || (case == "psf-blue-blur" && c == 2)) {
            0.8
        } else {
            0.
        };
        // Exact Gaussian convolution response of each continuous sine component.
        // The two-depth focus fixture prescribes local Gaussian PSFs; it does
        // not model physical occlusion at their shared depth discontinuity.
        let g = |kx: f32, ky: f32| (-0.5 * sigma * sigma * (kx * kx + ky * ky)).exp();
        return dc
            + 100.
                * (g(0.73, 0.) * (x * 0.73).sin()
                    + g(0., 0.41) * (y * 0.41).cos()
                    + 0.5 * g(0.31, 0.83) * (x * 0.31 + y * 0.83).sin());
    }
    let x = if case == "shift" && pass == 1 {
        x + 0.5
    } else {
        x
    };
    let mut amplitude = 100.;
    if case == "focus-sweep" || case == "fine-focus-offset" {
        let z = if x < 64. { 0.5 } else { 2.5 };
        let offset = if case == "fine-focus-offset" && pass == 1 {
            0.25
        } else {
            0.
        };
        amplitude *= (-0.5 * ((ordinal as f32 + offset - z) / 0.8).powi(2)).exp();
    }
    if (case == "blur" || (case == "blue-blur" && c == 2)) && pass == 1 {
        amplitude *= 0.8;
    }
    let signal =
        dc + amplitude * ((x * 0.73).sin() + (y * 0.41).cos() + 0.5 * (x * 0.31 + y * 0.83).sin());
    if case == "brightness" && pass == 1 {
        signal + 20.
    } else {
        signal
    }
}
fn next(state: &mut u64) -> f32 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (((*state >> 40) as f32) + 0.5) / 16777216.
}
fn raw(case: &str, index: usize, seed: Option<u64>) -> Raw {
    let noise = model(case, index / 4);
    let mut state = 0x75a7_7193_59e8_bbb1_u64
        ^ (index as u64 + 1).wrapping_mul(0x9e37_79b9_7f4a_7c15)
        ^ seed.unwrap_or(0);
    Raw((0..FULL * FULL * 4)
        .map(|i| {
            let x = i % (2 * FULL);
            let y = i / (2 * FULL);
            let plane = strehl_core::CfaPlane::rggb_at(x, y);
            let c = match plane {
                strehl_core::CfaPlane::R => 0,
                strehl_core::CfaPlane::G1 => 1,
                strehl_core::CfaPlane::B => 2,
                strehl_core::CfaPlane::G2 => 3,
            };
            let signal = true_signal(case, index, c, (x / 2) as f32 - 3., (y / 2) as f32 - 3.);
            let perturb = if seed.is_some() {
                let u = next(&mut state);
                let v = next(&mut state);
                (-2. * u.ln()).sqrt()
                    * (std::f32::consts::TAU * v).cos()
                    * noise.sigma(plane, signal)
            } else {
                0.
            };
            if case == "clipped" && index / 4 == 1 && x > FULL {
                15360
            } else {
                (512. + signal + perturb).round().clamp(0., 65535.) as u16
            }
        })
        .collect())
}
#[derive(Clone, Copy, PartialEq, Eq)]
enum Precision {
    Off,
    Oracle,
    Missing,
}
struct Output {
    planes: [Vec<f32>; 4],
    diagnostics: Value,
}
fn exact_planes(a: &Output, b: &Output) -> bool {
    a.planes
        .iter()
        .flatten()
        .zip(b.planes.iter().flatten())
        .all(|(a, b)| a.to_bits() == b.to_bits())
}
fn render(
    case: &str,
    groups: &[Vec<usize>],
    seed: Option<u64>,
    primary: Option<usize>,
    precision: Precision,
    reference: GroupFocusReference,
    bands: usize,
) -> Result<Output> {
    let cfg = MergeConfig {
        bands,
        gate: 2.,
        exponent: 2.,
        sharpen_per_octave: 1.4,
        ..Default::default()
    };
    let policy = GroupPolicy {
        primary,
        ..Default::default()
    };
    let domain = SamplingDomain {
        full: PlaneGeometry {
            width: FULL,
            height: FULL,
        },
        x: 3,
        y: 3,
        width: W,
        height: W,
    };
    let mut sampler = NativeSampler::new(domain)?;
    let mut prepared = PreparedSource::new(W, W, cfg)?;
    let mut group =
        GroupWorkspace::new_with_precision(W, W, cfg, policy, precision != Precision::Off)?;
    let mut merge = SessionMerge::new(W, W, cfg)?;
    for members in groups {
        for &index in members {
            let original = raw(case, index, seed);
            let noise = model(case, index / 4);
            let measured = sampler.gather(
                &original,
                Levels {
                    black: 512.,
                    white: 15360.,
                },
                Similarity {
                    a: Cx::new(1., 0.),
                    b: Cx::new(0., 0.),
                },
                None,
                Resampler::CatmullRom,
            )?;
            prepared.prepare_with_masks(
                SourceKey {
                    acquisition: index as u64,
                    bracket: index / 4,
                },
                std::array::from_fn(|c| measured.planes[c].as_slice()),
                &noise,
                None,
                None,
                &measured.coverage,
                &measured.support,
                1.,
            )?;
            if precision != Precision::Off {
                // Oracle expected original signal, not measured target photons.
                // This commissions the operator, never camera/guide calibration.
                let prediction: [Vec<f32>; 4] = std::array::from_fn(|c| {
                    (0..W * W)
                        .map(|i| true_signal(case, index, c, (i % W) as f32, (i / W) as f32))
                        .collect()
                });
                let support = vec![precision == Precision::Oracle; W * W];
                prepared.predict_precision(
                    FrozenPrediction {
                        acquisition: 10000 + index as u64,
                        signal: std::array::from_fn(|c| prediction[c].as_slice()),
                        support: &support,
                    },
                    &noise,
                    1.,
                    None,
                    None,
                )?;
            }
            merge.add_source(&mut group, &prepared)?;
        }
        merge.fold_group_with_focus_reference(&mut group, reference)?;
    }
    let out = merge.finish()?;
    ensure!(
        out.valid.iter().all(|&v| v) && out.planes.iter().flatten().all(|v| v.is_finite()),
        "invalid actual consumer output"
    );
    let diagnostics=out.diagnostics.iter().map(|d|json!({"averaged":d.averaged_coefficients,"precision":d.precision_averaged_coefficients,"missing_prediction":d.missing_prediction_coefficients,
        "single":d.single_source_coefficients,"ordinary_fallback":d.ordinary_fallback_coefficients,
        "primary_fallback":d.primary_fallback_coefficients,"saturated_fallback":d.saturated_fallback_coefficients})).collect::<Vec<_>>();
    Ok(Output {
        planes: out.planes,
        diagnostics: json!(diagnostics),
    })
}
fn groups() -> Result<proposals::Plan> {
    use session_align::{EdgeReceipt, PairPurpose};
    let sources: Vec<_> = (0..8)
        .map(|i| proposals::Source {
            index: i,
            pass: i / 4,
            sha256: format!("{:064x}", i + 1),
            log_scale: (i % 4) as f64 * 0.0001,
        })
        .collect();
    let mut edges = Vec::new();
    for i in 0..8 {
        for j in i + 1..8 {
            edges.push(EdgeReceipt {
                i,
                j,
                purpose: PairPurpose::CrossProbe,
                stage: "native".into(),
                accepted: true,
                transform_bits: Some([
                    (sources[j].log_scale - sources[i].log_scale)
                        .exp()
                        .to_bits(),
                    0,
                    0,
                    0,
                ]),
                rms_plane_px: Some(0.1),
                lever_plane_px: Some(1000.),
                used: 8,
                attempted: 8,
                correlated: 8,
                peak_mean: Some(0.99),
                refusal: None,
            });
        }
    }
    proposals::plan(&sources, &edges, 0.000025, proposals::RESERVATION_BYTES)
}
fn stats(a: &[f32], reference: &[f32]) -> Value {
    let indices: Vec<_> = (24..104)
        .flat_map(|y| (24..104).map(move |x| y * W + x))
        .collect();
    let n = indices.len() as f64;
    let ma = indices.iter().map(|&i| f64::from(a[i])).sum::<f64>() / n;
    let mr = indices
        .iter()
        .map(|&i| f64::from(reference[i]))
        .sum::<f64>()
        / n;
    let mse = indices
        .iter()
        .map(|&i| f64::from(a[i] - reference[i]).powi(2))
        .sum::<f64>()
        / n;
    let power = indices
        .iter()
        .map(|&i| (f64::from(reference[i]) - mr).powi(2))
        .sum::<f64>()
        / n;
    let cross = indices
        .iter()
        .map(|&i| (f64::from(a[i]) - ma) * (f64::from(reference[i]) - mr))
        .sum::<f64>()
        / n;
    json!({"mse":mse,"mean_difference":ma-mr,"reference_ac_power":power,
        "centered_amplitude_transfer":if power>1e-9 {Some(cross/power)}else{None}})
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 3, "fresh output path flat|full required");
    let out = Path::new(&args[1]);
    ensure!(!out.exists(), "output exists");
    rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build_global()?;
    let plan = groups()?;
    ensure!(
        plan.groups == vec![vec![0, 4], vec![1, 5], vec![2, 6], vec![3, 7]],
        "assignment"
    );
    let singles: Vec<_> = (0..8).map(|i| vec![i]).collect();
    let legacy = vec![
        vec![0, 4],
        vec![1],
        vec![2],
        vec![3],
        vec![5],
        vec![6],
        vec![7],
    ];
    let pass_a: Vec<_> = (0..4).map(|i| vec![i]).collect();
    let pass_b: Vec<_> = (4..8).map(|i| vec![i]).collect();
    use GroupFocusReference::{Delivered, EqualObservation};
    let arms = [
        (
            "equal-proposed",
            &plan.groups,
            None,
            Precision::Off,
            EqualObservation,
        ),
        (
            "precision-oracle-fixed-focus",
            &plan.groups,
            None,
            Precision::Oracle,
            EqualObservation,
        ),
        (
            "precision-oracle-delivered-focus",
            &plan.groups,
            None,
            Precision::Oracle,
            Delivered,
        ),
        (
            "precision-missing-fixed-focus",
            &plan.groups,
            None,
            Precision::Missing,
            EqualObservation,
        ),
        (
            "all-single",
            &singles,
            None,
            Precision::Off,
            EqualObservation,
        ),
        (
            "legacy-partial",
            &legacy,
            None,
            Precision::Off,
            EqualObservation,
        ),
        (
            "equal-primary-a",
            &plan.groups,
            Some(0),
            Precision::Off,
            EqualObservation,
        ),
        (
            "precision-primary-a",
            &plan.groups,
            Some(0),
            Precision::Oracle,
            EqualObservation,
        ),
        (
            "equal-primary-b",
            &plan.groups,
            Some(1),
            Precision::Off,
            EqualObservation,
        ),
        (
            "precision-primary-b",
            &plan.groups,
            Some(1),
            Precision::Oracle,
            EqualObservation,
        ),
        ("pass-a", &pass_a, None, Precision::Off, EqualObservation),
        ("pass-b", &pass_b, None, Precision::Off, EqualObservation),
    ];
    let flat = ["unequal-flat-low", "unequal-flat-bright"];
    let full = [
        "unequal-variance",
        "stationary",
        "psf-blur",
        "psf-blue-blur",
        "psf-fine-focus-offset",
        "unequal-psf-blur",
        "unequal-psf-fine-focus-offset",
        "brightness",
        "shift",
        "clipped",
    ];
    let cases: &[&str] = match args[2].as_str() {
        "flat" => &flat,
        "full" => &full,
        _ => anyhow::bail!("mode"),
    };
    let band_counts: &[usize] = if args[2] == "flat" { &[0, 7] } else { &[7] };
    let mut rows = Vec::new();
    let mut temporal = Vec::new();
    let mut exact_missing = 0;
    for &bands in band_counts {
        for &case in cases {
            let clean: Vec<_> = arms
                .iter()
                .map(|(_, g, p, q, r)| render(case, g, None, *p, *q, *r, bands))
                .collect::<Result<_>>()?;
            ensure!(
                exact_planes(&clean[0], &clean[3]),
                "missing guide clean must equal existing mean bitwise"
            );
            exact_missing += 1;
            for (a, (name, _, _, _, _)) in arms.iter().enumerate() {
                rows.push(json!({"case":case,"bands":bands,"arm":name,"seed":null,"diagnostics":clean[a].diagnostics,
                "against_clean_all_single":(0..4).map(|c|stats(&clean[a].planes[c],&clean[4].planes[c])).collect::<Vec<_>>(),
                "against_clean_passes":(10..12).map(|r|(0..4).map(|c|stats(&clean[a].planes[c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>()}));
            }
            let mut means: Vec<[Vec<f32>; 4]> = (0..arms.len())
                .map(|_| std::array::from_fn(|_| vec![0.; W * W]))
                .collect();
            let mut m2 = means.clone();
            for seed in 160..168 {
                let measured: Vec<_> = arms
                    .iter()
                    .map(|(_, g, p, q, r)| render(case, g, Some(seed), *p, *q, *r, bands))
                    .collect::<Result<_>>()?;
                ensure!(
                    exact_planes(&measured[0], &measured[3]),
                    "missing guide noisy must equal existing mean bitwise"
                );
                exact_missing += 1;
                for (a, (name, _, _, _, _)) in arms.iter().enumerate() {
                    let count = (seed - 159) as f32;
                    for c in 0..4 {
                        for i in 0..W * W {
                            let delta = measured[a].planes[c][i] - means[a][c][i];
                            means[a][c][i] += delta / count;
                            m2[a][c][i] += delta * (measured[a].planes[c][i] - means[a][c][i]);
                        }
                    }
                    rows.push(json!({"case":case,"bands":bands,"arm":name,"seed":seed,"diagnostics":measured[a].diagnostics,
                    "against_clean_all_single":(0..4).map(|c|stats(&measured[a].planes[c],&clean[4].planes[c])).collect::<Vec<_>>(),
                    "against_clean_passes":(10..12).map(|r|(0..4).map(|c|stats(&measured[a].planes[c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>()}));
                }
            }
            for (a, (name, _, _, _, _)) in arms.iter().enumerate() {
                let variance: Vec<_> = (0..4)
                    .map(|c| {
                        (24..104)
                            .flat_map(|y| (24..104).map(move |x| y * W + x))
                            .map(|i| f64::from(m2[a][c][i]) / 7.)
                            .sum::<f64>()
                            / 6400.
                    })
                    .collect();
                temporal.push(json!({"case":case,"bands":bands,"arm":name,"realizations":8,"sample_temporal_variance":variance,
                "mean_against_clean_all_single":(0..4).map(|c|stats(&means[a][c],&clean[4].planes[c])).collect::<Vec<_>>(),
                "mean_against_clean_passes":(10..12).map(|r|(0..4).map(|c|stats(&means[a][c],&clean[r].planes[c])).collect::<Vec<_>>()).collect::<Vec<_>>()}));
            }
            eprintln!("completed {case} bands{bands}");
        }
    }
    let result = json!({"schema":"strehl.repeat-proposal-precision-controls.v1","command":args,"workers":4,
        "plan":plan,"rows":rows,"temporal_summary":temporal,"missing_guide_bitwise_checks":exact_missing,
        "scope":"Mechanical actual-core test only. Exact source expected means are oracle predictions in original black-subtracted DN; not a real independent-photon guide or physical calibration. Group membership fixed, unchanged residual admission and primary; EqualObservation freezes focus scoring except explicitly delivered-focus foil. Original u16 photon plants retained. Eight seeds, per-CFA/component risk to actual noise-gated clean pass and all-single references; no argmax, photographic quality or new matching admission.",
        "limitations":["Oracle variance does not commission the real shared noisy guide.","Identity resampling only; existing warped-source controls remain separate.","PSF fixture prescribes local Gaussian blur, not physical occlusion at the two-depth boundary.","Quantization and shot-Gaussian approximation remain, without fitting camera noise."]});
    std::fs::write(out, format!("{}\n", serde_json::to_string_pretty(&result)?))?;
    Ok(())
}
