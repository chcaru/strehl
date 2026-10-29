//! Flat first; exact measured warp and actual core output path, common truth.
use super::*;
fn truth(mode: &str) -> Planes {
    std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        (0..W * W)
            .map(|i| {
                let x = (i % W) as f32 + dx as f32 * 0.5 - 0.25;
                let y = (i / W) as f32 + dy as f32 * 0.5 - 0.25;
                if mode == "signal" {
                    1200. + 100. * (x * 0.07).sin() + 80. * (y * 0.11).cos()
                } else {
                    1200.
                }
            })
            .collect()
    })
}
fn ids() -> Vec<usize> {
    (24..W - 24)
        .flat_map(|y| (24..W - 24).map(move |x| y * W + x))
        .collect()
}
fn compare(image: &Planes, reference: &Planes) -> Vec<Value> {
    (0..4).map(|c|{let ids=ids();let n=ids.len() as f64;let mean=ids.iter().map(|&i|f64::from(reference[c][i])).sum::<f64>()/n;let den=ids.iter().map(|&i|(f64::from(reference[c][i])-mean).powi(2)).sum::<f64>();let mse=ids.iter().map(|&i|(f64::from(image[c][i])-f64::from(reference[c][i])).powi(2)).sum::<f64>()/n;let projection=ids.iter().map(|&i|(f64::from(reference[c][i])-mean)*(f64::from(image[c][i])-mean)).sum::<f64>()/den;json!({"rmse_to_common_unblurred_dn":mse.sqrt(),"signal_projection":if den>0. {json!(projection)}else{Value::Null}})}).collect()
}
pub(super) fn commission(c: &warped::Contexts, report: &Value, output: &Path) -> Result<()> {
    let domain = SamplingDomain {
        full: c.map.geometry(),
        x: 536,
        y: 257,
        width: W,
        height: W,
    };
    let indices = [31, 93];
    let valid = vec![true; W * W];
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut rows = Vec::new();
    for mode in ["flat", "signal"] {
        let reference = truth(mode);
        let run = |trial: Option<u64>| -> Result<Vec<Outcome>> {
            let mut sampler = RegionSampler::new(domain, 8 << 20)?;
            pool.install(|| {
                produce(c, report, indices, &reference, &valid, 28, |index| {
                    let pass = usize::from(index >= 62);
                    let t = c.map.warps()[index].placed().context("unplaced control")?;
                    let seed = trial
                        .map(|n| 1 + n * 7919 + index as u64 * 5939)
                        .unwrap_or(0);
                    let raw = warped::plant(
                        domain,
                        t,
                        c.profiles[pass],
                        &c.noise[pass],
                        c.gains[pass],
                        mode,
                        0.,
                        seed,
                    )?;
                    Ok(copied(sampler.gather(
                        &raw,
                        c.noise[pass].plane(CfaPlane::R).levels,
                        t,
                        c.profiles[pass],
                        c.map.resampler(),
                    )?))
                })
            })
        };
        let clean = run(None)?;
        if mode == "flat" {
            let trials = 16;
            let mut mean: Vec<_> = (0..4)
                .map(|_| {
                    [
                        vec![0f64; W * W],
                        vec![0.; W * W],
                        vec![0.; W * W],
                        vec![0.; W * W],
                    ]
                })
                .collect();
            let mut m2 = mean.clone();
            for trial in 0..trials {
                let produced = run(Some(trial))?;
                for arm in 0..4 {
                    for color in 0..4 {
                        for i in ids() {
                            ensure!(produced[arm].valid[i], "invalid flat control output");
                            let value = f64::from(produced[arm].planes[color][i]);
                            let delta = value - mean[arm][color][i];
                            mean[arm][color][i] += delta / (trial + 1) as f64;
                            m2[arm][color][i] += delta * (value - mean[arm][color][i]);
                        }
                    }
                }
            }
            let mut variances = [[0.; 4]; 4];
            for arm in 0..4 {
                let mut planes = Vec::new();
                for color in 0..4 {
                    let ids = ids();
                    let n = ids.len() as f64;
                    let variance = ids
                        .iter()
                        .map(|&i| m2[arm][color][i] / (trials - 1) as f64)
                        .sum::<f64>()
                        / n;
                    let bias = ids
                        .iter()
                        .map(|&i| mean[arm][color][i] - 1200.)
                        .sum::<f64>()
                        / n;
                    ensure!(bias.abs() < 4., "flat output bias");
                    variances[arm][color] = variance;
                    planes.push(json!({"temporal_variance_dn2":variance,"mean_bias_to_common_flat_dn":bias}));
                }
                rows.push(json!({"mode":mode,"arm":ARMS[arm],"trials":trials,"planes":planes,"clean_transfer":compare(&clean[arm].planes,&reference)}));
            }
            for color in 0..4 {
                ensure!(
                    variances[0][color] > variances[1][color],
                    "exposure noise order wrong"
                );
                ensure!(
                    variances[3][color] < variances[2][color] * 1.1,
                    "precision fails equal-repeat flat control"
                );
            }
            println!("Actual warped core flat controls passed; variances {variances:?}");
        } else {
            for arm in 0..4 {
                let stats = compare(&clean[arm].planes, &reference);
                for row in &stats {
                    ensure!(
                        row["rmse_to_common_unblurred_dn"].as_f64().unwrap() < 15.,
                        "actual consumer clean signal loss"
                    );
                }
                rows.push(json!({"mode":mode,"arm":ARMS[arm],"clean_transfer":stats}));
            }
            let base = &clean[3].planes;
            for foil in ["constant-output", "blurred-output", "shifted-output"] {
                let mut poisoned = base.clone();
                let mut scratch = vec![0.; W * W];
                for color in 0..4 {
                    match foil {
                        "constant-output" => {
                            let mean = base[color].iter().sum::<f32>() / (W * W) as f32;
                            poisoned[color].fill(mean);
                        }
                        "blurred-output" => box_mean(
                            &base[color],
                            PlaneGeometry {
                                width: W,
                                height: W,
                            },
                            12,
                            &mut scratch,
                            &mut poisoned[color],
                        ),
                        _ => {
                            for y in 0..W {
                                for x in 0..W {
                                    poisoned[color][y * W + x] =
                                        base[color][y * W + (x + 12).min(W - 1)];
                                }
                            }
                        }
                    }
                }
                let stats = compare(&poisoned, &reference);
                ensure!(
                    stats
                        .iter()
                        .all(|v| v["rmse_to_common_unblurred_dn"].as_f64().unwrap() > 15.),
                    "transfer sentinel failed to reject {foil}"
                );
                rows.push(json!({"mode":mode,"foil":foil,"clean_transfer":stats,"rejected":true}));
            }
            println!("Actual core common-signal controls and constant/blur/shift foils passed");
        }
    }
    write(
        &output.join("consumer-controls-before-measurement.json"),
        &json!({"schema":"strehl.real-noise-consumer-controls.v1","source_sha256":sha(include_bytes!("real-noise-consumer-controls.rs")),"rows":rows,"scope":"Measured trajectory+optics original-u16 injected-noise plants through the actual four core consumer arms; common unblurred clean reference. Ideal frozen guide isolates conditional consumer behavior; it does not validate real sensor calibration."}),
    )?;
    Ok(())
}
