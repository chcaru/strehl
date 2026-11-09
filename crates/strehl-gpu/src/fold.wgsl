// The default pyramid fold, one frame at a time, bit-identical to
// strehl_core::pyramid::BandMerge::add_frame_with_gain on its default route.
//
// Every expression mirrors its CPU counterpart operand for operand; the host
// decorates every float arithmetic result NoContraction, so no multiply-add is
// fused. f32 division goes through f64 (exact on the measured device; native
// f32 division was not). ln/exp are crate::portable_math, with their f64
// constants supplied in `consts`, not written as literals.

struct P {
    a: vec4<u32>,
    b: vec4<u32>,
    c: vec4<u32>,
    d: vec4<u32>,
    e: vec4<u32>,
    f: vec4<f32>,
    g: vec4<f32>,
}

@group(0) @binding(0) var<uniform> p: P;
@group(0) @binding(1) var<storage, read_write> work: array<f32>;
@group(0) @binding(2) var<storage, read_write> acc: array<f32>;
@group(0) @binding(3) var<storage, read> consts: array<f64>;
// Raw u16 CFA frames, two samples per word, low half first. Slot 1 (the
// probe) is written on the device by `noise`.
@group(0) @binding(4) var<storage, read_write> raw: array<u32>;
// Per-site pulls, 8 f64 each: a.re, a.im, b.re, b.im, ox, oy, cx, cy.
@group(0) @binding(5) var<storage, read> xf: array<f64>;
// f64 partial sums.
@group(0) @binding(6) var<storage, read_write> red: array<f64>;

// consts layout: [0..12) LN_SERIES, [12..27) EXP_SERIES, 27 LN2, 28 INV_LN2, 29 SQRT2,
// [30..45) LN64_SERIES, [45..56) SIN_SERIES, [56..67) COS_SERIES, 67 PIO2_HI,
// 68 PIO2_LO, 69 PIO2_HI + PIO2_LO, 70 TAU, 71 LN_UNIFORM_FLOOR, 72 2^-24,
// [73..) the f32 screen's constants, each an f32 widened exactly (C_F32 + F_*).
const C_LN: u32 = 0u;
const C_EXP: u32 = 12u;
const C_LN2: u32 = 27u;
const C_INV_LN2: u32 = 28u;
const C_SQRT2: u32 = 29u;
const C_LN64: u32 = 30u;
const C_SIN: u32 = 45u;
const C_COS: u32 = 56u;
const C_PIO2_HI: u32 = 67u;
const C_PIO2_LO: u32 = 68u;
const C_PIO2: u32 = 69u;
const C_TAU: u32 = 70u;
const C_LN_FLOOR: u32 = 71u;
const C_INV_2_24: u32 = 72u;
const C_F32: u32 = 73u;
const F_SQRT2: u32 = 0u;
const F_LN2: u32 = 1u;
const F_LN_FLOOR: u32 = 2u;
const F_T3: u32 = 3u;
const F_T5: u32 = 4u;
const F_T7: u32 = 5u;
const F_T9: u32 = 6u;
const F_T11: u32 = 7u;
const F_XSCALE: u32 = 8u;
const F_S3: u32 = 9u;
const F_S5: u32 = 10u;
const F_S7: u32 = 11u;
const F_S9: u32 = 12u;
const F_C2: u32 = 13u;
const F_C4: u32 = 14u;
const F_C6: u32 = 15u;
const F_C8: u32 = 16u;
const F_C10: u32 = 17u;

const K0: f32 = 0.0625;
const K1: f32 = 0.25;
const K2: f32 = 0.375;

fn kern(t: u32) -> f32 {
    switch t {
        case 0u, 4u: { return K0; }
        case 1u, 3u: { return K1; }
        default: { return K2; }
    }
}


fn clampi(i: i32, n: u32) -> u32 {
    return u32(clamp(i, 0, i32(n) - 1));
}

fn div(a: f32, b: f32) -> f32 {
    return f32(f64(a) / f64(b));
}

fn inf_pos() -> f32 { return bitcast<f32>(0x7f800000u); }
fn inf_neg() -> f32 { return bitcast<f32>(0xff800000u); }

fn pow2(k: i32) -> f64 {
    return f64(bitcast<f32>(u32(k + 127) << 23u));
}

// crate::portable_math::ln for x >= 0 (the fold never passes NaN or < 0).
fn pln(x: f32) -> f32 {
    if (x == 0.0) { return inf_neg(); }
    if (x == inf_pos()) { return inf_pos(); }
    return f32(pln64(x));
}

// portable_math::ln's f64 value before its rounding to f32, for a finite x > 0.
fn pln64(x: f32) -> f64 {
    var bits = bitcast<u32>(x);
    var e = i32((bits >> 23u) & 0xffu);
    if (e == 0) {
        bits = bitcast<u32>(x * 16777216.0);
        e = i32((bits >> 23u) & 0xffu) - 24;
    }
    var m = f64(bitcast<f32>((bits & 0x007fffffu) | 0x3f800000u));
    e = e - 127;
    if (m > consts[C_SQRT2]) {
        m = m * f64(0.5);
        e = e + 1;
    }
    let s = (m - f64(1.0)) / (m + f64(1.0));
    let s2 = s * s;
    var q = consts[C_LN + 11u];
    for (var k = 11u; k > 0u; k = k - 1u) {
        q = q * s2 + consts[C_LN + k - 1u];
    }
    let lnm = f64(2.0) * s * q;
    return f64(e) * consts[C_LN2] + lnm;
}

// crate::portable_math::exp for a finite x.
fn pexp(x: f32) -> f32 {
    if (x > 89.0) { return inf_pos(); }
    if (x < -104.0) { return 0.0; }
    return f32(pexp64(x));
}

// portable_math::exp's f64 value before its rounding to f32, for x in [-104, 89].
fn pexp64(x: f32) -> f64 {
    let xd = f64(x);
    let k = floor(xd * consts[C_INV_LN2] + f64(0.5));
    let r = xd - k * consts[C_LN2];
    var q = consts[C_EXP + 14u];
    for (var n = 14u; n > 0u; n = n - 1u) {
        q = q * r + consts[C_EXP + n - 1u];
    }
    let ki = i32(k);
    let k1 = ki / 2;
    return q * pow2(k1) * pow2(ki - k1);
}

// ---------------------------------------------------------------------------
// f32 screens for the weight's ln and exp. f64 is slow on most GPUs (1/64 of
// f32 on this one), and these two f64 evaluations were about two thirds of
// the level kernel. Each screen computes the result as an unevaluated f32 sum
// hi + lo (double-float, error-free transformations only: no fma, so the
// module stays free of fused arithmetic) with error far below f32 rounding,
// and returns hi when hi + lo is farther than a bound from every f32 rounding
// boundary: then the f64 value rounds to hi too. Otherwise the caller uses the
// f64 function. Exactness is not argued from the bound alone: `screen_census`
// runs every input either can receive on this device against the f64 function
// (tests/screen-census.rs) and must find no accepted value that differs.
// ---------------------------------------------------------------------------

// Tables in `work` at offset 0 (`weight_screen_tables`): ln's 128 entries of
// (r, -ln r hi, lo), then exp's 64 entries of (2^(j/64) hi, lo).
const TAB_LN: u32 = 0u;
const TAB_EXP: u32 = 384u;
// Each screen's error bound on hi + lo: a relative part for the table, the
// reduction and the summation, and a part proportional to the polynomial tail,
// which is evaluated in plain f32 (2^-24 relative). The census checks that the
// measured error is at most half the bound at every input.
const BOUND_REL: f32 = 0x1p-36f;
const BOUND_TAIL: f32 = 0x1p-21f;

struct Screen { v: f32, ok: bool }

fn two_sum(a: f32, b: f32) -> vec2<f32> {
    let s = a + b;
    let bb = s - a;
    return vec2(s, (a - (s - bb)) + (b - bb));
}

// |a| >= |b|, or a == 0.
fn fast_two_sum(a: f32, b: f32) -> vec2<f32> {
    let s = a + b;
    return vec2(s, b - (s - a));
}

// Dekker's exact product, a * b = p + e, for |a|, |b| far from overflow.
fn split(a: f32) -> vec2<f32> {
    let c = 4097.0 * a;
    let h = c - (c - a);
    return vec2(h, a - h);
}

fn two_prod(a: f32, b: f32) -> vec2<f32> {
    let p = a * b;
    let sa = split(a);
    let sb = split(b);
    let e = ((sa.x * sb.x - p) + sa.x * sb.y + sa.y * sb.x) + sa.y * sb.y;
    return vec2(p, e);
}

// Whether every value within `bound` of hi + lo (hi = fl(hi + lo)) rounds to
// hi in f32.
fn rounds_to_hi(hi: f32, lo: f32, bound: f32) -> bool {
    let bits = bitcast<u32>(hi);
    let e = (bits >> 23u) & 0xffu;
    if (e <= 25u || e == 255u) { return false; }
    // Half an ulp of hi, or a quarter toward zero from a power of two.
    var half = bitcast<f32>((e - 24u) << 23u);
    if ((bits & 0x007fffffu) == 0u && lo != 0.0 && (bitcast<u32>(lo) >> 31u) != (bits >> 31u)) {
        half = half * 0.5;
    }
    return abs(lo) + bound < half;
}

// ln(x) as hi + lo, and the error bound, for a normal x > 0.
fn ln_df(x: f32) -> vec3<f32> {
    let bits = bitcast<u32>(x);
    let j = (bits >> 16u) & 0x7fu;
    let m = bitcast<f32>((bits & 0x007fffffu) | 0x3f800000u);
    // x = 2^e m, m in [1, 2); the upper half of the table is stored as
    // ln(m) - ln 2 with e + 1, so a value near 1 from below does not cancel.
    let e = f32(i32((bits >> 23u) & 0xffu) - 127 + select(0, 1, j >= 64u));
    let r = work[TAB_LN + 3u * j];
    // t = m r - 1, exactly: th + tl.
    let pr = two_prod(m, r);
    let th = pr.x - 1.0;
    let tl = pr.y;
    // ln(1 + t) - th = th^2 (-1/2 + th/3 - ...) + tl / (1 + th).
    let t2 = th * th;
    let tail = t2 * (-0.5 + th * (0.33333334 + th * (-0.25 + th * (0.2 + th * (-0.16666667 + th * 0.14285715)))))
        + tl * ((1.0 - th) + t2);
    // e ln2 + (-ln r) + th, then the small terms.
    let a = two_sum(e * bitcast<f32>(0x3f317200u), work[TAB_LN + 3u * j + 1u]);
    let b = two_sum(a.x, th);
    let low = (((a.y + b.y) + e * bitcast<f32>(0x35bfbe8eu)) + work[TAB_LN + 3u * j + 2u]) + tail;
    let y = fast_two_sum(b.x, low);
    return vec3(y, abs(y.x) * BOUND_REL + abs(tail) * BOUND_TAIL);
}

fn ln_screen(x: f32) -> Screen {
    let be = (bitcast<u32>(x) >> 23u) & 0xffu;
    if (be == 0u || be == 255u) { return Screen(0.0, false); }
    let y = ln_df(x);
    return Screen(y.x, rounds_to_hi(y.x, y.y, y.z));
}

// exp(x) / 2^k as hi + lo near [1, 2) with its error bound, and k, for x in
// [-80, 80].
struct ExpDf { y: vec3<f32>, k: i32 }

fn exp_df(x: f32) -> ExpDf {
    // n = round(x 64 / ln2); r = x - n ln2/64, ln2/64 = C1 + C2 + C3 with
    // C1 and C2 of 11 bits, so n C1 and n C2 are exact (|n| < 2^13).
    let nf = floor(x * bitcast<f32>(0x42b8aa3bu) + 0.5);
    let r1 = x - nf * bitcast<f32>(0x3c318000u);
    let s = two_sum(r1, -(nf * bitcast<f32>(0xb65e8000u)));
    let rr = fast_two_sum(s.x, s.y - nf * bitcast<f32>(0xae02e308u));
    let rh = rr.x;
    // e^r - 1 - rh = rh^2 (1/2 + rh/6 + ...) + rl (1 + rh).
    let r2 = rh * rh;
    let tail = r2 * (0.5 + rh * (0.16666667 + rh * (0.041666668 + rh * 0.008333334)))
        + rr.y * (1.0 + rh);
    let n = i32(nf);
    let j = u32(n & 63);
    let th = work[TAB_EXP + 2u * j];
    let tl = work[TAB_EXP + 2u * j + 1u];
    // T (1 + p), p = rh + tail: th + th rh + (th tail + tl (1 + rh)).
    let a = two_prod(th, rh);
    let b = two_sum(th, a.x);
    let low = ((b.y + a.y) + th * tail) + tl * (1.0 + rh);
    let y = fast_two_sum(b.x, low);
    return ExpDf(vec3(y, abs(y.x) * BOUND_REL + abs(th * tail) * BOUND_TAIL), n >> 6u);
}

fn exp_screen(x: f32) -> Screen {
    let d = exp_df(x);
    if (!rounds_to_hi(d.y.x, d.y.y, d.y.z)) { return Screen(0.0, false); }
    // Exact: the result is a normal f32 for x in [-80, 80].
    return Screen(d.y.x * bitcast<f32>(u32(d.k + 127) << 23u), true);
}

// Rust f32::clamp(-80, 80) for a non-NaN value.
fn clamp80(x: f32) -> f32 {
    if (x < -80.0) { return -80.0; }
    if (x > 80.0) { return 80.0; }
    return x;
}

// select_weight with r_floor == 0. ln and exp through their screens, falling
// back to the f64 functions where a screen cannot decide.
fn select_weight(excess: f32, floor_: f32, pw: f32) -> f32 {
    if (excess <= 0.0) { return 0.0; }
    let r = div(div(excess, max(floor_, 1.0)), 64.0);
    if (pw == 1.0) { return r; }
    if (pw == 2.0) { return r * r; }
    let ls = ln_screen(r);
    var l: f32;
    if (ls.ok) { l = ls.v; } else { l = pln(r); }
    let z = clamp80(pw * l);
    let es = exp_screen(z);
    if (es.ok) { return es.v; }
    return pexp(z);
}
fn gid(id: vec3<u32>, nwg: vec3<u32>) -> u32 {
    return id.x + id.y * nwg.x * 256u;
}

// a = (dst, n, value_bits, arena: 0 work / 1 acc)
@compute @workgroup_size(256)
fn fill(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.y) { return; }
    let v = bitcast<f32>(p.a.z);
    if (p.a.w == 0u) { work[p.a.x + i] = v; } else { acc[p.a.x + i] = v; }
}

// a = (g1, g2, dst, n): luma = 0.5 * (g1 + g2)
@compute @workgroup_size(256)
fn luma(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.w) { return; }
    work[p.a.z + i] = 0.5 * (work[p.a.x + i] + work[p.a.y + i]);
}

// a = (plane, lo, hi, n)
@compute @workgroup_size(256)
fn hull(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.w) { return; }
    let v = work[p.a.x + i];
    acc[p.a.y + i] = min(acc[p.a.y + i], v);
    acc[p.a.z + i] = max(acc[p.a.z + i], v);
}

// reduce, horizontal: a = (src, sw, sh, scratch), b.x = dw. Over dw x sh.
@compute @workgroup_size(256)
fn reduce_h(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let dw = p.b.x; let sw = p.a.y;
    if (i >= dw * p.a.z) { return; }
    let x = i % dw; let y = i / dw;
    let c = i32(2u * x);
    var s = 0.0;
    for (var t = 0u; t < 5u; t = t + 1u) {
        s = s + kern(t) * work[p.a.x + y * sw + clampi(c + i32(t) - 2, sw)];
    }
    work[p.a.w + i] = s;
}

// reduce, vertical: a = (scratch, dw, sh, dst), b.x = dh. Over dw x dh.
@compute @workgroup_size(256)
fn reduce_v(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let dw = p.a.y; let sh = p.a.z;
    if (i >= dw * p.b.x) { return; }
    let x = i % dw; let y = i / dw;
    let c = i32(2u * y);
    var o = 0.0;
    for (var t = 0u; t < 5u; t = t + 1u) {
        o = o + kern(t) * work[p.a.x + clampi(c + i32(t) - 2, sh) * dw + x];
    }
    work[p.a.w + i] = o;
}

fn expand_tap(src: u32, sw: u32, row: u32, x: u32) -> f32 {
    let c = x / 2u;
    let base = src + row * sw;
    if (x % 2u == 0u) {
        return 0.125 * work[base + clampi(i32(c) - 1, sw)]
            + 0.75 * work[base + c]
            + 0.125 * work[base + clampi(i32(c) + 1, sw)];
    }
    return 0.5 * (work[base + c] + work[base + clampi(i32(c) + 1, sw)]);
}

// expand, horizontal: a = (src, sw, sh, scratch), b.x = dw. Over dw x sh.
@compute @workgroup_size(256)
fn expand_h(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let dw = p.b.x;
    if (i >= dw * p.a.z) { return; }
    let x = i % dw; let y = i / dw;
    work[p.a.w + i] = expand_tap(p.a.x, p.a.y, y, x);
}

// expand, vertical, fused with the Laplacian difference, in place:
// a = (scratch, dw, sh, dst), b.x = dh. dst -= e.
@compute @workgroup_size(256)
fn expand_sub_v(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let dw = p.a.y; let sh = p.a.z;
    if (i >= dw * p.b.x) { return; }
    let x = i % dw; let y = i / dw;
    let c = y / 2u;
    let s = p.a.x;
    var e: f32;
    if (y % 2u == 0u) {
        e = 0.125 * work[s + clampi(i32(c) - 1, sh) * dw + x]
            + 0.75 * work[s + c * dw + x]
            + 0.125 * work[s + clampi(i32(c) + 1, sh) * dw + x];
    } else {
        e = 0.5 * (work[s + c * dw + x] + work[s + clampi(i32(c) + 1, sh) * dw + x]);
    }
    work[p.a.w + i] = work[p.a.w + i] - e;
}

// Band energy, horizontal, squaring on the fly: a = (lv, w, h, scratch).
@compute @workgroup_size(256)
fn smooth_h(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let w = p.a.y;
    if (i >= w * p.a.z) { return; }
    let x = i % w; let y = i / w;
    var s = 0.0;
    for (var t = 0u; t < 5u; t = t + 1u) {
        let v = work[p.a.x + y * w + clampi(i32(x) + i32(t) - 2, w)];
        s = s + kern(t) * (v * v);
    }
    work[p.a.w + i] = s;
}

// Band energy, vertical: a = (scratch, w, h, sq).
@compute @workgroup_size(256)
fn smooth_v(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let w = p.a.y; let h = p.a.z;
    if (i >= w * h) { return; }
    let x = i % w; let y = i / w;
    var o = 0.0;
    for (var t = 0u; t < 5u; t = t + 1u) {
        o = o + kern(t) * work[p.a.x + clampi(i32(y) + i32(t) - 2, h) * w + x];
    }
    work[p.a.w + i] = o;
}

// One level's evidence, weight and ensemble sums (fused_pooled_level).
// a = (sq, vv, lv, ev), b = (ev_next, weight, n, flags: 1 first, 2 ensemble,
// 4 averaged), c = (zmax, zsum, lsum, esum), f = (beta, gate, p, ratio),
// g.x = levels.
@compute @workgroup_size(256)
fn level(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.b.z) { return; }
    let flags = p.b.w;
    if ((flags & 4u) != 0u) {
        work[p.b.y + i] = 0.0;
        return;
    }
    let beta = p.f.x; let gate = p.f.y; let pw = p.f.z; let ratio = p.f.w;
    let v = work[p.a.y + i];
    let e = work[p.a.x + i];
    let u = max(beta * max(v, 0.0), 1.0);
    var ev: f32;
    if ((flags & 1u) != 0u) {
        ev = div(e, u);
    } else {
        ev = ratio * work[p.b.x + i] + div(e, u);
    }
    work[p.a.w + i] = ev;
    let eff = div(u * ev, p.g.x);
    let fl = gate * beta * max(v, 0.0);
    let excess = max(eff - fl, 0.0);
    work[p.b.y + i] = select_weight(excess, fl, pw);
    if ((flags & 2u) != 0u) {
        let z = div(e, max(beta * max(v, 0.0), 1.0));
        acc[p.c.x + i] = max(acc[p.c.x + i], z);
        acc[p.c.y + i] = acc[p.c.y + i] + z;
        acc[p.c.z + i] = acc[p.c.z + i] + work[p.a.z + i];
        acc[p.c.w + i] = acc[p.c.w + i] + e;
    }
}

// accumulate_level, soft-power: a = (weight, den, n, planes),
// b = plane level offsets (work), c = num offsets (acc), d = usum offsets (acc).
@compute @workgroup_size(256)
fn accum(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.z) { return; }
    let w = work[p.a.x + i];
    acc[p.a.y + i] = acc[p.a.y + i] + w;
    for (var c = 0u; c < p.a.w; c = c + 1u) {
        let l = work[p.b[c] + i];
        acc[p.c[c] + i] = acc[p.c[c] + i] + w * div(l, 65536.0);
        acc[p.d[c] + i] = acc[p.d[c] + i] + l;
    }
}

// ---------------------------------------------------------------------------
// Frame preparation: the full-resolution gather, extraction, luma variance and
// the gate-floor probe's luma, each mirroring align_cmd / gatefloor / pyramid
// operand for operand.
// ---------------------------------------------------------------------------

// Raw sample at word-offset `base` + `i` samples.
fn sensel(base: u32, i: u32) -> u32 {
    let j = base + i;
    return (raw[j / 2u] >> (16u * (j & 1u))) & 65535u;
}

// demosaic::reflect
fn reflect(index: i32, n: i32) -> i32 {
    if (n <= 1) { return 0; }
    var i = index;
    loop {
        if (i < 0) { i = -i; } else if (i >= n) { i = 2 * (n - 1) - i; } else { break; }
    }
    return i;
}

// rggb_channel_index on local coordinates: 0 R, 1 G, 2 B.
fn channel(x: u32, y: u32) -> u32 {
    if ((y & 1u) == 0u && (x & 1u) == 0u) { return 0u; }
    if ((y & 1u) == 1u && (x & 1u) == 1u) { return 2u; }
    return 1u;
}

struct Mosaic { base: u32, stride: u32, fw: i32, fh: i32 }

// The black-subtracted, white-balanced mosaic sample at (x, y), mirrored.
fn mosaic(m: Mosaic, x: i32, y: i32) -> f32 {
    let sx = u32(reflect(x, m.fw));
    let sy = u32(reflect(y, m.fh));
    let gain = p.f[1u + channel(sx, sy)];
    return (f32(sensel(m.base, sy * m.stride + sx)) - p.f.x) * gain;
}

const FG = array<vec3<f32>, 9>(
    vec3(0., 0., 4.), vec3(-1., 0., 2.), vec3(1., 0., 2.), vec3(0., -1., 2.), vec3(0., 1., 2.),
    vec3(-2., 0., -1.), vec3(2., 0., -1.), vec3(0., -2., -1.), vec3(0., 2., -1.));
const FH = array<vec3<f32>, 11>(
    vec3(0., 0., 5.), vec3(-1., 0., 4.), vec3(1., 0., 4.), vec3(-2., 0., -1.), vec3(2., 0., -1.),
    vec3(-1., -1., -1.), vec3(1., -1., -1.), vec3(-1., 1., -1.), vec3(1., 1., -1.),
    vec3(0., -2., 0.5), vec3(0., 2., 0.5));
const FV = array<vec3<f32>, 11>(
    vec3(0., 0., 5.), vec3(0., -1., 4.), vec3(0., 1., 4.), vec3(0., -2., -1.), vec3(0., 2., -1.),
    vec3(-1., -1., -1.), vec3(1., -1., -1.), vec3(-1., 1., -1.), vec3(1., 1., -1.),
    vec3(-2., 0., 0.5), vec3(2., 0., 0.5));
const FX = array<vec3<f32>, 9>(
    vec3(0., 0., 6.), vec3(-1., -1., 2.), vec3(1., -1., 2.), vec3(-1., 1., 2.), vec3(1., 1., 2.),
    vec3(-2., 0., -1.5), vec3(2., 0., -1.5), vec3(0., -2., -1.5), vec3(0., 2., -1.5));

// The tables above written out: demosaic::conv's taps, in table order, as
// straight-line code. Indexing a constant table at run time inside a switch
// kept the loop from unrolling and the tables out of registers; the operations
// and their order are the table's, so the result is the same.

// The mosaic sample at (x, y) when the whole 5x5 neighbourhood is inside the
// frame (`mosaic` without reflection): the same expression.
fn mosaic_in(m: Mosaic, x: i32, y: i32) -> f32 {
    let sx = u32(x);
    let sy = u32(y);
    let gain = p.f[1u + channel(sx, sy)];
    return (f32(sensel(m.base, sy * m.stride + sx)) - p.f.x) * gain;
}

fn tap(m: Mosaic, x: i32, y: i32, inside: bool) -> f32 {
    if (inside) { return mosaic_in(m, x, y); }
    return mosaic(m, x, y);
}

// FG
fn conv_g(m: Mosaic, x: i32, y: i32, inside: bool) -> f32 {
    var acc = 0.0;
    acc = acc + 4. * tap(m, x, y, inside);
    acc = acc + 2. * tap(m, x - 1, y, inside);
    acc = acc + 2. * tap(m, x + 1, y, inside);
    acc = acc + 2. * tap(m, x, y - 1, inside);
    acc = acc + 2. * tap(m, x, y + 1, inside);
    acc = acc + -1. * tap(m, x - 2, y, inside);
    acc = acc + -1. * tap(m, x + 2, y, inside);
    acc = acc + -1. * tap(m, x, y - 2, inside);
    acc = acc + -1. * tap(m, x, y + 2, inside);
    return acc * 0.125;
}

// FH
fn conv_h(m: Mosaic, x: i32, y: i32, inside: bool) -> f32 {
    var acc = 0.0;
    acc = acc + 5. * tap(m, x, y, inside);
    acc = acc + 4. * tap(m, x - 1, y, inside);
    acc = acc + 4. * tap(m, x + 1, y, inside);
    acc = acc + -1. * tap(m, x - 2, y, inside);
    acc = acc + -1. * tap(m, x + 2, y, inside);
    acc = acc + -1. * tap(m, x - 1, y - 1, inside);
    acc = acc + -1. * tap(m, x + 1, y - 1, inside);
    acc = acc + -1. * tap(m, x - 1, y + 1, inside);
    acc = acc + -1. * tap(m, x + 1, y + 1, inside);
    acc = acc + 0.5 * tap(m, x, y - 2, inside);
    acc = acc + 0.5 * tap(m, x, y + 2, inside);
    return acc * 0.125;
}

// FV
fn conv_v(m: Mosaic, x: i32, y: i32, inside: bool) -> f32 {
    var acc = 0.0;
    acc = acc + 5. * tap(m, x, y, inside);
    acc = acc + 4. * tap(m, x, y - 1, inside);
    acc = acc + 4. * tap(m, x, y + 1, inside);
    acc = acc + -1. * tap(m, x, y - 2, inside);
    acc = acc + -1. * tap(m, x, y + 2, inside);
    acc = acc + -1. * tap(m, x - 1, y - 1, inside);
    acc = acc + -1. * tap(m, x + 1, y - 1, inside);
    acc = acc + -1. * tap(m, x - 1, y + 1, inside);
    acc = acc + -1. * tap(m, x + 1, y + 1, inside);
    acc = acc + 0.5 * tap(m, x - 2, y, inside);
    acc = acc + 0.5 * tap(m, x + 2, y, inside);
    return acc * 0.125;
}

// FX
fn conv_x(m: Mosaic, x: i32, y: i32, inside: bool) -> f32 {
    var acc = 0.0;
    acc = acc + 6. * tap(m, x, y, inside);
    acc = acc + 2. * tap(m, x - 1, y - 1, inside);
    acc = acc + 2. * tap(m, x + 1, y - 1, inside);
    acc = acc + 2. * tap(m, x - 1, y + 1, inside);
    acc = acc + 2. * tap(m, x + 1, y + 1, inside);
    acc = acc + -1.5 * tap(m, x - 2, y, inside);
    acc = acc + -1.5 * tap(m, x + 2, y, inside);
    acc = acc + -1.5 * tap(m, x, y - 2, inside);
    acc = acc + -1.5 * tap(m, x, y + 2, inside);
    return acc * 0.125;
}

// Malvar over the active region into planar channels at `a.x`, one 2x2 CFA
// quad per invocation (R G / G B), so a warp runs one path rather than every
// parity's; each sample's value is the same expression as before.
// a = (rgb, fw, fh, green_only), b = (raw_base, stride), f = (black, gR, gG, gB).
// Dispatched over (fw / 2) * (fh / 2) quads; fw and fh are even.
@compute @workgroup_size(256)
fn mhc(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let q = gid(id, nwg);
    let fw = p.a.y; let fh = p.a.z;
    let qw = fw / 2u;
    if (q >= qw * (fh / 2u)) { return; }
    let x = 2u * (q % qw); let y = 2u * (q / qw);
    let m = Mosaic(p.b.x, p.b.y, i32(fw), i32(fh));
    let xi = i32(x); let yi = i32(y);
    // Every tap of all four samples inside the frame: no reflection needed.
    let inside = x >= 2u && y >= 2u && x + 3u < fw && y + 3u < fh;
    let n = fw * fh;
    let o = p.a.x + y * fw + x;
    let r = tap(m, xi, yi, inside);
    let g1 = tap(m, xi + 1, yi, inside);
    let g2 = tap(m, xi, yi + 1, inside);
    let b = tap(m, xi + 1, yi + 1, inside);
    if (p.a.w != 0u) {
        work[o] = conv_g(m, xi, yi, inside);
        work[o + 1u] = g1;
        work[o + fw] = g2;
        work[o + fw + 1u] = conv_g(m, xi + 1, yi + 1, inside);
        return;
    }
    // (x, y): red known.
    work[o] = r;
    work[o + n] = conv_g(m, xi, yi, inside);
    work[o + 2u * n] = conv_x(m, xi, yi, inside);
    // (x + 1, y): green on a red row.
    work[o + 1u] = conv_h(m, xi + 1, yi, inside);
    work[o + n + 1u] = g1;
    work[o + 2u * n + 1u] = conv_v(m, xi + 1, yi, inside);
    // (x, y + 1): green on a blue row.
    work[o + fw] = conv_v(m, xi, yi + 1, inside);
    work[o + n + fw] = g2;
    work[o + 2u * n + fw] = conv_h(m, xi, yi + 1, inside);
    // (x + 1, y + 1): blue known.
    work[o + fw + 1u] = conv_x(m, xi + 1, yi + 1, inside);
    work[o + n + fw + 1u] = conv_g(m, xi + 1, yi + 1, inside);
    work[o + 2u * n + fw + 1u] = b;
}
fn cr_weights(f: f32) -> vec4<f32> {
    let f2 = f * f;
    let f3 = f2 * f;
    return vec4(-0.5 * f3 + f2 - 0.5 * f, 1.5 * f3 - 2.5 * f2 + 1.0,
                -1.5 * f3 + 2.0 * f2 + 0.5 * f, 0.5 * f3 - 0.5 * f2);
}

// f32::round (ties away) then clamp to [0, 65535], as `as u16` after it.
fn quantize(v: f32) -> u32 {
    let magnitude = bitcast<u32>(v) & 0x7fffffffu;
    if (magnitude > 0x7f800000u) { return 0u; }
    if (v <= 0.0) { return 0u; }
    if (v >= 65535.0) { return 65535u; }
    let whole = u32(v);
    return whole + select(0u, 1u, v - f32(whole) >= 0.5);
}

// One CFA site's checked Catmull-Rom pull, quantised as the writeback does and
// extracted as `extract_planes` does: (code - black).max(0).
// `src` is the channel plane, `s` the site's pull index in `xf`.
fn gather_value(src: u32, fw: u32, fh: u32, s: u32, px: u32, py: u32) -> f32 {
    let o = 8u * s;
    let ar = xf[o]; let ai = xf[o + 1u]; let br = xf[o + 2u]; let bi = xf[o + 3u];
    let ox = xf[o + 4u]; let oy = xf[o + 5u]; let cx = xf[o + 6u]; let cy = xf[o + 7u];
    // Similarity::apply_at: q = a * (p - c) + b, then + c.
    let pr = (f64(px) + ox) - cx;
    let pi = (f64(py) + oy) - cy;
    let qr = (ar * pr - ai * pi) + br;
    let qi = (ar * pi + ai * pr) + bi;
    let x = f64(2.0) * (qr + cx);
    let y = f64(2.0) * (qi + cy);
    let black = p.f.x;
    var code: u32;
    if (x >= f64(1.5) && y >= f64(1.5) && x <= f64(fw) - f64(2.5) && y <= f64(fh) - f64(2.5)) {
        let x0 = min(u32(x), fw - 3u);
        let y0 = min(u32(y), fh - 3u);
        let wx = cr_weights(f32(x - f64(x0)));
        let wy = cr_weights(f32(y - f64(y0)));
        let base = src + (y0 - 1u) * fw + x0 - 1u;
        var acc = 0.0;
        for (var dy = 0u; dy < 4u; dy = dy + 1u) {
            let row = base + dy * fw;
            var r = 0.0;
            r = r + work[row] * wx[0];
            r = r + work[row + 1u] * wx[1];
            r = r + work[row + 2u] * wx[2];
            r = r + work[row + 3u] * wx[3];
            acc = acc + r * wy[dy];
        }
        code = quantize(acc * p.f.y + black);
    } else {
        code = p.c.x;
    }
    return max(f32(code) - black, 0.0);
}

// Gather one site into a compact plane over the analysis rectangle.
// a = (channel plane, fw, fh, dst), b = (rect.x, rect.y, lw, lh), c = (black_dn, site),
// f = (black, inverse gain).
@compute @workgroup_size(256)
fn gather(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let lw = p.b.z;
    if (i >= lw * p.b.w) { return; }
    let lx = i % lw; let ly = i / lw;
    work[p.a.w + i] = gather_value(p.a.x, p.a.y, p.a.z, p.c.y, p.b.x + lx, p.b.y + ly);
}

// An unwarped site, extracted directly: a = (raw_base, stride, dst, _),
// b = (rect.x, rect.y, lw, lh), c = (dx, dy), f.x = black.
@compute @workgroup_size(256)
fn extract(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let lw = p.b.z;
    if (i >= lw * p.b.w) { return; }
    let lx = i % lw; let ly = i / lw;
    let sx = 2u * (p.b.x + lx) + p.c.x;
    let sy = 2u * (p.b.y + ly) + p.c.y;
    work[p.a.z + i] = max(f32(sensel(p.a.x, sy * p.a.y + sx)) - p.f.x, 0.0);
}

// luma_variance: sigma = sqrt(0.25 * (var_G1 + var_G2)) through f64, var = sigma^2.
// a = (luma, dst, n), f = (gain_G1, read_G1, gain_G2, read_G2).
@compute @workgroup_size(256)
fn variance(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.z) { return; }
    let s = max(work[p.a.x + i], 0.0);
    let v1 = p.f.x * s + p.f.y * p.f.y;
    let v2 = p.f.z * s + p.f.w * p.f.w;
    let sigma = f32(sqrt(f64(0.25 * (v1 + v2))));
    work[p.a.y + i] = sigma * sigma;
}

var<workgroup> tree64: array<f64, 256>;

// Sum each thread's `s` across the workgroup into tree64[0]. Every invocation
// must call it (it holds barriers).
fn tree_sum(t: u32, s: f64) {
    tree64[t] = s;
    workgroupBarrier();
    for (var w = 128u; w > 0u; w = w >> 1u) {
        if (t < w) { tree64[t] = tree64[t] + tree64[t + w]; }
        workgroupBarrier();
    }
}

// Partial f64 sums of `n` values in chunks of `a.w`, one chunk per workgroup:
// a = (src, n, red_base, chunk). Exact for the probe luma (half-integers far
// below 2^52), so order is free: each thread sums a strided share of the chunk
// (coalesced loads), then the workgroup sums the shares as a tree.
@compute @workgroup_size(256)
fn sum64(@builtin(workgroup_id) wid: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>,
         @builtin(local_invocation_index) t: u32) {
    let c = wid.x + wid.y * nwg.x;
    let start = c * p.a.w;
    let end = min(start + p.a.w, p.a.y);
    var s = f64(0.0);
    for (var j = start + t; j < end; j = j + 256u) { s = s + f64(work[p.a.x + j]); }
    tree_sum(t, s);
    if (t == 0u && start < p.a.y) { red[p.a.z + c] = tree64[0]; }
}

// Sum the `a.y` exact partials at red[a.x] into red[a.z] (sum64's; their
// order is free): one workgroup's strided shares, then a tree.
@compute @workgroup_size(256)
fn sum64_finish(@builtin(local_invocation_index) t: u32) {
    var s = f64(0.0);
    for (var j = t; j < p.a.y; j = j + 256u) { s = s + red[p.a.x + j]; }
    tree_sum(t, s);
    if (t == 0u) { red[p.a.z] = tree64[0]; }
}
// The probe's zero-mean: v -= (sum / n) as f32. a = (luma, n, red_index).
@compute @workgroup_size(256)
fn demean(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.y) { return; }
    let mean = f32(red[p.a.z] / f64(p.a.y));
    work[p.a.x + i] = work[p.a.x + i] - mean;
}

// ---------------------------------------------------------------------------
// The gate-floor probe's noise, generated in place of a host upload: a copy of
// the frame (slot 0) into slot 1 with the active complete quads replaced by
// gatefloor::fill_probe_noise's values. SplitMix64 is emulated in u32 pairs;
// Box-Muller is crate::portable_math::probe_gaussian_pair.
// ---------------------------------------------------------------------------

// A u64 as (low, high).
fn mul32(a: u32, b: u32) -> vec2<u32> {
    let a0 = a & 0xffffu; let a1 = a >> 16u;
    let b0 = b & 0xffffu; let b1 = b >> 16u;
    let p00 = a0 * b0; let p01 = a0 * b1; let p10 = a1 * b0; let p11 = a1 * b1;
    let mid = (p00 >> 16u) + (p01 & 0xffffu) + (p10 & 0xffffu);
    return vec2((p00 & 0xffffu) | (mid << 16u), p11 + (p01 >> 16u) + (p10 >> 16u) + (mid >> 16u));
}

fn mul64(a: vec2<u32>, b: vec2<u32>) -> vec2<u32> {
    let l = mul32(a.x, b.x);
    return vec2(l.x, l.y + a.x * b.y + a.y * b.x);
}

fn add64(a: vec2<u32>, b: vec2<u32>) -> vec2<u32> {
    let lo = a.x + b.x;
    return vec2(lo, a.y + b.y + select(0u, 1u, lo < a.x));
}

// z ^ (z >> n) for 0 < n < 32.
fn xorshr(z: vec2<u32>, n: u32) -> vec2<u32> {
    return vec2(z.x ^ ((z.x >> n) | (z.y << (32u - n))), z.y ^ (z.y >> n));
}

// The 24-bit draw after `n` SplitMix64 steps from `seed`.
fn splitmix24(seed: vec2<u32>, n: u32) -> u32 {
    var z = add64(seed, mul64(vec2(0x7F4A7C15u, 0x9E3779B9u), vec2(n, 0u)));
    z = mul64(xorshr(z, 30u), vec2(0x1CE4E5B9u, 0xBF58476Du));
    z = mul64(xorshr(z, 27u), vec2(0x133111EBu, 0x94D049BBu));
    return (z.y ^ (z.y >> 31u)) >> 8u;
}

// portable_math::ln_u24 for 1 <= k < 2^24.
fn ln_u24(k: u32) -> f64 {
    let bits = bitcast<u32>(f32(k));
    var e = i32((bits >> 23u) & 0xffu) - 127;
    var m = f64(bitcast<f32>((bits & 0x007fffffu) | 0x3f800000u));
    if (m > consts[C_SQRT2]) {
        m = m * f64(0.5);
        e = e + 1;
    }
    let s = (m - f64(1.0)) / (m + f64(1.0));
    let s2 = s * s;
    var q = consts[C_LN64 + 14u];
    for (var i = 14u; i > 0u; i = i - 1u) {
        q = q * s2 + consts[C_LN64 + i - 1u];
    }
    return f64(e - 24) * consts[C_LN2] + f64(2.0) * s * q;
}

// portable_math::probe_gaussian_pair: (r cos th, r sin th).
fn gaussian_pair(k1: u32, k2: u32) -> vec2<f64> {
    var ln_u1 = consts[C_LN_FLOOR];
    if (k1 != 0u) { ln_u1 = ln_u24(k1); }
    let r = sqrt(f64(-2.0) * ln_u1);
    let th = consts[C_TAU] * (f64(k2) * consts[C_INV_2_24]);
    // portable_math::sin_cos
    let q = floor(th / consts[C_PIO2] + f64(0.5));
    let t = th - q * consts[C_PIO2_HI] - q * consts[C_PIO2_LO];
    let t2 = t * t;
    var sn = consts[C_SIN + 10u];
    var cs = consts[C_COS + 10u];
    for (var i = 10u; i > 0u; i = i - 1u) {
        sn = sn * t2 + consts[C_SIN + i - 1u];
        cs = cs * t2 + consts[C_COS + i - 1u];
    }
    sn = t * sn;
    var s: f64; var c: f64;
    switch (u32(i32(q)) & 3u) {
        case 0u: { s = sn; c = cs; }
        case 1u: { s = cs; c = -sn; }
        case 2u: { s = -sn; c = -cs; }
        default: { s = -cs; c = sn; }
    }
    return vec2(r * c, r * s);
}

// f64::round (ties away), clamp to [0, 65535], as u16.
fn quantize64(v: f64) -> u32 {
    if (v < f64(0.5)) { return 0u; }
    if (v >= f64(65535.0)) { return 65535u; }
    let w = floor(v);
    return u32(w) + select(0u, 1u, v - w >= f64(0.5));
}

// portable_math's f32 screen, operand for operand.
fn cf(i: u32) -> f32 { return f32(consts[C_F32 + i]); }

fn recip32(d: f32) -> f32 {
    var y = bitcast<f32>(0x7EF311C3u - bitcast<u32>(d));
    for (var i = 0u; i < 3u; i = i + 1u) { y = y * (2.0 - d * y); }
    return y;
}

fn sqrt32(x: f32) -> f32 {
    var y = bitcast<f32>(0x5F3759DFu - (bitcast<u32>(x) >> 1u));
    for (var i = 0u; i < 3u; i = i + 1u) { y = y * (1.5 - 0.5 * x * y * y); }
    return x * y;
}

fn ln_u24_f32(k: u32) -> f32 {
    let bits = bitcast<u32>(f32(k));
    var e = i32((bits >> 23u) & 0xffu) - 127;
    var m = bitcast<f32>((bits & 0x007fffffu) | 0x3f800000u);
    if (m > cf(F_SQRT2)) {
        m = m * 0.5;
        e = e + 1;
    }
    let s = (m - 1.0) * recip32(m + 1.0);
    let s2 = s * s;
    let p = 1.0 + s2 * (cf(F_T3) + s2 * (cf(F_T5) + s2 * (cf(F_T7) + s2 * (cf(F_T9) + s2 * cf(F_T11)))));
    return f32(e - 24) * cf(F_LN2) + 2.0 * s * p;
}

fn gaussian_pair_f32(k1: u32, k2: u32) -> vec2<f32> {
    var ln_u1 = cf(F_LN_FLOOR);
    if (k1 != 0u) { ln_u1 = ln_u24_f32(k1); }
    let r = sqrt32(-2.0 * ln_u1);
    let q = (k2 + (1u << 21u)) >> 22u;
    let f = i32(k2) - i32(q << 22u);
    let x = f32(f) * cf(F_XSCALE);
    let x2 = x * x;
    let s = x * (1.0 + x2 * (cf(F_S3) + x2 * (cf(F_S5) + x2 * (cf(F_S7) + x2 * cf(F_S9)))));
    let c = 1.0 + x2 * (cf(F_C2) + x2 * (cf(F_C4) + x2 * (cf(F_C6) + x2 * (cf(F_C8) + x2 * cf(F_C10)))));
    var cs: vec2<f32>;
    switch (q & 3u) {
        case 0u: { cs = vec2(c, s); }
        case 1u: { cs = vec2(-s, c); }
        case 2u: { cs = vec2(-c, -s); }
        default: { cs = vec2(s, -c); }
    }
    return vec2(r * cs.x, r * cs.y);
}

// The quantised sample when the screened value `v` is farther than `margin`
// from every rounding boundary, else 0xffffffff.
fn screened(v: f64, margin: f64) -> u32 {
    let lo = floor(v - margin + f64(0.5));
    let hi = floor(v + margin + f64(0.5));
    if (lo != hi) { return 0xffffffffu; }
    if (lo <= f64(0.0)) { return 0u; }
    if (lo >= f64(65535.0)) { return 65535u; }
    return u32(lo);
}

// The Box-Muller pair for active-relative sites (row, col & ~1) and (row, col | 1)
// of a fill `width` wide, quantised. Screened in f32; f64 only near a boundary.
fn probe_pair(seed: vec2<u32>, row: u32, col: u32, width: u32) -> vec2<u32> {
    let n = row * width + (col & ~1u) + 1u;
    let k1 = splitmix24(seed, n);
    let k2 = splitmix24(seed, n + 1u);
    let level = xf[64u]; let sigma = xf[65u]; let margin = xf[66u];
    let g32 = gaussian_pair_f32(k1, k2);
    let a = screened(level + sigma * f64(g32.x), margin);
    let b = screened(level + sigma * f64(g32.y), margin);
    if (a != 0xffffffffu && b != 0xffffffffu) { return vec2(a, b); }
    let g = gaussian_pair(k1, k2);
    return vec2(quantize64(level + sigma * g.x), quantize64(level + sigma * g.y));
}

// One word of the probe slot from a frame slot, noise where the fill reaches.
// a = (words, probe word base, stride, width), b = (ax, ay, rows, frame word base),
// c = (seed lo, seed hi);
// xf[64], xf[65] = level, sigma.
@compute @workgroup_size(256)
fn noise(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let w = gid(id, nwg);
    if (w >= p.a.x) { return; }
    var word = raw[p.b.w + w];
    let seed = vec2(p.c.x, p.c.y);
    // A pair covers two adjacent sites of a row; compute each pair once per
    // word (one pair when the word is pair-aligned, else parts of two).
    var have = false;
    var pair_row = 0u; var pair_col = 0u; var pair = vec2(0u, 0u);
    for (var h = 0u; h < 2u; h = h + 1u) {
        let i = 2u * w + h;
        let y = i / p.a.z; let x = i % p.a.z;
        if (y >= p.b.y && y < p.b.y + p.b.z && x >= p.b.x && x < p.b.x + p.a.w) {
            let row = y - p.b.y; let col = x - p.b.x;
            if (!have || row != pair_row || (col & ~1u) != pair_col) {
                pair = probe_pair(seed, row, col, p.a.w);
                pair_row = row; pair_col = col & ~1u; have = true;
            }
            let v = select(pair.x, pair.y, (col & 1u) == 1u);
            word = (word & ~(0xffffu << (16u * h))) | (v << (16u * h));
        }
    }
    raw[p.a.y + w] = word;
}

// gatefloor::square_sum over up to four windows in one dispatch, so that
// their ordered f64 chains (which no reassociation may shorten) run side by
// side. Window j: a, b, c, d = (level, level width, x | y << 16, w | h << 16);
// e = (first row-sum index, windows, total index). Window j's row sums follow
// window j - 1's.
fn sq_window(j: u32) -> vec4<u32> {
    if (j == 0u) { return p.a; }
    if (j == 1u) { return p.b; }
    if (j == 2u) { return p.c; }
    return p.d;
}

// One row's f64 sum of squares, in column order: square_sum's inner sums.
// Loads are issued eight at a time, so the ordered chain waits on memory once
// per eight values.
@compute @workgroup_size(256)
fn rowsq(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    var r = gid(id, nwg);
    var row = p.e.x;
    var j = 0u;
    loop {
        if (j >= p.e.y) { return; }
        let h = sq_window(j).w >> 16u;
        if (r < h) { break; }
        r = r - h; row = row + h; j = j + 1u;
    }
    let win = sq_window(j);
    let n = win.w & 0xffffu;
    let base = win.x + ((win.z >> 16u) + r) * win.y + (win.z & 0xffffu);
    var s = f64(0.0);
    var c = 0u;
    loop {
        if (c + 8u > n) { break; }
        let v0 = f64(work[base + c]); let v1 = f64(work[base + c + 1u]);
        let v2 = f64(work[base + c + 2u]); let v3 = f64(work[base + c + 3u]);
        let v4 = f64(work[base + c + 4u]); let v5 = f64(work[base + c + 5u]);
        let v6 = f64(work[base + c + 6u]); let v7 = f64(work[base + c + 7u]);
        s = s + v0 * v0; s = s + v1 * v1; s = s + v2 * v2; s = s + v3 * v3;
        s = s + v4 * v4; s = s + v5 * v5; s = s + v6 * v6; s = s + v7 * v7;
        c = c + 8u;
    }
    loop {
        if (c >= n) { break; }
        let v = f64(work[base + c]);
        s = s + v * v;
        c = c + 1u;
    }
    red[row + r] = s;
}

// Each window's row sums, in row order, into red[e.z + j]: square_sum's outer
// sum. One invocation per window, loads eight at a time.
@compute @workgroup_size(256)
fn rowsq_finish(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let j = gid(id, nwg);
    if (j >= p.e.y) { return; }
    var b = p.e.x;
    for (var k = 0u; k < j; k = k + 1u) { b = b + (sq_window(k).w >> 16u); }
    let n = sq_window(j).w >> 16u;
    var s = f64(0.0);
    var c = 0u;
    loop {
        if (c + 8u > n) { break; }
        let v0 = red[b + c]; let v1 = red[b + c + 1u];
        let v2 = red[b + c + 2u]; let v3 = red[b + c + 3u];
        let v4 = red[b + c + 4u]; let v5 = red[b + c + 5u];
        let v6 = red[b + c + 6u]; let v7 = red[b + c + 7u];
        s = s + v0; s = s + v1; s = s + v2; s = s + v3;
        s = s + v4; s = s + v5; s = s + v6; s = s + v7;
        c = c + 8u;
    }
    loop {
        if (c >= n) { break; }
        s = s + red[b + c];
        c = c + 1u;
    }
    red[p.e.z + j] = s;
}
// Copy a rectangle of a level to a packed row-major block.
// a = (level, level width, x, w), b = (y, h, dst).
@compute @workgroup_size(256)
fn pack(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.w * p.b.y) { return; }
    let r = i / p.a.w; let c = i % p.a.w;
    work[p.b.z + i] = work[p.a.x + (p.b.x + r) * p.a.y + p.a.z + c];
}

// One frame's ensemble-null window (BandMerge::add_null_windows):
// a = (packed lv, packed energy, n), b = (zmax, zsum, lsum, esum) in acc, f.x = unit.
@compute @workgroup_size(256)
fn null_accum(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    if (i >= p.a.z) { return; }
    let lv = work[p.a.x + i];
    let e = work[p.a.y + i];
    let z = div(e, p.f.x);
    acc[p.b.x + i] = max(acc[p.b.x + i], z);
    acc[p.b.y + i] = acc[p.b.y + i] + z;
    acc[p.b.z + i] = acc[p.b.z + i] + lv;
    acc[p.b.w + i] = acc[p.b.w + i] + e;
}

// ---------------------------------------------------------------------------
// The screens' census (test only, `GpuFold::screen_census`): every input in
// [a.x, b.x] (f32 bits) against the f64 function on this device.
// a = (first bits, inputs per invocation, 0 ln / 1 exp, invocations),
// b.x = last bits (inclusive). Per invocation, at raw[4 i ..]: accepted values
// that differ from the f64 function's, fallbacks, the smallest input that
// differs (or all ones), and the largest error of hi + lo against the f64 value
// before rounding as a fraction of the bound the screen used (f32 bits).
// ---------------------------------------------------------------------------
@compute @workgroup_size(256)
fn screen_census(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let t = gid(id, nwg);
    if (t >= p.a.w) { return; }
    var bad = 0u;
    var fell = 0u;
    var first = 0xffffffffu;
    var worst = 0.0;
    for (var i = 0u; i < p.a.y; i = i + 1u) {
        let bits = p.a.x + t * p.a.y + i;
        if (bits < p.a.x || bits > p.b.x) { break; }
        let x = bitcast<f32>(bits);
        var want: f32;
        var s: Screen;
        var approx: vec3<f32>;
        var exact: f64;
        if (p.a.z == 0u) {
            want = pln(x);
            s = ln_screen(x);
            approx = ln_df(x);
            exact = pln64(x);
        } else {
            want = pexp(x);
            s = exp_screen(x);
            let d = exp_df(x);
            approx = d.y;
            exact = pexp64(x) * f64(bitcast<f32>(u32(127 - d.k) << 23u));
        }
        if (s.ok) {
            if (bitcast<u32>(s.v) != bitcast<u32>(want)) {
                bad = bad + 1u;
                first = min(first, bits);
            }
        } else {
            fell = fell + 1u;
        }
        if (approx.z > 0.0) {
            worst = max(worst, f32(abs((f64(approx.x) + f64(approx.y)) - exact) / f64(approx.z)));
        }
    }
    raw[4u * t] = bad;
    raw[4u * t + 1u] = fell;
    raw[4u * t + 2u] = first;
    raw[4u * t + 3u] = bitcast<u32>(worst);
}