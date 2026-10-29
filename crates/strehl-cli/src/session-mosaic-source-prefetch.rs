//! Bounded, disjoint original-CFA cache preparation before mosaic alignment.
//! This changes scheduling only: the normal SourceCache decoder, representation,
//! atomic publication and subsequent verification remain the sole pixel path.
use crate::session_cache::{CachedSource, SourceCache};
use crate::session_input::{ResolvedSession, SourceIdentity, SourceMetadata};
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::Serialize;
use std::{collections::BTreeSet, path::Path, sync::Arc, time::Instant};

const FIXED_BYTES: usize = 512 << 20;
const STACK_BYTES: usize = 2 << 20;
const MAX_WORKERS: usize = 16;

#[derive(Clone, Debug, Serialize)]
pub(super) struct PrefetchPlan {
    pub workers: usize,
    pub resident_cfa_bytes_per_worker: usize,
    pub padded_frame_bytes: usize,
    pub decode_reservation_per_worker: usize,
    pub largest_input_file_bytes: usize,
    pub control_and_stack_bytes_per_worker: usize,
    pub per_worker_bytes: usize,
    pub fixed_bytes: usize,
    pub total_reserved_bytes: usize,
}
#[derive(Debug, Serialize)]
pub(super) struct PrefetchReport {
    pub schema: &'static str,
    pub sources: usize,
    pub existing_entries_deferred_to_consumer: usize,
    pub missing_at_start: usize,
    pub workers_used: usize,
    pub sources_prepared: usize,
    pub actual_decodes: u64,
    pub concurrent_publication_cache_hits: u64,
    pub plan: PrefetchPlan,
    pub elapsed_seconds: f64,
    pub policy: &'static str,
}
#[derive(Clone, Copy)]
struct Bounds {
    active: usize,
    padded: usize,
    width: usize,
    height: usize,
}
fn bounds(item: &SourceMetadata) -> Result<Bounds> {
    let [width, height] = item.stored_dimensions.with_context(|| {
        format!(
            "mosaic prefetch needs stored dimensions: {}",
            item.path.display()
        )
    })?;
    let (width, height) = (width as usize, height as usize);
    ensure!(
        width > 0 && height > 0,
        "mosaic prefetch stored dimensions are empty"
    );
    let active = width
        .checked_mul(height)
        .and_then(|n| n.checked_mul(2))
        .context("prefetch active allocation overflow")?;
    // Exactly the existing session alignment upper bound, including decoder
    // padding. Four buffers cover decode/copy scratch; retained CFA is separate.
    let padded = width
        .checked_add(256)
        .and_then(|w| height.checked_add(256).and_then(|h| w.checked_mul(h)))
        .and_then(|n| n.checked_mul(2))
        .context("prefetch padded allocation overflow")?;
    Ok(Bounds {
        active,
        padded,
        width,
        height,
    })
}
fn plan(
    metadata: &[SourceMetadata],
    ids: &[SourceIdentity],
    memory: usize,
    requested: usize,
    session_bytes: usize,
) -> Result<PrefetchPlan> {
    ensure!(
        !metadata.is_empty() && metadata.len() == ids.len() && requested > 0,
        "invalid mosaic prefetch census/workers"
    );
    let limits = metadata.iter().map(bounds).collect::<Result<Vec<_>>>()?;
    let resident = limits.iter().map(|b| b.active).max().unwrap();
    let padded = limits.iter().map(|b| b.padded).max().unwrap();
    let decode = padded
        .checked_mul(4)
        .context("prefetch decode reservation overflow")?;
    let file = ids
        .iter()
        .map(|id| usize::try_from(id.bytes).context("prefetch input file too large"))
        .collect::<Result<Vec<_>>>()?
        .into_iter()
        .max()
        .unwrap();
    // Each independent cache clones the session. Serialized text is a
    // conservative basis for path/string storage; extra per-source records,
    // header/hash/publication buffers and the explicit worker stack are counted.
    let control = session_bytes
        .checked_mul(4)
        .and_then(|n| n.checked_add(ids.len().checked_mul(512)?))
        .and_then(|n| n.checked_add((1 << 20) + STACK_BYTES))
        .context("prefetch control reservation overflow")?;
    let per_worker = resident
        .checked_add(decode)
        .and_then(|n| n.checked_add(file))
        .and_then(|n| n.checked_add(control))
        .context("prefetch worker reservation overflow")?;
    let capacity = memory
        .checked_sub(FIXED_BYTES)
        .context("mosaic prefetch memory below fixed reservation")?
        / per_worker;
    let workers = requested.min(MAX_WORKERS).min(ids.len()).min(capacity);
    ensure!(
        workers > 0,
        "mosaic memory cannot hold one bounded original decode/cache publication worker"
    );
    let total = workers
        .checked_mul(per_worker)
        .and_then(|n| n.checked_add(FIXED_BYTES))
        .context("prefetch total reservation overflow")?;
    ensure!(
        total <= memory,
        "mosaic prefetch exceeds explicit memory limit"
    );
    Ok(PrefetchPlan {
        workers,
        resident_cfa_bytes_per_worker: resident,
        padded_frame_bytes: padded,
        decode_reservation_per_worker: decode,
        largest_input_file_bytes: file,
        control_and_stack_bytes_per_worker: control,
        per_worker_bytes: per_worker,
        fixed_bytes: FIXED_BYTES,
        total_reserved_bytes: total,
    })
}

pub(super) fn prepare(
    session: &ResolvedSession,
    ids: &[SourceIdentity],
    metadata: &[SourceMetadata],
    root: &Path,
    memory: usize,
    workers: usize,
) -> Result<PrefetchReport> {
    prepare_with(
        session,
        ids,
        metadata,
        root,
        memory,
        workers,
        |cache, index| Ok(cache.load_or_decode(&session.frames[index], &ids[index])?),
    )
}

#[allow(clippy::too_many_arguments)]
fn prepare_with<F>(
    session: &ResolvedSession,
    ids: &[SourceIdentity],
    metadata: &[SourceMetadata],
    root: &Path,
    memory: usize,
    workers: usize,
    load: F,
) -> Result<PrefetchReport>
where
    F: Fn(&mut SourceCache, usize) -> Result<Arc<CachedSource>> + Sync,
{
    let started = Instant::now();
    ensure!(
        session.len() == ids.len() && metadata.len() == ids.len(),
        "mosaic prefetch source census differs"
    );
    let mut unique = BTreeSet::new();
    for (index, ((frame, id), item)) in session.frames.iter().zip(ids).zip(metadata).enumerate() {
        ensure!(
            frame.global_index == index
                && item.global_index == index
                && frame.path == id.path
                && item.path == id.path
                && frame.bytes == id.bytes
                && frame.modified_unix_nanos == id.modified_unix_nanos
                && unique.insert(&id.path),
            "mosaic prefetch sources must be unique, ordered and identity bound"
        );
        id.validate()?;
        id.check_unchanged()?;
    }
    let plan = plan(
        metadata,
        ids,
        memory,
        workers,
        serde_json::to_vec(session)?.len(),
    )?;
    let discovery = SourceCache::new(root, session, plan.resident_cfa_bytes_per_worker)?;
    let mut missing = Vec::new();
    for (index, id) in ids.iter().enumerate() {
        // Existence is scheduling information only. A named entry may be
        // corrupt; the unchanged downstream load verifies bytes before use.
        if !discovery.cache_path(id)?.try_exists()? {
            missing.push(index);
        }
    }
    drop(discovery);
    let actual_workers = plan.workers.min(missing.len());
    let mut processed = 0;
    let mut decodes = 0;
    let mut hits = 0;
    if actual_workers > 0 {
        eprintln!(
            "mosaic: preparing {} uncached originals with {} workers; {:.2} GiB reserved",
            missing.len(),
            actual_workers,
            plan.total_reserved_bytes as f64 / (1_u64 << 30) as f64
        );
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(actual_workers)
            .stack_size(STACK_BYTES)
            .build()?;
        let results=pool.install(||(0..actual_workers).into_par_iter().map(|worker|->Result<(usize,u64,u64)>{
            let mut cache=SourceCache::new(root,session,plan.resident_cfa_bytes_per_worker)?;
            let mut count=0;
            for &index in missing.iter().skip(worker).step_by(actual_workers){
                let original=load(&mut cache,index)?;
                let bound=bounds(&metadata[index])?;
                ensure!(original.identity==ids[index]&&original.geometry.width<=bound.width&&original.geometry.height<=bound.height&&original.geometry.full_frame_bytes().is_some_and(|n|n<=bound.padded),"prefetched decode exceeds original identity/header allocation bound: {}",ids[index].path.display());
                drop(original);count+=1;
            }
            let stats=cache.stats();
            Ok((count,stats.decodes,stats.disk_hits))
        }).collect::<Vec<_>>());
        for result in results {
            let (count, d, h) = result?;
            processed += count;
            decodes += d;
            hits += h;
        }
    }
    ensure!(
        processed == missing.len(),
        "mosaic prefetch did not complete its disjoint source census"
    );
    Ok(PrefetchReport {
        schema: "strehl.mosaic-source-prefetch.v1",
        sources: ids.len(),
        existing_entries_deferred_to_consumer: ids.len() - missing.len(),
        missing_at_start: missing.len(),
        workers_used: actual_workers,
        sources_prepared: processed,
        actual_decodes: decodes,
        concurrent_publication_cache_hits: hits,
        plan,
        elapsed_seconds: started.elapsed().as_secs_f64(),
        policy: "Scheduling only. Disjoint original identities, independent one-frame u16 SourceCache instances, bounded shared decoder pool. Existing named files are not certified here; every consuming normal cache load still checks identity, format and payload. No aligned-frame volume; decoder, alignment and mosaic-geometry identities unchanged.",
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_input::{PassSpec, SessionSpec};
    use std::{
        fs,
        path::PathBuf,
        sync::atomic::{AtomicU64, AtomicUsize, Ordering},
    };
    use strehl_core::noise::Levels;
    use strehl_raw::{Frame, Region};
    struct Fixture {
        root: PathBuf,
        session: ResolvedSession,
        ids: Vec<SourceIdentity>,
        metadata: Vec<SourceMetadata>,
    }
    impl Fixture {
        fn new() -> Self {
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let root = std::env::temp_dir().join(format!(
                "strehl-mosaic-prefetch-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&root).unwrap();
            fs::create_dir(root.join("raw")).unwrap();
            for i in 0..4 {
                fs::write(
                    root.join(format!("raw/{i}.ARW")),
                    format!("synthetic original{i}"),
                )
                .unwrap();
            }
            let session = SessionSpec {
                passes: vec![PassSpec {
                    name: "test".into(),
                    directories: vec![PathBuf::from("raw")],
                }],
                ..Default::default()
            }
            .resolve_from(&root)
            .unwrap();
            let ids = session.hash_sources(true).unwrap();
            let metadata=session.frames.iter().map(|frame|serde_json::from_value(serde_json::json!({"global_index":frame.global_index,"path":frame.path,"stored_dimensions":[8,6],"optical_header_present":false})).unwrap()).collect();
            Self {
                root,
                session,
                ids,
                metadata,
            }
        }
        fn frame(&self, index: usize) -> Frame {
            Frame {
                data: (0..48).map(|i| i + index as u16).collect(),
                stride: 8,
                buffer_height: 6,
                active: Region {
                    x: 0,
                    y: 0,
                    width: 8,
                    height: 6,
                },
                levels: Levels {
                    black: 0.0,
                    white: 16000.0,
                },
                iso: Some(100.0),
                wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: vec![],
                camera: "prefetch fixture".into(),
                path: self.ids[index].path.clone(),
            }
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }
    #[test]
    fn mosaic_source_prefetch_planner_checks_joint_reservations_and_worker_caps() {
        let f = Fixture::new();
        let one = plan(&f.metadata, &f.ids, 2 << 30, 1, 2000).unwrap();
        let constrained = plan(
            &f.metadata,
            &f.ids,
            FIXED_BYTES + one.per_worker_bytes * 2,
            99,
            2000,
        )
        .unwrap();
        assert_eq!(constrained.workers, 2);
        assert_eq!(
            constrained.total_reserved_bytes,
            FIXED_BYTES + 2 * one.per_worker_bytes
        );
        assert!(
            plan(
                &f.metadata,
                &f.ids,
                FIXED_BYTES + one.per_worker_bytes - 1,
                4,
                2000
            )
            .is_err()
        );
        assert!(plan(&f.metadata, &f.ids, usize::MAX, 4, usize::MAX).is_err());
        let many: Vec<_> = (0..32).map(|_| f.metadata[0].clone()).collect();
        let ids = vec![f.ids[0].clone(); 32];
        assert_eq!(
            plan(&many, &ids, usize::MAX, 100, 2000).unwrap().workers,
            16
        );
    }
    #[test]
    fn mosaic_source_prefetch_serial_parallel_bytes_warm_skip_and_corruption_refusal() {
        let f = Fixture::new();
        let serial = f.root.join("serial");
        let parallel = f.root.join("parallel");
        for (root, workers) in [(&serial, 1), (&parallel, 4)] {
            let seen = (0..4).map(|_| AtomicUsize::new(0)).collect::<Vec<_>>();
            let report = prepare_with(
                &f.session,
                &f.ids,
                &f.metadata,
                root,
                2 << 30,
                workers,
                |cache, i| {
                    seen[i].fetch_add(1, Ordering::Relaxed);
                    Ok(cache.store_original(&f.ids[i], &f.frame(i))?)
                },
            )
            .unwrap();
            assert_eq!(report.sources_prepared, 4);
            assert_eq!(report.workers_used, workers);
            assert!(seen.iter().all(|s| s.load(Ordering::Relaxed) == 1));
        }
        let mut a = SourceCache::new(&serial, &f.session, 96).unwrap();
        let mut b = SourceCache::new(&parallel, &f.session, 96).unwrap();
        for id in &f.ids {
            assert_eq!(
                fs::read(a.cache_path(id).unwrap()).unwrap(),
                fs::read(b.cache_path(id).unwrap()).unwrap()
            );
            assert!(a.load(id).unwrap().is_some());
            assert!(b.load(id).unwrap().is_some());
        }
        drop(a);
        drop(b);
        let warm = prepare_with(
            &f.session,
            &f.ids,
            &f.metadata,
            &parallel,
            2 << 30,
            4,
            |_, _| panic!("warm prefetch must not decode or claim payload verification"),
        )
        .unwrap();
        assert_eq!(warm.existing_entries_deferred_to_consumer, 4);
        assert_eq!(warm.workers_used, 0);
        assert_eq!(warm.actual_decodes, 0);
        let mut check = SourceCache::new(&parallel, &f.session, 96).unwrap();
        let path = check.cache_path(&f.ids[0]).unwrap();
        fs::write(path, b"corrupt existing cache").unwrap();
        let deferred = prepare_with(
            &f.session,
            &f.ids,
            &f.metadata,
            &parallel,
            2 << 30,
            4,
            |_, _| panic!("corruption is not permission to re-decode silently"),
        )
        .unwrap();
        assert_eq!(deferred.existing_entries_deferred_to_consumer, 4);
        assert!(check.load(&f.ids[0]).is_err());
        let mut duplicate = f.ids.clone();
        duplicate[1] = duplicate[0].clone();
        assert!(
            prepare_with(
                &f.session,
                &duplicate,
                &f.metadata,
                &parallel,
                2 << 30,
                4,
                |_, _| panic!("bad census must fail before work")
            )
            .is_err()
        );
    }
}
