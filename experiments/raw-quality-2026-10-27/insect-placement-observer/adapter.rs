// Test-only export of the actual normal alignment's producing observations.
use super::*;
use anyhow::ensure;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufWriter, Read, Write},
    mem::size_of,
    sync::Mutex,
    time::{Instant, SystemTime},
};
use strehl_core::align::{AlignFailure, PairTrace, StageFit, TileCensus};

const ORDER_SHA: &str = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f";
const MAP_SHA: &str = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225";
const SOURCE149_SHA: &str = "e85572179c8a98f5a2de2be5c81cd0b1bdeae67999aa00e585c6dde35f531154";
const TRACE_LIMIT: usize = 256 * 1024 * 1024;
const JSONL_LIMIT: usize = 512 * 1024 * 1024;
const PARITY_PAIRS: [(usize, usize); 4] = [(0, 1), (104, 105), (148, 149), (0, 128)];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    index: usize,
    path: PathBuf,
    sha256: String,
    bytes: u64,
    mtime_ns: u64,
}
fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn sha(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(digest(h))
}
fn guide_hash(plane: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in plane.chunks(bytes.len() / 4) {
        for (dst, v) in bytes.as_chunks_mut::<4>().0.iter_mut().zip(chunk) {
            dst.copy_from_slice(&v.to_bits().to_le_bytes());
        }
        h.update(&bytes[..chunk.len() * 4]);
    }
    digest(h)
}
fn source_identity(s: &Source) -> Result<Value> {
    let m = std::fs::metadata(&s.path)?;
    let mtime = u64::try_from(
        m.modified()?
            .duration_since(SystemTime::UNIX_EPOCH)?
            .as_nanos(),
    )?;
    let observed_sha = sha(&s.path)?;
    ensure!(
        m.len() == s.bytes && mtime == s.mtime_ns && observed_sha == s.sha256,
        "source {} differs from frozen manifest",
        s.index
    );
    Ok(
        json!({"index":s.index,"path":s.path,"bytes":m.len(),"mtime_ns":mtime,"sha256":observed_sha}),
    )
}
fn file_ref(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":sha(path)?}))
}
fn write_json(path: &Path, v: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    writeln!(f)?;
    Ok(())
}
fn f32_json(v: f32) -> Value {
    json!({"value":if v.is_finite() { Some(v) } else { None },"bits":format!("{:08x}",v.to_bits())})
}
fn f64_json(v: f64) -> Value {
    json!({"value":if v.is_finite() { Some(v) } else { None },"bits":format!("{:016x}",v.to_bits())})
}
fn params_json(p: SimilarityParams) -> Value {
    json!({"ax":f64_json(p.ax),"ay":f64_json(p.ay),"g":f64_json(p.g),"rot":f64_json(p.rot)})
}
fn census_json(c: TileCensus) -> Value {
    json!({"low_contrast":c.low_contrast,"low_peak":c.low_peak,"border":c.border,"oob":c.oob,"outlier":c.outlier})
}
fn result_json(r: &std::result::Result<StageFit, AlignFailure>) -> Value {
    match r {
        Ok(f) => json!({"state":"fit","fit":params_json(f.fit),"used":f.used,"total":f.total,
            "raw_n":f.raw_n,"rms":f32_json(f.rms),"lever_rms":f32_json(f.lever_rms),
            "peak_mean":f32_json(f.peak_mean),"rejected":census_json(f.rejected)}),
        Err(e) => json!({"state":"refused","reason":format!("{e:?}")}),
    }
}
fn config_json(c: &AlignConfig) -> Value {
    json!({"coarse_factors":c.coarse_factors,"coarse_tile":c.coarse_tile,
        "coarse_grid":c.coarse_grid,"coarse_radius":c.coarse_radius,
        "fine_tile":c.fine_tile,"fine_grid":c.fine_grid,"fine_radius":c.fine_radius,
        "margin":c.margin,"min_contrast":f32_json(c.min_contrast),"min_peak":f32_json(c.min_peak),
        "min_tiles":c.min_tiles,"outlier_mads":f32_json(c.outlier_mads),
        "fine_iters":c.fine_iters,"warp_tiles":c.warp_tiles,"peak_refinement":format!("{:?}",c.peak_refinement)})
}
fn core_json(t: &PairTrace) -> Value {
    let passes: Vec<Value> = t.fine_passes.iter().map(|p| {
        let m = &p.stage.measurements;
        let tiles: Vec<Value> = m.tiles.iter().map(|r| {
            let obs = r.observation.map(|o| json!({"ux":f32_json(o.ux),"uy":f32_json(o.uy),
                "dx":f32_json(o.dx),"dy":f32_json(o.dy)}));
            json!({"ordinal":r.ordinal,"origin":[r.probe.tx,r.probe.ty],"size":r.probe.size,
                "radius":r.probe.radius,"predicted":[f32_json(r.probe.predicted.0),f32_json(r.probe.predicted.1)],
                "fit_center":[f64_json(r.fit_center.0),f64_json(r.fit_center.1)],
                "centered_offset":[f64_json(r.centered_offset.0),f64_json(r.centered_offset.1)],
                "status":format!("{:?}",r.measurement.status),"contrast":f32_json(r.measurement.contrast),
                "dx":f32_json(r.measurement.dx),"dy":f32_json(r.measurement.dy),"peak":f32_json(r.measurement.peak),
                "observation_index":r.observation_index,"observation":obs})
        }).collect();
        let initial_residuals = m.initial_residuals.as_ref().map(|a| a.iter().map(|&v| f32_json(v)).collect::<Vec<_>>());
        let final_residuals = m.final_residuals.as_ref().map(|a| a.iter().map(|&v| f32_json(v)).collect::<Vec<_>>());
        let mut v = json!({"index":p.index,"corner_moved":p.corner_moved.map(f64_json),
            "result":result_json(&p.stage.result),"reference_dimensions":m.reference_dimensions,
            "moving_dimensions":m.moving_dimensions,"plane_center":[f64_json(m.plane_center.0),f64_json(m.plane_center.1)],
            "tile":m.tile,"radius":m.radius,"seed":m.seed.map(params_json),"config":config_json(&m.config),
            "warped_tiles_used":m.warped_tiles_used,"tiles":tiles});
        v.as_object_mut().unwrap().extend(json!({"initial_fit":m.initial_fit.map(params_json),
            "initial_residuals":initial_residuals,"median":m.median.map(f32_json),"mad":m.mad.map(f32_json),
            "cutoff":m.cutoff.map(f32_json),"keep":m.keep,"final_fit":m.final_fit.map(params_json),
            "final_residuals":final_residuals,"census":census_json(m.census)}).as_object().unwrap().clone());
        v
    }).collect();
    json!({"fine_passes":passes,"selected_fine_pass":t.selected_fine_pass,
        "termination":format!("{:?}",t.termination),"result":result_json(&t.result)})
}
fn pair_json(t: &PairMeasurementTrace) -> Value {
    json!({"ordinal":t.ordinal,"i":t.i,"j":t.j,"unavailable":t.unavailable,"core":t.core.as_ref().map(core_json)})
}
fn trace_bytes(t: &PairMeasurementTrace) -> usize {
    let mut n = size_of::<PairMeasurementTrace>();
    if let Some(t) = &t.core {
        n += t.fine_passes.capacity() * size_of::<strehl_core::align::FinePassTrace>();
        for p in &t.fine_passes {
            let m = &p.stage.measurements;
            n += m.tiles.capacity() * size_of::<strehl_core::align::TileTrace>();
            n += m.config.coarse_factors.capacity() * size_of::<usize>();
            n += m
                .initial_residuals
                .as_ref()
                .map_or(0, |v| v.capacity() * size_of::<f32>());
            n += m
                .final_residuals
                .as_ref()
                .map_or(0, |v| v.capacity() * size_of::<f32>());
            n += m
                .keep
                .as_ref()
                .map_or(0, |v| v.capacity() * size_of::<bool>());
        }
    }
    n
}
fn warp_json(w: &FrameWarp) -> Value {
    match w {
        FrameWarp::Placed(t) => {
            json!({"state":"placed","a_re":f64_json(t.a.re),"a_im":f64_json(t.a.im),
            "b_re":f64_json(t.b.re),"b_im":f64_json(t.b.im)})
        }
        FrameWarp::Refused(s) => json!({"state":"refused","reason":s}),
    }
}

#[test]
#[ignore = "root-scheduled complete299 alignment observer; reads original corpus"]
fn observe_complete_weevil_alignment() -> Result<()> {
    let started = Instant::now();
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_INSECT_PLACEMENT_CONFIG")
            .context("strict config path required")?,
    );
    let config_bytes = std::fs::read(&config_path)?;
    let config: Config = serde_json::from_slice(&config_bytes)?;
    ensure!(
        config.schema == 1 && config.expected_test_executable_sha256.len() == 64,
        "config schema"
    );
    let config_before = file_ref(&config_path)?;
    let exe = std::env::current_exe()?;
    ensure!(
        sha(&exe)? == config.expected_test_executable_sha256,
        "executable binding"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    let campaign = repo.join("outputs/raw-quality-2026-10-26");
    ensure!(
        config.out_dir.is_absolute()
            && !config.out_dir.exists()
            && config
                .out_dir
                .parent()
                .context("output parent")?
                .canonicalize()?
                .starts_with(repo.join("outputs").canonicalize()?),
        "fresh workspace output required"
    );
    let map_path = config.out_dir.join("alignment.txt");
    ensure!(
        std::env::var_os("STREHL_WARPMAP").map(PathBuf::from) == Some(map_path.clone()),
        "isolated STREHL_WARPMAP required"
    );
    ensure!(
        std::env::var_os("STREHL_SMOOTH").is_none()
            && std::env::var_os("STREHL_SMOOTH_HUBER").is_none(),
        "held ordinary solve defaults required"
    );
    let order_path = campaign.join("weevil-107-baseline/input-order.json");
    let held_path = campaign.join("weevil-107-ca-off-alignment.txt");
    ensure!(
        sha(&order_path)? == ORDER_SHA && sha(&held_path)? == MAP_SHA,
        "held input/map identities"
    );
    let sources: Vec<Source> = serde_json::from_slice(&std::fs::read(&order_path)?)?;
    ensure!(
        sources.len() == 299
            && sources.iter().enumerate().all(|(i, s)| s.index == i)
            && sources[149].sha256 == SOURCE149_SHA,
        "exact299 source order"
    );
    let paths: Vec<PathBuf> = sources.iter().map(|s| s.path.clone()).collect();
    ensure!(
        paths.windows(2).all(|p| p[0] < p[1])
            && paths.iter().all(|p| p.parent() == paths[0].parent()),
        "unique ordered corpus paths"
    );
    let originals_before = sources
        .iter()
        .map(source_identity)
        .collect::<Result<Vec<_>>>()?;
    let identity = StackIdentity::from_paths("107MSDCF", &paths)?;
    let held = WarpMap::load(&held_path)?;
    held.check_stack(&identity)?;
    ensure!(
        held.len() == 299
            && held.provenance().reference == 149
            && held.provenance().strategy == NORMAL_ALIGNMENT_STRATEGY
            && held.provenance().note == format!("strehl align, M86b, spans {DEFAULT_SPANS:?}")
            && held.resampler() == Resampler::CatmullRom,
        "held provenance/config"
    );
    std::fs::create_dir(&config.out_dir)?;
    write_json(
        &config.out_dir.join("inputs-before.json"),
        &json!({"sources":originals_before,"config":config_before,"order":file_ref(&order_path)?,"held_map":file_ref(&held_path)?}),
    )?;
    let decode_started = Instant::now();
    let st = decode_stack(&paths, 4)?;
    let decode_seconds = decode_started.elapsed().as_secs_f64();
    ensure!(
        st.geom == held.geometry() && st.geom.width == 3516 && st.geom.height == 2344,
        "held guide geometry"
    );
    let guides_before: Vec<String> = st.planes.iter().map(|p| guide_hash(p)).collect();
    write_json(
        &config.out_dir.join("guides-before.json"),
        &json!({"geometry":[st.geom.width,st.geom.height],"sha256":guides_before}),
    )?;
    let cfg = AlignConfig::deep();
    let mut pairs = Vec::new();
    for &span in &DEFAULT_SPANS {
        for i in 0..299usize.saturating_sub(span) {
            pairs.push((i, i + span));
        }
    }
    pairs.sort_unstable();
    pairs.dedup();
    ensure!(pairs.len() == 2340, "complete requested pair population");
    // Allocation guard is checked before retaining each record; overflow never
    // produces a successful truncated trace. No serialization runs in NCC.
    let collected = Mutex::new((Vec::with_capacity(pairs.len()), 0usize, false));
    let collect = |t: PairMeasurementTrace| {
        let mut state = collected.lock().expect("trace collector poisoned");
        let bytes = trace_bytes(&t);
        if state.1.saturating_add(bytes) > TRACE_LIMIT || state.0.len() >= pairs.len() {
            state.2 = true;
        } else {
            state.1 += bytes;
            state.0.push(t);
        }
    };
    let measure_started = Instant::now();
    let edges = measure_edges_traced(&st, &pairs, &cfg, 4, None, Some(&collect))?;
    let measurement_seconds = measure_started.elapsed().as_secs_f64();
    let (mut records, retained_trace_bytes, trace_overflow) = collected
        .into_inner()
        .map_err(|_| anyhow::anyhow!("trace collector poisoned"))?;
    ensure!(
        !trace_overflow && records.len() == pairs.len(),
        "trace capacity/population incomplete"
    );
    records.sort_unstable_by_key(|r| r.ordinal);
    ensure!(
        records.iter().enumerate().all(|(k, r)| r.ordinal == k
            && (r.i, r.j) == pairs[k]
            && (r.unavailable.is_some() ^ r.core.is_some())),
        "pair trace canonical identity/completeness"
    );
    let parity_started = Instant::now();
    let spots = tile_grid(
        PlaneRef::from_geometry(&st.planes[0], st.geom).context("guide view")?,
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .context("fine grid")?;
    let mut parity = Vec::new();
    for &(i, j) in &PARITY_PAIRS {
        let a = PlaneRef::from_geometry(&st.planes[i], st.geom).context("parity reference")?;
        let b = PlaneRef::from_geometry(&st.planes[j], st.geom).context("parity moving")?;
        let ap = AlignPyramid::build(a, &cfg).context("parity reference pyramid")?;
        let bp = AlignPyramid::build(b, &cfg).context("parity moving pyramid")?;
        let ordinary = align_pair(
            AlignFrame {
                plane: a,
                pyramid: &ap,
            },
            AlignFrame {
                plane: b,
                pyramid: &bp,
            },
            &spots,
            &cfg,
        );
        let traced = records
            .iter()
            .find(|r| r.i == i && r.j == j)
            .and_then(|r| r.core.as_ref())
            .context("parity observed result")?;
        let off = result_json(&ordinary);
        let on = result_json(&traced.result);
        parity.push(json!({"i":i,"j":j,"ordinary":off,"observed":on,"exact":off == on}));
    }
    let parity_seconds = parity_started.elapsed().as_secs_f64();
    let parity_exact = parity.iter().all(|v| v["exact"] == true);
    write_json(
        &config.out_dir.join("real-pair-parity.json"),
        &json!({"checks":parity,"exact":parity_exact,"additional_pair_fits":4,"additional_RAW_decodes":0}),
    )?;
    let solve_started = Instant::now();
    let map = finish_measured_map(
        identity,
        st.geom,
        299,
        149,
        &DEFAULT_SPANS,
        Resampler::CatmullRom,
        &edges,
        None,
    )?;
    let solve_seconds = solve_started.elapsed().as_secs_f64();
    save_atomic(&map, &map_path)?;
    let comparisons: Vec<Value> = map
        .warps()
        .iter()
        .zip(held.warps())
        .enumerate()
        .map(|(i, (a, b))| {
            let a = warp_json(a);
            let b = warp_json(b);
            json!({"index":i,"observed":a,"historical":b,"exact":a == b})
        })
        .collect();
    let historical_exact = comparisons.iter().all(|v| v["exact"] == true);
    write_json(
        &config.out_dir.join("historical-map-comparison.json"),
        &json!({"interpretation":"historical consistency, not physical placement truth",
        "placements_exact":historical_exact,"placements":comparisons,
        "heldout_observed":map.provenance().heldout_px.map(f64_json),"heldout_historical":held.provenance().heldout_px.map(f64_json),
        "cycle_observed":map.provenance().cycle_floor_px.map(f64_json),"cycle_historical":held.provenance().cycle_floor_px.map(f64_json)}),
    )?;
    let jsonl_path = config.out_dir.join("pairs.jsonl");
    let mut writer = BufWriter::new(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&jsonl_path)?,
    );
    let mut jsonl_bytes = 0usize;
    let mut fine_pass_count = 0usize;
    let mut tile_count = 0usize;
    for r in &records {
        if let Some(c) = &r.core {
            fine_pass_count += c.fine_passes.len();
            tile_count += c
                .fine_passes
                .iter()
                .map(|p| p.stage.measurements.tiles.len())
                .sum::<usize>();
        }
        let line = serde_json::to_vec(&pair_json(r))?;
        jsonl_bytes = jsonl_bytes
            .checked_add(line.len() + 1)
            .context("JSONL size overflow")?;
        ensure!(jsonl_bytes <= JSONL_LIMIT, "JSONL export bound");
        writer.write_all(&line)?;
        writer.write_all(b"\n")?;
    }
    writer.flush()?;
    drop(writer);
    ensure!(
        std::fs::metadata(&jsonl_path)?.len() == jsonl_bytes as u64,
        "JSONL complete bytes"
    );
    let guides_after: Vec<String> = st.planes.iter().map(|p| guide_hash(p)).collect();
    let originals_after = sources
        .iter()
        .map(source_identity)
        .collect::<Result<Vec<_>>>()?;
    let preservation = guides_before == guides_after
        && originals_before == originals_after
        && file_ref(&config_path)? == config_before
        && sha(&order_path)? == ORDER_SHA
        && sha(&held_path)? == MAP_SHA
        && sha(&exe)? == config.expected_test_executable_sha256;
    write_json(
        &config.out_dir.join("inputs-after.json"),
        &json!({"sources":originals_after,"guide_sha256":guides_after,"unchanged":preservation}),
    )?;
    let artifacts = [
        "inputs-before.json",
        "guides-before.json",
        "real-pair-parity.json",
        "alignment.txt",
        "historical-map-comparison.json",
        "pairs.jsonl",
        "inputs-after.json",
    ]
    .iter()
    .map(|s| file_ref(&config.out_dir.join(s)))
    .collect::<Result<Vec<_>>>()?;
    let mut receipt = json!({"schema":1,"status":"COMPLETE299_INSECT_PLACEMENT_OBSERVATION",
        "mechanical_pass":parity_exact && preservation,"admission":false,"quality_claim":false,"photographic_admission":false,
        "source_count":299,"RAW_decode_count":299,"reference":149,"workers":4,"pair_count":pairs.len(),
        "measured_edges":edges.len(),"refused_pairs":pairs.len()-edges.len(),"fine_pass_count":fine_pass_count,
        "fine_tile_count":tile_count,"retained_trace_bytes":retained_trace_bytes,"trace_byte_limit":TRACE_LIMIT,
        "jsonl_bytes":jsonl_bytes,"jsonl_byte_limit":JSONL_LIMIT,"all_pairs_retained":true});
    receipt.as_object_mut().unwrap().extend(json!({"config":config_before,"executable":file_ref(&exe)?,
        "artifacts":artifacts,"input_preservation":preservation,"guides_unchanged":guides_before == guides_after,
        "real_pair_on_off_exact":parity_exact,"additional_unobserved_pair_fits":4,"historical_map_placements_exact":historical_exact,
        "placed":map.placed_count(),"refused_frames":map.refused_count(),"spans":DEFAULT_SPANS,"align_config":config_json(&cfg),
        "solve":{"strategy":NORMAL_ALIGNMENT_STRATEGY,"weighting":"Unit","smooth":f64_json(DEFAULT_SMOOTH_LAMBDA),"smooth_huber_px":f64_json(DEFAULT_SMOOTH_HUBER_PX)},
        "guide_geometry":[st.geom.width,st.geom.height],"active_native_extent":[2*st.geom.width,2*st.geom.height],
        "guide":"mean of individually clamped black-subtracted G1 and G2; no optical/noise profile used by alignment",
        "coordinate_contract":"guide centroid (2u+0.5,2v+0.5) active-native; displacement times2; fit center tx+tile/2; pair i to j, not anchor149",
        "decode_seconds":decode_seconds,"measurement_seconds":measurement_seconds,"parity_seconds":parity_seconds,"solve_seconds":solve_seconds,
        "elapsed_seconds":started.elapsed().as_secs_f64(),"physical_placement_claim":false}).as_object().unwrap().clone());
    write_json(&config.out_dir.join("receipt.json"), &receipt)?;
    ensure!(
        parity_exact && preservation,
        "observer parity or input preservation failed"
    );
    Ok(())
}

mod independent_controls {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-27/insect-placement-observer/controls.rs"
    ));
}
