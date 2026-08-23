//! M17's own modes: the blind-spot ladder, and a cost sweep that alternates.
//!
//! Everything else in this crate is M13's harness, kept byte-identical so its
//! rows reproduce. This module is the new measurement.

use std::path::Path;

use crate::edge::{EdgeGeometry, EdgeScene, EdgeSpec};
use crate::measures::{Measure, Scratch};
use crate::planted::{add_noise, gaussian_blur, synthetic_texture};
use crate::tile::{Roi, TileGeom};
use crate::{extract_tiles, flat_noise, open_stack, parse_args};
use strehl_core::plane::PlaneGeometry;

/// Inset used when reducing a field to an interior statistic, on top of the
/// measure's own support and the widest blur in the ladder. Nothing read back
/// was ever computed from a clamped window.
const EXTRA_INSET: usize = 2;

// --------------------------------------------------------------- blind spot

/// A hard vertical step: `base` on the left, `base + amp` on the right.
///
/// This is fact 73's plant. Sobel on a hard step of amplitude `A` puts `A/2` on
/// each of the two columns straddling it, so the total variation of a row is
/// exactly `A`, and `box_mean` over any window that contains the whole
/// transition reads `A / (2w+1)^2 * (2w+1) = A / (2w+1)`. For `A = 1000` and
/// `w = 13` that is `1000/27 = 37.037037` — the number fact 73 records at every
/// blur sigma, because blur moves total variation around without creating or
/// destroying any of it.
fn step_plane(geom: PlaneGeometry, base: f32, amp: f32) -> Vec<f32> {
    let x0 = geom.width / 2;
    (0..geom.pixels())
        .map(|p| {
            if p % geom.width >= x0 {
                base + amp
            } else {
                base
            }
        })
        .collect()
}

/// A monotone *ramp* rather than a step: still untextured, still monotone, but
/// with the transition spread over `run` px so it is not a delta in gradient.
///
/// Registered as a second blind-spot plant because a hard step is the easiest
/// possible case for a max: its gradient is a two-pixel ridge and blur has
/// nowhere to go but down. A ramp already has a low, wide gradient plateau, and
/// blurring it at a sigma below the ramp width barely changes the peak. If the
/// max's advantage survives here it is not an artefact of the step being ideal.
fn ramp_plane(geom: PlaneGeometry, base: f32, amp: f32, run: usize) -> Vec<f32> {
    let x0 = geom.width / 2;
    (0..geom.pixels())
        .map(|p| {
            let x = (p % geom.width) as f32;
            let t = ((x - (x0 as f32 - run as f32 / 2.0)) / run as f32).clamp(0.0, 1.0);
            base + amp * t
        })
        .collect()
}

/// Statistics a field is reduced to. `edge` is the pre-registered primary on
/// the monotone plants — the response at the boundary column, which is the
/// pixel a per-pixel selector would actually be choosing at.
struct Reduced {
    edge: f64,
    edge_dark: f64,
    interior_mean: f64,
    interior_max: f64,
}

fn reduce(field: &[f32], geom: PlaneGeometry, inset: usize) -> Reduced {
    let x0 = geom.width / 2;
    let yc = geom.height / 2;
    let mut sum = 0.0f64;
    let mut n = 0usize;
    let mut mx = f64::NEG_INFINITY;
    for y in inset..geom.height - inset {
        for x in inset..geom.width - inset {
            let v = field[y * geom.width + x] as f64;
            sum += v;
            n += 1;
            if v > mx {
                mx = v;
            }
        }
    }
    Reduced {
        edge: field[yc * geom.width + x0] as f64,
        edge_dark: field[yc * geom.width + x0 - 1] as f64,
        interior_mean: sum / n as f64,
        interior_max: mx,
    }
}

#[allow(clippy::too_many_arguments)]
fn emit(
    csv: &mut String,
    plant: &str,
    m: &Measure,
    noise_scale: f32,
    seed: u64,
    sigma: f32,
    r: &Reduced,
) {
    csv.push_str(&format!(
        "{},{},{},{},{},{:.6},{:.8},{:.8},{:.8},{:.8}\n",
        plant,
        m.name,
        m.norm_str(),
        noise_scale,
        seed,
        sigma,
        r.edge,
        r.edge_dark,
        r.interior_mean,
        r.interior_max
    ));
}

const BLIND_HEADER: &str =
    "plant,measure,norm,noise_scale,seed,sigma,edge,edge_dark,interior_mean,interior_max\n";

/// `blindspot` — the B1 ladder, plus both positive controls and the null.
pub fn blindspot(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let out_path = a
        .one("out")
        .ok_or("blindspot needs --out <FILE>")?
        .to_string();
    let ms = a.measures()?;
    let sigmas = a.list_f32("sigmas", &[0.0, 1.0, 2.0, 3.0, 4.0])?;
    let amp = a.f32_or("amp", 1000.0)?;
    let base = a.f32_or("base", 1000.0)?;
    let run = a.usize_or("ramp-run", 9)?;
    let size = a.usize_or("size", 257)?;
    let seeds: Vec<u64> = match a.one("seeds") {
        Some(s) => s
            .split(',')
            .map(|v| v.trim().parse::<u64>().map_err(|e| e.to_string()))
            .collect::<Result<_, _>>()?,
        None => vec![20_260_823, 771_117, 4_242_424],
    };
    let noise_scales = a.list_f32("noise-scales", &[0.0, 1.0])?;

    let geom = PlaneGeometry {
        width: size,
        height: size,
    };
    let noise = flat_noise();
    let blur_radius = sigmas.iter().fold(0.0f32, |m, s| m.max(*s)).ceil() as usize * 3;

    // Plants that need no corpus access.
    let mut plants: Vec<(String, Vec<f32>)> = vec![
        ("step".to_string(), step_plane(geom, base, amp)),
        (
            format!("ramp{run}"),
            ramp_plane(geom, base, amp, run.max(1)),
        ),
        (
            "texture-synth".to_string(),
            synthetic_texture(geom, base, amp),
        ),
    ];

    // The real-tile positive control, when a corpus directory is supplied.
    if let Some(dir) = a.one("dir") {
        let stack = open_stack(Path::new(dir), Some(1), a.one("label"))?;
        let roi = Roi::parse(a.one("roi").unwrap_or("2272,1344,255,255"))?;
        if roi.width != roi.height || size < roi.width || (size - roi.width) % 2 != 0 {
            return Err(format!(
                "--roi must be square and (--size {size} - roi {}) must be even",
                roi.width
            ));
        }
        let tg = TileGeom::new(roi, (size - roi.width) / 2, stack.plane)?;
        let tiles = extract_tiles(&stack, std::slice::from_ref(&tg), false)?;
        let t = &tiles[0][0].luma;
        if t.len() == geom.pixels() {
            plants.push(("texture-real".to_string(), t.clone()));
        } else {
            return Err(format!(
                "real tile is {} px but the plant grid is {} px; adjust --size or --roi",
                t.len(),
                geom.pixels()
            ));
        }
    }

    let mut csv = String::from(BLIND_HEADER);
    let mut blurred = vec![0.0f32; geom.pixels()];
    let mut frame = vec![0.0f32; geom.pixels()];
    let mut field = vec![0.0f32; geom.pixels()];

    for (plant, src) in &plants {
        for &ns in &noise_scales {
            let seed_list: &[u64] = if ns <= 0.0 { &seeds[..1] } else { &seeds };
            for &seed in seed_list {
                for &sigma in &sigmas {
                    gaussian_blur(src, geom, sigma, &mut blurred);
                    if ns <= 0.0 {
                        frame.copy_from_slice(&blurred);
                    } else {
                        add_noise(&blurred, &noise, ns, seed, &mut frame);
                    }
                    for m in &ms {
                        let mut scratch = Scratch::default();
                        m.compute(&frame, geom, &noise, 0, &mut scratch, &mut field);
                        let inset = m.support_radius + blur_radius + EXTRA_INSET;
                        let r = reduce(&field, geom, inset);
                        emit(&mut csv, plant, m, ns, seed, sigma, &r);
                    }
                }
            }
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!(
        "blindspot: {} plants x {} measures -> {out_path}",
        plants.len(),
        ms.len()
    );
    Ok(())
}

/// `blindspot-edge` — B2. The same monotone boundary, but rendered through
/// M13's own two-layer occlusion compositor with real calibrated noise on
/// M13's own 41-frame ladder, with **both layers untextured** so the only
/// image content in the tile is the boundary itself.
pub fn blindspot_edge(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let out_path = a
        .one("out")
        .ok_or("blindspot-edge needs --out <FILE>")?
        .to_string();
    let ms = a.measures()?;
    let frames = a.usize_or("frames", 41)?;
    let w_true = a.usize_or("w-true", 20)?;
    let sigma0 = a.f32_or("sigma0", 0.8)?;
    let alpha = a.f32_or("alpha", 0.35)?;
    let size = a.usize_or("size", 257)?;
    let near = a.f32_or("near", 3000.0)?;
    let far = a.f32_or("far", 1200.0)?;
    let seeds: Vec<u64> = match a.one("seeds") {
        Some(s) => s
            .split(',')
            .map(|v| v.trim().parse::<u64>().map_err(|e| e.to_string()))
            .collect::<Result<_, _>>()?,
        None => vec![20_260_823, 771_117, 4_242_424],
    };
    let noise_scales = a.list_f32("noise-scales", &[0.0, 1.0])?;

    let geom = PlaneGeometry {
        width: size,
        height: size,
    };
    let noise = flat_noise();
    // Untextured: two constant layers. This is the whole point of B2 — an
    // occluding boundary carrying no texture on either side of it.
    let tex_near = vec![near; geom.pixels()];
    let tex_far = vec![far; geom.pixels()];

    let mut csv = String::from(BLIND_HEADER);
    let mut field = vec![0.0f32; geom.pixels()];

    for &ns in &noise_scales {
        let seed_list: &[u64] = if ns <= 0.0 { &seeds[..1] } else { &seeds };
        for &seed in seed_list {
            let spec = EdgeSpec {
                frames,
                w_near: w_true,
                w_far: w_true,
                sigma0,
                alpha,
                noise_scale: ns,
                seed,
                geometry: EdgeGeometry::Vertical { at: geom.width / 2 },
            };
            let scene = EdgeScene::render(&tex_near, &tex_far, geom, spec, Some(&noise));
            let blur_radius = spec.max_blur_radius();
            for (k, fr) in scene.frames.iter().enumerate() {
                for m in &ms {
                    let mut scratch = Scratch::default();
                    m.compute(fr, geom, &noise, k, &mut scratch, &mut field);
                    let inset = m.support_radius + blur_radius + EXTRA_INSET;
                    if 2 * inset + 4 >= geom.width {
                        return Err(format!("tile too small for inset {inset}"));
                    }
                    let r = reduce(&field, geom, inset);
                    // `sigma` column carries the frame index here; the extra
                    // blur in sigma units is `alpha * |k - w_true|`.
                    emit(&mut csv, "edge2", m, ns, seed, k as f32, &r);
                }
            }
        }
    }

    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    eprintln!("blindspot-edge: {} measures -> {out_path}", ms.len());
    Ok(())
}

// --------------------------------------------------------------------- cost

/// `m17cost` — per-measure wall clock, swept with **alternating direction**.
///
/// SYNTHESIS rule 16 / discipline 30: this project has already read −0.7% on a
/// forward sweep and +19% on the reverse sweep of the *same binary*, so a
/// one-directional sweep here would be worthless. Each measure is timed
/// `passes` times in alternating order and the **per-setting minimum** is
/// reported, because the minimum is the only order statistic a scheduler
/// cannot inflate.
pub fn cost(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let out_path = a
        .one("out")
        .ok_or("m17cost needs --out <FILE>")?
        .to_string();
    let ms = a.measures()?;
    let reps = a.usize_or("reps", 3)?;
    let passes = a.usize_or("passes", 6)?;
    let size = a.usize_or("size", 512)?;

    let geom = PlaneGeometry {
        width: size,
        height: size,
    };
    let noise = flat_noise();
    // A real-ish field: broadband texture on a DN pedestal, so the branchy
    // parts of a max filter see realistic data rather than a constant.
    let luma = synthetic_texture(geom, 500.0, 3000.0);
    let mpx = geom.pixels() as f64 / 1.0e6;

    let mut best: Vec<f64> = vec![f64::INFINITY; ms.len()];
    let mut worst: Vec<f64> = vec![0.0; ms.len()];
    let mut scratch = Scratch::default();
    let mut out = vec![0.0f32; geom.pixels()];
    // Warm the caches and the branch predictors once per measure before any
    // timing is recorded.
    for m in &ms {
        m.compute(&luma, geom, &noise, 0, &mut scratch, &mut out);
    }

    for pass in 0..passes {
        let order: Vec<usize> = if pass % 2 == 0 {
            (0..ms.len()).collect()
        } else {
            (0..ms.len()).rev().collect()
        };
        for i in order {
            let m = &ms[i];
            let t = std::time::Instant::now();
            for k in 0..reps {
                m.compute(&luma, geom, &noise, k, &mut scratch, &mut out);
            }
            let each = t.elapsed().as_secs_f64() * 1000.0 / reps as f64 / mpx;
            if each < best[i] {
                best[i] = each;
            }
            if each > worst[i] {
                worst[i] = each;
            }
        }
    }

    let mut csv = String::from(
        "measure,window,support_radius,mpx,reps,passes,ms_per_frame_per_mpx_min,ms_per_frame_per_mpx_max,spread_pct\n",
    );
    for (i, m) in ms.iter().enumerate() {
        let spread = 100.0 * (worst[i] - best[i]) / best[i];
        csv.push_str(&format!(
            "{},{},{},{:.4},{},{},{:.5},{:.5},{:.2}\n",
            m.name,
            crate::window_of(m),
            m.support_radius,
            mpx,
            reps,
            passes,
            best[i],
            worst[i],
            spread
        ));
        eprintln!(
            "  {:<22} min {:.4}  max {:.4} ms/frame/Mpx  (+{:.1}%)",
            m.name, best[i], worst[i], spread
        );
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    Ok(())
}

/// `boxcost` — the radius axis on its own, for `box_mean` against `box_max`.
///
/// This is the O(1) claim's own test: the filters are timed directly, without
/// the Sobel or the normalisation in the way, over a radius ladder wide enough
/// that an O(r) or O(r^2) term could not hide.
pub fn boxcost(rest: &[String]) -> Result<(), String> {
    let a = parse_args(rest);
    let out_path = a
        .one("out")
        .ok_or("boxcost needs --out <FILE>")?
        .to_string();
    let radii = a.list_usize("radii", &[1, 2, 3, 5, 8, 13, 21, 34, 40])?;
    let reps = a.usize_or("reps", 5)?;
    let passes = a.usize_or("passes", 6)?;
    let size = a.usize_or("size", 512)?;
    let with_pct = a.has("with-pct");

    let geom = PlaneGeometry {
        width: size,
        height: size,
    };
    let src = synthetic_texture(geom, 500.0, 3000.0);
    let mpx = geom.pixels() as f64 / 1.0e6;
    let mut scratch = vec![0.0f32; geom.pixels()];
    let mut dst = vec![0.0f32; geom.pixels()];
    let mut maxstate = crate::boxmax::MaxScratch::default();

    let mut kinds: Vec<&str> = vec!["box_mean", "box_max"];
    if with_pct {
        kinds.push("window_p95");
    }
    let mut best: Vec<Vec<f64>> = vec![vec![f64::INFINITY; radii.len()]; kinds.len()];
    let mut worst: Vec<Vec<f64>> = vec![vec![0.0; radii.len()]; kinds.len()];

    let run = |kind: &str,
               r: usize,
               st: &mut crate::boxmax::MaxScratch,
               scratch: &mut [f32],
               dst: &mut [f32]| match kind {
        "box_mean" => strehl_core::boxfilter::box_mean(&src, geom, r, scratch, dst),
        "box_max" => crate::boxmax::box_max_with(st, &src, geom, r, scratch, dst),
        _ => crate::boxmax::window_percentile(&src, geom, r, 0.95, dst),
    };

    for (ki, kind) in kinds.iter().enumerate() {
        run(kind, radii[0], &mut maxstate, &mut scratch, &mut dst);
        for pass in 0..passes {
            let order: Vec<usize> = if pass % 2 == 0 {
                (0..radii.len()).collect()
            } else {
                (0..radii.len()).rev().collect()
            };
            for i in order {
                let r = radii[i];
                let t = std::time::Instant::now();
                for _ in 0..reps {
                    run(kind, r, &mut maxstate, &mut scratch, &mut dst);
                }
                let each = t.elapsed().as_secs_f64() * 1000.0 / reps as f64 / mpx;
                if each < best[ki][i] {
                    best[ki][i] = each;
                }
                if each > worst[ki][i] {
                    worst[ki][i] = each;
                }
            }
        }
    }

    let mut csv = String::from(
        "filter,radius,diameter,mpx,reps,passes,ms_per_frame_per_mpx_min,ms_per_frame_per_mpx_max,spread_pct\n",
    );
    for (ki, kind) in kinds.iter().enumerate() {
        for (i, r) in radii.iter().enumerate() {
            let spread = 100.0 * (worst[ki][i] - best[ki][i]) / best[ki][i];
            csv.push_str(&format!(
                "{},{},{},{:.4},{},{},{:.6},{:.6},{:.2}\n",
                kind,
                r,
                2 * r + 1,
                mpx,
                reps,
                passes,
                best[ki][i],
                worst[ki][i],
                spread
            ));
        }
        let lo = best[ki].iter().cloned().fold(f64::MAX, f64::min);
        let hi = best[ki].iter().cloned().fold(0.0, f64::max);
        eprintln!(
            "  {:<12} over radii {:?}: min {:.4}  max {:.4} ms/frame/Mpx  ratio {:.3}x",
            kind,
            radii,
            lo,
            hi,
            hi / lo
        );
    }
    std::fs::write(&out_path, csv).map_err(|e| format!("writing {out_path}: {e}"))?;
    Ok(())
}

/// `m17check` — the arithmetic gates that need no corpus at all.
pub fn check(_rest: &[String]) -> Result<(), String> {
    let mut fails = 0usize;
    let mut say = |ok: bool, what: &str, detail: String| {
        if ok {
            println!("  PASS  {what}  {detail}");
        } else {
            println!("  FAIL  {what}  {detail}");
            fails += 1;
        }
    };

    let geom = PlaneGeometry {
        width: 257,
        height: 257,
    };
    let noise = flat_noise();
    let src = step_plane(geom, 1000.0, 1000.0);
    let mut blurred = vec![0.0f32; geom.pixels()];
    let mut field = vec![0.0f32; geom.pixels()];
    let mut scratch = Scratch::default();

    // G5: fact 73's own number, at every sigma in its ladder.
    let m = crate::measures::parse("tenengrad-w13-nonorm").unwrap();
    let mut vals = Vec::new();
    for sigma in [0.0f32, 1.0, 2.0, 3.0] {
        gaussian_blur(&src, geom, sigma, &mut blurred);
        m.compute(&blurred, geom, &noise, 0, &mut scratch, &mut field);
        vals.push(field[128 * geom.width + 128] as f64);
    }
    let want = 1000.0 / 27.0;
    say(
        vals.iter().all(|v| (v - want).abs() < 5e-5),
        "G5 mean-w13 reads A/27 at every sigma",
        format!("{vals:?} vs {want:.6}"),
    );
    say(
        (vals[3] / vals[0] - 1.0).abs() < 1e-6,
        "G5 mean-w13 blind-spot ratio is exactly 1",
        format!("{:.8}", vals[3] / vals[0]),
    );

    // G5b: fact 73's radius-1 control, 0.376.
    let m1 = crate::measures::parse("tenengrad-w1-nonorm").unwrap();
    let mut v1 = Vec::new();
    for sigma in [0.0f32, 3.0] {
        gaussian_blur(&src, geom, sigma, &mut blurred);
        m1.compute(&blurred, geom, &noise, 0, &mut scratch, &mut field);
        v1.push(field[128 * geom.width + 128] as f64);
    }
    let r1 = v1[1] / v1[0];
    say(
        (r1 - 0.376).abs() < 0.02,
        "G5b mean-w1 recovers fact 73's 0.376",
        format!("{r1:.6}"),
    );

    // The dual must reduce to its parts when the other term is removed.
    let dual = crate::measures::parse("tgdual-tie0-w13-nonorm").unwrap();
    let mean = crate::measures::parse("tenengrad-w13-nonorm").unwrap();
    gaussian_blur(&src, geom, 1.5, &mut blurred);
    let mut fa = vec![0.0f32; geom.pixels()];
    let mut fb = vec![0.0f32; geom.pixels()];
    dual.compute(&blurred, geom, &noise, 0, &mut scratch, &mut fa);
    mean.compute(&blurred, geom, &noise, 0, &mut scratch, &mut fb);
    say(
        fa == fb,
        "dual with weight 0 is exactly the status quo",
        format!(
            "{} px differ",
            fa.iter().zip(&fb).filter(|(x, y)| x != y).count()
        ),
    );

    // The gradient field is shared: max at window 0 is the bare magnitude, and
    // so is mean at window 0.
    let m0max = crate::measures::parse("tgmax-w0-nonorm").unwrap();
    let m0mean = crate::measures::parse("tenengrad-w0-nonorm").unwrap();
    m0max.compute(&blurred, geom, &noise, 0, &mut scratch, &mut fa);
    m0mean.compute(&blurred, geom, &noise, 0, &mut scratch, &mut fb);
    say(
        fa == fb,
        "max and mean agree at window 0 (same gradient field)",
        format!(
            "{} px differ",
            fa.iter().zip(&fb).filter(|(x, y)| x != y).count()
        ),
    );

    // p100 is the max, on real-ish data, through the measure layer.
    let tex = synthetic_texture(geom, 1000.0, 2000.0);
    let p100 = crate::measures::parse("tgp100-w5-nonorm").unwrap();
    let mx5 = crate::measures::parse("tgmax-w5-nonorm").unwrap();
    p100.compute(&tex, geom, &noise, 0, &mut scratch, &mut fa);
    mx5.compute(&tex, geom, &noise, 0, &mut scratch, &mut fb);
    say(
        fa == fb,
        "tgp100 == tgmax through the measure layer",
        format!(
            "{} px differ",
            fa.iter().zip(&fb).filter(|(x, y)| x != y).count()
        ),
    );

    // Support radii are declared correctly, which is what sets the tile margin.
    for (name, want) in [
        ("tenengrad-w13", 14usize),
        ("tgmax-w13", 14),
        ("tgp95-w13", 14),
        ("tgdual-geo-w13", 14),
        ("tgrad-larger-w1-w13", 14),
        ("tenengrad-sq-w13", 14),
        ("tenengrad-w40", 41),
    ] {
        let m = crate::measures::parse(name).unwrap();
        say(
            m.support_radius == want,
            "support radius",
            format!("{name}: {} (want {want})", m.support_radius),
        );
    }
    // Degree: candidate (c) must be normalised by sigma^2, the rest by sigma.
    for (name, want) in [
        ("tenengrad-w13", 1i32),
        ("tgmax-w13", 1),
        ("tgdual-geo-w13", 1),
        ("tenengrad-sq-w13", 2),
    ] {
        let m = crate::measures::parse(name).unwrap();
        say(
            m.kind.degree() == want,
            "sigma degree",
            format!("{name}: {} (want {want})", m.kind.degree()),
        );
    }

    println!("\n{}", if fails == 0 { "ALL PASS" } else { "FAILURES" });
    if fails > 0 {
        return Err(format!("{fails} check(s) failed"));
    }
    Ok(())
}
