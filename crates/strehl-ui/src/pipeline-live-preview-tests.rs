use crate::pipeline::PipelineProgress;

fn preview(sequence: u64, frame: usize, folded: usize, total: usize, pixels: &str) -> String {
    format!(
        "STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max={} folded={folded} total={total} sampling=nearest data={pixels}\n",
        100 + folded
    )
}
type Retained = (usize, usize, u64, Vec<u8>);
fn signature(progress: &PipelineProgress) -> Option<Retained> {
    progress.live_preview.latest.as_ref().map(|packet| {
        (
            packet.frame,
            packet.folded,
            packet.sequence,
            packet.pixels.to_vec(),
        )
    })
}

#[test]
fn full_replay_and_arbitrary_chunks_retain_identical_latest_photo_after_ring_eviction() {
    let mut log = String::from("planes: 120 x 80 per CFA plane\n");
    for prefix in 1..=600 {
        log.push_str(&preview(
            prefix as u64,
            prefix - 1,
            prefix,
            600,
            &format!("{:02x}4080ff", prefix % 256),
        ));
    }
    let mut replay = PipelineProgress::default();
    replay.ingest(&log);
    let mut incremental = PipelineProgress::default();
    for chunk in log.as_bytes().chunks(13) {
        incremental.ingest(std::str::from_utf8(chunk).unwrap());
    }
    assert_eq!(signature(&replay), signature(&incremental));
    assert_eq!(
        signature(&replay),
        Some((599, 600, 600, vec![88, 64, 128, 255]))
    );
    assert!(
        replay
            .diagnostic_surfaces
            .iter()
            .all(|packet| packet.folded > 200),
        "fixture must evict early packets from the recent ring"
    );
    assert_eq!(
        replay.live_preview.tone_range,
        Some((0.0, 101.0)),
        "exposure remains anchored to first nonflat preview after its pixels are released"
    );
    assert_eq!(
        replay.live_preview.latest.as_ref().unwrap().pixels.len(),
        4,
        "only the latest photo payload is retained"
    );
    replay.diagnostic_surfaces.clear();
    assert_eq!(
        signature(&replay),
        signature(&incremental),
        "a sparse UI paint still receives the latest real photo after ring removal"
    );
}

#[test]
fn refused_sources_do_not_relabel_latest_photo_or_regress_accepted_prefix() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    progress.ingest(&preview(1, 66, 10, 67, "01020304"));
    assert_eq!(signature(&progress), Some((66, 10, 1, vec![1, 2, 3, 4])));
    let before = signature(&progress);
    for line in [
        preview(2, 66, 0, 67, "ffffeeee"),
        preview(3, 66, 68, 67, "ffffeeee"),
        preview(4, 67, 11, 67, "ffffeeee"),
    ] {
        progress.ingest(&line);
    }
    assert_eq!(
        signature(&progress),
        before,
        "invalid packets cannot replace the current photograph"
    );
    progress.ingest(&preview(5, 64, 9, 67, "ffffffff"));
    assert_eq!(
        signature(&progress),
        before,
        "late smaller accepted prefixes cannot regress the live photograph"
    );
    progress.ingest(&preview(6, 65, 11, 67, "20304050"));
    assert_eq!(
        signature(&progress),
        Some((65, 11, 6, vec![32, 48, 64, 80]))
    );
}

#[test]
fn crop_domain_replacement_removes_old_photo_and_tone_anchor() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    for prefix in 1..=12 {
        progress.ingest(&preview(prefix as u64, prefix - 1, prefix, 12, "10203040"));
    }
    assert_eq!(progress.live_preview.latest.as_ref().unwrap().folded, 12);
    let epoch = progress.diagnostic_epoch;
    progress.ingest(
        "analysis domain: 100 x 60 at full-plane origin (4, 7) -- Crop is applied BEFORE luma\n",
    );
    assert!(progress.diagnostic_epoch > epoch);
    assert!(progress.live_preview.is_empty());
    assert_eq!(progress.live_preview.tone_range, None);
    progress.ingest(&preview(13, 2, 1, 12, "ffeeddcc"));
    assert_eq!(
        signature(&progress),
        Some((2, 1, 13, vec![255, 238, 221, 204]))
    );
    assert_eq!(progress.live_preview.tone_range, Some((0.0, 101.0)));
}

#[test]
fn preview_geometry_change_starts_a_new_bounded_generation() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    progress.ingest(&preview(1, 0, 1, 12, "10203040"));
    let generation = progress.live_preview.generation;
    progress.ingest(
        &preview(2, 11, 12, 12, "ffeeddcc").replace("width=2 height=2", "width=4 height=1"),
    );
    assert!(progress.live_preview.generation > generation);
    let packet = progress.live_preview.latest.as_ref().unwrap();
    assert_eq!((packet.width, packet.height, packet.folded), (4, 1, 12));
    assert_eq!(progress.live_preview.tone_range, Some((0.0, 112.0)));
}

#[test]
fn first_nonflat_range_is_stable_while_latest_same_prefix_pixels_can_refresh() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    progress.ingest(&preview(1, 0, 1, 4, "00000000").replace("max=101", "max=0"));
    assert_eq!(progress.live_preview.tone_range, None);
    progress.ingest(&preview(2, 1, 2, 4, "01020304"));
    assert_eq!(progress.live_preview.tone_range, Some((0.0, 102.0)));
    progress.ingest(&preview(3, 1, 2, 4, "aabbccdd").replace("max=102", "max=400"));
    assert_eq!(
        signature(&progress),
        Some((1, 2, 3, vec![170, 187, 204, 221]))
    );
    assert_eq!(progress.live_preview.tone_range, Some((0.0, 102.0)));
}
