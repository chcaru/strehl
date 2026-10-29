//! Root-scheduled full-census preparation through frozen production consumers.
//! Exits after independently aligned focus evidence and exact compact guides;
//! it cannot produce a photograph or accept cross-view geometry.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs::File, io::{BufReader, BufWriter, Read, Write}, path::Path, time::Instant};
use strehl_cli::{session_align, session_cache, session_focus, session_input, session_sampling};
use strehl_cli::session_mosaic_geometry::{self as geometry, MosaicGuide, MosaicGeometryConfig};
use session_input::{ResolvedSession, SessionMode, SessionSpec};
use strehl_core::{align::Resampler, warpmap::{FrameWarp, StackIdentity, WarpMap}};
#[path = "../../../../crates/strehl-cli/src/session-mosaic-source-prefetch.rs"]
mod prefetch;

fn hash(path: &Path) -> Result<String> {
    let mut file = BufReader::new(File::open(path)?);
    let mut digest = Sha256::new();
    let mut block = [0_u8; 65536];
    loop { let n=file.read(&mut block)?; if n==0 {break;} digest.update(&block[..n]); }
    Ok(digest.finalize().iter().map(|b|format!("{b:02x}")).collect())
}
fn save(path: &Path, value: &impl serde::Serialize) -> Result<()> {
    let mut writer=BufWriter::new(File::options().write(true).create_new(true).open(path)?);
    serde_json::to_writer_pretty(&mut writer,value)?;
    writer.write_all(b"\n")?;writer.flush()?;writer.get_ref().sync_all()?;Ok(())
}
fn local_session(session: &ResolvedSession, pass: usize) -> Result<ResolvedSession> {
    let track=session.passes.get(pass).context("pass outside census")?;
    let start=track.global_range.start;let count=track.global_range.len();
    let mut local=session.clone();local.manifest_path=None;
    local.spec=SessionSpec{mode:SessionMode::Combine,passes:vec![session.spec.passes[pass].clone()],primary_pass:None,..Default::default()};
    let mut own=track.clone();own.global_range=0..count;
    own.segment_ranges=track.segment_ranges.iter().map(|r|r.start-start..r.end-start).collect();
    local.passes=vec![own];
    local.frames=session.frames[track.global_range.clone()].iter().enumerate().map(|(index,frame)|{
        let mut frame=frame.clone();frame.global_index=index;frame.pass_index=0;frame
    }).collect();Ok(local)
}
fn embed(session: &ResolvedSession,pass:usize,local:&WarpMap)->Result<WarpMap>{
    let track=&session.passes[pass];ensure!(local.len()==track.global_range.len(),"local census differs");
    let mut warps=vec![FrameWarp::Refused("outside this independently aligned mosaic pass".into());session.len()];
    warps[track.global_range.clone()].clone_from_slice(local.warps());
    let mut provenance=local.provenance().clone();provenance.reference+=track.global_range.start;
    let entries:Vec<_>=session.frames.iter().map(|f|(f.path.to_string_lossy().into_owned(),f.bytes)).collect();
    provenance.stack=StackIdentity::from_entries(&format!("mosaic pass {pass} in full census"),&entries);
    provenance.note=format!("Independent pass {pass}; global source indices; original local reference {}. {}",local.provenance().reference,provenance.note);
    Ok(WarpMap::new(provenance,local.geometry(),local.resampler(),warps))
}
fn compact(guide:&MosaicGuide,root:&Path,out:&Path)->Result<Value>{
    guide.validate()?;let pass=guide.pass;
    let directory=root.join(format!("pass-{:02}",pass+1));
    let header=json!({"schema":"strehl.cached-mosaic-guide.v1","record_bytes":46,"receipt":guide.receipt,
        "source_identities_sha256":hash(&root.join("source-identities.json"))?,
        "alignment_envelope_sha256":hash(&directory.join("alignment.json"))?,
        "focus_receipt_sha256":hash(&directory.join("focus/geometry.json"))?});
    let bytes=serde_json::to_vec(&header)?;let path=out.join(format!("guide-{pass}.bin"));
    let mut writer=BufWriter::new(File::options().write(true).create_new(true).open(&path)?);
    writer.write_all(b"STRHGUI1")?;writer.write_all(&u32::try_from(bytes.len())?.to_le_bytes())?;writer.write_all(&bytes)?;
    let mut digest=Sha256::new();
    // This harness always consumes SamplingDomain::full: its domain origin is
    // zero; the guide center origin includes the box-centering offset.
    for v in [pass,guide.geometry.width,guide.geometry.height,guide.step,0,0]{digest.update((v as u64).to_le_bytes());}
    for i in 0..guide.geometry.pixels(){
        let mut pixel=[0_u8;46];pixel[..4].copy_from_slice(&guide.intensity[i].to_le_bytes());
        pixel[4]=u8::from(guide.covered[i]);pixel[5]=u8::from(guide.usable_focus[i]);
        for (j,id) in guide.source_indices[i].iter().enumerate(){pixel[6+8*j..14+8*j].copy_from_slice(&(*id as u64).to_le_bytes());}
        pixel[38..42].copy_from_slice(&guide.focus_ordinal[i].to_le_bytes());pixel[42..].copy_from_slice(&guide.focus_width[i].to_le_bytes());
        digest.update(&pixel[..38]);writer.write_all(&pixel)?;
    }
    let actual:String=digest.finalize().iter().map(|b|format!("{b:02x}")).collect();ensure!(actual==guide.receipt.guide_sha256,"compact pixels differ from production guide");
    writer.flush()?;writer.get_ref().sync_all()?;
    Ok(json!({"pass_index":pass,"covered":guide.receipt.covered_pixels,"usable":guide.receipt.usable_focus_pixels,
        "guide_sha256":actual,"compact_guide_sha256":hash(&path)?,"scope":"Exact direct serialization of production diagnostic guide; not a photograph"}))
}
fn main()->Result<()>{
    let args:Vec<_>=std::env::args().skip(1).collect();
    ensure!(args.len()==5,"prepare-geometry MANIFEST CACHE FRESH_OUTPUT WORKERS MEMORY_GIB");
    let workers:usize=args[3].parse()?;let gib:usize=args[4].parse()?;
    ensure!((1..=8).contains(&workers)&&gib<=16,"research release caps8workers16GiB");
    let budget=gib.checked_mul(1<<30).context("budget overflow")?;ensure!(budget>=4<<30,"minimum4GiB");
    let session=ResolvedSession::load(Path::new(&args[0]))?;
    ensure!(session.spec.mode==SessionMode::Mosaic&&session.primary_pass_index().is_none(),"explicit mosaic with no primary required");
    let out=session.ensure_output_outside_sources(Path::new(&args[2]))?;
    std::fs::create_dir(&out)?;save(&out.join("session.json"),&session)?;
    let started=Instant::now();let ids=session.hash_sources(true)?;save(&out.join("source-identities.json"),&ids)?;
    let metadata=session.read_metadata()?;
    for pass in &session.passes {let lead=&metadata[pass.global_range.start];for index in pass.global_range.clone(){let item=&metadata[index];
        ensure!(item.camera_model==lead.camera_model&&item.camera_make==lead.camera_make&&item.lens_type3==lead.lens_type3&&item.iso==lead.iso&&item.aperture==lead.aperture&&item.exposure_time==lead.exposure_time,"within-pass capture metadata changes");
    }}
    let cache_path=Path::new(&args[1]);
    let prepared=prefetch::prepare(&session,&ids,&metadata,cache_path,budget,workers)?;
    save(&out.join("source-prefetch.json"),&prepared)?;
    let mut cache=session_cache::SourceCache::new(cache_path,&session,budget/8)?;
    let config=session_align::SessionAlignConfig{memory_limit_bytes:budget,workers,..Default::default()};
    let geometry_config=MosaicGeometryConfig::default();
    save(&out.join("preparation-config.json"),&json!({"alignment":config,"geometry":geometry_config,"workers":workers,"memory_limit_bytes":budget,"cache_budget_bytes":cache.budget_bytes(),"semantics":"Full-census geometry preparation only; no cross-view acceptance or photograph"}))?;
    let compact_root=out.join("compact-guides");std::fs::create_dir(&compact_root)?;
    let pool=rayon::ThreadPoolBuilder::new().num_threads(workers).build()?;
    let reports=pool.install(||->Result<Vec<Value>>{
        let mut reports=Vec::new();let mut geometry=None;
        for pass in 0..session.passes.len(){
            let track=&session.passes[pass];eprintln!("prepare: independently aligning pass{} ({} originals)",pass+1,track.global_range.len());
            let local=local_session(&session,pass)?;
            let aligned=session_align::align_session(&local,&ids[track.global_range.clone()],&mut cache,&config,Resampler::Bilinear)?;
            let directory=out.join(format!("pass-{:02}",pass+1));std::fs::create_dir(&directory)?;
            aligned.save(&directory.join("alignment.json"),&local)?;
            let map=embed(&session,pass,&aligned.map)?;
            ensure!(geometry.is_none_or(|g|g==map.geometry()),"source geometries differ");geometry=Some(map.geometry());
            let domain=session_sampling::SamplingDomain::full(map.geometry());
            let overhead=cache.budget_bytes().checked_add(512<<20).and_then(|v|v.checked_add(map.geometry().pixels().checked_mul(32)?)).context("overhead overflow")?;
            let available=budget.checked_sub(overhead).context("no focus working memory")?;
            let lead=track.global_range.start;let source=cache.load_or_decode(&session.frames[lead],&ids[lead])?;
            let noise=strehl_core::profile::noise_model_for(source.camera(),source.iso(),source.levels());
            let profile=strehl_core::optics::profile_for_capture_env(metadata[lead].camera_model.as_deref(),metadata[lead].lens_type3)?;drop(source);
            eprintln!("prepare: full native focus evidence pass{}",pass+1);
            let focus=session_focus::compute_pass(&session,&ids,pass,&map,&mut cache,domain,&noise,profile,available)?;
            let focus_dir=directory.join("focus");std::fs::create_dir(&focus_dir)?;
            session_focus::save(&focus_dir,&focus,domain,pass)?;
            let guide=geometry::build_guide(&session,&ids,pass,&map,&mut cache,domain,&focus,&geometry_config,available.checked_sub(focus.reservation_bytes).context("focus plus guide exceeds budget")?)?;
            save(&focus_dir.join("guide-receipt.json"),&guide.receipt)?;geometry::save_diagnostics(&focus_dir,&guide)?;
            reports.push(compact(&guide,&out,&compact_root)?);
            drop(guide);drop(focus);
        }Ok(reports)
    })?;
    let current=session.spec.resolve_from(&session.passes[0].directories[0])?;
    ensure!(current.frames==session.frames&&current.hash_sources(true)?==ids,"source census or bytes changed during preparation");
    save(&compact_root.join("receipt.json"),&json!({"source":out,"threads":workers,"passes":reports,"direct_production_serialization":true}))?;
    let stats=cache.stats();
    save(&out.join("prepared.json"),&json!({"schema":"strehl.mosaic-preparation.v1","source_count":session.len(),"passes":session.passes.len(),"workers":workers,"memory_limit_bytes":budget,"elapsed_seconds":started.elapsed().as_secs_f64(),"cache_stats":{"decodes":stats.decodes,"disk_hits":stats.disk_hits,"peak_resident_cfa_bytes":stats.peak_resident_cfa_bytes},"focus_algorithm_sha256":session_focus::algorithm_sha256(),"source_identities_sha256":hash(&out.join("source-identities.json"))?,"compact_guides_sha256":hash(&compact_root.join("receipt.json"))?,"claim":"Independent native focus/guide preparation only. No accepted mosaic geometry or output photograph."}))?;
    Ok(())
}
