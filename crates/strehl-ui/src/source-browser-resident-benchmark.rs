//! Actual decode -> scheduler -> egui texture publication, with real pointer
//! cadence. This measures CPU publication, not a rendered GPU frame or quality.
use super::*;
use serde_json::json;

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
        (12..=512).contains(&frames.len()),
        "use12..512 actual RAW photographs, ideally the full299-frame stack"
    );
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
