//! The alignment's NCC tile search (`strehl_core::align::ncc_tile_impl`'s
//! loops, copied from the product as surveyed on 2026-11-18) against a form
//! that runs the x offsets of one row of the search as lanes. Each offset's
//! three sums keep their own order over (y, x), so every score must be
//! bit-identical; the test below checks that before it times anything.
use std::time::Instant;

struct Plane {
    width: usize,
    height: usize,
    data: Vec<f32>,
}

/// The reference tile with its mean removed, and its sum of squares.
fn tile(reference: &Plane, tx: usize, ty: usize, ts: usize) -> (Vec<f32>, f32) {
    let mut a = vec![0f32; ts * ts];
    let mut mean = 0f32;
    for y in 0..ts {
        let row = (ty + y) * reference.width + tx;
        for x in 0..ts {
            let v = reference.data[row + x];
            a[y * ts + x] = v;
            mean += v;
        }
    }
    mean /= (ts * ts) as f32;
    let mut sa = 0f32;
    for v in a.iter_mut() {
        *v -= mean;
        sa += *v * *v;
    }
    (a, sa)
}

/// The product's search: one offset at a time, three scalar chains.
#[allow(clippy::too_many_arguments)]
fn scores_product(a: &[f32], sa: f32, moving: &Plane, tx: usize, ty: usize, bx: i32, by: i32, ts: usize, radius: i32, scores: &mut [f32]) {
    let n = (2 * radius + 1) as usize;
    scores.fill(f32::NEG_INFINITY);
    for j in -radius..=radius {
        for i in -radius..=radius {
            let ox = tx as i32 + bx + i;
            let oy = ty as i32 + by + j;
            if ox < 0 || oy < 0 || ox as usize + ts > moving.width || oy as usize + ts > moving.height {
                continue;
            }
            let (ox, oy) = (ox as usize, oy as usize);
            let mut mb = 0f32;
            for y in 0..ts {
                let row = (oy + y) * moving.width + ox;
                for x in 0..ts {
                    mb += moving.data[row + x];
                }
            }
            mb /= (ts * ts) as f32;
            let (mut num, mut sb) = (0f32, 0f32);
            for y in 0..ts {
                let row = (oy + y) * moving.width + ox;
                for x in 0..ts {
                    let bv = moving.data[row + x] - mb;
                    num += a[y * ts + x] * bv;
                    sb += bv * bv;
                }
            }
            if sb <= 1e-6 {
                continue;
            }
            let s = num / (sa * sb).sqrt();
            scores[(j + radius) as usize * n + (i + radius) as usize] = s;
        }
    }
}

const LANES: usize = 16;

/// The same scores: for each search row, up to sixteen x offsets at once.
/// Lane `l` reads `moving[row + x + l]`, so each lane performs exactly the
/// product's operations for its offset, in the product's order.
#[allow(clippy::too_many_arguments)]
fn scores_lanes(a: &[f32], sa: f32, moving: &Plane, tx: usize, ty: usize, bx: i32, by: i32, ts: usize, radius: i32, scores: &mut [f32]) {
    let n = (2 * radius + 1) as usize;
    scores.fill(f32::NEG_INFINITY);
    let (mw, mh) = (moving.width as i32, moving.height as i32);
    let i_lo = (-radius).max(-(tx as i32 + bx));
    let i_hi = radius.min(mw - ts as i32 - tx as i32 - bx);
    if i_lo > i_hi {
        return;
    }
    let scale = (ts * ts) as f32;
    for j in -radius..=radius {
        let oy = ty as i32 + by + j;
        if oy < 0 || oy + ts as i32 > mh {
            continue;
        }
        let oy = oy as usize;
        let mut i0 = i_lo;
        while i0 <= i_hi {
            let ox0 = (tx as i32 + bx + i0) as usize;
            // Sixteen lanes are read whatever `lanes` is; near the right edge
            // of the plane the block starts further left so the read stays in
            // bounds, and the surplus lanes at its start are ignored.
            let base = ox0.min(moving.width - ts - (LANES - 1));
            let shift = ox0 - base;
            let lanes = ((i_hi - i0 + 1) as usize).min(LANES - shift);
            let mut mb = [0f32; LANES];
            for y in 0..ts {
                let row = &moving.data[(oy + y) * moving.width + base..][..ts + LANES - 1];
                for x in 0..ts {
                    let w: &[f32; LANES] = row[x..x + LANES].try_into().unwrap();
                    for l in 0..LANES {
                        mb[l] += w[l];
                    }
                }
            }
            for m in &mut mb {
                *m /= scale;
            }
            let (mut num, mut sb) = ([0f32; LANES], [0f32; LANES]);
            for y in 0..ts {
                let row = &moving.data[(oy + y) * moving.width + base..][..ts + LANES - 1];
                let arow = &a[y * ts..(y + 1) * ts];
                for x in 0..ts {
                    let w: &[f32; LANES] = row[x..x + LANES].try_into().unwrap();
                    let av = arow[x];
                    for l in 0..LANES {
                        let bv = w[l] - mb[l];
                        num[l] += av * bv;
                        sb[l] += bv * bv;
                    }
                }
            }
            for l in 0..lanes {
                let lane = l + shift;
                if lane >= LANES {
                    // Not reached: `shift` leaves room for `lanes` lanes.
                    break;
                }
                if sb[lane] <= 1e-6 {
                    continue;
                }
                let s = num[lane] / (sa * sb[lane]).sqrt();
                let i = i0 + l as i32;
                scores[(j + radius) as usize * n + (i + radius) as usize] = s;
            }
            i0 += lanes as i32;
        }
    }
}

fn synthetic(width: usize, height: usize, seed: u64, shift: (usize, usize)) -> Plane {
    // Half-integer values in a 14-bit range with structure, like green luma.
    let mut state = seed;
    let mut next = || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let noise: Vec<f32> = (0..(width + 64) * (height + 64)).map(|_| (next() % 4096) as f32 * 0.5).collect();
    let mut data = vec![0f32; width * height];
    for y in 0..height {
        for x in 0..width {
            let (sx, sy) = (x + shift.0, y + shift.1);
            let smooth = 3000.0 + 2000.0 * ((sx as f32 * 0.021).sin() * (sy as f32 * 0.017).cos());
            data[y * width + x] = ((smooth + noise[sy * (width + 64) + sx]) * 2.0).round() * 0.5;
        }
    }
    Plane { width, height, data }
}

pub fn run() {
    let (w, h) = (1400usize, 1000usize);
    let reference = synthetic(w, h, 0x9e3779b97f4a7c15, (8, 8));
    let moving = synthetic(w, h, 0x9e3779b97f4a7c15, (11, 6));
    // Different noise in a second moving plane, so scores are not near 1.
    let other = synthetic(w, h, 0xdeadbeefcafef00d, (9, 9));
    for (label, ts, radius) in [("fine 128 px, radius 6", 128usize, 6i32), ("coarse 32 px, radius 10", 32, 10)] {
        let n = (2 * radius + 1) as usize;
        // Tiles including ones at every edge of the plane, where offsets fall outside.
        let mut tiles: Vec<(usize, usize, i32, i32)> = Vec::new();
        for (tx, ty) in [(0, 0), (4, 3), (w - ts, h - ts), (w - ts - 3, 10), (500, h - ts - 2), (640, 420), (96, 96), (w - ts - 20, h - ts - 20)] {
            for (bx, by) in [(0, 0), (3, -2), (-5, 4), (7, 7)] {
                tiles.push((tx, ty, bx, by));
            }
        }
        let mut identical = true;
        let (mut tp, mut tl) = (0f64, 0f64);
        let (mut sp, mut sl) = (vec![0f32; n * n], vec![0f32; n * n]);
        let mut scored = 0usize;
        for m in [&moving, &other] {
            for &(tx, ty, bx, by) in &tiles {
                let (a, sa) = tile(&reference, tx, ty, ts);
                let t = Instant::now();
                scores_product(&a, sa, m, tx, ty, bx, by, ts, radius, &mut sp);
                tp += t.elapsed().as_secs_f64();
                let t = Instant::now();
                scores_lanes(&a, sa, m, tx, ty, bx, by, ts, radius, &mut sl);
                tl += t.elapsed().as_secs_f64();
                let same = sp.iter().zip(&sl).all(|(a, b)| a.to_bits() == b.to_bits());
                if !same && identical {
                    let k = sp.iter().zip(&sl).position(|(a, b)| a.to_bits() != b.to_bits()).unwrap();
                    println!(
                        "  first difference: tile ({tx}, {ty}) seed ({bx}, {by}), offset j {} i {}: product {:e} lanes {:e}",
                        k / n,
                        k % n,
                        sp[k],
                        sl[k]
                    );
                }
                identical &= same;
                scored += sp.iter().filter(|s| s.is_finite()).count();
            }
        }
        println!(
            "{label}: {} tile searches, {scored} offsets scored | product {:.3} s | offset lanes {:.3} s | {:.1}x | every score bit-identical: {identical}",
            2 * tiles.len(),
            tp,
            tl,
            tp / tl
        );
    }
}
