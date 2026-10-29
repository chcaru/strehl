//! Opt-in focus-aware mosaics. Independent focus tracks establish each view;
//! directly measured cross-view geometry establishes a bounded union canvas.
//! Original CFA is gathered once at each consuming site and demosaiced once.
use super::super::write_merged_observed_with_coverage;
use super::{Calibration, cached_alignment, calibration, check_source, rational, validate_headers};
use super::{Merged, PyramidDomain};
use crate::session_cache::SourceCache;
use crate::session_cmd::{StackArgs, reserve_output_directory, write_json_new};
use crate::session_input::{
    ResolvedSession, SessionMode, SessionSpec, SourceIdentity, SourceMetadata,
};
use crate::session_mosaic_geometry::{self as geometry, MosaicGeometry, MosaicGeometryConfig};
use crate::session_sampling::SamplingDomain;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
use std::time::Instant;
use strehl_core::CfaPlane;
use strehl_core::align::Resampler;
use strehl_core::color::Exposure;
use strehl_core::plane::PlaneGeometry;
use strehl_core::warpmap::{FrameWarp, StackIdentity, WarpMap};

use super::native_output as output;
#[path = "session-mosaic-probe.rs"]
mod probe;
#[path = "session-mosaic-source-prefetch.rs"]
mod source_prefetch;
#[path = "session-mosaic-tiles.rs"]
mod tiles;

/// Copy the already frozen census, never rescan directories between independent
/// alignment and embedding. One-pass acquisition ordinals remain ordered.
fn local_session(session: &ResolvedSession, pass: usize) -> Result<ResolvedSession> {
    let track = session
        .passes
        .get(pass)
        .context("mosaic pass outside session")?;
    let start = track.global_range.start;
    let count = track.global_range.len();
    let mut local = session.clone();
    local.manifest_path = None;
    local.spec = SessionSpec {
        mode: SessionMode::Combine,
        passes: vec![session.spec.passes[pass].clone()],
        primary_pass: None,
        ..SessionSpec::default()
    };
    let mut own = track.clone();
    own.global_range = 0..count;
    own.segment_ranges = track
        .segment_ranges
        .iter()
        .map(|r| r.start - start..r.end - start)
        .collect();
    local.passes = vec![own];
    local.frames = session.frames[track.global_range.clone()]
        .iter()
        .enumerate()
        .map(|(index, frame)| {
            let mut frame = frame.clone();
            frame.global_index = index;
            frame.pass_index = 0;
            frame
        })
        .collect();
    Ok(local)
}
fn embed(session: &ResolvedSession, pass: usize, local: &WarpMap) -> Result<WarpMap> {
    let track = &session.passes[pass];
    ensure!(
        local.len() == track.global_range.len(),
        "local alignment census differs"
    );
    let mut warps = vec![
        FrameWarp::Refused("outside this independently aligned mosaic pass".into());
        session.len()
    ];
    warps[track.global_range.clone()].clone_from_slice(local.warps());
    let mut provenance = local.provenance().clone();
    provenance.reference += track.global_range.start;
    let entries: Vec<_> = session
        .frames
        .iter()
        .map(|f| (f.path.to_string_lossy().into_owned(), f.bytes))
        .collect();
    provenance.stack =
        StackIdentity::from_entries(&format!("mosaic pass {pass} in full census"), &entries);
    provenance.note = format!(
        "Independent pass {pass}; global source indices; original local reference {}. {}",
        local.provenance().reference,
        provenance.note
    );
    Ok(WarpMap::new(
        provenance,
        local.geometry(),
        local.resampler(),
        warps,
    ))
}
fn renderer_hash() -> String {
    let mut h = Sha256::new();
    h.update(super::renderer_source_hash());
    for source in [
        include_bytes!("session-mosaic-consumer.rs").as_slice(),
        include_bytes!("session-mosaic-tiles.rs").as_slice(),
        include_bytes!("session-mosaic-probe.rs").as_slice(),
        include_bytes!("session-mosaic-output.rs").as_slice(),
        include_bytes!("session-mosaic-source-prefetch.rs").as_slice(),
        include_bytes!("session-mapped-sampling.rs").as_slice(),
        include_bytes!("session-mosaic-geometry.rs").as_slice(),
        include_bytes!("../../strehl-core/src/mosaic.rs").as_slice(),
    ] {
        h.update((source.len() as u64).to_le_bytes());
        h.update(source);
    }
    crate::session_input::hex(&h.finalize())
}
fn headers(session: &ResolvedSession, metadata: &[SourceMetadata]) -> Result<()> {
    // Reuse the strict sensor/lens/ISO/aperture/within-pass policy, permitting
    // shutter changes only. This does not label the mosaic an HDR reconstruction.
    let mut check = session.clone();
    check.spec.mode = SessionMode::Hdr;
    validate_headers(&check, metadata)?;
    for pass in &session.passes {
        rational(
            metadata[pass.global_range.start].exposure_time,
            "mosaic shutter",
        )?;
    }
    Ok(())
}

pub(crate) fn run(args: &StackArgs) -> Result<()> {
    args.merge_config()?;
    ensure!(
        !args.binned,
        "mosaics retain full-resolution masters; omit --binned"
    );
    ensure!(
        args.only_pass.is_none(),
        "mosaic rendering cannot select one pass; use aligned layers"
    );
    ensure!(
        !args.precision_weights && !args.contribution_maps,
        "mosaic uses per-view focus reconstruction; repeat precision/contribution options do not apply"
    );
    let session = SessionSpec::load(&args.manifest)?.resolve(&args.manifest)?;
    ensure!(
        session.passes.len() >= 2,
        "a mosaic requires at least two spatial views"
    );
    ensure!(
        session.primary_pass_index().is_none(),
        "stitching has no primary pass preference"
    );
    let metadata = session.read_metadata()?;
    headers(&session, &metadata)?;
    let destination = reserve_output_directory(&session, &args.out_dir)?;
    write_json_new(&destination.join("session.json"), &session)?;
    let started = Instant::now();
    let progress = crate::ui_progress::Progress::new(session.len());
    progress.stage("read");
    eprintln!(
        "mosaic: hashing {} original RAW acquisitions in {} views",
        session.len(),
        session.passes.len()
    );
    let identities = session.hash_sources(true)?;
    write_json_new(&destination.join("source-identities.json"), &identities)?;
    let config = args.resources.config()?;
    let cache_path = args
        .resources
        .cache
        .clone()
        .unwrap_or_else(|| destination.join("source-cache"));
    let resampler = crate::align_cmd::parse_resampler(&args.resources.resampler)?;
    ensure!(
        resampler != Resampler::ClampedCatmullRom,
        "mosaic noise propagation requires a linear resampler"
    );
    // Complete the bounded decode/publication phase before the main cache,
    // alignment guides or output buffers exist. No geometry identity changes.
    let prefetch_report = source_prefetch::prepare(
        &session,
        &identities,
        &metadata,
        &cache_path,
        config.memory_limit_bytes,
        args.resources.threads,
    )?;
    write_json_new(&destination.join("source-prefetch.json"), &prefetch_report)?;
    let mut cache = SourceCache::new(&cache_path, &session, args.resources.cache_budget()?)?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(args.resources.threads)
        .build()?;
    pool.install(||->Result<()>{
        let mut maps=Vec::new();let mut calibration_data=Vec::new();let mut pass_reports=Vec::new();
        progress.stage("alignment");
        for pass in 0..session.passes.len(){
            let local=local_session(&session,pass)?;let track=&session.passes[pass];
            eprintln!("mosaic: independently aligning view {}/{} ({}, {} acquisitions)",pass+1,session.passes.len(),track.name,track.global_range.len());
            let aligned=cached_alignment(&local,&identities[track.global_range.clone()],&mut cache,&config,resampler)?;
            let directory=destination.join(format!("pass-{:02}",pass+1));std::fs::create_dir(&directory)?;aligned.save(&directory.join("alignment.json"),&local)?;
            let map=embed(&session,pass,&aligned.map)?;
            if let Some(first)=maps.first(){let first:&WarpMap=first;ensure!(first.geometry()==map.geometry(),"mosaic source geometries differ");}
            let index=track.global_range.start;let source=cache.load_or_decode(&session.frames[index],&identities[index])?;
            let calibration=calibration(&source,&metadata[index],config.memory_limit_bytes/8)?;
            if let Some(first)=calibration_data.first(){let first:&Calibration=first;ensure!(calibration.levels==first.levels&&calibration.iso==first.iso&&calibration.camera==first.camera&&calibration.metadata.xyz_to_cam_bits==first.metadata.xyz_to_cam_bits&&calibration.metadata.color_matrices_bits==first.metadata.color_matrices_bits,"mosaic decoded sensor/color calibration differs across passes");}
            pass_reports.push(json!({"pass":pass,"name":track.name,"frames":track.global_range.len(),"placed":map.warps()[track.global_range.clone()].iter().filter(|w|w.placed().is_some()).count(),"reference_global":map.provenance().reference,"alignment":aligned.report,"shutter_seconds":calibration.shutter,"black":calibration.levels.black,"white":calibration.levels.white,"noise_model":format!("{:?}",calibration.noise)}));
            maps.push(map);calibration_data.push(calibration);
        }
        let full=maps[0].geometry();let domain=SamplingDomain::full(full);
        let overhead=cache.budget_bytes().checked_add(512<<20).and_then(|n|n.checked_add(full.pixels().checked_mul(32)?)).context("mosaic geometry overhead overflow")?;
        ensure!(overhead<config.memory_limit_bytes,"mosaic source overhead exceeds memory budget");
        // Keep every full-resolution RGB16/RGB32F product safely inside classic
        // TIFF offsets, including metadata and encoder strip tables. BigTIFF is
        // not silently assumed merely because the RAM budget is large.
        let geometry_config=MosaicGeometryConfig{max_canvas_pixels:33_000_000,..MosaicGeometryConfig::default()};let mut guides=Vec::new();let mut retained=0_usize;
        for pass in 0..session.passes.len(){
            eprintln!("mosaic: measuring focus evidence and diagnostic guide for view {}/{}",pass+1,session.passes.len());
            let available=config.memory_limit_bytes.checked_sub(overhead+retained).context("no memory for mosaic focus evidence")?;
            let cal=&calibration_data[pass];
            let focus=crate::session_focus::compute_pass(&session,&identities,pass,&maps[pass],&mut cache,domain,&cal.noise,cal.profile,available)?;
            let directory=destination.join(format!("pass-{:02}",pass+1)).join("focus");std::fs::create_dir(&directory)?;
            let focus_report=crate::session_focus::save(&directory,&focus,domain,pass)?;
            let guide_budget=available.checked_sub(focus.reservation_bytes).context("mosaic focus plus diagnostic guide exceeds memory budget")?;
            let guide=geometry::build_guide(&session,&identities,pass,&maps[pass],&mut cache,domain,&focus,&geometry_config,guide_budget)?;
            write_json_new(&directory.join("guide-receipt.json"),&guide.receipt)?;
            geometry::save_diagnostics(&directory,&guide)?;
            pass_reports[pass]["focus"]=focus_report;
            retained=retained.checked_add(guide.geometry.pixels().checked_mul(80).context("guide retention overflow")?).context("guide retention overflow")?;
            guides.push(guide);drop(focus);
        }
        let available=config.memory_limit_bytes.checked_sub(overhead+retained).context("no memory for mosaic correspondence measurements")?;
        let mosaic=if let Some(path)=&args.alignment{MosaicGeometry::load(path,&session,&identities,&guides,&geometry_config)?}else{
            eprintln!("mosaic: discovering direct view correspondences and refining original CFA measurements");
            let (pairs,source_feature_receipts)=geometry::discover_source_pairs(&session,&identities,&maps,&mut cache,&guides,&geometry_config,available)?;
            write_json_new(&destination.join("mosaic-source-features.json"),&source_feature_receipts)?;
            write_json_new(&destination.join("mosaic-candidates.json"),&pairs)?;
            let native=geometry::refine_native_correspondences(&session,&identities,&maps,&mut cache,&guides,&pairs,&geometry_config,available)?;
            write_json_new(&destination.join("mosaic-native-measurements.json"),&native)?;
            geometry::solve_geometry(&session,&identities,&guides,&pairs,&native,&geometry_config,available)?
        };
        mosaic.save(&destination.join("mosaic-geometry.json"),&session)?;
        ensure!(mosaic.report.measured_pass_edges>=session.passes.len()-1,"mosaic extended canvas lacks a measured connected view graph");
        let geometry_report=json!({"schema":"strehl.mosaic.v1","build":crate::VERSION,"renderer_source_sha256":renderer_hash(),"sources":session.len(),"passes":pass_reports,"primary_pass":null,"geometry":mosaic.report,"geometry_config":geometry_config,"resources":{"memory_limit_bytes":config.memory_limit_bytes,"workers":args.resources.threads,"cache_budget_bytes":cache.budget_bytes(),"source_prefetch":prefetch_report},"photometric_policy":"Known shutter ratio to pass-zero linear radiance units, equal ISO/aperture/sensor calibration. Per-pixel disagreement remains explicit and prevents cross-view blending; shutter metadata is not a measured general response calibration.","development_reference_pass":0,"coordinate_semantics":"Canvas origin is signed full green-quad coordinates. Physical sensor coordinate is 2*quad+0.5. Focus ordinates are acquisition order, never metric depth."});
        write_json_new(&destination.join("mosaic-report.json"),&geometry_report)?;
        drop(guides);
        // The geometry object owns sparse measurements, mesh vertices and bin
        // inputs, not image volume. Reserve its bounded serialized size twice.
        let retained=serde_json::to_vec(&geometry_report)?.len().checked_mul(2).and_then(|n|n.checked_add(session.len()*1024)).context("mosaic receipt reservation overflow")?;
        let output=tiles::render(args,&session,&identities,&maps,&mut cache,&calibration_data,&mosaic,&destination,retained)?;
        write_json_new(&destination.join("render-report.json"),&output.report)?;
        ensure!(output.valid.iter().any(|&v|v),"mosaic has no fully supported reconstructed pixels; measurements saved, photograph withheld");
        let canvas_geometry=PlaneGeometry{width:mosaic.canvas.width,height:mosaic.canvas.height};
        tiles::write_masks(&destination,canvas_geometry,&output.owner,&output.join)?;
        output::save_sensor(&destination.join("sensor-master.tiff"),canvas_geometry,&output.planes,&json!({"schema":"strehl.mosaic-cfa-master.v1","cfa":"RGGB","units":"black-subtracted native DN, normalized by nominal shutter ratio to pass zero; signed f32 values retained","canvas_origin_quad":mosaic.canvas.origin,"physical_sensor_origin":[2*mosaic.canvas.origin[0],2*mosaic.canvas.origin[1]],"black_subtracted":true,"reference_black":calibration_data[0].levels.black,"reference_white":calibration_data[0].levels.white,"coverage":"coverage.tiff","geometry":"mosaic-geometry.json","sources":"source-identities.json","renderer_source_sha256":renderer_hash()}))?;
        let [r,g1,b,g2]=output.planes;let planes=[r,g1,g2,b];let reference=&calibration_data[0];let photograph=destination.join("photograph.tiff");
        write_merged_observed_with_coverage(Merged::Bands{domain:PyramidDomain::whole(canvas_geometry),planes:&planes},reference.levels,reference.wb,reference.matrix.as_ref(),crate::image_out::OutputSpace::from_flags(true,false)?,true,Exposure::resolve(true,args.exposure,false)?,None,&photograph,Some(&progress),Some(&destination.join("master.tiff")),None,Some(&output.valid))?;
        crate::image_out::apply_mosaic_coverage(&photograph,&destination.join("coverage.tiff"),canvas_geometry,&output.valid)?;
        drop(planes);
        let coverage_sha256=output::sha256(&destination.join("coverage.tiff"))?;
        let join_confidence_sha256=output::sha256(&destination.join("join-confidence.tiff"))?;
        let view_owner_sha256=output::sha256(&destination.join("view-owner.tiff"))?;
        let photograph_sha256=output::sha256(&photograph)?;
        let master_sha256=output::sha256(&destination.join("master.tiff"))?;
        let sensor_master_sha256=output::sha256(&destination.join("sensor-master.tiff"))?;
        crate::session_reproducibility::publish_render_binding(&destination)?;
        let current=session.spec.resolve_from(&session.passes[0].directories[0])?;ensure!(current.frames==session.frames&&current.hash_sources(true)?==identities,"mosaic sources changed during rendering; completion withheld");
        let render_bindings=crate::session_reproducibility::completion_bindings(&destination)?;
        write_json_new(&destination.join("completed.json"),&json!({"schema":"strehl.session-completion.v1","mode":"mosaic","outputs":1,"frames":session.len(),"passes":session.passes.len(),"primary_pass":null,"elapsed_seconds":started.elapsed().as_secs_f64(),"render_bindings":render_bindings,"coverage":"coverage.tiff","coverage_sha256":coverage_sha256,"join_confidence":"join-confidence.tiff","join_confidence_sha256":join_confidence_sha256,"view_owner":"view-owner.tiff","view_owner_sha256":view_owner_sha256,"photograph_sha256":photograph_sha256,"master_sha256":master_sha256,"sensor_master":"sensor-master.tiff","sensor_master_sha256":sensor_master_sha256,"join_legend":{"0":"uncovered","1":"single_view","2":"qualified_compatible_blend","3":"unmerged_overlap_one_view"},"owner_legend":"Zero is uncovered; positive integers are one-based declared pass indices. Blended pixels retain the maximum-interior contributor as owner."}))?;
        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::super::same_rational;
    use super::*;
    use crate::session_input::{PassSpec, ResolvedPass, SourceFrame};
    use strehl_core::align::{Cx, Similarity};
    use strehl_core::warpmap::Provenance;
    fn session() -> ResolvedSession {
        let mut frames = Vec::new();
        for pass in 0..2 {
            for n in 0..3 {
                frames.push(SourceFrame {
                    global_index: pass * 3 + n,
                    pass_index: pass,
                    segment_index: usize::from(n == 2),
                    pass_frame_index: n,
                    segment_frame_index: if n == 2 { 0 } else { n },
                    path: format!("p{pass}/f{n}").into(),
                    bytes: 1,
                    modified_unix_nanos: None,
                });
            }
        }
        ResolvedSession {
            spec: SessionSpec {
                passes: (0..2)
                    .map(|p| PassSpec {
                        name: format!("p{p}"),
                        directories: vec![format!("p{p}/a").into(), format!("p{p}/b").into()],
                    })
                    .collect(),
                ..SessionSpec::default()
            },
            manifest_path: None,
            passes: (0..2)
                .map(|p| ResolvedPass {
                    name: format!("p{p}"),
                    directories: vec![],
                    global_range: p * 3..p * 3 + 3,
                    segment_ranges: vec![p * 3..p * 3 + 2, p * 3 + 2..p * 3 + 3],
                })
                .collect(),
            frames,
        }
    }
    #[test]
    fn independent_pass_embedding_preserves_gauge_refusals_segments_and_global_focus_ids() {
        let session = session();
        let local = local_session(&session, 1).unwrap();
        assert_eq!(
            local
                .frames
                .iter()
                .map(|f| f.global_index)
                .collect::<Vec<_>>(),
            [0, 1, 2]
        );
        assert_eq!(local.passes[0].segment_ranges, [0..2, 2..3]);
        assert!(local.frames.iter().all(|f| f.pass_index == 0));
        let t = Similarity {
            a: Cx::new(1.01, 0.002),
            b: Cx::new(12.0, -9.0),
        };
        let map = WarpMap::new(
            Provenance {
                stack: StackIdentity::from_entries("x", &[("a", 1)]),
                strategy: "test".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: 1,
                note: "gauge".into(),
            },
            PlaneGeometry {
                width: 101,
                height: 81,
            },
            Resampler::Bilinear,
            vec![
                FrameWarp::Placed(t),
                FrameWarp::Placed(strehl_core::align::Similarity::IDENTITY),
                FrameWarp::Refused("no evidence".into()),
            ],
        );
        let embedded = embed(&session, 1, &map).unwrap();
        assert_eq!(embedded.provenance().reference, 4);
        assert_eq!(embedded.warps()[3].placed(), Some(t));
        assert!(embedded.warps()[0..3].iter().all(|w| w.is_refused()));
        assert!(embedded.warps()[5].is_refused());
        assert_eq!(embedded.geometry(), map.geometry());
    }
    #[test]
    fn shutter_policy_is_exact_and_does_not_infer_physical_depth() {
        assert!(same_rational(Some([4, 5]), Some([8, 10])));
        assert!(!same_rational(Some([4, 5]), Some([1, 1])));
    }
}
