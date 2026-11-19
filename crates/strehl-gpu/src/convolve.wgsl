// `strehl_core::optical_restore::convolve` on the device: each output pixel
// sums `t * v` from zero over the kernel's live taps in (ky, kx) order, a
// multiply then an add each (the host decorates every float result
// NoContraction), `v` read mirror-reflected at the borders exactly as the
// CPU reflects. Bit-identical to the CPU form.

struct P {
    w: u32,
    h: u32,
    r: u32,
    taps: u32,
}

@group(0) @binding(0) var<uniform> p: P;
@group(0) @binding(1) var<storage, read> src: array<f32>;
// Live taps in order: (kx, ky, bits of t, unused).
@group(0) @binding(2) var<storage, read> taps: array<vec4<u32>>;
@group(0) @binding(3) var<storage, read_write> dst: array<f32>;

fn reflect(i: i32, n: u32) -> u32 {
    let m = i32(n);
    var j = i;
    if (j < 0) { j = -j; }
    if (j >= m) { j = 2 * (m - 1) - j; }
    return u32(clamp(j, 0, m - 1));
}

@compute @workgroup_size(256)
fn conv(@builtin(global_invocation_id) id: vec3<u32>, @builtin(num_workgroups) nwg: vec3<u32>) {
    let i = id.x + id.y * nwg.x * 256u;
    if (i >= p.w * p.h) { return; }
    let x = i32(i % p.w);
    let y = i32(i / p.w);
    let r = i32(p.r);
    var acc = 0.0;
    if (x >= r && y >= r && x + r < i32(p.w) && y + r < i32(p.h)) {
        // Inside: no tap reflects.
        let base = i32(i) - r * i32(p.w) - r;
        for (var k = 0u; k < p.taps; k = k + 1u) {
            let t = taps[k];
            let v = src[u32(base + i32(t.y) * i32(p.w) + i32(t.x))];
            acc = acc + bitcast<f32>(t.z) * v;
        }
    } else {
        for (var k = 0u; k < p.taps; k = k + 1u) {
            let t = taps[k];
            let sx = reflect(x + i32(t.x) - r, p.w);
            let sy = reflect(y + i32(t.y) - r, p.h);
            acc = acc + bitcast<f32>(t.z) * src[sy * p.w + sx];
        }
    }
    dst[i] = acc;
}
