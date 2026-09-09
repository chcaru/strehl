//! Independently authored fixed public-API boundary commission.
//! See experiments/sampler-boundary/independent-test-spec.md. No sampler implementation is copied.
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::panic::{AssertUnwindSafe, catch_unwind};
use strehl_core::align::{Cx, PlaneRef, Resampler, Similarity};
use strehl_core::plane::PlaneGeometry;
use strehl_core::warpmap::gather_checked;

const W: usize = 128;
const H: usize = 96;
const TOL: f64 = 1.0 / 32.0;
const DIFFERENT: f64 = 0.25;
const EXPECTED_ROWS: usize = 344;
const GROUPS: [(&str, usize); 11] = [
    ("support", 6),
    ("boundary", 126),
    ("null", 18),
    ("nonfinite", 36),
    ("tiny", 48),
    ("unchecked", 60),
    ("unchecked-tiny", 20),
    ("constructor", 4),
    ("lanczos-commission", 18),
    ("cubic-limiter", 6),
    ("gather", 2),
];

#[derive(Clone, Copy)]
struct Kernel {
    name: &'static str,
    sampler: Resampler,
    support: f64,
    lanczos: bool,
}
const KERNELS: [Kernel; 6] = [
    Kernel {
        name: "nearest",
        sampler: Resampler::Nearest,
        support: 0.5,
        lanczos: false,
    },
    Kernel {
        name: "bilinear",
        sampler: Resampler::Bilinear,
        support: 1.0,
        lanczos: false,
    },
    Kernel {
        name: "catmull-rom",
        sampler: Resampler::CatmullRom,
        support: 2.0,
        lanczos: false,
    },
    Kernel {
        name: "clamped-catmull-rom",
        sampler: Resampler::ClampedCatmullRom,
        support: 2.0,
        lanczos: false,
    },
    Kernel {
        name: "lanczos2",
        sampler: Resampler::Lanczos2,
        support: 2.0,
        lanczos: true,
    },
    Kernel {
        name: "lanczos3",
        sampler: Resampler::Lanczos3,
        support: 3.0,
        lanczos: true,
    },
];

#[derive(Clone, Copy)]
enum Observed {
    Returned(f32),
    Refused,
    Panicked,
    Boolean(bool),
}
impl Observed {
    fn kind(self) -> &'static str {
        match self {
            Self::Returned(v) if v.is_finite() => "finite",
            Self::Returned(_) => "nonfinite",
            Self::Refused => "refused",
            Self::Panicked => "panic",
            Self::Boolean(true) => "true",
            Self::Boolean(false) => "false",
        }
    }
    fn bits(self) -> String {
        match self {
            Self::Returned(v) => v.to_bits().to_string(),
            _ => "null".into(),
        }
    }
    fn finite(self) -> Option<f32> {
        match self {
            Self::Returned(v) if v.is_finite() => Some(v),
            _ => None,
        }
    }
}

struct Oracle {
    kind: &'static str,
    paired: Option<Observed>,
    literal: Option<f64>,
    tolerance: f64,
}
impl Oracle {
    fn literal(v: f64, tolerance: f64) -> Self {
        Self {
            kind: "literal",
            paired: None,
            literal: Some(v),
            tolerance,
        }
    }
    fn pair(v: Observed, tolerance: f64) -> Self {
        Self {
            kind: "translated-stencil",
            paired: Some(v),
            literal: None,
            tolerance,
        }
    }
    fn boolean() -> Self {
        Self {
            kind: "true",
            paired: None,
            literal: None,
            tolerance: 0.0,
        }
    }
    fn refusal() -> Self {
        Self {
            kind: "refused",
            paired: None,
            literal: None,
            tolerance: 0.0,
        }
    }
}

#[derive(Default)]
struct Journal {
    rows: usize,
    failed: usize,
    ids: BTreeSet<String>,
    groups: BTreeMap<&'static str, usize>,
}
impl Journal {
    #[allow(clippy::too_many_arguments)]
    fn row(
        &mut self,
        id: String,
        group: &'static str,
        kernel: &str,
        api: &str,
        x: f64,
        y: f64,
        actual: Observed,
        oracle: Oracle,
        exercised: bool,
        agrees: bool,
    ) {
        let unique = self.ids.insert(id.clone());
        let passed = unique && exercised && agrees;
        let ordinal = self.rows;
        self.rows += 1;
        self.failed += usize::from(!passed);
        *self.groups.entry(group).or_default() += 1;
        let paired = oracle.paired.map_or_else(|| "null".into(), Observed::bits);
        let literal = oracle
            .literal
            .map_or_else(|| "null".into(), |v| v.to_bits().to_string());
        println!(
            concat!(
                "SAMPLER_BOUNDARY_ROW {{\"ordinal\":{},\"id\":\"{}\",\"group\":\"{}\",",
                "\"kernel\":\"{}\",\"api\":\"{}\",\"x_f64_bits\":{},\"y_f64_bits\":{},",
                "\"actual_kind\":\"{}\",\"actual_f32_bits\":{},\"oracle_kind\":\"{}\",",
                "\"oracle_f32_bits\":{},\"oracle_f64_bits\":{},\"tolerance_code_units\":{},",
                "\"exercised\":{},\"passed\":{}}}"
            ),
            ordinal,
            id,
            group,
            kernel,
            api,
            x.to_bits(),
            y.to_bits(),
            actual.kind(),
            actual.bits(),
            oracle.kind,
            paired,
            literal,
            oracle.tolerance,
            exercised && unique,
            passed
        );
    }
    fn boolean(
        &mut self,
        id: &str,
        group: &'static str,
        kernel: &str,
        exercised: bool,
        passed: bool,
    ) {
        self.row(
            id.into(),
            group,
            kernel,
            "metadata-or-consumer",
            0.0,
            0.0,
            Observed::Boolean(passed),
            Oracle::boolean(),
            exercised,
            passed,
        );
    }
}

fn affine(x: f64, y: f64) -> f64 {
    1000.0 + 8.0 * x + 16.0 * y
}
fn plane(w: usize, h: usize, dx: i32, dy: i32) -> Vec<f32> {
    (0..w * h)
        .map(|i| {
            affine(
                (i % w) as f64 + f64::from(dx),
                (i / w) as f64 + f64::from(dy),
            ) as f32
        })
        .collect()
}
fn declared_covered(k: Kernel, w: usize, h: usize, x: f64, y: f64) -> bool {
    x.is_finite()
        && y.is_finite()
        && x >= k.support - 0.5
        && y >= k.support - 0.5
        && x <= w as f64 - 0.5 - k.support
        && y <= h as f64 - 0.5 - k.support
}
fn close(actual: Observed, expected: f64, tolerance: f64) -> bool {
    actual
        .finite()
        .is_some_and(|v| (f64::from(v) - expected).abs() <= tolerance)
}
fn paired_close(a: Observed, b: Observed, tolerance: f64) -> bool {
    match (a.finite(), b.finite()) {
        (Some(a), Some(b)) => (f64::from(a) - f64::from(b)).abs() <= tolerance,
        _ => false,
    }
}
fn bit_equal(a: Observed, b: Observed) -> bool {
    match (a.finite(), b.finite()) {
        (Some(a), Some(b)) => a.to_bits() == b.to_bits(),
        _ => false,
    }
}
fn observe(k: Kernel, checked: bool, data: &[f32], w: usize, h: usize, x: f64, y: f64) -> Observed {
    match catch_unwind(AssertUnwindSafe(|| {
        // Every intended view is valid; a surprising constructor failure is retained as a panic row.
        let p = PlaneRef::new(data, w, h).expect("fixed valid scalar view");
        if checked {
            k.sampler.sample_checked(p, x, y)
        } else {
            Some(k.sampler.sample(p, x, y))
        }
    })) {
        Ok(Some(v)) => Observed::Returned(v),
        Ok(None) => Observed::Refused,
        Err(_) => Observed::Panicked,
    }
}

// Literal tap-address correspondence, with no implementation weights or coordinate clamp.
fn corresponding_stencils(
    k: Kernel,
    data: &[f32],
    w: usize,
    h: usize,
    x: f64,
    y: f64,
    translated: &[f32],
    qx: f64,
    qy: f64,
) -> bool {
    let radius = if k.name == "lanczos3" { 3isize } else { 2isize };
    if x.fract() != qx.fract() || y.fract() != qy.fract() {
        return false;
    }
    let (ix, iy, qix, qiy) = (
        x.floor() as isize,
        y.floor() as isize,
        qx.floor() as isize,
        qy.floor() as isize,
    );
    for oy in (1 - radius)..=radius {
        for ox in (1 - radius)..=radius {
            let (ax, ay, bx, by) = (ix + ox, iy + oy, qix + ox, qiy + oy);
            if ax < 0
                || ay < 0
                || ax >= w as isize
                || ay >= h as isize
                || bx < 0
                || by < 0
                || bx >= W as isize
                || by >= H as isize
            {
                return false;
            }
            if data[ay as usize * w + ax as usize].to_bits()
                != translated[by as usize * W + bx as usize].to_bits()
            {
                return false;
            }
        }
    }
    true
}

#[allow(clippy::too_many_arguments)]
fn sample_row(
    j: &mut Journal,
    k: Kernel,
    group: &'static str,
    site: &str,
    checked: bool,
    data: &[f32],
    w: usize,
    h: usize,
    x: f64,
    y: f64,
    extra_guard: bool,
) {
    let actual = observe(k, checked, data, w, h, x, y);
    let api = if checked { "sample_checked" } else { "sample" };
    let id = format!("{}-{}-{}", k.name, group, site);
    if checked && !declared_covered(k, w, h, x, y) {
        j.row(
            id,
            group,
            k.name,
            api,
            x,
            y,
            actual,
            Oracle::refusal(),
            extra_guard,
            matches!(actual, Observed::Refused),
        );
        return;
    }
    let (rx, ry) = if checked {
        (x, y)
    } else {
        // Fixed extension semantics from legal sample centres, not the repair's base-index algorithm.
        let low = (k.support - 1.0).max(0.0);
        let (ex, ey) = if k.name == "nearest" {
            ((w - 1) as f64, (h - 1) as f64)
        } else {
            (w as f64 - k.support, h as f64 - k.support)
        };
        (x.clamp(low, ex), y.clamp(low, ey))
    };
    if k.name == "nearest" {
        let expected = affine((rx + 0.5).floor(), (ry + 0.5).floor());
        j.row(
            id,
            group,
            k.name,
            api,
            x,
            y,
            actual,
            Oracle::literal(expected, 0.0),
            extra_guard,
            close(actual, expected, 0.0),
        );
    } else if !k.lanczos || (rx.fract() == 0.0 && ry.fract() == 0.0) {
        let expected = affine(rx, ry);
        j.row(
            id,
            group,
            k.name,
            api,
            x,
            y,
            actual,
            Oracle::literal(expected, TOL),
            extra_guard,
            close(actual, expected, TOL),
        );
    } else {
        let (qx, qy) = (20.0 + rx.fract(), 20.0 + ry.fract());
        let translated = plane(W, H, rx.floor() as i32 - 20, ry.floor() as i32 - 20);
        let other = observe(k, true, &translated, W, H, qx, qy);
        let guard = extra_guard
            && declared_covered(k, W, H, qx, qy)
            && corresponding_stencils(k, data, w, h, rx, ry, &translated, qx, qy);
        j.row(
            id,
            group,
            k.name,
            api,
            x,
            y,
            actual,
            Oracle::pair(other, TOL),
            guard,
            paired_close(actual, other, TOL),
        );
    }
}

fn ordinary_rows(j: &mut Journal, k: Kernel, data: &[f32]) {
    j.boolean(
        &format!("{}-support-literal", k.name),
        "support",
        k.name,
        true,
        k.sampler.support() == k.support,
    );
    let lo = k.support - 0.5;
    let (hx, hy) = (W as f64 - 0.5 - k.support, H as f64 - 0.5 - k.support);
    let (ux, uy) = if k.name == "nearest" {
        ((W - 2) as f64, (H - 2) as f64)
    } else {
        (W as f64 - k.support - 1.0, H as f64 - k.support - 1.0)
    };
    let (lastx, lasty) = if k.name == "nearest" {
        ((W - 1) as f64, (H - 1) as f64)
    } else {
        (ux, uy)
    };
    let sites = [
        ("low-corner", lo, lo),
        ("low-x", lo, 20.25),
        ("low-y", 20.25, lo),
        ("interior-quarter", 20.25, 20.25),
        ("interior-half", 20.5, 20.5),
        ("last-integer", lastx, lasty),
        ("high-x-quarter", ux + 0.25, 20.25),
        ("high-x-half", ux + 0.5, 20.25),
        ("high-y-quarter", 20.25, uy + 0.25),
        ("high-y-half", 20.25, uy + 0.5),
        ("high-corner-quarter", ux + 0.25, uy + 0.25),
        ("high-corner-half", ux + 0.5, uy + 0.5),
        ("exact-upper-corner", hx, hy),
        ("just-low-x", lo - 0.25, 20.25),
        ("just-low-y", 20.25, lo - 0.25),
        ("just-high-x", hx + 0.25, 20.25),
        ("just-high-y", 20.25, hy + 0.25),
        ("distant-low-x", -50.0, 20.25),
        ("distant-low-y", 20.25, -50.0),
        ("distant-high-x", W as f64 + 50.0, 20.25),
        ("distant-high-y", 20.25, H as f64 + 50.0),
    ];
    for (site, x, y) in sites {
        let high_guard = !site.starts_with("high-")
            || k.name == "nearest"
            || (declared_covered(k, W, H, x, y) && (x > ux || y > uy));
        sample_row(j, k, "boundary", site, true, data, W, H, x, y, high_guard);
    }
    let null = vec![-4321.25f32; W * H];
    for (site, x, y) in [
        ("low", lo, lo),
        ("interior", 20.25, 20.25),
        ("upper", hx, hy),
    ] {
        let got = observe(k, true, &null, W, H, x, y);
        let tolerance = if k.lanczos { TOL } else { 0.0 };
        j.row(
            format!("{}-null-{}", k.name, site),
            "null",
            k.name,
            "sample_checked",
            x,
            y,
            got,
            Oracle::literal(-4321.25, tolerance),
            declared_covered(k, W, H, x, y),
            close(got, -4321.25, tolerance),
        );
    }
    for (kind, value) in [
        ("nan", f64::NAN),
        ("positive-infinity", f64::INFINITY),
        ("negative-infinity", f64::NEG_INFINITY),
    ] {
        for (axis, x, y) in [("x", value, 20.25), ("y", 20.25, value)] {
            sample_row(
                j,
                k,
                "nonfinite",
                &format!("{}-{}", kind, axis),
                true,
                data,
                W,
                H,
                x,
                y,
                !value.is_finite(),
            );
        }
    }
    for (w, h) in [
        (1, 1),
        (1, 7),
        (7, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
        (6, 6),
    ] {
        let tiny = plane(w, h, 0, 0);
        sample_row(
            j,
            k,
            "tiny",
            &format!("{}x{}", w, h),
            true,
            &tiny,
            w,
            h,
            (w - 1) as f64 * 0.5,
            (h - 1) as f64 * 0.5,
            true,
        );
    }
    let (ex, ey) = if k.name == "nearest" {
        ((W - 1) as f64, (H - 1) as f64)
    } else {
        (W as f64 - k.support, H as f64 - k.support)
    };
    for (site, x, y) in [
        ("high-x-quarter", ex - 0.75, 20.25),
        ("high-y-quarter", 20.25, ey - 0.75),
        ("endpoint-x", ex, 20.0),
        ("endpoint-y", 20.0, ey),
        ("endpoint-corner", ex, ey),
        ("far-high-x", W as f64 + 50.0, 20.0),
        ("far-high-y", 20.0, H as f64 + 50.0),
        ("far-high-corner", W as f64 + 50.0, H as f64 + 50.0),
        ("far-low-corner", -50.0, -50.0),
        ("interior-quarter", 20.25, 20.25),
    ] {
        sample_row(j, k, "unchecked", site, false, data, W, H, x, y, true);
    }
}

// Independently fixed reached-fallback cases. The final field names the effective
// public contract (0=Nearest, 1=Bilinear, 2=CatmullRom), not a call used as oracle.
fn unchecked_tiny_rows(j: &mut Journal) {
    const CASES: [(usize, usize, usize, usize); 20] = [
        (1, 1, 7, 0),
        (1, 7, 1, 0),
        (2, 1, 7, 0),
        (2, 7, 1, 0),
        (2, 2, 7, 1),
        (2, 7, 2, 1),
        (3, 1, 7, 0),
        (3, 7, 1, 0),
        (3, 2, 7, 1),
        (3, 7, 2, 1),
        (4, 1, 7, 0),
        (4, 7, 1, 0),
        (4, 2, 7, 1),
        (4, 7, 2, 1),
        (5, 1, 7, 0),
        (5, 7, 1, 0),
        (5, 2, 7, 1),
        (5, 7, 2, 1),
        (5, 4, 7, 2),
        (5, 7, 4, 2),
    ];
    for (index, w, h, effective) in CASES {
        let k = KERNELS[index];
        let data = plane(w, h, 0, 0);
        let (ex, ey, old) = match effective {
            0 => ((w - 1) as f64, (h - 1) as f64, None),
            1 => (
                (w - 1) as f64,
                (h - 1) as f64,
                Some(affine((w - 2) as f64, (h - 2) as f64)),
            ),
            2 => (
                (w - 2) as f64,
                (h - 2) as f64,
                Some(affine((w - 3) as f64, (h - 3) as f64)),
            ),
            _ => unreachable!("closed literal effective-kernel table"),
        };
        let expected = affine(ex, ey);
        let (x, y) = (w as f64 + 50.0, h as f64 + 50.0);
        let endpoint = observe(k, false, &data, w, h, ex, ey);
        let outside = observe(k, false, &data, w, h, x, y);
        let tolerance = if effective == 0 { 0.0 } else { TOL };
        let minimum = [1usize, 2, 4, 4, 4, 6][index];
        let guard = (w < minimum || h < minimum)
            && ex.fract() == 0.0
            && ey.fract() == 0.0
            && ex >= 0.0
            && ex < w as f64
            && ey >= 0.0
            && ey < h as f64
            && x > ex
            && y > ey
            && endpoint.finite().is_some()
            && outside.finite().is_some()
            && old.is_none_or(|v| (expected - v).abs() > DIFFERENT);
        let old_rejected = old.is_none_or(|old| {
            [endpoint, outside].into_iter().all(|v| {
                v.finite()
                    .is_some_and(|v| (f64::from(v) - old).abs() > DIFFERENT)
            })
        });
        j.row(
            format!("{}-unchecked-tiny-{}x{}", k.name, w, h),
            "unchecked-tiny",
            k.name,
            "sample-endpoint-and-far-high",
            x,
            y,
            outside,
            Oracle {
                kind: "effective-fallback-endpoint",
                paired: Some(endpoint),
                literal: Some(expected),
                tolerance,
            },
            guard,
            close(endpoint, expected, tolerance)
                && close(outside, expected, tolerance)
                && bit_equal(endpoint, outside)
                && old_rejected,
        );
    }
}

fn lanczos_commission(j: &mut Journal, k: Kernel, data: &[f32]) {
    for phase in [0.25, 0.5] {
        for (axis, dx, dy) in [("x", 7, 0), ("y", 0, 5), ("corner", 7, 5)] {
            let (x, y) = (20.0 + f64::from(dx) + phase, 20.0 + f64::from(dy) + phase);
            let translated = plane(W, H, dx, dy);
            let a = observe(k, true, data, W, H, x, y);
            let b = observe(k, true, &translated, W, H, 20.0 + phase, 20.0 + phase);
            let guard = corresponding_stencils(
                k,
                data,
                W,
                H,
                x,
                y,
                &translated,
                20.0 + phase,
                20.0 + phase,
            ) && (dx != 0 || dy != 0);
            j.row(
                format!(
                    "{}-lanczos-commission-{}-{}",
                    k.name,
                    axis,
                    if phase == 0.25 { "quarter" } else { "half" }
                ),
                "lanczos-commission",
                k.name,
                "sample_checked-pair",
                x,
                y,
                a,
                Oracle::pair(b, TOL),
                guard,
                paired_close(a, b, TOL),
            );
        }
    }
    let translated = plane(W, H, 7, 5);
    let wrong = plane(W, H, 8, 5);
    let a = observe(k, true, data, W, H, 27.25, 25.25);
    let wrong_translation = observe(k, true, &wrong, W, H, 20.25, 20.25);
    let changed = translated
        .iter()
        .zip(&wrong)
        .filter(|(a, b)| a.to_bits() != b.to_bits())
        .count();
    let guard = changed == W * H
        && !corresponding_stencils(k, data, W, H, 27.25, 25.25, &wrong, 20.25, 20.25);
    let differs = match (a.finite(), wrong_translation.finite()) {
        (Some(a), Some(b)) => (f64::from(a) - f64::from(b)).abs() > DIFFERENT,
        _ => false,
    };
    j.row(
        format!("{}-lanczos-commission-wrong-translation", k.name),
        "lanczos-commission",
        k.name,
        "sample_checked-destroyer",
        20.25,
        20.25,
        wrong_translation,
        Oracle {
            kind: "must-differ",
            paired: Some(a),
            literal: Some(changed as f64),
            tolerance: DIFFERENT,
        },
        guard,
        differs,
    );
    let wrong_phase = observe(k, true, &translated, W, H, 20.5, 20.25);
    let differs = match (a.finite(), wrong_phase.finite()) {
        (Some(a), Some(b)) => (f64::from(a) - f64::from(b)).abs() > DIFFERENT,
        _ => false,
    };
    j.row(
        format!("{}-lanczos-commission-wrong-phase", k.name),
        "lanczos-commission",
        k.name,
        "sample_checked-destroyer",
        20.5,
        20.25,
        wrong_phase,
        Oracle {
            kind: "must-differ",
            paired: Some(a),
            literal: None,
            tolerance: DIFFERENT,
        },
        !corresponding_stencils(k, data, W, H, 27.25, 25.25, &translated, 20.5, 20.25),
        differs,
    );
    let restored = observe(k, true, &translated, W, H, 20.25, 20.25);
    j.row(
        format!("{}-lanczos-commission-restored", k.name),
        "lanczos-commission",
        k.name,
        "sample_checked-pair",
        20.25,
        20.25,
        restored,
        Oracle::pair(a, TOL),
        corresponding_stencils(k, data, W, H, 27.25, 25.25, &translated, 20.25, 20.25),
        paired_close(restored, a, TOL),
    );
}

fn cubic_limiter_rows(j: &mut Journal, data: &[f32]) {
    let raw_kernel = KERNELS[2];
    let limited = KERNELS[3];
    let step: Vec<f32> = (0..W * H)
        .map(|i| if i % W < 64 { 0.0 } else { 100.0 })
        .collect();
    for (site, x, expected, which) in [
        ("below", 62.5, 0.0, -1),
        ("inside", 63.5, 50.0, 0),
        ("above", 64.5, 100.0, 1),
    ] {
        let y = 20.25;
        let raw = observe(raw_kernel, true, &step, W, H, x, y);
        let got = observe(limited, true, &step, W, H, x, y);
        let (lo, hi) = support16(&step, x, y);
        let guard = match raw.finite() {
            Some(v) => match which {
                -1 => v < lo,
                0 => v >= lo && v <= hi,
                _ => v > hi,
            },
            None => false,
        };
        let same = which != 0 || bit_equal(raw, got);
        let agrees =
            close(got, expected, 0.0) && same && got.finite().is_some_and(|v| v >= lo && v <= hi);
        j.row(
            format!("clamped-catmull-rom-cubic-limiter-{}", site),
            "cubic-limiter",
            limited.name,
            "sample_checked-raw-and-limited",
            x,
            y,
            got,
            Oracle {
                kind: "literal-support-hull",
                paired: Some(raw),
                literal: Some(expected),
                tolerance: 0.0,
            },
            guard,
            agrees,
        );
    }
    for (site, x, y) in [
        ("affine-low", 1.5, 1.5),
        ("affine-interior", 20.25, 20.5),
        ("affine-upper", 125.5, 93.5),
    ] {
        let raw = observe(raw_kernel, true, data, W, H, x, y);
        let got = observe(limited, true, data, W, H, x, y);
        let (lo, hi) = support16(data, x, y);
        j.row(
            format!("clamped-catmull-rom-cubic-limiter-{}", site),
            "cubic-limiter",
            limited.name,
            "sample_checked-raw-and-limited",
            x,
            y,
            got,
            Oracle {
                kind: "in-hull-bit-identity",
                paired: Some(raw),
                literal: None,
                tolerance: 0.0,
            },
            raw.finite().is_some_and(|v| v >= lo && v <= hi),
            bit_equal(raw, got),
        );
    }
}
fn support16(data: &[f32], x: f64, y: f64) -> (f32, f32) {
    let mut lo = f32::INFINITY;
    let mut hi = f32::NEG_INFINITY;
    let (ix, iy) = (x.floor() as usize, y.floor() as usize);
    for oy in 0..4 {
        for ox in 0..4 {
            let v = data[(iy + oy - 1) * W + ix + ox - 1];
            lo = lo.min(v);
            hi = hi.max(v);
        }
    }
    (lo, hi)
}
fn mask_hex(mask: &[bool]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    mask.chunks(4)
        .map(|chunk| {
            let n = chunk
                .iter()
                .enumerate()
                .fold(0usize, |n, (i, b)| n | (usize::from(*b) << i));
            char::from(HEX[n])
        })
        .collect()
}
fn value_hex(values: &[f32]) -> String {
    let mut s = String::with_capacity(values.len() * 8);
    for value in values {
        let _ = write!(s, "{:08x}", value.to_bits());
    }
    s
}
fn gather_rows(j: &mut Journal, data: &[f32]) -> String {
    let mut dst = vec![8675.5f32; W * H];
    let mut cover = vec![true; W * H];
    let t = Similarity {
        a: Cx::ONE,
        b: Cx::new(0.25, 0.25),
    };
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        let src = PlaneRef::new(data, W, H).expect("fixed valid gather view");
        gather_checked(
            src,
            t,
            PlaneGeometry {
                width: W,
                height: H,
            },
            Resampler::Bilinear,
            &mut dst,
            &mut cover,
        )
    }));
    let (state, count) = match outcome {
        Ok(Ok(n)) => ("ok", Some(n)),
        Ok(Err(_)) => ("error", None),
        Err(_) => ("panic", None),
    };
    let mut expected = Vec::with_capacity(W * H);
    let mut mask_bad = 0usize;
    let mut values_bad = 0usize;
    let mut nan_bad = 0usize;
    let mut wrong_mask = 0usize;
    let mut wrong_values = 0usize;
    let mut reference_mask_equal = true;
    let mut worst = 0.0f64;
    for y in 0..H {
        for x in 0..W {
            let i = y * W + x;
            let sx = x as f64 + 0.25;
            let sy = y as f64 + 0.25;
            // Independently enumerated reference-to-source map and Bilinear declared domain.
            let valid = sx >= 0.5 && sx <= 126.5 && sy >= 0.5 && sy <= 94.5;
            expected.push(valid);
            mask_bad += usize::from(cover[i] != valid);
            if valid {
                let error = (f64::from(dst[i]) - affine(sx, sy)).abs();
                values_bad += usize::from(!dst[i].is_finite() || error > TOL);
                if error.is_finite() {
                    worst = worst.max(error);
                }
            } else {
                nan_bad += usize::from(!dst[i].is_nan());
            }
            let wx = x as f64 - 0.25;
            let wy = y as f64 - 0.25;
            let wvalid = wx >= 0.5 && wx <= 126.5 && wy >= 0.5 && wy <= 94.5;
            reference_mask_equal &= valid == wvalid;
            wrong_mask += usize::from(cover[i] != wvalid);
            if wvalid {
                wrong_values += usize::from(
                    !dst[i].is_finite() || (f64::from(dst[i]) - affine(wx, wy)).abs() > TOL,
                );
            }
        }
    }
    let expected_count = expected.iter().filter(|&&v| v).count();
    let observed_count = cover.iter().filter(|&&v| v).count();
    let exercised = expected_count == 11844
        && W * H - expected_count == 444
        && data[1] - data[0] == 8.0
        && data[W] - data[0] == 16.0;
    let good = state == "ok"
        && count == Some(expected_count)
        && observed_count == expected_count
        && mask_bad == 0
        && values_bad == 0
        && nan_bad == 0;
    j.boolean(
        "bilinear-gather-requested-map",
        "gather",
        "bilinear",
        exercised,
        good,
    );
    j.boolean(
        "bilinear-gather-opposite-direction-rejected",
        "gather",
        "bilinear",
        exercised
            && reference_mask_equal
            && state == "ok"
            && count == Some(expected_count)
            && observed_count == expected_count
            && mask_bad == 0
            && nan_bad == 0,
        wrong_values > 0 || wrong_mask > 0,
    );
    let count_text = count.map_or_else(|| "null".into(), |n| n.to_string());
    format!(
        concat!(
            "SAMPLER_BOUNDARY_GATHER {{\"schema\":\"sampler-boundary-gather-v1\",\"width\":128,\"height\":96,",
            "\"map\":\"source=(reference.x+0.25,reference.y+0.25)\",\"sampler\":\"bilinear\",",
            "\"status\":\"{}\",\"returned_count\":{},\"expected_count\":{},\"observed_count\":{},",
            "\"mask_mismatches\":{},\"value_mismatches\":{},\"refusal_nan_mismatches\":{},",
            "\"wrong_direction_mask_mismatches\":{},\"wrong_direction_value_mismatches\":{},\"max_abs_error\":{},",
            "\"mask_nibble_lsb_first_hex\":\"{}\",\"expected_mask_nibble_lsb_first_hex\":\"{}\",",
            "\"row_major_f32_bits_hex\":\"{}\"}}"
        ),
        state,
        count_text,
        expected_count,
        observed_count,
        mask_bad,
        values_bad,
        nan_bad,
        wrong_mask,
        wrong_values,
        worst,
        mask_hex(&cover),
        mask_hex(&expected),
        value_hex(&dst)
    )
}

#[test]
fn sampler_boundary_public_contract() {
    println!(
        "\nSAMPLER_BOUNDARY_BEGIN {{\"schema\":\"sampler-boundary-begin-v1\",\"expected_rows\":344,\"width\":128,\"height\":96,\"gauge\":\"integer sample centres; scalar plane sample pitch\"}}"
    );
    let mut j = Journal::default();
    let data = plane(W, H, 0, 0);
    for kernel in KERNELS {
        ordinary_rows(&mut j, kernel, &data);
    }
    unchecked_tiny_rows(&mut j);
    for (name, w, h, len) in [
        ("empty-both", 0, 0, 0),
        ("empty-width", 0, 1, 0),
        ("empty-height", 1, 0, 0),
        ("short-data", W, H, W * H - 1),
    ] {
        let values = vec![0.0f32; len];
        j.boolean(
            &format!("plane-constructor-{}", name),
            "constructor",
            "none",
            w == 0 || h == 0 || len != w * h,
            PlaneRef::new(&values, w, h).is_none(),
        );
    }
    for kernel in [KERNELS[4], KERNELS[5]] {
        lanczos_commission(&mut j, kernel, &data);
    }
    cubic_limiter_rows(&mut j, &data);
    let gather_record = gather_rows(&mut j, &data);
    println!("{}", gather_record);
    let population = j.rows == EXPECTED_ROWS
        && j.ids.len() == EXPECTED_ROWS
        && j.groups.len() == GROUPS.len()
        && GROUPS.iter().all(|(name, n)| j.groups.get(name) == Some(n));
    let groups = GROUPS
        .iter()
        .map(|(name, _)| format!("\"{}\":{}", name, j.groups.get(name).copied().unwrap_or(0)))
        .collect::<Vec<_>>()
        .join(",");
    println!(
        "SAMPLER_BOUNDARY_SUMMARY {{\"schema\":\"sampler-boundary-summary-v1\",\"rows\":{},\"failed\":{},\"passed\":{},\"population_complete\":{},\"groups\":{{{}}}}}",
        j.rows,
        j.failed,
        j.rows - j.failed,
        population,
        groups
    );
    // This is the only aggregate assertion; every fixed row and full gather operands precede it.
    assert!(
        population && j.failed == 0,
        "fixed sampler boundary contract: {} failed of {} rows; full transcript retained",
        j.failed,
        j.rows
    );
}
