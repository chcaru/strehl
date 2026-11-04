//! Strict cached-only production geometry replay from exact saved guides.
//! The local geometry module is compiled from the current owned source; core,
//! cache and decoder types come from a root-frozen library build.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Read, Write},
    path::{Path, PathBuf},
    time::Instant,
};
use strehl_cli::{session_cache, session_focus, session_input, session_sampling};
#[path = "../../../../crates/strehl-cli/src/session-mosaic-geometry.rs"]
pub(crate) mod session_mosaic_geometry;
use session_mosaic_geometry::{GuideReceipt, MosaicGeometryConfig, MosaicGuide};
use strehl_core::{
    plane::PlaneGeometry,
    warpmap::{FrameWarp, StackIdentity, WarpMap},
};

pub(crate) fn hash_bytes(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
pub(crate) fn hash(path: &Path) -> Result<String> {
    let mut input = BufReader::new(File::open(path)?);
    let mut hash = Sha256::new();
    let mut block = [0_u8; 65536];
    loop {
        let n = input.read(&mut block)?;
        if n == 0 {
            break;
        }
        hash.update(&block[..n]);
    }
    Ok(hash.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
pub(crate) fn read<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    Ok(serde_json::from_reader(BufReader::new(File::open(path)?))?)
}
pub(crate) fn save(path: &Path, value: &impl serde::Serialize) -> Result<()> {
    let file = File::options().write(true).create_new(true).open(path)?;
    let mut output = BufWriter::new(file);
    serde_json::to_writer_pretty(&mut output, value)?;
    output.flush()?;
    output.get_ref().sync_all()?;
    Ok(())
}
pub(crate) fn embed(
    session: &session_input::ResolvedSession,
    pass: usize,
    local: &WarpMap,
) -> Result<WarpMap> {
    let track = &session.passes[pass];
    ensure!(
        local.len() == track.global_range.len(),
        "local map length differs"
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
pub(crate) fn guide(
    root: &Path,
    pilot: &Path,
    pass: usize,
    session: &session_input::ResolvedSession,
) -> Result<MosaicGuide> {
    let record: Value = read(&root.join("receipt.json"))?;
    let path = root.join(format!("guide-{pass}.bin"));
    ensure!(
        hash(&path)?
            == record["passes"][pass]["compact_guide_sha256"]
                .as_str()
                .context("compact guide hash absent")?,
        "compact guide checksum differs"
    );
    let mut input = BufReader::new(File::open(path)?);
    let mut prefix = [0; 12];
    input.read_exact(&mut prefix)?;
    ensure!(&prefix[..8] == b"STRHGUI1", "unknown compact guide format");
    let length = u32::from_le_bytes(prefix[8..12].try_into().unwrap()) as usize;
    ensure!(length <= 1 << 20, "oversized compact guide header");
    let mut bytes = vec![0; length];
    input.read_exact(&mut bytes)?;
    let header: Value = serde_json::from_slice(&bytes)?;
    ensure!(
        header["schema"] == "strehl.cached-mosaic-guide.v1" && header["record_bytes"] == 46,
        "compact guide layout differs"
    );
    ensure!(
        header["source_identities_sha256"] == hash(&pilot.join("source-identities.json"))?
            && header["alignment_envelope_sha256"]
                == hash(&pilot.join(format!("pass-{:02}/alignment.json", pass + 1)))?
            && header["focus_receipt_sha256"]
                == hash(&pilot.join(format!("pass-{:02}/focus/geometry.json", pass + 1)))?,
        "compact guide source/map/focus binding differs"
    );
    let receipt: GuideReceipt = serde_json::from_value(header["receipt"].clone())?;
    ensure!(receipt.pass == pass, "compact guide pass differs");
    let [w, h] = receipt.guide_geometry;
    let n = w.checked_mul(h).context("guide dimensions overflow")?;
    ensure!(n <= 2048 * 2048, "guide exceeds bounded replay size");
    let mut guide = MosaicGuide {
        pass,
        source_geometry: PlaneGeometry {
            width: receipt.source_geometry[0],
            height: receipt.source_geometry[1],
        },
        geometry: PlaneGeometry {
            width: w,
            height: h,
        },
        origin: receipt.origin_quad_pixels,
        step: receipt.step_quad_pixels,
        intensity: Vec::with_capacity(n),
        covered: Vec::with_capacity(n),
        focus_ordinal: Vec::with_capacity(n),
        focus_width: Vec::with_capacity(n),
        usable_focus: Vec::with_capacity(n),
        source_indices: Vec::with_capacity(n),
        receipt,
    };
    let mut digest = Sha256::new();
    for value in [pass, w, h, guide.step, 0, 0] {
        digest.update((value as u64).to_le_bytes());
    }
    for _ in 0..n {
        let mut pixel = [0_u8; 46];
        input.read_exact(&mut pixel)?;
        digest.update(&pixel[..38]);
        ensure!(pixel[4] <= 1 && pixel[5] <= 1, "invalid guide mask");
        guide
            .intensity
            .push(f32::from_le_bytes(pixel[..4].try_into().unwrap()));
        guide.covered.push(pixel[4] != 0);
        guide.usable_focus.push(pixel[5] != 0);
        let mut ids = [usize::MAX; 4];
        for (j, id) in ids.iter_mut().enumerate() {
            let source = u64::from_le_bytes(pixel[6 + 8 * j..14 + 8 * j].try_into().unwrap());
            *id = usize::try_from(source).context("guide source index overflow")?;
            ensure!(
                *id == usize::MAX || session.passes[pass].global_range.contains(id),
                "guide witness outside pass"
            );
        }
        guide.source_indices.push(ids);
        guide
            .focus_ordinal
            .push(f32::from_le_bytes(pixel[38..42].try_into().unwrap()));
        guide
            .focus_width
            .push(f32::from_le_bytes(pixel[42..46].try_into().unwrap()));
    }
    let mut tail = [0; 1];
    ensure!(input.read(&mut tail)? == 0, "trailing guide data");
    let actual: String = digest
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    ensure!(
        actual == guide.receipt.guide_sha256,
        "original production guide hash differs"
    );
    guide.validate()?;
    Ok(guide)
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    ensure!(
        args.len() == 4
            || (args.len() == 5 && args[4].to_str() == Some("features-only"))
            || (6..=10).contains(&args.len()),
        "geometry-replay PILOT COMPACT_GUIDES CACHE FRESH_OUTPUT [FROZEN_CANDIDATES NATIVE_TILE [LOWPASS_BOOL [AFFINE_BOOL [EXPLICIT_ONLY_BOOL [ROBUST_AFFINE_BOOL]]]]]"
    );
    let started = Instant::now();
    let features_only = args.len() == 5;
    let pilot = &args[0];
    let session: session_input::ResolvedSession = read(&pilot.join("session.json"))?;
    let ids: Vec<session_input::SourceIdentity> = read(&pilot.join("source-identities.json"))?;
    let current = session
        .spec
        .resolve_from(&session.passes[0].directories[0])?;
    ensure!(current.frames == session.frames, "original census changed");
    for id in &ids {
        id.check_unchanged()?;
    }
    let destination = session.ensure_output_outside_sources(&args[3])?;
    std::fs::create_dir(&destination)?;
    let mut guides = Vec::new();
    let mut maps = Vec::new();
    for pass in 0..session.passes.len() {
        let loaded = guide(&args[1], pilot, pass, &session)?;
        let alignment: Value = read(&pilot.join(format!("pass-{:02}/alignment.json", pass + 1)))?;
        let map = embed(
            &session,
            pass,
            &WarpMap::from_text(alignment["warpmap"].as_str().context("map absent")?)?,
        )?;
        ensure!(
            hash_bytes(map.to_text().as_bytes()) == loaded.receipt.alignment_sha256,
            "embedded global-index map hash differs"
        );
        guides.push(loaded);
        maps.push(map);
    }
    let config = MosaicGeometryConfig {
        max_canvas_pixels: 33_000_000,
        native_tile: if args.len() >= 6 {
            args[5].to_str().context("native tile UTF8")?.parse()?
        } else {
            32
        },
        native_lowpass: args.len() >= 7
            && args[6].to_str().context("lowpass bool UTF8")?.parse()?,
        native_affine: args.len() >= 8 && args[7].to_str().context("affine bool UTF8")?.parse()?,
        native_affine_robust: args.len() >= 10
            && args[9]
                .to_str()
                .context("robust affine bool UTF8")?
                .parse()?,
        ..Default::default()
    };
    let binding = session_mosaic_geometry::binding(&session, &ids, &guides, &config)?;
    let explicit_only = args.len() >= 9
        && args[8]
            .to_str()
            .context("explicit-only bool UTF8")?
            .parse()?;
    save(
        &destination.join("replay-binding.json"),
        &json!({"schema":"strehl.cached-mosaic-geometry-replay.v1","binding":binding,"original_session_sha256":hash(&pilot.join("session.json"))?,"compact_guides_receipt_sha256":hash(&args[1].join("receipt.json"))?,"workers":4,"memory_limit_bytes":4_u64<<30,"raw_decode_policy":"strict cached-only production entry points", "explicit_candidates_only":explicit_only,"frozen_candidates_sha256":if args.len()>=6 {Some(hash(&args[4])?)}else{None},"candidate_provenance_sha256":if explicit_only && args[4].with_file_name("receipt.json").exists(){Some(hash(&args[4].with_file_name("receipt.json"))?)}else{None}}),
    )?;
    save(&destination.join("session.json"), &session)?;
    save(&destination.join("source-identities.json"), &ids)?;
    let mut cache = session_cache::SourceCache::new(&args[2], &session, 512 << 20)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let result = pool.install(|| -> Result<()> {
        let pairs = if args.len() >= 6 {
            read(&args[4])?
        } else {
            let (pairs, features) = session_mosaic_geometry::discover_source_pairs_cached(
                &session,
                &ids,
                &maps,
                &mut cache,
                &guides,
                &config,
                3 << 30,
            )?;
            save(&destination.join("mosaic-source-features.json"), &features)?;
            pairs
        };
        save(&destination.join("mosaic-candidates.json"), &pairs)?;
        if features_only {
            return Ok(());
        }
        let refine = if explicit_only {
            session_mosaic_geometry::refine_explicit_correspondences_cached
        } else {
            session_mosaic_geometry::refine_native_correspondences_cached
        };
        let native = refine(
            &session,
            &ids,
            &maps,
            &mut cache,
            &guides,
            &pairs,
            &config,
            3 << 30,
        )?;
        save(
            &destination.join("mosaic-native-measurements.json"),
            &native,
        )?;
        let geometry = session_mosaic_geometry::solve_geometry(
            &session,
            &ids,
            &guides,
            &pairs,
            &native,
            &config,
            3 << 30,
        )?;
        geometry.save(&destination.join("mosaic-geometry.json"), &session)?;
        save(
            &destination.join("mosaic-geometry-report.json"),
            &geometry.report,
        )?;
        Ok(())
    });
    ensure!(
        cache.stats().decodes == 0,
        "cached-only geometry attempted RAW decode"
    );
    save(
        &destination.join("replay-outcome.json"),
        &json!({"elapsed_seconds":started.elapsed().as_secs_f64(),"raw_decodes":cache.stats().decodes,"peak_resident_cfa_bytes":cache.stats().peak_resident_cfa_bytes,"success":result.is_ok(),"features_only":features_only,"geometry_solved":result.is_ok()&&!features_only,"error":result.as_ref().err().map(ToString::to_string)}),
    )?;
    result
}
