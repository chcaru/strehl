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
    return f32(f64(e) * consts[C_LN2] + lnm);
}

// crate::portable_math::exp for a finite x.
fn pexp(x: f32) -> f32 {
    if (x > 89.0) { return inf_pos(); }
    if (x < -104.0) { return 0.0; }
    let xd = f64(x);
    let k = floor(xd * consts[C_INV_LN2] + f64(0.5));
    let r = xd - k * consts[C_LN2];
    var q = consts[C_EXP + 14u];
    for (var n = 14u; n > 0u; n = n - 1u) {
        q = q * r + consts[C_EXP + n - 1u];
    }
    let ki = i32(k);
    let k1 = ki / 2;
    return f32(q * pow2(k1) * pow2(ki - k1));
}

// Rust f32::clamp(-80, 80) for a non-NaN value.
fn clamp80(x: f32) -> f32 {
    if (x < -80.0) { return -80.0; }
    if (x > 80.0) { return 80.0; }
    return x;
}

// select_weight with r_floor == 0.
fn select_weight(excess: f32, floor_: f32, pw: f32) -> f32 {
    if (excess <= 0.0) { return 0.0; }
    let r = div(div(excess, max(floor_, 1.0)), 64.0);
    if (pw == 1.0) { return r; }
    if (pw == 2.0) { return r * r; }
    return pexp(clamp80(pw * pln(r)));
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

// demosaic::conv: acc += w * at(x + dx, y + dy), then * 0.125.
fn conv(m: Mosaic, x: i32, y: i32, kind: u32) -> f32 {
    var acc = 0.0;
    let count = select(9u, 11u, kind == 1u || kind == 2u);
    for (var i = 0u; i < count; i = i + 1u) {
        var t: vec3<f32>;
        switch kind {
            case 0u: { t = FG[i]; }
            case 1u: { t = FH[i]; }
            case 2u: { t = FV[i]; }
            default: { t = FX[i]; }
        }
        acc = acc + t.z * mosaic(m, x + i32(t.x), y + i32(t.y));
    }
    return acc * 0.125;
}

// Malvar over the active region into planar channels at `a.x`.
// a = (rgb, fw, fh, green_only), b = (raw_base, stride), f = (black, gR, gG, gB).
@compute @workgroup_size(256)
fn mhc(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let fw = p.a.y; let fh = p.a.z;
    if (i >= fw * fh) { return; }
    let x = i % fw; let y = i / fw;
    let m = Mosaic(p.b.x, p.b.y, i32(fw), i32(fh));
    let xi = i32(x); let yi = i32(y);
    let known = mosaic(m, xi, yi);
    let n = fw * fh;
    if (p.a.w != 0u) {
        if (channel(x, y) == 1u) { work[p.a.x + i] = known; } else { work[p.a.x + i] = conv(m, xi, yi, 0u); }
        return;
    }
    var v: vec3<f32>;
    switch ((y & 1u) * 2u + (x & 1u)) {
        case 0u: { v = vec3(known, conv(m, xi, yi, 0u), conv(m, xi, yi, 3u)); }
        case 3u: { v = vec3(conv(m, xi, yi, 3u), conv(m, xi, yi, 0u), known); }
        case 1u: { v = vec3(conv(m, xi, yi, 1u), known, conv(m, xi, yi, 2u)); }
        default: { v = vec3(conv(m, xi, yi, 2u), known, conv(m, xi, yi, 1u)); }
    }
    work[p.a.x + i] = v.x;
    work[p.a.x + n + i] = v.y;
    work[p.a.x + 2u * n + i] = v.z;
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

// Partial f64 sums of `n` values in chunks of `a.w`: a = (src, n, red_base, chunk).
// Exact for the probe luma (half-integers far below 2^52), so order is free.
@compute @workgroup_size(256)
fn sum64(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = gid(id, nwg);
    let start = i * p.a.w;
    if (start >= p.a.y) { return; }
    let end = min(start + p.a.w, p.a.y);
    var s = f64(0.0);
    for (var j = start; j < end; j = j + 1u) { s = s + f64(work[p.a.x + j]); }
    red[p.a.z + i] = s;
}

// Sum `a.y` partials at red[a.x] into red[a.z].
@compute @workgroup_size(256)
fn sum64_finish(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    if (gid(id, nwg) != 0u) { return; }
    var s = f64(0.0);
    for (var j = 0u; j < p.a.y; j = j + 1u) { s = s + red[p.a.x + j]; }
    red[p.a.z] = s;
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

// One word of slot 1 from slot 0, noise where the fill reaches.
// a = (words, slot-1 word base, stride, width), b = (ax, ay, rows), c = (seed lo, seed hi);
// xf[64], xf[65] = level, sigma.
@compute @workgroup_size(256)
fn noise(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let w = gid(id, nwg);
    if (w >= p.a.x) { return; }
    var word = raw[w];
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

// One row's f64 sum of squares over a rectangle of a level, in column order:
// gatefloor::square_sum's inner sums. a = (level, level width, x, w),
// b = (y, h, red_dst).
@compute @workgroup_size(256)
fn rowsq(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let r = gid(id, nwg);
    if (r >= p.b.y) { return; }
    let base = p.a.x + (p.b.x + r) * p.a.y + p.a.z;
    var s = f64(0.0);
    for (var j = 0u; j < p.a.w; j = j + 1u) {
        let v = f64(work[base + j]);
        s = s + v * v;
    }
    red[p.b.z + r] = s;
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