//! Actual decode -> scheduler -> egui texture publication, with real pointer
//! cadence. This measures CPU publication, not a rendered GPU frame or quality.
use super::*;
use serde_json::json;
use std::path::Path;

fn tick(
    browser: &mut SourceBrowser,
    viewer: &mut Viewer,
    ctx: &egui::Context,
    frames: &[FrameFile],
    selected: usize,
) -> (f64, usize, usize) {
    let began = Instant::now();
    let output = ctx.run(egui::RawInput::default(), |ctx| {
        browser.poll(ctx, 1, selected, frames, &[], 8192, viewer);
    });
    let poll_us = began.elapsed().as_secs_f64() * 1e6;
    let bytes = output
        .textures_delta
        .set
        .iter()
        .map(|(_, delta)| delta.image.size().into_iter().product::<usize>() * 4)
        .sum();
    let manager = ctx.tex_manager();
    let manager = manager.read();
    let canonical_bytes = output
        .textures_delta
        .set
        .iter()
        .filter(|(id, _)| {
            manager.meta(*id).is_some_and(|meta| {
                [":Scrub", ":Overview", ":Image"]
                    .iter()
                    .any(|suffix| meta.name.ends_with(suffix))
            })
        })
        .map(|(_, delta)| delta.image.size().into_iter().product::<usize>() * 4)
        .sum();
    (poll_us, bytes, canonical_bytes)
}

fn trace(
    browser: &mut SourceBrowser,
    viewer: &mut Viewer,
    ctx: &egui::Context,
    frames: &[FrameFile],
    reverse: bool,
    expected_ready: bool,
) -> serde_json::Value {
    let mut rows = Vec::new();
    let mut immediate = 0;
    let mut available = 0;
    let mut retained = 0;
    let mut uploads = 0;
    let mut canonical_uploads = 0;
    let mut decoder_active_ticks = 0;
    let mut current_hold = 0;
    let mut maximum_hold = 0;
    let native_identities: Vec<_> = (0..frames.len())
        .map(|index| browser.native_thumbnail(index).map(TextureHandle::id))
        .collect();
    for step in 0..frames.len() {
        let selected = if reverse {
            frames.len() - 1 - step
        } else {
            step
        };
        let previous = browser.displayed.map(|(index, kind)| {
            (
                index,
                kind,
                viewer.texture.as_ref().unwrap().id(),
                viewer.source_size,
            )
        });
        let (poll_us, upload_bytes, canonical_upload_bytes) =
            tick(browser, viewer, ctx, frames, selected);
        let displayed = browser.displayed_index();
        let snapshot = browser.texture_snapshot(selected);
        let canonical_available = snapshot.is_some();
        let correct = browser.displayed.is_some_and(|(index, kind)| {
            index == selected && matches!(kind, Kind::Scrub | Kind::Overview | Kind::Image)
        });
        immediate += usize::from(correct);
        available += usize::from(canonical_available);
        retained += usize::from(correct && !canonical_available);
        uploads += upload_bytes;
        canonical_uploads += canonical_upload_bytes;
        let decoder_active = browser.work.is_some() || browser.film_work.is_some();
        decoder_active_ticks += usize::from(decoder_active);
        current_hold = if correct { 0 } else { current_hold + 1 };
        maximum_hold = maximum_hold.max(current_hold);
        if correct {
            if let Some((_, texture, aperture)) = snapshot {
                assert_eq!(viewer.texture.as_ref().unwrap().id(), texture.id());
                assert_eq!(viewer.source_size, aperture);
            } else {
                // Clearing the resident cache deliberately does not erase the
                // photograph already retained by Viewer. Witness its exact
                // texture and aperture instead of treating it as a cache hit.
                let (index, kind, texture, aperture) = previous.expect("retained actual source");
                assert_eq!(index, selected);
                assert!(matches!(kind, Kind::Scrub | Kind::Overview | Kind::Image));
                assert_eq!(viewer.texture.as_ref().unwrap().id(), texture);
                assert_eq!(viewer.source_size, aperture);
            }
        }
        if expected_ready {
            assert!(
                correct,
                "resident source {selected} missed actual publication"
            );
            assert!(
                canonical_available,
                "resident source must be available for reuse"
            );
            assert_eq!(
                upload_bytes, 0,
                "a resident sweep must not rebuild textures in any tier"
            );
            assert!(
                !browser.active(),
                "a resident sweep must not dispatch any decoder or retain pending uploads"
            );
            assert_eq!(
                browser.native_thumbnail(selected).map(TextureHandle::id),
                native_identities[selected],
                "a resident contact must keep its original texture"
            );
            assert!(
                native_identities[selected].is_some(),
                "native contact must be resident"
            );
        }
        rows.push(json!({"requested":selected,"displayed":displayed,"canonical_current":correct,"canonical_available":canonical_available,"retained_current":correct && !canonical_available,"displayed_tier":browser.displayed.map(|(_,kind)| format!("{kind:?}")),"poll_us":poll_us,"upload_bytes":upload_bytes,"canonical_upload_bytes":canonical_upload_bytes,"decoder_active":decoder_active}));
        // Same cadence for every arm. Each real source is requested, rather
        // than timing one image decoder and extrapolating a whole gesture.
        std::thread::sleep(Duration::from_millis(8));
    }
    json!({"immediate":immediate,"canonical_available":available,"retained_current":retained,"requested":frames.len(),"upload_bytes":uploads,"canonical_upload_bytes":canonical_uploads,"decoder_active_ticks":decoder_active_ticks,"longest_held_request_run":maximum_hold,"rows":rows})
}

#[test]
#[ignore = "actual RAW whole-stack scrub publication at8ms input cadence"]
fn benchmark_real_stack_scrub_publication() {
    let directory =
        PathBuf::from(std::env::var_os("STREHL_UI_BENCH_SOURCE").expect("owned RAW folder"));
    let report =
        PathBuf::from(std::env::var_os("STREHL_UI_BENCH_REPORT").expect("owned JSON report"));
    let mut frames: Vec<_> = std::fs::read_dir(&directory)
        .unwrap()
        .map(Result::unwrap)
        .filter(|entry| {
            entry
                .path()
                .extension()
                .and_then(|ext| ext.to_str())
                .is_some_and(|ext| ext.eq_ignore_ascii_case("arw"))
        })
        .map(|entry| FrameFile {
            path: entry.path(),
            bytes: entry.metadata().unwrap().len(),
        })
        .collect();
    frames.sort_by(|a, b| a.path.cmp(&b.path));
    assert!(
        (12..=6_000).contains(&frames.len()),
        "use 12..6000 actual RAW photographs, ideally the full 299- or 1,444-frame stack"
    );
    if frames.len() > SCRUB_COUNT {
        return long_stack_scrub_publication(&directory, &report, &frames);
    }
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser::default();
    let mut viewer = Viewer::default();
    let cold = trace(&mut browser, &mut viewer, &ctx, &frames, false, false);
    let selected = frames.len() - 1;
    let warm_start = Instant::now();
    let mut warm_ticks = 0;
    let mut max_warm_poll_us = 0.0_f64;
    let mut max_warm_upload_bytes = 0;
    loop {
        let (poll_us, upload_bytes, _) = tick(&mut browser, &mut viewer, &ctx, &frames, selected);
        warm_ticks += 1;
        max_warm_poll_us = max_warm_poll_us.max(poll_us);
        max_warm_upload_bytes = max_warm_upload_bytes.max(upload_bytes);
        assert!(
            browser
                .scrubs
                .values()
                .map(|image| image.bytes)
                .sum::<usize>()
                <= SCRUB_BYTES
        );
        assert!(browser.thumbs.len() <= THUMB_COUNT);
        assert!(
            browser
                .thumbs
                .values()
                .map(|image| image.bytes)
                .sum::<usize>()
                <= THUMB_BYTES
        );
        if cache_covers_range(&browser.scrubs, &(0..frames.len()))
            && cache_covers_range(&browser.thumbs, &(0..frames.len()))
            && !browser.active()
        {
            break;
        }
        assert!(
            warm_start.elapsed() < Duration::from_secs(90),
            "real stack did not warm: {} / {}, errors={:?}",
            browser.scrubs.len(),
            frames.len(),
            browser.errors
        );
        std::thread::sleep(Duration::from_millis(16));
    }
    let warm_ms = warm_start.elapsed().as_secs_f64() * 1000.0;
    let resident_bytes = browser
        .scrubs
        .values()
        .map(|image| image.bytes)
        .sum::<usize>();
    let contact_bytes = browser
        .thumbs
        .values()
        .map(|image| image.bytes)
        .sum::<usize>();
    let forward = trace(&mut browser, &mut viewer, &ctx, &frames, false, true);
    let reverse = trace(&mut browser, &mut viewer, &ctx, &frames, true, true);
    // Explicit cache-removal control on the same binary and files. Refined
    // textures and native contacts remain. Do not present this as a v25 timing.
    browser.scrubs.clear();
    let evicted = trace(&mut browser, &mut viewer, &ctx, &frames, false, false);
    assert!(
        evicted["immediate"].as_u64().unwrap() < frames.len() as u64,
        "eviction control must really lose canonical source availability"
    );
    let data = json!({
        "measurement":"real camera decoding + scheduler + CPU egui texture publication; GPU not measured",
        "source":directory,"frames":frames.len(),"input_interval_ms":8,
        "cold_forward":cold,"warm_forward":forward,"warm_reverse":reverse,
        "resident_evicted_control":evicted,"resident_side":browser.scrub_side,
        "resident_bytes":resident_bytes,"resident_byte_cap":SCRUB_BYTES,
        "native_contact_count":browser.thumbs.len(),"native_contact_bytes":contact_bytes,
        "native_contact_count_cap":THUMB_COUNT,"native_contact_byte_cap":THUMB_BYTES,
        "warm_ms":warm_ms,"warm_ticks":warm_ticks,"max_warm_poll_us":max_warm_poll_us,
        "max_warm_upload_bytes_all_tiers":max_warm_upload_bytes,
        "quality_claim":false
    });
    std::fs::write(&report, serde_json::to_vec_pretty(&data).unwrap()).unwrap();
    println!(
        "{} actual sources; resident warming {:.1}ms; report {}",
        frames.len(),
        warm_ms,
        report.display()
    );
}

/// One sweep step: what is on screen, how far it is from the request, and
/// what the step cost. A long stack cannot hold every capture resident, so
/// the claim is the sparse tier's: the requested capture or its nearest
/// resident neighbour is on screen at every step, with no upload.
fn neighbour_trace(
    browser: &mut SourceBrowser,
    viewer: &mut Viewer,
    ctx: &egui::Context,
    frames: &[FrameFile],
    reverse: bool,
    limit: Option<usize>,
) -> serde_json::Value {
    let mut exact = 0;
    let mut stand_in = 0;
    let mut blank = 0;
    let mut worst = 0;
    let mut uploads = 0;
    let mut polls = Vec::new();
    for step in 0..frames.len() {
        let selected = if reverse {
            frames.len() - 1 - step
        } else {
            step
        };
        let (poll_us, upload_bytes, _) = tick(browser, viewer, ctx, frames, selected);
        uploads += upload_bytes;
        polls.push(poll_us);
        match browser.displayed_index() {
            Some(shown) if shown == selected => exact += 1,
            Some(shown) => {
                stand_in += 1;
                worst = worst.max(shown.abs_diff(selected));
            }
            None => blank += 1,
        }
        if let Some(limit) = limit {
            let shown = browser.displayed_index();
            assert!(
                shown.is_some_and(|shown| shown.abs_diff(selected) <= limit),
                "step {selected} showed {shown:?}: farther than the nearest resident neighbour"
            );
            assert_eq!(upload_bytes, 0, "a resident stand-in uploads nothing");
        }
        std::thread::sleep(Duration::from_millis(8));
    }
    polls.sort_by(f64::total_cmp);
    let p95 = polls[(polls.len() * 95 / 100).min(polls.len() - 1)];
    json!({"requested":frames.len(),"exact":exact,"stand_in":stand_in,"blank":blank,"worst_distance":worst,"upload_bytes":uploads,"poll_us_p95":p95,"poll_us_max":polls.last().copied().unwrap_or(0.0)})
}

fn sparse_complete(browser: &SourceBrowser, count: usize) -> bool {
    let stride = SourceBrowser::sparse_stride(count).expect("a long stack");
    browser.sparse.len() + browser.sparse_failures.len() >= count.div_ceil(stride)
        && browser.sparse_pending.is_empty()
}

fn long_stack_scrub_publication(directory: &Path, report: &Path, frames: &[FrameFile]) {
    // An explicit, emptied derivative folder: the cold run decodes every
    // picture; the reopen then measures the persistent tier honestly.
    let cache = std::env::var_os("STREHL_UI_BENCH_CACHE").map(PathBuf::from);
    if let Some(cache) = &cache {
        let _ = std::fs::remove_dir_all(cache);
    }
    crate::source_preview::disk::set_root(cache.clone());
    let count = frames.len();
    let stride = SourceBrowser::sparse_stride(count).unwrap();
    let ctx = egui::Context::default();
    let mut browser = SourceBrowser::default();
    let mut viewer = Viewer::default();
    let cold = trace(&mut browser, &mut viewer, &ctx, frames, false, false);
    // Rest at the end of the stack until both resident tiers are warm.
    let selected = count - 1;
    let warm_start = Instant::now();
    let mut sparse_ms = None;
    loop {
        tick(&mut browser, &mut viewer, &ctx, frames, selected);
        if sparse_ms.is_none() && sparse_complete(&browser, count) {
            sparse_ms = Some(warm_start.elapsed().as_secs_f64() * 1000.0);
        }
        if sparse_complete(&browser, count)
            && cache_covers_range(&browser.scrubs, &browser.scrub_range(count))
            && !browser.active()
        {
            break;
        }
        assert!(
            warm_start.elapsed() < Duration::from_secs(300),
            "long stack did not warm: sparse {} scrub {}",
            browser.sparse.len(),
            browser.scrubs.len()
        );
        std::thread::sleep(Duration::from_millis(16));
    }
    let warm_ms = warm_start.elapsed().as_secs_f64() * 1000.0;
    let sparse_bytes: usize = browser.sparse.values().map(|image| image.bytes).sum();
    let scrub_bytes: usize = browser.scrubs.values().map(|image| image.bytes).sum();
    assert!(sparse_bytes <= SPARSE_BYTES && scrub_bytes <= SCRUB_BYTES);
    // The acceptance sweep: every larger tier removed, the sparse tier only.
    browser.scrubs.clear();
    browser.overviews.clear();
    browser.images.clear();
    let limit = Some(stride / 2 + 1);
    let cold_forward = neighbour_trace(&mut browser, &mut viewer, &ctx, frames, false, limit);
    let cold_reverse = neighbour_trace(&mut browser, &mut viewer, &ctx, frames, true, limit);
    // Reopen: a new browser on the same files, with the derivative folder.
    let mut reopened = SourceBrowser::default();
    let mut viewer = Viewer::default();
    let reopen_start = Instant::now();
    let mut reopen_sparse_ms = None;
    loop {
        tick(&mut reopened, &mut viewer, &ctx, frames, selected);
        if sparse_complete(&reopened, count) {
            reopen_sparse_ms = Some(reopen_start.elapsed().as_secs_f64() * 1000.0);
            break;
        }
        if reopen_start.elapsed() > Duration::from_secs(300) {
            break;
        }
        std::thread::sleep(Duration::from_millis(16));
    }
    crate::source_preview::disk::set_root(None);
    let data = json!({
        "measurement":"real camera decoding + scheduler + CPU egui texture publication; GPU not measured",
        "source":directory,"frames":count,"input_interval_ms":8,
        "sparse_stride":stride,"sparse_side":SPARSE_SIDE,"sparse_bytes":sparse_bytes,
        "scrub_side":browser.scrub_side,"scrub_bytes":scrub_bytes,
        "disk_derivatives":cache.is_some(),
        "cold_forward_from_open":cold,
        "warm_ms":warm_ms,"sparse_warm_ms":sparse_ms,
        "sparse_only_forward":cold_forward,"sparse_only_reverse":cold_reverse,
        "reopen_sparse_ms":reopen_sparse_ms,
        "quality_claim":false
    });
    std::fs::write(report, serde_json::to_vec_pretty(&data).unwrap()).unwrap();
    println!(
        "{count} actual sources; sparse tier {:.1} ms, both tiers {warm_ms:.1} ms; sparse-only sweeps exact {}+{} stand-in {}+{} blank {}+{} worst {} / {}; reopen sparse {:?} ms; report {}",
        sparse_ms.unwrap_or(f64::NAN),
        cold_forward["exact"],
        cold_reverse["exact"],
        cold_forward["stand_in"],
        cold_reverse["stand_in"],
        cold_forward["blank"],
        cold_reverse["blank"],
        cold_forward["worst_distance"],
        cold_reverse["worst_distance"],
        reopen_sparse_ms,
        report.display()
    );
}
