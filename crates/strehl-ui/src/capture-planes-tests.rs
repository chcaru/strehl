//! The plane view's data: binding tries, focus maps, the four-shot
//! assembly, the pyramid and its tiles, and the deck's requests.
use super::*;
use std::io::Write;

fn buffered(plane: u64, first: u64, group: &str, unix_ms: u64, focus: u64) -> String {
    let files: Vec<String> = (0..4)
        .map(|k| {
            format!(
                r#"{{"name":"frame-{:06}.ARW","plane":{plane},"group_id":"{group}","member_index":{}}}"#,
                first + k,
                k + 1
            )
        })
        .collect();
    format!(
        r#"{{"event":"capture_buffered","unix_ms":{unix_ms},"data":{{"response":{{"camera_reply":{{"focus":{focus}}},"files":[{}]}}}}}}"#,
        files.join(",")
    )
}

fn receipt_line(n: u64) -> String {
    format!(
        r#"{{"ok":true,"durable":true,"logical_name":"frame-{n:06}.ARW","storage_encoding":"strehl-archive-v2"}}"#
    )
}

fn append(path: &Path, lines: &[String]) {
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .unwrap();
    for l in lines {
        writeln!(f, "{l}").unwrap();
    }
}

/// A try arrives when the journal has bound its RAWs and each has a
/// durable receipt; a retake is the plane's next try, and a group still
/// missing a RAW does not hold up later ones.
#[test]
fn the_tail_binds_tries_and_waits_for_their_raws() {
    let dir = tempfile::tempdir().unwrap();
    let run = dir.path();
    let events = run.join("events.jsonl");
    let receipts = run.join("transfer-receipts.jsonl");
    append(
        &events,
        &[
            buffered(1, 1, "g1", 1_000, 31_006),
            buffered(2, 5, "g2", 2_000, 31_013),
            // Plane 1's retake, taken after plane 2.
            buffered(1, 9, "g3", 3_000, 31_006),
        ],
    );
    let mut lines: Vec<String> = (1..=7).map(receipt_line).collect();
    lines.extend((9..=12).map(receipt_line));
    append(&receipts, &lines);
    let mut tail = TryTail::new(run.to_path_buf(), 4);
    let got = tail.poll();
    let keys: Vec<(u64, u32)> = got.iter().map(|t| (t.plane, t.attempt)).collect();
    assert_eq!(keys, [(1, 1), (1, 2)], "plane 2 waits for frame 8");
    assert_eq!(got[0].focus, Some(31_006));
    assert_eq!(got[1].taken_ms, Some(3_000));
    assert_eq!(&*got[1].names[0], "frame-000009.ARW");
    assert_eq!(got[1].paths[3], run.join("frame-000012.ARW.straw"));
    assert!(tail.poll().is_empty());
    append(&receipts, &[receipt_line(8)]);
    let got = tail.poll();
    assert_eq!(
        got.iter().map(|t| (t.plane, t.attempt)).collect::<Vec<_>>(),
        [(2, 1)]
    );
    // The same group journaled twice is one try.
    append(&events, &[buffered(2, 5, "g2", 2_000, 31_013)]);
    assert!(tail.poll().is_empty());
}

/// Without bindings (an older host), every `shots` RAWs are a plane.
#[test]
fn without_bindings_every_shots_raws_are_a_plane() {
    let dir = tempfile::tempdir().unwrap();
    let receipts = dir.path().join("transfer-receipts.jsonl");
    append(&receipts, &(1..=10).map(receipt_line).collect::<Vec<_>>());
    let mut tail = TryTail::new(dir.path().to_path_buf(), 4);
    let got = tail.poll();
    assert_eq!(
        got.iter()
            .map(|t| (t.plane, t.names.len()))
            .collect::<Vec<_>>(),
        [(1, 4), (2, 4)]
    );
    append(&receipts, &[receipt_line(11), receipt_line(12)]);
    let got = tail.poll();
    assert_eq!(got.iter().map(|t| t.plane).collect::<Vec<_>>(), [3]);
}

/// A preview: fine checker texture where `sharp(x)` holds, flat grey
/// elsewhere (as blur leaves it).
fn preview(w: usize, h: usize, sharp: impl Fn(usize) -> bool) -> Vec<u8> {
    let mut rgba = Vec::with_capacity(w * h * 4);
    for y in 0..h {
        for x in 0..w {
            let v = if sharp(x) {
                if (x / 2 + y / 2) % 2 == 0 { 70 } else { 190 }
            } else {
                130
            };
            rgba.extend_from_slice(&[v, v, v, 255]);
        }
    }
    rgba
}

fn info(plane: u64, map: Vec<u16>) -> TryInfo {
    TryInfo {
        t: PlaneTry {
            plane,
            attempt: 1,
            names: vec![],
            paths: vec![],
            focus: None,
            taken_ms: None,
        },
        map: Some(map.into()),
        share: None,
    }
}

/// The focus measure finds detail, and a cell is sharp only in the try
/// that shows the most of it there (within 70 %) and above the run's floor.
#[test]
fn sharp_is_where_a_try_shows_the_most_detail() {
    let (w, h) = (480, 320);
    let (grid, l) = focus_map(&preview(w, h, |x| x < w / 2), [w, h]);
    let (_, r) = focus_map(&preview(w, h, |x| x >= w / 2), [w, h]);
    let (_, f) = focus_map(&preview(w, h, |_| false), [w, h]);
    assert_eq!(grid, [48, 32]);
    let mut snap = DeckSnapshot {
        tries: vec![info(1, l.clone()), info(2, r.clone()), info(3, f.clone())],
        grid,
        preview: [w, h],
        ..Default::default()
    };
    summarize(&mut snap);
    let cell = |x: usize, y: usize| y * grid[0] + x;
    assert!(snap.sharp(&l, cell(5, 10)) && !snap.sharp(&l, cell(40, 10)));
    assert!(snap.sharp(&r, cell(40, 10)) && !snap.sharp(&r, cell(5, 10)));
    assert!(
        !(0..grid[0] * grid[1]).any(|i| snap.sharp(&f, i)),
        "flat is never sharp"
    );
    let shares: Vec<f32> = snap.tries.iter().map(|t| t.share.unwrap()).collect();
    assert!(
        (shares[0] - 0.5).abs() < 0.05 && (shares[1] - 0.5).abs() < 0.05,
        "{shares:?}"
    );
    assert_eq!(shares[2], 0.0);
    // A try with a tenth of the detail is not sharp where another is.
    let faint: Vec<u16> = l.iter().map(|v| v.saturating_sub(850)).collect();
    assert!(!snap.sharp(&faint, cell(5, 10)));
}

/// A frame of `w` x `h` active photosites (a two-photosite margin) whose
/// photosite at active `(x, y)` reads `scene(x - dx, y - dy)` in its CFA
/// colour: a member shifted by `(dx, dy)`.
fn member(
    w: usize,
    h: usize,
    dx: isize,
    dy: isize,
    scene: &dyn Fn(isize, isize, usize) -> f32,
) -> strehl_raw::Frame {
    let (stride, bh) = (w + 4, h + 4);
    let mut data = vec![0u16; stride * bh];
    for by in 0..bh {
        for bx in 0..stride {
            let (x, y) = (bx as isize - 2, by as isize - 2);
            let c = strehl_core::pixel_shift::cfa_colour(x, y);
            data[by * stride + bx] = (512.0 + scene(x - dx, y - dy, c)) as u16;
        }
    }
    strehl_raw::Frame {
        data,
        stride,
        buffer_height: bh,
        active: strehl_raw::Region {
            x: 2,
            y: 2,
            width: w,
            height: h,
        },
        levels: strehl_core::noise::Levels {
            black: 512.0,
            white: 15_360.0,
        },
        iso: Some(100.0),
        wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "test".into(),
        path: PathBuf::from("test.ARW"),
    }
}

/// Four shots of a coloured scene, each shifted by its member's offset:
/// every site gets its red, both greens and its blue from the members that
/// sampled it, so the assembly returns the scene itself. With the offsets
/// wrong the colours mix (the control).
#[test]
fn the_four_shot_assembly_takes_each_colour_from_its_member() {
    let scene = |x: isize, y: isize, c: usize| {
        let base = [900.0, 2000.0, 3100.0][c];
        base + 10.0 * ((x * 3 + y * 5).rem_euclid(7)) as f32
    };
    let offsets = [(0, 0), (1, 0), (0, 1), (1, 1)];
    // Member k's photosite (x + o.x, y + o.y) sees scene point (x, y).
    let frames: Vec<strehl_raw::Frame> = offsets
        .iter()
        .map(|o| member(16, 12, o.0, o.1, &scene))
        .collect();
    let table_of = |o: &[(isize, isize); 4]| -> [[usize; 4]; 4] {
        std::array::from_fn(|p| {
            strehl_core::pixel_shift::site_members(o, (p & 1) as isize, (p >> 1) as isize)
        })
    };
    let table = table_of(&offsets);
    for y in 2..10 {
        for x in 2..14 {
            let v = assembled(&frames, &offsets, &[1.0; 4], &table, x, y);
            let want = [0, 1, 2].map(|c| scene(x as isize, y as isize, c));
            assert_eq!(v, want, "site ({x}, {y})");
        }
    }
    let wrong = [(0, 0), (0, 1), (1, 0), (1, 1)];
    let v = assembled(&frames, &wrong, &[1.0; 4], &table_of(&wrong), 5, 5);
    assert_ne!(
        v,
        [0, 1, 2].map(|c| scene(5, 5, c)),
        "the control mixes colours"
    );
    // The first shot alone, demosaiced: a flat scene stays flat.
    let flat = member(16, 12, 0, 0, &|_, _, c| [900.0, 2000.0, 3100.0][c]);
    assert_eq!(bilinear(&flat, 0, 0), [900.0, 2000.0, 3100.0]);
    assert_eq!(bilinear(&flat, 7, 5), [900.0, 2000.0, 3100.0]);
}

/// Each level halves in linear light; the coarsest fits the overview.
#[test]
fn the_pyramid_halves_in_linear_light() {
    let size = [2500u32, 1700];
    let mut rgb = vec![0u8; 2500 * 1700 * 3];
    for (i, p) in rgb.as_chunks_mut::<3>().0.iter_mut().enumerate() {
        if i % 2 == 1 {
            p.copy_from_slice(&[255, 255, 255]);
        }
    }
    let levels = pyramid(size, rgb, &mut Buffers::default());
    assert_eq!(
        levels
            .iter()
            .map(|l| (l.stride, l.size))
            .collect::<Vec<_>>(),
        [(1, [2500, 1700]), (2, [1250, 850]), (4, [625, 425])]
    );
    // Black beside white averages to half the light: sRGB 188, not 128.
    assert_eq!(levels[1].rgb[0], 188);
}

fn image_of(size: [u32; 2]) -> PlaneImage {
    let [w, h] = size.map(|v| v as usize);
    let rgb: Vec<u8> = (0..w * h)
        .flat_map(|i: usize| [(i % 251) as u8, (i / w % 241) as u8, 7])
        .collect();
    PlaneImage {
        id: 1,
        key: TryKey::default(),
        size,
        frame: size,
        levels: pyramid(size, rgb, &mut Buffers::default()),
        kind: ImageKind::FourShot,
        findings: None,
        iso: None,
        display_ev: 0.0,
        cost: [0.0; 3],
    }
}

/// Tiles' cores tile the picture without gaps or overlaps, and each apron
/// texel is its neighbour's edge texel.
#[test]
fn tiles_cover_the_picture_and_their_aprons_match() {
    let image = image_of([2500, 1700]);
    let mut covered = 0.0;
    for ty in 0..2 {
        for tx in 0..3 {
            let mut rgba = Vec::new();
            let (tsize, core, uv) = cut(
                &image,
                TileKey {
                    stride: 1,
                    x: tx,
                    y: ty,
                },
                &mut rgba,
            )
            .unwrap();
            assert!(unit(core) && unit(uv));
            covered += core.area();
            if tx > 0 {
                // The texel left of the core is the previous tile's last.
                let (x, y) = ((tx * TILE - 1) as usize, (ty * TILE) as usize);
                let i = (y * 2500 + x) * 3;
                let row = usize::from(ty > 0);
                let t = row * tsize[0] as usize * 4;
                assert_eq!(&rgba[t..t + 3], &image.levels[0].rgb[i..i + 3]);
            }
        }
    }
    assert!((covered - 1.0).abs() < 1e-4, "{covered}");
    assert!(
        cut(
            &image,
            TileKey {
                stride: 1,
                x: 3,
                y: 0
            },
            &mut Vec::new()
        )
        .is_none()
    );
}

fn fixture_deck(size: [u32; 2]) -> (PlaneDeck, egui::Context) {
    let progress = super::super::fixture::progress();
    let source = FixtureSource::new(&progress, 96, size);
    let deck = PlaneDeck::start(PathBuf::from("fixture"), Box::new(source));
    let ctx = egui::Context::default();
    deck.set_uploader(None, &ctx);
    (deck, ctx)
}

fn wait(deck: &mut PlaneDeck, what: &str, done: impl Fn(&PlaneDeck) -> bool) {
    let end = Instant::now() + Duration::from_secs(60);
    loop {
        deck.poll();
        if done(deck) {
            return;
        }
        assert!(Instant::now() < end, "timed out waiting for {what}");
        // The view asks again every frame it is painted.
        let (key, full) = (deck.want.key, deck.want.full);
        deck.want(key, full, false);
        std::thread::sleep(Duration::from_millis(10));
    }
}

/// The deck measures every try, builds the one asked for, and a newer
/// request supersedes an older one before its build starts.
#[test]
fn the_deck_builds_what_the_view_asks() {
    let (mut deck, _ctx) = fixture_deck([480, 320]);
    wait(&mut deck, "the tries", |d| {
        d.snapshot().polled && d.snapshot().pending == 0
    });
    let snap = deck.snapshot().clone();
    assert_eq!(
        snap.tries.len(),
        super::super::fixture::progress().feed.len()
    );
    assert!(snap.tries.iter().all(|t| t.map.is_some()));
    // Plane 30's band: sharp somewhere, not everywhere.
    let i = snap
        .index(TryKey {
            plane: 30,
            attempt: 1,
        })
        .unwrap();
    let share = snap.tries[i].share.unwrap();
    assert!((0.02..0.6).contains(&share), "{share}");
    let k = TryKey {
        plane: 52,
        attempt: 2,
    };
    deck.want(
        Some(TryKey {
            plane: 10,
            attempt: 1,
        }),
        true,
        false,
    );
    deck.want(Some(k), true, false);
    wait(&mut deck, "plane 52", PlaneDeck::settled);
    let image = deck.image().unwrap().clone();
    assert_eq!(image.key, k);
    assert_eq!(image.id, 1, "plane 10 was superseded before its build");
    let f = image.findings.as_ref().unwrap();
    assert!(
        f.reason
            .as_deref()
            .unwrap()
            .contains("witness tiles disagree")
    );
    assert!(f.local.iter().any(|z| *z >= LOCAL_LIMIT as f32));
    assert!(deck.overview().is_some());
    // A pattern failure is shown as its first shot, without witness tiles.
    let k = TryKey {
        plane: 24,
        attempt: 1,
    };
    deck.want(Some(k), true, true);
    wait(&mut deck, "plane 24", PlaneDeck::settled);
    let image = deck.image().unwrap();
    assert_eq!((image.key, &image.kind), (k, &ImageKind::FirstShot));
    assert!(image.findings.as_ref().unwrap().z2.is_empty());
}

/// Tiles in view are uploaded on the worker, not the UI thread, and kept
/// within the budget.
#[test]
fn tiles_are_uploaded_off_the_ui_thread() {
    let (mut deck, _ctx) = fixture_deck([2200, 1500]);
    deck.want(
        Some(TryKey {
            plane: 40,
            attempt: 1,
        }),
        true,
        false,
    );
    wait(&mut deck, "the picture", PlaneDeck::settled);
    let image = deck.image().unwrap().clone();
    let keys: Vec<TileKey> = (0..3)
        .flat_map(|x| (0..2).map(move |y| TileKey { stride: 1, x, y }))
        .collect();
    let started = Instant::now();
    deck.demand(&keys);
    assert!(
        started.elapsed() < Duration::from_millis(20),
        "demand only queues"
    );
    wait(&mut deck, "the tiles", |d| {
        keys.iter().all(|k| d.tile(k).is_some())
    });
    assert_eq!(deck.tile_count(), 6);
    assert_eq!(image.levels.len(), 3);
}

/// The display gain puts the bright end at 0.9 and is bounded.
#[test]
fn the_display_gain_is_bounded() {
    assert_eq!(Develop::gain_for(vec![0.1; 100]), 8.0);
    assert!((Develop::gain_for(vec![0.45; 100]) - 2.0).abs() < 1e-4);
    assert_eq!(Develop::gain_for(vec![2.0; 100]), 1.0);
    assert_eq!(Develop::gain_for(Vec::new()), 1.0);
}

/// The cost of building real planes: `STREHL_PLANE_RUN=<capture folder>`
/// (read only) and optionally `STREHL_PLANE_COUNT` (spread over the run) or
/// `STREHL_PLANE_LIST` (plane numbers, every try). With
/// `STREHL_PLANE_JOURNAL` (a copy of the run's checker journal) each try's
/// verdict, reason and offsets here are compared with the checker's.
/// `cargo test --release -p strehl-ui plane_build_cost -- --ignored --nocapture`.
#[test]
#[ignore = "needs a capture folder"]
fn plane_build_cost() {
    let Some(run) = std::env::var_os("STREHL_PLANE_RUN").map(PathBuf::from) else {
        return;
    };
    let count: usize = std::env::var("STREHL_PLANE_COUNT")
        .ok()
        .and_then(|c| c.parse().ok())
        .unwrap_or(6);
    let mut tail = TryTail::new(run, 4);
    let tries = tail.poll();
    println!("{} tries bound and on disk", tries.len());
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(PLANE_THREADS)
        .start_handler(|_| crate::draft_preview::lower_thread_priority())
        .build()
        .unwrap();
    let source = RunSource {
        tail: TryTail::new(PathBuf::new(), 4),
    };
    let journal: Vec<serde_json::Value> = std::env::var_os("STREHL_PLANE_JOURNAL")
        .and_then(|j| std::fs::read_to_string(j).ok())
        .map(|text| {
            text.lines()
                .filter_map(|l| serde_json::from_str(l).ok())
                .collect()
        })
        .unwrap_or_default();
    let list: Vec<u64> = std::env::var("STREHL_PLANE_LIST")
        .ok()
        .map(|l| l.split(',').filter_map(|p| p.trim().parse().ok()).collect())
        .unwrap_or_default();
    let chosen: Vec<&PlaneTry> = if list.is_empty() {
        let step = (tries.len() / count.max(1)).max(1);
        tries.iter().step_by(step).take(count).collect()
    } else {
        tries.iter().filter(|t| list.contains(&t.plane)).collect()
    };
    let (mut same, mut differ) = (0, 0);
    let mut gain = None;
    let mut buffers = Buffers::default();
    for t in chosen {
        let started = Instant::now();
        let (psize, rgba) = source.preview(t, MAP_SIDE).unwrap();
        let mapped = Instant::now();
        let (grid, _) = focus_map(&rgba, psize);
        let preview_ms = mapped.duration_since(started).as_secs_f64() * 1000.0;
        let map_ms = mapped.elapsed().as_secs_f64() * 1000.0;
        let built = Instant::now();
        let d = pool
            .install(|| build_raw(&t.paths, gain, &|| false, &mut buffers))
            .unwrap();
        gain.get_or_insert(d.gain);
        let develop_ms = built.elapsed().as_secs_f64() * 1000.0 - d.decode_ms - d.check_ms;
        let pyr = Instant::now();
        let size = d.size;
        let kind = d.kind.clone();
        let reason = d.findings.as_ref().and_then(|f| f.reason.clone());
        let local = d.findings.as_ref().map_or(f64::NAN, |f| f.local_px);
        let offsets: Option<Vec<[i64; 2]>> = d
            .findings
            .as_ref()
            .map(|f| f.offsets.iter().map(|o| [o.0 as i64, o.1 as i64]).collect());
        let levels = pool.install(|| pyramid(size, d.rgb, &mut buffers));
        let pyramid_ms = pyr.elapsed().as_secs_f64() * 1000.0;
        let bytes: usize = levels.iter().map(|l| l.rgb.len()).sum();
        println!(
            "plane {:>4} try {}: preview {preview_ms:.1} ms {psize:?}, map {map_ms:.1} ms {grid:?} | decode {:.0} ms, check {:.0} ms, develop {develop_ms:.0} ms, pyramid {pyramid_ms:.0} ms | {kind:?} {size:?} gain {:.2} | {} MB | local p99 {local:.2} px {reason:?}",
            t.plane,
            t.attempt,
            d.decode_ms,
            d.check_ms,
            d.gain,
            bytes / 1_000_000,
        );
        if let Some(line) = journal
            .iter()
            .find(|l| l["names"][0].as_str() == t.first().map(|n| &**n))
        {
            let theirs = line["reason"].as_str().map(str::to_owned);
            let their_offsets: Option<Vec<[i64; 2]>> = line["offsets"].as_array().map(|a| {
                a.iter()
                    .map(|o| [o[0].as_i64().unwrap_or(9), o[1].as_i64().unwrap_or(9)])
                    .collect()
            });
            let agree = theirs == reason && their_offsets == offsets;
            if agree {
                same += 1;
            } else {
                differ += 1;
            }
            println!(
                "    checker: {:?} {theirs:?} {their_offsets:?} -> {}",
                line["verdict"].as_str(),
                if agree { "the same" } else { "DIFFERENT" }
            );
        }
    }
    if !journal.is_empty() {
        println!("compared with the checker's journal: {same} the same, {differ} different");
        assert_eq!(differ, 0);
    }
}

/// Whether a worker allocating and freeing picture-sized buffers stalls
/// small allocations on another thread (the UI's): the worst of 200 bursts
/// of 20,000 small allocations, with and without the worker.
/// `cargo test --release -p strehl-ui large_buffers_stall_small_allocations -- --ignored --nocapture`.
#[test]
#[ignore = "experiment: prints latencies"]
fn large_buffers_stall_small_allocations() {
    fn bursts() -> (f64, f64) {
        let mut worst = 0.0f64;
        let mut total = 0.0;
        for _ in 0..200 {
            let t = Instant::now();
            let v: Vec<Vec<u8>> = (0..20_000).map(|i| vec![i as u8; 64 + i % 512]).collect();
            std::hint::black_box(&v);
            drop(v);
            let ms = t.elapsed().as_secs_f64() * 1000.0;
            worst = worst.max(ms);
            total += ms;
            std::thread::sleep(Duration::from_millis(5));
        }
        (total / 200.0, worst)
    }
    println!(
        "alone: mean {:.2} ms, worst {:.2} ms",
        bursts().0,
        bursts().1
    );
    for (label, pooled) in [
        ("allocating 4 x 122 MB and freeing them", false),
        ("reusing 4 x 122 MB", true),
    ] {
        let stop = Arc::new(AtomicBool::new(false));
        let s = stop.clone();
        let worker = std::thread::spawn(move || {
            let mut keep: Vec<Vec<u16>> = Vec::new();
            while !s.load(Ordering::Relaxed) {
                let mut frames: Vec<Vec<u16>> = if pooled && keep.len() == 4 {
                    std::mem::take(&mut keep)
                } else {
                    (0..4).map(|_| vec![0u16; 61_000_000]).collect()
                };
                for f in &mut frames {
                    for v in f.iter_mut().step_by(2048) {
                        *v = 1;
                    }
                }
                if pooled {
                    keep = frames;
                } else {
                    drop(frames);
                }
                std::thread::sleep(Duration::from_millis(20));
            }
        });
        let (mean, worst) = bursts();
        stop.store(true, Ordering::Relaxed);
        worker.join().unwrap();
        println!("{label}: mean {mean:.2} ms, worst {worst:.2} ms");
    }
}
