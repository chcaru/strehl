use super::*;

pub(super) fn geom() -> PlaneGeometry {
    PlaneGeometry::from_active(7032, 4688)
}

pub(super) fn options(smooth: f64) -> GlobalOptions {
    let mut opts = GlobalOptions::new(geom());
    opts.smooth = smooth;
    opts.smooth_huber_px = Some(1.0);
    opts
}

// Read the saved M103 measurements, not originals. The nine generated frame
// positions inherit measured scale curvature; this is not photographic truth.
pub(super) fn truth() -> Vec<Similarity> {
    let saved: serde_json::Value = serde_json::from_str(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/M103-halfdrift/data/truth-dense.json"
    )))
    .unwrap();
    [0, 40, 80, 120, 144, 184, 224, 264, 298]
        .into_iter()
        .enumerate()
        .map(|(k, rung)| {
            let scale = saved["ladder"][rung.to_string()]["scale"].as_f64().unwrap();
            let x = k as f64;
            let angle = 0.0003 * x + 0.00002 * x * x;
            Similarity {
                a: Cx::new(scale * angle.cos(), scale * angle.sin()),
                b: Cx::new(0.9 * x + 0.07 * x * x, -0.4 * x + 0.03 * x * x),
            }
        })
        .collect()
}

// Independently expand the affine coordinate relation, without calling
// Similarity::relative/invert/then (which the solver and CLI also exercise).
pub(super) fn relative(i: Similarity, j: Similarity) -> Similarity {
    let d = i.a.re * i.a.re + i.a.im * i.a.im;
    let re = (j.a.re * i.a.re + j.a.im * i.a.im) / d;
    let im = (j.a.im * i.a.re - j.a.re * i.a.im) / d;
    Similarity {
        a: Cx::new(re, im),
        b: Cx::new(
            j.b.re - re * i.b.re + im * i.b.im,
            j.b.im - im * i.b.re - re * i.b.im,
        ),
    }
}

pub(super) fn edges_for(ids: &[usize], track: &[Similarity]) -> Vec<AlignEdge> {
    let mut edges = Vec::new();
    for (at, &i) in ids.iter().enumerate() {
        for &j in &ids[at + 1..] {
            edges.push(AlignEdge {
                i,
                j,
                t: relative(track[i], track[j]),
                rms: 0.1,
                used: 32,
                lever: 1000.0,
            });
        }
    }
    edges
}

pub(super) fn bits(g: &[Option<Similarity>]) -> Vec<Option<[u64; 4]>> {
    g.iter()
        .map(|t| {
            t.map(|t| {
                [
                    t.a.re.to_bits(),
                    t.a.im.to_bits(),
                    t.b.re.to_bits(),
                    t.b.im.to_bits(),
                ]
            })
        })
        .collect()
}

pub(super) fn expect_mask(g: &[Option<Similarity>], ids: &[usize]) {
    for (k, t) in g.iter().enumerate() {
        assert_eq!(
            t.is_some(),
            ids.contains(&k),
            "unexpected admission at frame {k}"
        );
        if let Some(t) = t {
            assert!(
                [t.a.re, t.a.im, t.b.re, t.b.im]
                    .iter()
                    .all(|x| x.is_finite())
            );
        }
    }
}

// Independent maximum displacement at four plane corners, converted to native
// sensor pixels. No estimate, metric threshold, or prior is fit to this truth.
pub(super) fn native_error(a: Similarity, b: Similarity) -> f64 {
    let g = geom();
    let mut worst: f64 = 0.0;
    for x in [-0.5 * g.width as f64, 0.5 * g.width as f64] {
        for y in [-0.5 * g.height as f64, 0.5 * g.height as f64] {
            let dx = (a.a.re - b.a.re) * x - (a.a.im - b.a.im) * y + a.b.re - b.b.re;
            let dy = (a.a.im - b.a.im) * x + (a.a.re - b.a.re) * y + a.b.im - b.b.im;
            worst = worst.max(2.0 * dx.hypot(dy));
        }
    }
    worst
}
