use super::*;
use serde_json::{Value, json};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

const W: usize = 384;
const H: usize = 288;
const SX: f64 = 1.010;
const SY: f64 = 0.990;

fn f32j(v: f32) -> Value {
    json!({"bits":v.to_bits(),"value":v.is_finite().then_some(v)})
}
fn f64j(v: f64) -> Value {
    json!({"bits":v.to_bits(),"value":v.is_finite().then_some(v)})
}
fn params(p: SimilarityParams) -> Value {
    json!([f64j(p.ax), f64j(p.ay), f64j(p.g), f64j(p.rot)])
}
fn outcome(r: &Result<StageFit, AlignFailure>) -> Value {
    match r {
        Ok(s) => json!({"ok":true,"fit":params(s.fit),"used":s.used,"total":s.total,
            "raw_n":s.raw_n,"rms":f32j(s.rms),"lever":f32j(s.lever_rms),
            "peak_mean":f32j(s.peak_mean),"census":format!("{:?}",s.rejected)}),
        Err(e) => json!({"ok":false,"failure":format!("{e:?}")}),
    }
}
fn stage_json(s: &StageTrace) -> Value {
    let m = &s.measurements;
    let tiles: Vec<Value> = m.tiles.iter().map(|t| json!({
        "ordinal":t.ordinal,"origin":[t.probe.tx,t.probe.ty],"size":t.probe.size,
        "radius":t.probe.radius,"predicted":[f32j(t.probe.predicted.0),f32j(t.probe.predicted.1)],
        "fit_center":[f64j(t.fit_center.0),f64j(t.fit_center.1)],
        "centered_offset":[f64j(t.centered_offset.0),f64j(t.centered_offset.1)],
        "status":format!("{:?}",t.measurement.status),"contrast":f32j(t.measurement.contrast),
        "measurement":[f32j(t.measurement.dx),f32j(t.measurement.dy),f32j(t.measurement.peak)],
        "observation_index":t.observation_index,
        "observation":t.observation.map(|o|json!([f32j(o.ux),f32j(o.uy),f32j(o.dx),f32j(o.dy)]))
    })).collect();
    json!({"result":outcome(&s.result),"tiles":tiles,"seed":m.seed.map(params),
        "dimensions":[m.reference_dimensions,m.moving_dimensions],"plane_center":[f64j(m.plane_center.0),f64j(m.plane_center.1)],
        "config":format!("{:?}",m.config),"warped_tiles_used":m.warped_tiles_used,
        "initial_fit":m.initial_fit.map(params),"initial_residuals":m.initial_residuals.as_ref().map(|v|v.iter().copied().map(f32j).collect::<Vec<_>>()),
        "median":m.median.map(f32j),"mad":m.mad.map(f32j),"cutoff":m.cutoff.map(f32j),"keep":m.keep,
        "final_fit":m.final_fit.map(params),"final_residuals":m.final_residuals.as_ref().map(|v|v.iter().copied().map(f32j).collect::<Vec<_>>()),
        "census":format!("{:?}",m.census)})
}
fn trace_json(t: &PairTrace) -> Value {
    json!({"result":outcome(&t.result),"selected_fine_pass":t.selected_fine_pass,
        "termination":format!("{:?}",t.termination),
        "passes":t.fine_passes.iter().map(|p|json!({"index":p.index,"corner_moved":p.corner_moved.map(f64j),"stage":stage_json(&p.stage)})).collect::<Vec<_>>()})
}
fn cfg() -> AlignConfig {
    AlignConfig {
        coarse_factors: vec![2],
        coarse_tile: 16,
        coarse_grid: (7, 5),
        coarse_radius: 4,
        fine_tile: 32,
        fine_grid: (7, 5),
        fine_radius: 4,
        margin: 32,
        min_tiles: 12,
        min_contrast: 10.,
        min_peak: 0.75,
        fine_iters: 3,
        warp_tiles: false,
        ..AlignConfig::shallow()
    }
}
fn uniform(seed: &mut u32) -> f64 {
    *seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
    ((*seed >> 8) as f64 + 0.5) / 16777216.
}
#[allow(clippy::too_many_arguments)]
fn render(sx: f64, sy: f64, tx: f64, ty: f64, sigma: f64, patch: bool, mut seed: u32) -> Vec<f32> {
    let terms = [
        (180., 0.037, 0.013, 0.2),
        (140., 0.011, -0.041, 1.1),
        (110., 0.067, 0.023, 2.3),
        (95., 0.019, 0.079, 0.7),
        (80., 0.083, -0.055, 1.7),
    ];
    (0..W * H)
        .map(|i| {
            let (x, y) = ((i % W) as f64, (i / W) as f64);
            let shift = if patch && (168.0..216.0).contains(&x) && (120.0..168.0).contains(&y) {
                3.0
            } else {
                0.0
            };
            let qx = (x - W as f64 / 2. - tx - shift) / sx + W as f64 / 2.;
            let qy = (y - H as f64 / 2. - ty) / sy + H as f64 / 2.;
            let mut value = 1000.;
            for &(a, fx, fy, p) in &terms {
                // Independent analytic continuous scene; symmetric source-coordinate Gaussian.
                let damp = (-2.
                    * std::f64::consts::PI.powi(2)
                    * sigma
                    * sigma
                    * ((fx / sx).powi(2) + (fy / sy).powi(2)))
                .exp();
                value += a * damp * (std::f64::consts::TAU * (fx * qx + fy * qy) + p).cos();
            }
            // One fixed known guide-noise distribution, fresh after optical blur.
            value += 2. * ((0..12).map(|_| uniform(&mut seed)).sum::<f64>() - 6.);
            value as f32
        })
        .collect()
}
fn save_plane(out: &Path, name: &str, p: &[f32]) -> std::io::Result<()> {
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join(format!("{name}.f32le")))?;
    for v in p {
        f.write_all(&v.to_le_bytes())?;
    }
    let mut f = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join(format!("{name}.pgm")))?;
    write!(f, "P5\n{W} {H}\n255\n")?;
    f.write_all(
        &p.iter()
            .map(|v| ((v / 2048.).clamp(0., 1.) * 255.).round() as u8)
            .collect::<Vec<_>>(),
    )
}
fn trace_valid(t: &PairTrace, spots: &[(usize, usize)]) -> bool {
    let mut good = true;
    for (pass, p) in t.fine_passes.iter().enumerate() {
        let m = &p.stage.measurements;
        good &= p.index == pass
            && m.tiles.len() == spots.len()
            && m.plane_center == (W as f64 / 2., H as f64 / 2.);
        let mut count = 0;
        let mut census = TileCensus::default();
        for (i, tile) in m.tiles.iter().enumerate() {
            let Some(&(tx, ty)) = spots.get(i) else {
                good = false;
                continue;
            };
            let center = (tx as f64 + 16., ty as f64 + 16.);
            good &= tile.ordinal == i
                && (tile.probe.tx, tile.probe.ty) == (tx, ty)
                && tile.fit_center == center
                && tile.centered_offset == (center.0 - W as f64 / 2., center.1 - H as f64 / 2.);
            match tile.measurement.status {
                TileStatus::Ok => {
                    good &= tile.observation_index == Some(count);
                    good &= tile.observation.is_some_and(|o| {
                        o.ux.to_bits() == ((center.0 - W as f64 / 2.) as f32).to_bits()
                            && o.uy.to_bits() == ((center.1 - H as f64 / 2.) as f32).to_bits()
                            && o.dx.to_bits() == tile.measurement.dx.to_bits()
                            && o.dy.to_bits() == tile.measurement.dy.to_bits()
                    });
                    count += 1;
                }
                TileStatus::LowContrast => census.low_contrast += 1,
                TileStatus::LowPeak => census.low_peak += 1,
                TileStatus::Border => census.border += 1,
                TileStatus::Oob => census.oob += 1,
            }
            if tile.measurement.status != TileStatus::Ok {
                good &= tile.observation_index.is_none() && tile.observation.is_none();
            }
        }
        if let Some(keep) = &m.keep {
            good &= keep.len() == count;
            census.outlier = keep.iter().filter(|v| !**v).count();
            good &= m
                .initial_residuals
                .as_ref()
                .is_some_and(|v| v.len() == count);
            if let Ok(fit) = &p.stage.result {
                good &= fit.raw_n == count
                    && fit.used == count - census.outlier
                    && m.final_residuals
                        .as_ref()
                        .is_some_and(|v| v.len() == fit.used);
            }
        }
        good &= census == m.census;
    }
    if let Some(index) = t.selected_fine_pass {
        good &= t.fine_passes.get(index).is_some_and(|p| {
            p.stage.result.is_ok() && outcome(&p.stage.result) == outcome(&t.result)
        });
    } else {
        good &= t.result.is_err();
    }
    good
}
fn geometry(
    trace: &PairTrace,
    spots: &[(usize, usize)],
    sx: f64,
    sy: f64,
    tx: f64,
    ty: f64,
    positive: bool,
) -> Value {
    let Some(pass) = trace.fine_passes.first() else {
        return json!({"pass":false,"reason":"no fine pass"});
    };
    let rows = &pass.stage.measurements.tiles;
    let all = rows.len() == 35 && rows.iter().all(|r| r.measurement.status == TileStatus::Ok);
    if !all {
        return json!({"pass":false,"reason":"fixed 35-tile population unavailable"});
    }
    let xx: f64 = spots
        .iter()
        .map(|(x, _)| (*x as f64 + 16. - W as f64 / 2.).powi(2))
        .sum();
    let yy: f64 = spots
        .iter()
        .map(|(_, y)| (*y as f64 + 16. - H as f64 / 2.).powi(2))
        .sum();
    let g = ((SX - 1.) * xx + (SY - 1.) * yy) / (xx + yy);
    let mut numerator = 0.;
    let mut denominator = 0.;
    let mut error = 0.;
    let mut mean = [0., 0.];
    for r in rows {
        let (u, v) = r.centered_offset;
        let template = [(SX - 1. - g) * u, (SY - 1. - g) * v];
        let measured = [r.measurement.dx as f64, r.measurement.dy as f64];
        let truth = [(sx - 1.) * u + tx, (sy - 1.) * v + ty];
        for k in 0..2 {
            numerator += template[k] * measured[k];
            denominator += template[k] * template[k];
            error += (measured[k] - truth[k]).powi(2);
            mean[k] += measured[k] / 35.;
        }
    }
    let amplitude = numerator / denominator;
    let rms = (error / 35.).sqrt();
    let pass = if positive {
        (0.75..=1.25).contains(&amplitude) && rms <= 0.35
    } else {
        amplitude.abs() <= 0.20 && mean[0].hypot(mean[1]) <= 0.15
    };
    json!({"pass":pass,"fixed_population":35,"all_correlated":all,"signed_non_similarity_amplitude":amplitude,
        "vector_rms_error_guide_pixels":rms,"mean_displacement_guide":mean,
        "positive":positive,"positive_amplitude_bounds":[0.75,1.25],"positive_rms_bound":0.35,
        "null_amplitude_bound":0.20,"null_mean_bound":0.15})
}

#[test]
#[ignore = "root-owned bounded observer commissioning"]
fn generated_controls() -> anyhow::Result<()> {
    let out = std::path::PathBuf::from(std::env::var("STREHL_INSECT_PLACEMENT_CORE_OUT")?);
    fs::create_dir(&out)?;
    let config = cfg();
    let reference = render(1., 1., 0., 0., 0., false, 0x11223344);
    let rp = PlaneRef::new(&reference, W, H).unwrap();
    let pyram = AlignPyramid::build(rp, &config).unwrap();
    let spots = tile_grid(rp, 32, 7, 5, 32).unwrap();
    save_plane(&out, "reference", &reference)?;
    let cases = [
        ("sharp-null", 1., 1., 0., 0., 0., false, false),
        ("symmetric-defocus-null", 1., 1., 0., 0., 2., false, false),
        ("non-similarity", SX, SY, 0., 0., 0., false, true),
        ("non-similarity-defocus", SX, SY, 0., 0., 2., false, true),
        ("outlier-patch", 1., 1., 0., 0., 0., true, false),
    ];
    let mut records = Vec::new();
    let mut mechanics = true;
    let mut geometric = true;
    for (index, (name, sx, sy, tx, ty, sigma, patch, positive)) in cases.into_iter().enumerate() {
        let moving = render(sx, sy, tx, ty, sigma, patch, 0x55667700 + index as u32);
        let before: Vec<u32> = reference
            .iter()
            .chain(&moving)
            .map(|v| v.to_bits())
            .collect();
        let mp = PlaneRef::new(&moving, W, H).unwrap();
        let pyramid = AlignPyramid::build(mp, &config).unwrap();
        let a = AlignFrame {
            plane: rp,
            pyramid: &pyram,
        };
        let b = AlignFrame {
            plane: mp,
            pyramid: &pyramid,
        };
        let ordinary = align_pair(a, b, &spots, &config);
        let mut traces = Vec::new();
        let observed =
            align_pair_observed(a, b, &spots, &config, Some(&mut |t| traces.push(t.clone())));
        let unchanged = before
            == reference
                .iter()
                .chain(&moving)
                .map(|v| v.to_bits())
                .collect::<Vec<_>>();
        let mut ok = outcome(&ordinary) == outcome(&observed) && unchanged && traces.len() == 1;
        let mut score = json!({"not_scored":"outlier census control"});
        if let Some(trace) = traces.first() {
            ok &= trace_valid(trace, &spots) && outcome(&trace.result) == outcome(&observed);
            if patch {
                ok &= trace
                    .fine_passes
                    .iter()
                    .any(|p| p.stage.measurements.census.outlier > 0);
            } else {
                score = geometry(trace, &spots, sx, sy, tx, ty, positive);
                geometric &= score["pass"] == true;
                if positive {
                    let mut wrong = trace.clone();
                    for tile in &mut wrong.fine_passes[0].stage.measurements.tiles {
                        tile.measurement.dx *= 0.5;
                        tile.measurement.dy *= 0.5;
                    }
                    let foil = geometry(&wrong, &spots, sx, sy, tx, ty, true);
                    let rejected = foil["pass"] == false;
                    geometric &= rejected;
                    score["wrong_guide_native_scale_foil"] = foil;
                    score["wrong_scale_foil_rejected"] = json!(rejected);
                }
            }
        }
        mechanics &= ok;
        save_plane(&out, name, &moving)?;
        records.push(
            json!({"name":name,"observer_bits_and_population_pass":ok,"inputs_unchanged":unchanged,
            "ordinary":outcome(&ordinary),"observed":outcome(&observed),"geometry":score,
            "trace":traces.first().map(trace_json)}),
        );
    }
    // Every failed tile is retained; no fabricated zero displacement or survivor mask.
    let flat = vec![1000.; W * H];
    let fp = PlaneRef::new(&flat, W, H).unwrap();
    let mut stage_traces = Vec::new();
    let ordinary = fit_stage(fp, rp, 32, &spots, 4, None, &config);
    let observed = fit_stage_observed(
        fp,
        rp,
        32,
        &spots,
        4,
        None,
        &config,
        Some(&mut |t| stage_traces.push(t.clone())),
    );
    let flat_pass = outcome(&ordinary) == outcome(&observed)
        && stage_traces.len() == 1
        && observed.is_err()
        && stage_traces[0].measurements.tiles.len() == 35
        && stage_traces[0].measurements.keep.is_none()
        && stage_traces[0].measurements.tiles.iter().all(|t| {
            t.measurement.status == TileStatus::LowContrast
                && t.measurement.dx.is_nan()
                && t.measurement.dy.is_nan()
                && t.observation.is_none()
        });
    let fpyramid = AlignPyramid::build(fp, &config).unwrap();
    let mut refused = Vec::new();
    let coarse_ordinary = align_pair(
        AlignFrame {
            plane: fp,
            pyramid: &fpyramid,
        },
        AlignFrame {
            plane: rp,
            pyramid: &pyram,
        },
        &spots,
        &config,
    );
    let coarse = align_pair_observed(
        AlignFrame {
            plane: fp,
            pyramid: &fpyramid,
        },
        AlignFrame {
            plane: rp,
            pyramid: &pyram,
        },
        &spots,
        &config,
        Some(&mut |t| refused.push(t.clone())),
    );
    let coarse_pass = outcome(&coarse_ordinary) == outcome(&coarse)
        && coarse.is_err()
        && refused.len() == 1
        && refused[0].fine_passes.is_empty()
        && refused[0].selected_fine_pass.is_none();
    // First unwarped match fits inside the image; the next warped full search
    // rectangle crosses its right boundary. No tune/search is used to force failure.
    let mut boundary_cfg = config.clone();
    boundary_cfg.coarse_factors.clear();
    boundary_cfg.warp_tiles = true;
    boundary_cfg.min_tiles = 3;
    let boundary_spots = vec![(350, 40), (350, 120), (200, 220)];
    let moved = render(1., 1., 2., 0., 0., false, 0x81726354);
    let moved_plane = PlaneRef::new(&moved, W, H).unwrap();
    let ra = AlignPyramid::build(rp, &boundary_cfg).unwrap();
    let rb = AlignPyramid::build(moved_plane, &boundary_cfg).unwrap();
    let a = AlignFrame {
        plane: rp,
        pyramid: &ra,
    };
    let b = AlignFrame {
        plane: moved_plane,
        pyramid: &rb,
    };
    let ordinary = align_pair(a, b, &boundary_spots, &boundary_cfg);
    let mut retained = Vec::new();
    let observed = align_pair_observed(
        a,
        b,
        &boundary_spots,
        &boundary_cfg,
        Some(&mut |t| retained.push(t.clone())),
    );
    let retained_pass = outcome(&ordinary) == outcome(&observed)
        && observed.is_ok()
        && retained.len() == 1
        && retained[0].selected_fine_pass == Some(0)
        && retained[0].fine_passes.len() == 2
        && matches!(
            retained[0].termination,
            PairTermination::FinePassFailedRetained { pass: 1, .. }
        )
        && retained[0].fine_passes[1].stage.result.is_err()
        && retained[0].fine_passes[1].stage.measurements.census.oob >= 2
        && trace_valid(&retained[0], &boundary_spots);
    save_plane(&out, "retained-pass-boundary", &moved)?;
    mechanics &= flat_pass && coarse_pass && retained_pass;
    let report = json!({"status":"COMPLETE_INSECT_PLACEMENT_CORE_CONTROLS","all_cases_completed":true,
        "mechanical_pass":mechanics,"geometry_pass":geometric,"all_pass":mechanics&&geometric,
        "configuration":format!("{config:?}"),"guide_dimensions":[W,H],"noise_sigma_guide_dn":2.0,
        "cases":records,"flat_stage":{"pass":flat_pass,"trace":stage_traces.first().map(stage_json)},
        "coarse_refusal":{"pass":coarse_pass,"ordinary":outcome(&coarse_ordinary),"trace":refused.first().map(trace_json)},
        "later_failed_pass_retained":{"pass":retained_pass,"ordinary":outcome(&ordinary),"trace":retained.first().map(trace_json)},
        "track_scope":"pair-only static plants; no deep-track placement/curvature qualification",
        "display":"native PGM; clamp(DN/2048,0,1), round255; complete f32 masters retained",
        "photographic_admission":false,"placement_improvement_claimed":false});
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("core-screen.json"))?;
    serde_json::to_writer_pretty(&mut file, &report)?;
    file.write_all(b"\n")?;
    anyhow::ensure!(
        mechanics && geometric,
        "observer controls refused; complete evidence retained"
    );
    Ok(())
}
