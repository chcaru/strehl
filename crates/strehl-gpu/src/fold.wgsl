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

// consts layout: [0..12) LN_SERIES, [12..27) EXP_SERIES, 27 LN2, 28 INV_LN2, 29 SQRT2
const C_LN: u32 = 0u;
const C_EXP: u32 = 12u;
const C_LN2: u32 = 27u;
const C_INV_LN2: u32 = 28u;
const C_SQRT2: u32 = 29u;

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

fn index() -> u32 { return 0u; }

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
