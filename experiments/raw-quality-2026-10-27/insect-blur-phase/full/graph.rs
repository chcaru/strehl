// Root-owned experiment adapter. The existing core fit and global solve remain
// the estimators; this file accepts retained observations, never image pixels.
use super::*;
use anyhow::ensure;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use strehl_core::align::{AlignFailure, Observation, StageFit, TileCensus, fit_similarity};

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    path: PathBuf,
    sha256: String,
    bytes: u64,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    mode: String,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
    observations: Binding,
    observer: Binding,
    held_map: Binding,
    input_order: Binding,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InputObservation {
    ux: f32,
    uy: f32,
    dx: f32,
    dy: f32,
    score: f32,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InputTile {
    ordinal: usize,
    p1: Option<InputObservation>,
    p2: Option<InputObservation>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct InputPair {
    schema: u32,
    ordinal: usize,
    i: usize,
    j: usize,
    tiles: Vec<InputTile>,
}

fn hash(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut block = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut block)?;
        if n == 0 {
            break;
        }
        h.update(&block[..n]);
    }
    Ok(h.finalize().iter().map(|v| format!("{v:02x}")).collect())
}
fn checked(b: &Binding) -> Result<()> {
    ensure!(
        b.path.is_absolute() && b.sha256.len() == 64,
        "strict absolute binding"
    );
    ensure!(
        std::fs::metadata(&b.path)?.len() == b.bytes && hash(&b.path)? == b.sha256,
        "bound file changed: {}",
        b.path.display()
    );
    Ok(())
}
fn file_ref(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":hash(path)?}))
}
fn write_json(path: &Path, value: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}
fn f32_value(v: &Value) -> Result<f32> {
    let bits = u32::from_str_radix(v["bits"].as_str().context("f32 bits")?, 16)?;
    let x = f32::from_bits(bits);
    ensure!(
        x.is_finite() && (v["value"].as_f64().context("f32 value")? as f32).to_bits() == bits,
        "f32 readable/bits mismatch"
    );
    Ok(x)
}
fn scalar(v: f32) -> Value {
    json!({"value":v,"bits":format!("{:08x}",v.to_bits())})
}
fn params(p: SimilarityParams) -> Value {
    let val = |x: f64| json!({"value":x,"bits":format!("{:016x}",x.to_bits())});
    json!({"ax":val(p.ax),"ay":val(p.ay),"g":val(p.g),"rot":val(p.rot)})
}
fn stage_json(r: &std::result::Result<StageFit, AlignFailure>) -> Value {
    match r {
        Ok(s) => json!({"state":"fit","fit":params(s.fit),"used":s.used,"total":s.total,
            "raw_n":s.raw_n,"rms":scalar(s.rms),"lever_rms":scalar(s.lever_rms),
            "peak_mean":scalar(s.peak_mean),"rejected":{"low_contrast":s.rejected.low_contrast,
            "low_peak":s.rejected.low_peak,"border":s.rejected.border,"oob":s.rejected.oob,
            "outlier":s.rejected.outlier}}),
        Err(e) => json!({"state":"refused","reason":format!("{e:?}")}),
    }
}
fn residuals(obs: &[Observation], f: SimilarityParams) -> Vec<f32> {
    obs.iter()
        .map(|o| {
            let x = f.ax + f.g * f64::from(o.ux) - f.rot * f64::from(o.uy);
            let y = f.ay + f.g * f64::from(o.uy) + f.rot * f64::from(o.ux);
            let ex = f64::from(o.dx) - x;
            let ey = f64::from(o.dy) - y;
            (ex * ex + ey * ey).sqrt() as f32
        })
        .collect()
}
// Same one-pass MAD arithmetic as align::fit_stage_impl; calls the actual core
// fit_similarity twice. Exact saved ordinary StageFits commission this adapter.
fn fit(
    obs: &[Observation],
    peaks: &[f32],
    mut census: TileCensus,
) -> (std::result::Result<StageFit, AlignFailure>, Value) {
    let cfg = AlignConfig::deep();
    let mut trace = json!({"correlated":obs.len(),"total":96});
    if obs.len() < cfg.min_tiles {
        return (
            Err(AlignFailure::TooFewTiles {
                correlated: obs.len(),
            }),
            trace,
        );
    }
    let Some(f0) = fit_similarity(obs) else {
        return (Err(AlignFailure::Singular), trace);
    };
    let res = residuals(obs, f0);
    let mut sorted = res.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let med = sorted[sorted.len() / 2];
    let mut dev: Vec<f32> = res.iter().map(|r| (r - med).abs()).collect();
    dev.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mad = dev[dev.len() / 2].max(1e-3);
    let cut = med + cfg.outlier_mads * 1.4826 * mad;
    let keep: Vec<bool> = res.iter().map(|r| *r <= cut).collect();
    let kept: Vec<Observation> = obs
        .iter()
        .zip(&keep)
        .filter(|(_, k)| **k)
        .map(|(o, _)| *o)
        .collect();
    census.outlier = obs.len() - kept.len();
    trace = json!({"correlated":obs.len(),"total":96,"initial_fit":params(f0),
        "initial_residuals":res.iter().map(|&v| scalar(v)).collect::<Vec<_>>(),
        "median":scalar(med),"mad":scalar(mad),"cutoff":scalar(cut),"keep":keep});
    if kept.len() < cfg.min_tiles {
        return (
            Err(AlignFailure::TooFewAfterOutliers {
                survivors: kept.len(),
            }),
            trace,
        );
    }
    let Some(f1) = fit_similarity(&kept) else {
        return (Err(AlignFailure::Singular), trace);
    };
    let kres = residuals(&kept, f1);
    let rms = (kres.iter().map(|r| r * r).sum::<f32>() / kres.len() as f32).sqrt();
    let lever = (kept
        .iter()
        .map(|o| (o.ux * o.ux + o.uy * o.uy) as f64)
        .sum::<f64>()
        / kept.len() as f64)
        .sqrt() as f32;
    let peak_sum: f32 = peaks
        .iter()
        .zip(&keep)
        .filter(|(_, k)| **k)
        .map(|(p, _)| *p)
        .sum();
    trace["final_residuals"] = json!(kres.iter().map(|&v| scalar(v)).collect::<Vec<_>>());
    (
        Ok(StageFit {
            fit: f1,
            used: kept.len(),
            total: 96,
            raw_n: obs.len(),
            rms,
            lever_rms: lever,
            peak_mean: peak_sum / kept.len() as f32,
            rejected: census,
        }),
        trace,
    )
}
fn requested() -> Vec<(usize, usize)> {
    let mut v = Vec::new();
    for &span in &DEFAULT_SPANS {
        for i in 0..299 - span {
            v.push((i, i + span));
        }
    }
    v.sort_unstable();
    v.dedup();
    v
}
fn pair_identity(index: usize, i: usize, j: usize, expected: &[(usize, usize)]) -> Result<()> {
    ensure!(
        expected.get(index) == Some(&(i, j)),
        "missing/reordered/foreign pair"
    );
    Ok(())
}
fn validate_pair(v: &InputPair, count: usize, expected: &[(usize, usize)]) -> Result<()> {
    ensure!(
        v.schema == 1 && v.ordinal == count && v.tiles.len() == 96,
        "full pair/tile census"
    );
    pair_identity(count, v.i, v.j, expected)?;
    ensure!(
        v.tiles.iter().enumerate().all(|(k, t)| t.ordinal == k),
        "tile order"
    );
    Ok(())
}
fn grid(path: &Path) -> Result<Vec<(f32, f32)>> {
    let first = BufReader::new(File::open(path)?)
        .lines()
        .next()
        .context("empty observer")??;
    let v: Value = serde_json::from_str(&first)?;
    let tiles = v["core"]["fine_passes"][0]["tiles"]
        .as_array()
        .context("retained grid")?;
    ensure!(tiles.len() == 96, "complete grid");
    tiles
        .iter()
        .enumerate()
        .map(|(k, t)| {
            ensure!(t["ordinal"] == k && t["size"] == 128, "grid identity");
            Ok((
                t["origin"][0].as_u64().context("tile x")? as f32,
                t["origin"][1].as_u64().context("tile y")? as f32,
            ))
        })
        .collect()
}
fn solve_and_record(
    edges: &[AlignEdge],
    paths: &[PathBuf],
    out: &Path,
    name: &str,
) -> Result<Value> {
    let component = measured_reference_edges(edges, 299, 149);
    let mut vertices = BTreeSet::from([149]);
    for e in &component {
        vertices.insert(e.i);
        vertices.insert(e.j);
    }
    let cycle_rank = component.len() + 1 - vertices.len();
    let geom = PlaneGeometry {
        width: 3516,
        height: 2344,
    };
    let identity = StackIdentity::from_paths("107MSDCF", paths)?;
    let solved = finish_measured_map(
        identity,
        geom,
        299,
        149,
        &DEFAULT_SPANS,
        Resampler::CatmullRom,
        edges,
        None,
    );
    match solved {
        Err(e) => Ok(
            json!({"arm":name,"accepted_edges":edges.len(),"component_vertices":vertices.len(),
            "component_edges":component.len(),"cycle_rank":cycle_rank,"render_eligible":false,"solve_refusal":e.to_string()}),
        ),
        Ok(map) => {
            let path = out.join(format!("{name}-alignment.txt"));
            save_atomic(&map, &path)?;
            let unplaced: Vec<usize> = map
                .warps()
                .iter()
                .enumerate()
                .filter_map(|(k, w)| matches!(w, FrameWarp::Refused(_)).then_some(k))
                .collect();
            Ok(
                json!({"arm":name,"accepted_edges":edges.len(),"component_vertices":vertices.len(),
                "component_edges":component.len(),"cycle_rank":cycle_rank,"unplaced_frames":unplaced,
                "render_eligible":unplaced.is_empty() && cycle_rank>0,"map":file_ref(&path)?,
                "heldout_guide_px":map.provenance().heldout_px,"cycle_floor_guide_px":map.provenance().cycle_floor_px,
                "reference":149,"guide_geometry":[3516,2344],"physical_placement_accuracy_claimed":false}),
            )
        }
    }
}

#[test]
fn graph_input_and_centroid_controls() -> Result<()> {
    let pairs = requested();
    ensure!(pairs.len() == 2340, "pair ladder");
    ensure!(
        pair_identity(0, pairs[1].0, pairs[1].1, &pairs).is_err(),
        "missing pair foil"
    );
    let mut row = InputPair {
        schema: 1,
        ordinal: 0,
        i: pairs[0].0,
        j: pairs[0].1,
        tiles: (0..96)
            .map(|ordinal| InputTile {
                ordinal,
                p1: None,
                p2: None,
            })
            .collect(),
    };
    validate_pair(&row, 0, &pairs)?;
    row.tiles.pop();
    ensure!(validate_pair(&row, 0, &pairs).is_err(), "missing tile foil");
    let truth = SimilarityParams {
        ax: 0.3,
        ay: -0.2,
        g: 0.035,
        rot: -0.02,
    };
    let mut obs = Vec::new();
    for y in [70.0f32, 310.0, 570.0] {
        for x in [130.0f32, 430.0, 890.0] {
            let ux = x - 0.25;
            let uy = y - 0.25;
            obs.push(Observation {
                ux,
                uy,
                dx: (truth.ax + truth.g * f64::from(ux) - truth.rot * f64::from(uy)) as f32,
                dy: (truth.ay + truth.g * f64::from(uy) + truth.rot * f64::from(ux)) as f32,
            });
        }
    }
    let score = |v: &[Observation]| -> Result<f64> {
        let (s, _) = fit(v, &vec![1.0; v.len()], TileCensus::default());
        let f = s.map_err(|e| anyhow::anyhow!("{e:?}"))?.fit;
        Ok((f.ax - truth.ax).hypot(f.ay - truth.ay))
    };
    ensure!(score(&obs)? < 1e-5, "correct centroid positive");
    let mut wrong = obs.clone();
    for o in &mut wrong {
        o.ux += 0.25;
        o.uy += 0.25;
    }
    ensure!(score(&wrong)? > 0.01, "wrong centroid scorer foil");
    wrong = obs.clone();
    for o in &mut wrong {
        o.dx = -o.dx;
        o.dy = -o.dy;
    }
    ensure!(score(&wrong)? > 0.1, "wrong sign scorer foil");
    Ok(())
}

#[test]
#[ignore = "root-scheduled retained-observation global solve; no RAW decoding"]
fn fit_and_solve_weevil_phase_maps() -> Result<()> {
    let path = PathBuf::from(
        std::env::var_os("STREHL_INSECT_BLUR_PHASE_GRAPH_CONFIG").context("strict config")?,
    );
    let config: Config = serde_json::from_slice(&std::fs::read(&path)?)?;
    ensure!(
        config.schema == 1 && ["replay", "candidate"].contains(&config.mode.as_str()),
        "mode/schema"
    );
    ensure!(
        hash(&std::env::current_exe()?)? == config.expected_test_executable_sha256,
        "executable binding"
    );
    ensure!(
        std::env::var_os("STREHL_SMOOTH").is_none()
            && std::env::var_os("STREHL_SMOOTH_HUBER").is_none(),
        "ordinary solve defaults"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    ensure!(
        config.out_dir.is_absolute()
            && !config.out_dir.exists()
            && config
                .out_dir
                .parent()
                .context("output parent")?
                .canonicalize()?
                .starts_with(repo.join("outputs").canonicalize()?),
        "fresh workspace output"
    );
    let bindings = [
        &config.observations,
        &config.observer,
        &config.held_map,
        &config.input_order,
    ];
    for b in &bindings {
        checked(b)?;
    }
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&config.input_order.path)?)?;
    ensure!(order.len() == 299, "299 input identities");
    let paths: Vec<PathBuf> = order
        .iter()
        .enumerate()
        .map(|(i, v)| {
            ensure!(v["index"] == i, "input order");
            Ok(PathBuf::from(v["path"].as_str().context("source path")?))
        })
        .collect::<Result<_>>()?;
    let held = WarpMap::load(&config.held_map.path)?;
    held.check_stack(&StackIdentity::from_paths("107MSDCF", &paths)?)?;
    ensure!(
        held.len() == 299
            && held.provenance().reference == 149
            && held.resampler() == Resampler::CatmullRom,
        "held gauge"
    );
    let expected = requested();
    let spots = grid(&config.observer.path)?;
    std::fs::create_dir(&config.out_dir)?;
    let mut log = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(config.out_dir.join("pair-fits.jsonl"))?,
    );
    let mut edges: [Vec<AlignEdge>; 2] = [Vec::new(), Vec::new()];
    let mut count = 0usize;
    for line in BufReader::new(File::open(&config.observations.path)?).lines() {
        let line = line?;
        ensure!(
            !line.is_empty() && line.len() < (16 << 20),
            "bounded nonempty pair row"
        );
        let mut outputs = Vec::new();
        if config.mode == "replay" {
            let v: Value = serde_json::from_str(&line)?;
            let i = v["i"].as_u64().context("i")? as usize;
            let j = v["j"].as_u64().context("j")? as usize;
            ensure!(v["ordinal"] == count, "ordinal");
            pair_identity(count, i, j, &expected)?;
            let passes = v["core"]["fine_passes"].as_array().context("fine pass")?;
            ensure!(passes.len() == 1, "one held fine pass");
            let s = &passes[0];
            let tiles = s["tiles"].as_array().context("tiles")?;
            ensure!(tiles.len() == 96, "tile census");
            let mut obs = Vec::new();
            let mut peaks = Vec::new();
            let mut census = TileCensus::default();
            for (k, t) in tiles.iter().enumerate() {
                ensure!(t["ordinal"] == k && t["size"] == 128, "tile identity");
                match t["status"].as_str().context("tile status")? {
                    "Ok" => {
                        let o = &t["observation"];
                        obs.push(Observation {
                            ux: f32_value(&o["ux"])?,
                            uy: f32_value(&o["uy"])?,
                            dx: f32_value(&o["dx"])?,
                            dy: f32_value(&o["dy"])?,
                        });
                        peaks.push(f32_value(&t["peak"])?);
                    }
                    "LowContrast" => census.low_contrast += 1,
                    "LowPeak" => census.low_peak += 1,
                    "Border" => census.border += 1,
                    "Oob" => census.oob += 1,
                    _ => bail!("unknown retained status"),
                }
            }
            let (result, trace) = fit(&obs, &peaks, census);
            ensure!(
                stage_json(&result) == s["result"],
                "ordinary stage parity at pair {i},{j}"
            );
            if trace.get("initial_fit").is_some() {
                for key in [
                    "initial_fit",
                    "initial_residuals",
                    "median",
                    "mad",
                    "cutoff",
                    "keep",
                ] {
                    ensure!(
                        trace[key] == s[key],
                        "ordinary trace {key} parity at pair {i},{j}"
                    );
                }
            }
            if trace.get("final_residuals").is_some() {
                ensure!(
                    trace["final_residuals"] == s["final_residuals"],
                    "ordinary final residual parity"
                );
            }
            if let Ok(stage) = &result {
                edges[0].push(AlignEdge::from_stage(i, j, stage));
            }
            outputs.push(
                json!({"i":i,"j":j,"arm":"replay","result":stage_json(&result),"trace":trace}),
            );
        } else {
            let v: InputPair = serde_json::from_str(&line)?;
            validate_pair(&v, count, &expected)?;
            for arm in 0..2 {
                let mut obs = Vec::new();
                let mut peaks = Vec::new();
                let mut ordinals = Vec::new();
                for (k, t) in v.tiles.iter().enumerate() {
                    ensure!(t.ordinal == k, "tile order");
                    let item = if arm == 0 { &t.p1 } else { &t.p2 };
                    if let Some(o) = item {
                        ensure!(
                            [o.ux, o.uy, o.dx, o.dy, o.score]
                                .iter()
                                .all(|x| x.is_finite()),
                            "finite observation"
                        );
                        ensure!(
                            o.ux.to_bits() == (spots[k].0 + 63.75 - 1758.0).to_bits()
                                && o.uy.to_bits() == (spots[k].1 + 63.75 - 1172.0).to_bits(),
                            "physical mean-centroid gauge"
                        );
                        obs.push(Observation {
                            ux: o.ux,
                            uy: o.uy,
                            dx: o.dx,
                            dy: o.dy,
                        });
                        peaks.push(o.score);
                        ordinals.push(k);
                    }
                }
                let (result, trace) = fit(&obs, &peaks, TileCensus::default());
                if let Ok(stage) = &result {
                    edges[arm].push(AlignEdge::from_stage(v.i, v.j, stage));
                }
                outputs.push(json!({"i":v.i,"j":v.j,"arm":arm+1,"new_reader_refused_tiles":96-obs.len(),
                    "observation_tile_ordinals":ordinals,"result":stage_json(&result),"trace":trace}));
            }
        }
        serde_json::to_writer(&mut log, &json!({"ordinal":count,"arms":outputs}))?;
        writeln!(log)?;
        count += 1;
    }
    ensure!(count == 2340, "missing terminal pair rows");
    log.flush()?;
    let names: &[&str] = if config.mode == "replay" {
        &["replay"]
    } else {
        &["p1", "p2"]
    };
    let mut maps = Vec::new();
    for (k, name) in names.iter().enumerate() {
        maps.push(solve_and_record(&edges[k], &paths, &config.out_dir, name)?);
    }
    if config.mode == "replay" {
        ensure!(
            edges[0].len() == 2314 && maps[0]["render_eligible"] == true,
            "ordinary edge/coverage parity"
        );
        ensure!(
            std::fs::read(config.out_dir.join("replay-alignment.txt"))?
                == std::fs::read(&config.held_map.path)?,
            "exact ordinary map text parity"
        );
    }
    for b in &bindings {
        checked(b)?;
    }
    write_json(
        &config.out_dir.join("receipt.json"),
        &json!({"schema":1,"status":"COMPLETE_INSECT_PHASE_GRAPH",
        "complete":true,"mode":config.mode,"pair_count":count,"tile_count":count*96,"maps":maps,
        "pair_fits":file_ref(&config.out_dir.join("pair-fits.jsonl"))?,"inputs_unchanged":true,
        "quality_claim":false,"photographic_admission":false,"RAW_decodes":0,"physical_accuracy_claimed":false}),
    )?;
    Ok(())
}
