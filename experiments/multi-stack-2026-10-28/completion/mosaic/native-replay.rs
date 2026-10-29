//! Cached-only observer of exactly the pilot's existing descriptor candidates.
//! It never calls load_or_decode and never publishes a geometry certificate.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{
    fs::File,
    io::{BufReader, BufWriter},
    path::{Path, PathBuf},
};
use strehl_cli::{
    session_cache::SourceCache,
    session_input::{ResolvedSession, SourceIdentity},
    session_mosaic_geometry::{MosaicGeometryConfig, NativeCorrespondence, PairDiscovery},
};
use strehl_core::{
    align::{AlignConfig, Cx, PairTrace, PlaneRef, Similarity, refine_pair_observed},
    plane::{PlaneGeometry, QuadSource, green_luma},
    warpmap::WarpMap,
};
fn read<T: serde::de::DeserializeOwned>(p: &Path) -> Result<T> {
    Ok(serde_json::from_reader(BufReader::new(File::open(p)?))?)
}
fn point(t: Similarity, p: [f64; 2], g: PlaneGeometry) -> [f64; 2] {
    let q = t.apply_at(p[0], p[1], g.width as f64 * 0.5, g.height as f64 * 0.5);
    [q.0, q.1]
}
fn seed(a: Cx, p: [f64; 2], q: [f64; 2], g: PlaneGeometry) -> Similarity {
    let c = Cx::new(g.width as f64 * 0.5, g.height as f64 * 0.5);
    Similarity {
        a,
        b: Cx::new(q[0], q[1]) - c - a * (Cx::new(p[0], p[1]) - c),
    }
}
fn spots(p: [f64; 2], g: PlaneGeometry, tile: usize, radius: i32) -> Result<Vec<(usize, usize)>> {
    let half = tile as f64 * 0.5;
    let mut out = Vec::new();
    for dy in [-half, 0., half] {
        for dx in [-half, 0., half] {
            let x = (p[0] + dx - half).round();
            let y = (p[1] + dy - half).round();
            ensure!(
                x >= f64::from(radius) + 2.
                    && y >= f64::from(radius) + 2.
                    && x + tile as f64 + f64::from(radius) + 2. < g.width as f64
                    && y + tile as f64 + f64::from(radius) + 2. < g.height as f64,
                "patch outside"
            );
            out.push((x as usize, y as usize));
        }
    }
    Ok(out)
}
fn observed(trace: &PairTrace) -> Value {
    json!({"selected_fine_pass":trace.selected_fine_pass,"termination":format!("{:?}",trace.termination),"result":format!("{:?}",trace.result),"passes":trace.fine_passes.iter().map(|p|{
        let s=&p.stage.measurements;
        json!({"pass":p.index,"plane_center":s.plane_center,"seed":s.seed.map(|p|{let t=Similarity::from_params(p);[t.a.re,t.a.im,t.b.re,t.b.im]}),"initial_residuals":s.initial_residuals,"final_residuals":s.final_residuals,"kept":s.keep,"tiles":s.tiles.iter().map(|t|json!({"origin":[t.probe.tx,t.probe.ty],"size":t.probe.size,"radius":t.probe.radius,"fit_center":t.fit_center,"offset":t.centered_offset,"status":format!("{:?}",t.measurement.status),"peak":t.measurement.peak.is_finite().then_some(t.measurement.peak),"observation":t.observation.map(|o|[o.ux,o.uy,o.dx,o.dy])})).collect::<Vec<_>>()})
    }).collect::<Vec<_>>()})
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    ensure!(args.len() == 3, "native-replay PILOT CACHE OUTPUT_JSON");
    let pilot = &args[0];
    let session: ResolvedSession = read(&pilot.join("session.json"))?;
    let ids: Vec<SourceIdentity> = read(&pilot.join("source-identities.json"))?;
    let previous: Vec<NativeCorrespondence> = read(&pilot.join("mosaic-native-measurements.json"))?;
    let pairs: Vec<PairDiscovery> = read(&pilot.join("mosaic-candidates.json"))?;
    let maps: Vec<_> = (0..session.passes.len())
        .map(|p| -> Result<WarpMap> {
            let v: Value = read(&pilot.join(format!("pass-{:02}/alignment.json", p + 1)))?;
            Ok(WarpMap::from_text(
                v["warpmap"].as_str().context("missing map")?,
            )?)
        })
        .collect::<Result<_>>()?;
    let mut cache = SourceCache::new(&args[1], &session, 256 << 20)?;
    let defaults = MosaicGeometryConfig::default();
    let mut cfg = AlignConfig::shallow();
    cfg.fine_tile = defaults.native_tile;
    cfg.fine_radius = defaults.native_search_radius;
    cfg.fine_iters = 3;
    cfg.warp_tiles = true;
    cfg.min_peak = defaults.native_minimum_peak;
    cfg.min_tiles = 6;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let results=pool.install(||->Result<Vec<Value>>{
        let mut result=Vec::new();
        for receipt in previous.iter().filter(|r|!r.candidate.grid_nomination&&(r.accepted||r.refusal.as_deref()==Some("native local fit residual exceeds configured bar"))){
            let c=&receipt.candidate;let global_pair=pairs.iter().find(|p|p.pass_a==c.pass_a&&p.pass_b==c.pass_b).context("pair absent")?.seed_a_to_b.context("seed absent")?;
            let wa=maps[c.pass_a].warps()[c.source_a-session.passes[c.pass_a].global_range.start].placed().context("unplaced")?;let wb=maps[c.pass_b].warps()[c.source_b-session.passes[c.pass_b].global_range.start].placed().context("unplaced")?;
            let source_a=cache.load(&ids[c.source_a])?.context("verified existing CFA required; decoding prohibited")?;let source_b=cache.load(&ids[c.source_b])?.context("verified existing CFA required; decoding prohibited")?;
            let g=source_a.geometry();ensure!(source_b.geometry()==g,"shape differs");let mut va=vec![0.;g.pixels()];let mut vb=vec![0.;g.pixels()];green_luma(source_a.as_ref(),source_a.levels().black,&mut va);green_luma(source_b.as_ref(),source_b.levels().black,&mut vb);
            let a=PlaneRef::from_geometry(&va,g).unwrap();let b=PlaneRef::from_geometry(&vb,g).unwrap();let pa=point(wa,c.point_a_quad,g);let pb=point(wb,c.point_b_quad,g);
            let linear=wa.invert().unwrap().then(Similarity{a:Cx::new(global_pair[0],global_pair[1]),b:Cx::new(global_pair[2],global_pair[3])}).then(wb).a;
            let initial=seed(linear,pa,pb,g);let measured_pb=point(initial,pa,g);let mut forward_trace=Value::Null;let mut reverse_trace=Value::Null;
            let f=refine_pair_observed(a,b,&spots(pa,g,cfg.fine_tile,cfg.fine_radius)?,&cfg,initial,Some(&mut|t|forward_trace=observed(t)));
            let r=refine_pair_observed(b,a,&spots(measured_pb,g,cfg.fine_tile,cfg.fine_radius)?,&cfg,initial.invert().unwrap(),Some(&mut|t|reverse_trace=observed(t)));
            let reciprocity=f.as_ref().ok().zip(r.as_ref().ok()).map(|(f,r)|{let q=point(r.similarity(),point(f.similarity(),pa,g),g);(q[0]-pa[0]).hypot(q[1]-pa[1])});
            result.push(json!({"id":c.id,"sources":[c.source_a,c.source_b],"source_sha256":[ids[c.source_a].sha256,ids[c.source_b].sha256],"role":c.role,"original_receipt":receipt,"native_points":[pa,measured_pb],"forward":forward_trace,"reverse":reverse_trace,"rms":[f.as_ref().ok().map(|f|f.rms),r.as_ref().ok().map(|f|f.rms)],"reciprocal_quad":reciprocity,"semantics":"Existing production refinement call/config/coordinates; diagnostics only; original acceptance bars retained; no RAW decode or geometry publication."}));
        }Ok(result)
    })?;
    let output = File::options()
        .write(true)
        .create_new(true)
        .open(&args[2])?;
    serde_json::to_writer_pretty(
        BufWriter::new(output),
        &json!({"schema":"strehl.mosaic-native-replay.v1","workers":4,"raw_decodes":0,"measurements":results}),
    )?;
    Ok(())
}
