// M7 — ring-difference focus measure as one wgpu compute kernel.
//
// The CPU reference this must reproduce is `crates/strehl-core/src/focus.rs`
// plus `boxfilter.rs`, at commit 037d966. Both box means are clamped-window
// means: the window is intersected with the plane and the sum is divided by the
// number of samples that survive. That is reproduced here by loading zeros
// outside the plane (zeros add nothing) and dividing by the clamped count.
//
// WHY THE SUMS ARE BIT-EXACT, not merely close:
//   luma L = (G1 + G2) / 2 with G1, G2 integers in [0, 14848] after black
//   subtraction, so every L is a multiple of 0.5 in [0, 14848]. A sum of at
//   most 7 of them is <= 103936, and a sum of 7 of those is <= 727552. Every
//   multiple of 0.5 up to 2^23 * 0.5 = 4194304 is exactly representable in f32,
//   so every partial sum is exact and the accumulation order cannot matter.
//   The CPU accumulates the same sums in f64. They therefore agree exactly, and
//   the only places f32 and f64 can diverge are the two divisions, the sqrt and
//   any fused multiply-add the driver chooses to emit.
//
// The placeholders {{...}} are substituted in `gpu.rs` before compilation.

struct Params {
    plane_w: u32,
    plane_h: u32,
    row_words: u32,
    frame_index: u32,
    black: f32,
    gain: f32,
    read_noise_e: f32,
    sigma_eps: f32,
};

@group(0) @binding(0) var<uniform> P: Params;
@group(0) @binding(1) var<storage, read> frame: array<u32>;
@group(0) @binding(2) var<storage, read_write> sel_focus: array<f32>;
@group(0) @binding(3) var<storage, read_write> sel_index: array<u32>;
@group(0) @binding(4) var<storage, read_write> sel_w0: array<u32>;
@group(0) @binding(5) var<storage, read_write> sel_w1: array<u32>;
@group(0) @binding(6) var<storage, read_write> focus_io: array<f32>;
@group(0) @binding(7) var<storage, read_write> scratch: array<u32>;

const TILE_W: u32 = {{TILE_W}}u;
const TILE_H: u32 = {{TILE_H}}u;
const THREADS: u32 = TILE_W * TILE_H;
const INNER_R: i32 = {{INNER_R}};
const OUTER_R: i32 = {{OUTER_R}};
// Second, wider measure. Used only by the two-measure entry points.
const INNER_R2: i32 = {{INNER_R2}};
const OUTER_R2: i32 = {{OUTER_R2}};
// OUTER_R2 >= OUTER_R, so the halo is sized for the wider one and both
// measures read the same shared tile. That sharing *is* the fusion.
const HALO: i32 = OUTER_R2;
const SH_W: u32 = {{SH_W}}u;
const SH_H: u32 = {{SH_H}}u;
const SH_N: u32 = {{SH_N}}u;
const HS_N: u32 = {{HS_N}}u;
const NO_FRAME: u32 = 65535u;
// When true, every division is refined to round-to-nearest with an FMA
// residual. Vulkan only requires 2.5 ULP of OpFDiv for fp32, and the CPU
// reference divides in f64 and rounds once, so the raw fp32 divide disagrees
// with it by about 1 ULP of the *mean* -- which cancellation then turns into a
// large relative error in the ring difference. Compiled both ways so the cost
// of exactness can be priced rather than assumed.
const EXACT_DIV: bool = {{EXACT_DIV}};

// Round-to-nearest division. `q0` is within 2.5 ULP; `r = p - d*q0` is computed
// exactly by the FMA (the classic division-residual lemma), and `q0 + r/d`
// re-rounds once. The correction is of order ULP^2, so the result is the
// correctly rounded quotient except at exact ties, where both this and the
// CPU's f64-then-f32 path round half to even.
fn div_rn(p: f32, d: f32) -> f32 {
    let q0 = p / d;
    if (!EXACT_DIV) {
        return q0;
    }
    let r = fma(-d, q0, p);
    return q0 + r / d;
}

var<workgroup> sh_luma: array<f32, {{SH_N}}>;
var<workgroup> sh_h_out: array<f32, {{HS_N}}>;
var<workgroup> sh_h_in: array<f32, {{HS_N}}>;
var<workgroup> sh_red: array<u32, 256>;

fn clamped_count(p: i32, n: u32, r: i32) -> u32 {
    let lo = max(p - r, 0);
    let hi = min(p + r, i32(n) - 1);
    return u32(hi - lo + 1);
}

// `noise.rs::green_luma_sigma`, op for op. Both greens carry the same
// coefficients, so Var(L) = (2 * Var) / 4.
fn green_luma_sigma(l: f32) -> f32 {
    let s = max(l, 0.0);
    let read_dn = P.read_noise_e * P.gain;
    let rd2 = read_dn * read_dn;
    let v1 = P.gain * s + rd2;
    let v = v1 + v1;
    return sqrt(0.25 * v);
}

fn load_tile(tx0: i32, ty0: i32, lid: u32) {
    var i = lid;
    loop {
        if (i >= SH_N) { break; }
        let lx = i % SH_W;
        let ly = i / SH_W;
        let px = tx0 + i32(lx) - HALO;
        let py = ty0 + i32(ly) - HALO;
        var v = 0.0;
        if (px >= 0 && px < i32(P.plane_w) && py >= 0 && py < i32(P.plane_h)) {
            let w0 = frame[u32(2 * py) * P.row_words + u32(px)];
            let w1 = frame[u32(2 * py + 1) * P.row_words + u32(px)];
            // RGGB: row 2py holds R at even x and G1 at odd x; row 2py+1 holds
            // G2 at even x and B at odd x. One packed word per row per quad.
            let g1 = max(f32(w0 >> 16u) - P.black, 0.0);
            let g2 = max(f32(w1 & 0xffffu) - P.black, 0.0);
            v = 0.5 * (g1 + g2);
        }
        sh_luma[i] = v;
        i = i + THREADS;
    }
}

// Horizontal clamped-window sums for one (inner, outer) radius pair.
fn horizontal(lid: u32, inner_r: i32, outer_r: i32) {
    var j = lid;
    loop {
        if (j >= HS_N) { break; }
        let ox = j % TILE_W;
        let ly = j / TILE_W;
        let row = ly * SH_W + ox + u32(HALO - outer_r);
        var so = 0.0;
        for (var k: i32 = 0; k <= 2 * outer_r; k = k + 1) {
            so = so + sh_luma[row + u32(k)];
        }
        let rowi = ly * SH_W + ox + u32(HALO - inner_r);
        var si = 0.0;
        for (var k: i32 = 0; k <= 2 * inner_r; k = k + 1) {
            si = si + sh_luma[rowi + u32(k)];
        }
        sh_h_out[j] = so;
        sh_h_in[j] = si;
        j = j + THREADS;
    }
}

// Vertical sums plus the ring value, for the output pixel this thread owns.
fn ring_value(lid: u32, px: i32, py: i32, inner_r: i32, outer_r: i32) -> f32 {
    let ox = lid % TILE_W;
    let oy = lid / TILE_W;
    var so = 0.0;
    let base_o = (oy + u32(HALO - outer_r)) * TILE_W + ox;
    for (var k: i32 = 0; k <= 2 * outer_r; k = k + 1) {
        so = so + sh_h_out[base_o + u32(k) * TILE_W];
    }
    var si = 0.0;
    let base_i = (oy + u32(HALO - inner_r)) * TILE_W + ox;
    for (var k: i32 = 0; k <= 2 * inner_r; k = k + 1) {
        si = si + sh_h_in[base_i + u32(k) * TILE_W];
    }
    let n_out = f32(clamped_count(px, P.plane_w, outer_r) * clamped_count(py, P.plane_h, outer_r));
    let n_in = f32(clamped_count(px, P.plane_w, inner_r) * clamped_count(py, P.plane_h, inner_r));
    return abs(div_rn(si, n_in) - div_rn(so, n_out));
}

fn centre_luma(lid: u32) -> f32 {
    let ox = lid % TILE_W;
    let oy = lid / TILE_W;
    return sh_luma[(oy + u32(HALO)) * SH_W + ox + u32(HALO)];
}

fn merge_pixel(i: u32, f: f32, px: i32, py: i32) {
    let cur_f = sel_focus[i];
    let cur_i = sel_index[i];
    // `Selection::beats`: ties go to the lower frame index.
    if (f > cur_f || (f == cur_f && P.frame_index < cur_i)) {
        sel_focus[i] = f;
        sel_index[i] = P.frame_index;
        sel_w0[i] = frame[u32(2 * py) * P.row_words + u32(px)];
        sel_w1[i] = frame[u32(2 * py + 1) * P.row_words + u32(px)];
    }
}

// --- entry points ----------------------------------------------------------

// FUSED: focus measure and merge in one dispatch. The focus field is never
// written to memory; it lives in a register between being computed and being
// consumed.
@compute @workgroup_size({{TILE_W}}, {{TILE_H}}, 1)
fn focus_merge_fused(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) lid: u32) {
    let tx0 = i32(wg.x * TILE_W);
    let ty0 = i32(wg.y * TILE_H);
    load_tile(tx0, ty0, lid);
    workgroupBarrier();
    horizontal(lid, INNER_R, OUTER_R);
    workgroupBarrier();
    let px = tx0 + i32(lid % TILE_W);
    let py = ty0 + i32(lid / TILE_W);
    if (px >= i32(P.plane_w) || py >= i32(P.plane_h)) { return; }
    let ring = ring_value(lid, px, py, INNER_R, OUTER_R);
    let f = div_rn(ring, max(green_luma_sigma(centre_luma(lid)), P.sigma_eps));
    merge_pixel(u32(py) * P.plane_w + u32(px), f, px, py);
}

// UNFUSED, pass 1: the same measure, written out to a focus field in memory.
@compute @workgroup_size({{TILE_W}}, {{TILE_H}}, 1)
fn focus_write(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) lid: u32) {
    let tx0 = i32(wg.x * TILE_W);
    let ty0 = i32(wg.y * TILE_H);
    load_tile(tx0, ty0, lid);
    workgroupBarrier();
    horizontal(lid, INNER_R, OUTER_R);
    workgroupBarrier();
    let px = tx0 + i32(lid % TILE_W);
    let py = ty0 + i32(lid / TILE_W);
    if (px >= i32(P.plane_w) || py >= i32(P.plane_h)) { return; }
    let ring = ring_value(lid, px, py, INNER_R, OUTER_R);
    focus_io[u32(py) * P.plane_w + u32(px)] = div_rn(ring, max(green_luma_sigma(centre_luma(lid)), P.sigma_eps));
}

// UNFUSED, pass 2: read the focus field back and merge.
@compute @workgroup_size(256)
fn merge_only(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x;
    let n = P.plane_w * P.plane_h;
    if (i >= n) { return; }
    let px = i32(i % P.plane_w);
    let py = i32(i / P.plane_w);
    merge_pixel(i, focus_io[i], px, py);
}

// FUSED, two measures in one dispatch: one shared tile, one set of loads.
@compute @workgroup_size({{TILE_W}}, {{TILE_H}}, 1)
fn focus2_merge_fused(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) lid: u32) {
    let tx0 = i32(wg.x * TILE_W);
    let ty0 = i32(wg.y * TILE_H);
    load_tile(tx0, ty0, lid);
    workgroupBarrier();
    horizontal(lid, INNER_R, OUTER_R);
    workgroupBarrier();
    let px = tx0 + i32(lid % TILE_W);
    let py = ty0 + i32(lid / TILE_W);
    var ring_a = 0.0;
    if (px < i32(P.plane_w) && py < i32(P.plane_h)) {
        ring_a = ring_value(lid, px, py, INNER_R, OUTER_R);
    }
    workgroupBarrier();
    horizontal(lid, INNER_R2, OUTER_R2);
    workgroupBarrier();
    if (px >= i32(P.plane_w) || py >= i32(P.plane_h)) { return; }
    let ring_b = ring_value(lid, px, py, INNER_R2, OUTER_R2);
    let sigma = max(green_luma_sigma(centre_luma(lid)), P.sigma_eps);
    let f = max(div_rn(ring_a, sigma), div_rn(ring_b, sigma));
    merge_pixel(u32(py) * P.plane_w + u32(px), f, px, py);
}

// UNFUSED second measure: a whole separate pass over the stack, max-combined
// into measure A's already-materialised field. Compiled in a module whose
// INNER_R/OUTER_R *are* the second measure's radii, so its halo is its own and
// the unfused path is not handicapped by the fused path's wider tile.
@compute @workgroup_size({{TILE_W}}, {{TILE_H}}, 1)
fn focus_write_b(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) lid: u32) {
    let tx0 = i32(wg.x * TILE_W);
    let ty0 = i32(wg.y * TILE_H);
    load_tile(tx0, ty0, lid);
    workgroupBarrier();
    horizontal(lid, INNER_R, OUTER_R);
    workgroupBarrier();
    let px = tx0 + i32(lid % TILE_W);
    let py = ty0 + i32(lid / TILE_W);
    if (px >= i32(P.plane_w) || py >= i32(P.plane_h)) { return; }
    let ring = ring_value(lid, px, py, INNER_R, OUTER_R);
    let i = u32(py) * P.plane_w + u32(px);
    let f = div_rn(ring, max(green_luma_sigma(centre_luma(lid)), P.sigma_eps));
    // Combine with measure A's already-materialised field.
    focus_io[i] = max(focus_io[i], f);
}

// Reset the selection to the sentinels `Selection::new` uses: focus
// -infinity, index u16::MAX. Run outside every timed region.
@compute @workgroup_size(256)
fn reset_kernel(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x;
    if (i >= P.plane_w * P.plane_h) { return; }
    sel_focus[i] = bitcast<f32>(0xff800000u);
    sel_index[i] = NO_FRAME;
    sel_w0[i] = 0u;
    sel_w1[i] = 0u;
}

// --- controls --------------------------------------------------------------

// NULL: the same grid and workgroup shape as the focus kernel, and no memory
// traffic at all. The store is guarded by a condition the compiler cannot fold
// away (P is a uniform), so the kernel is not eliminated, but the branch is
// never taken. This bounds dispatch and scheduling overhead.
@compute @workgroup_size({{TILE_W}}, {{TILE_H}}, 1)
fn null_kernel(@builtin(workgroup_id) wg: vec3<u32>, @builtin(local_invocation_index) lid: u32) {
    if (P.plane_w == 0xffffffffu) {
        scratch[wg.x] = lid;
    }
}

// READ: touches every word of the frame exactly once and writes one word per
// workgroup. Positive control for read bandwidth.
@compute @workgroup_size(256)
fn read_kernel(@builtin(global_invocation_id) gid: vec3<u32>, @builtin(local_invocation_index) lid: u32,
               @builtin(workgroup_id) wg: vec3<u32>) {
    var acc = 0u;
    if (gid.x < arrayLength(&frame)) {
        acc = frame[gid.x];
    }
    sh_red[lid] = acc;
    workgroupBarrier();
    if (lid == 0u) {
        var s = 0u;
        for (var k = 0u; k < 256u; k = k + 1u) { s = s + sh_red[k]; }
        scratch[wg.x] = s;
    }
}

// COPY: reads every word and writes every word. Positive control for combined
// read+write bandwidth, and its time is predictable from the measured D2D rate.
@compute @workgroup_size(256)
fn copy_kernel(@builtin(global_invocation_id) gid: vec3<u32>) {
    if (gid.x < arrayLength(&frame)) {
        scratch[gid.x] = frame[gid.x];
    }
}
