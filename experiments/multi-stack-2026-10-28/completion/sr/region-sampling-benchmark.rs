//! Actual cached-original preparation timing. No RAW decode or photographic gain claim.
use anyhow::{Context,Result,ensure};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{path::Path,io::Write,sync::atomic::{AtomicUsize,Ordering},time::Instant};
use strehl_cli::{session_cache::{CachedSource,SourceCache},session_input::{ResolvedSession,SourceIdentity},
    session_sampling::{NativeSampler,SampledCfa,SamplingDomain,sampling_bytes},
    session_reconstruction_sampling::RegionSampler};
use strehl_core::{plane::{PlaneGeometry,QuadSource},align::{Cx,Similarity,Resampler}};
struct Count<'a>{source:&'a CachedSource,rows:AtomicUsize}
impl QuadSource for Count<'_> {
    fn geometry(&self)->PlaneGeometry {self.source.geometry()}
    fn quad_rows(&self,y:usize)->(&[u16],&[u16]) {self.rows.fetch_add(1,Ordering::Relaxed);self.source.quad_rows(y)}
}
fn digest(s:&SampledCfa)->String {
    let mut h=Sha256::new();for p in &s.planes {for &v in p {h.update(v.to_bits().to_le_bytes());}}
    for m in [&s.coverage,&s.clipped,&s.support] {for &v in m {h.update([u8::from(v)]);}}
    h.finalize().iter().map(|v|format!("{v:02x}")).collect()
}
fn main()->Result<()> {
    let args:Vec<_>=std::env::args().collect();ensure!(args.len()==4,"RENDER CACHE OUT_JSON");
    let render=Path::new(&args[1]);let cache=Path::new(&args[2]);let out=Path::new(&args[3]);
    let session:ResolvedSession=serde_json::from_slice(&std::fs::read(render.join("session.json"))?)?;
    let ids:Vec<SourceIdentity>=serde_json::from_slice(&std::fs::read(render.join("source-identities.json"))?)?;
    let mut cache=SourceCache::new(cache,&session,256<<20)?;
    let original=cache.load(&ids[0])?.context("cached original missing; decoder is unavailable in this harness")?;
    let count=Count {source:&original,rows:AtomicUsize::new(0)};
    let full=original.geometry();let domain=SamplingDomain {full,x:full.width/3,y:full.height/3,width:80,height:48};
    let cases=[Similarity::IDENTITY,Similarity {a:Cx::new(1.,0.),b:Cx::new(0.37,-0.29)},
        Similarity {a:Cx::new(1.0023,0.0007),b:Cx::new(-1.7,0.83)}];
    let pool=rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let reports=pool.install(||->Result<Vec<serde_json::Value>> {
        let mut result=Vec::new();
        for pull in cases {
            let mut native=NativeSampler::new(domain)?;let mut local=RegionSampler::new(domain,8<<20)?;
            count.rows.store(0,Ordering::Relaxed);
            let expected=digest(native.gather(&count,original.levels(),pull,None,Resampler::CatmullRom)?);
            let native_rows=count.rows.swap(0,Ordering::Relaxed);
            let actual=digest(local.gather(&count,original.levels(),pull,None,Resampler::CatmullRom)?);
            let local_rows=count.rows.swap(0,Ordering::Relaxed);ensure!(actual==expected,"region values or masks differ");
            let mut timing=Vec::new();let iterations=8;
            for arm in ["native","region","region","native"] {
                let start=Instant::now();
                for _ in 0..iterations {
                    let value=if arm=="native" {native.gather(std::hint::black_box(&count),original.levels(),pull,None,Resampler::CatmullRom)?}
                        else {local.gather(std::hint::black_box(&count),original.levels(),pull,None,Resampler::CatmullRom)?};
                    std::hint::black_box(value);
                }
                timing.push(json!({"arm":arm,"iterations":iterations,"seconds":start.elapsed().as_secs_f64()}));
            }
            result.push(json!({"pull_bits":[pull.a.re.to_bits(),pull.a.im.to_bits(),pull.b.re.to_bits(),pull.b.im.to_bits()],
                "all_planes_and_masks_sha256":actual,"equal_bits":true,"native_source_rows":native_rows,
                "region_source_rows":local_rows,"native_buffer_reservation":sampling_bytes(domain)?,
                "region_buffer_peak_reservation":local.peak_reserved_bytes(),"abba":timing}));
        }
        Ok(result)
    })?;
    ids[0].check_unchanged()?;ensure!(cache.stats().decodes==0,"unexpected decode");
    let mut file=std::fs::OpenOptions::new().create_new(true).write(true).open(out)?;
    serde_json::to_writer_pretty(&mut file,&json!({"schema":"strehl.region-sampling-benchmark.v1","command":args,
        "original":ids[0],"full_quad_geometry":[full.width,full.height],"domain":[domain.x,domain.y,domain.width,domain.height],
        "workers":4,"raw_decodes":0,"cases":reports,"scope":"MEASURED preparation only, same original/gauge/resampler and exact values/masks. Reused workspaces, ABBA order; does not time reconstruction or establish photographic quality."}))?;
    file.write_all(b"\n")?;file.sync_all()?;Ok(())
}
