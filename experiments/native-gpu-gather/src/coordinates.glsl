#version 450 core
// Owned coordinate planner only. All nontrivial constants arrive as binary f64.
// Exact dyadic f32 literals are explicitly widened because Naga's GLSL parser
// does not accept double literals. No image sample is processed here.
layout(local_size_x=64, local_size_y=1, local_size_z=1) in;
layout(set=0, binding=0, std430) readonly buffer Transforms { dvec4 pull[3]; } transforms;
layout(set=0, binding=1, std140) uniform Parameters {
    uvec4 dims; vec4 photometry; vec4 inverse; uvec4 flags;
} p;
struct Plan { uint x0; uint y0; float fx; float fy; };
layout(set=0, binding=2, std430) buffer Plans { Plan values[]; } plans;
void main() {
    uint i = gl_GlobalInvocationID.x;
    if (i >= p.dims.x * p.dims.w) { return; }
    uint x = i % p.dims.x;
    uint y = p.dims.z + i / p.dims.x;
    uint ci = ((y & 1u) == 0u && (x & 1u) == 0u) ? 0u :
              (((y & 1u) == 1u && (x & 1u) == 1u) ? 2u : 1u);
    Plan result = Plan(0xffffffffu, 0u, 0.0, 0.0);
    if (p.flags.x != 0u && ci != 1u) {
        result.x0 = 0xfffffffeu; plans.values[i] = result; return;
    }
    // Same grouping as Cx::mul, Cx::add, Similarity::apply_at, then *2.
    double cx = double(p.dims.x / 2u) * double(0.5);
    double cy = double(p.dims.y / 2u) * double(0.5);
    double px = double(x / 2u) + double(x % 2u) * double(0.5);
    double py = double(y / 2u) + double(y % 2u) * double(0.5);
    double dx = px - cx; double dy = py - cy;
    dvec4 t = transforms.pull[ci];
    double sx = double(2.0) * (((t.x * dx - t.y * dy) + t.z) + cx);
    double sy = double(2.0) * (((t.x * dy + t.y * dx) + t.w) + cy);
    if (isnan(sx) || isinf(sx) || isnan(sy) || isinf(sy) ||
        sx < double(1.5) || sy < double(1.5) ||
        sx > double(p.dims.x) - double(2.5) || sy > double(p.dims.y) - double(2.5)) {
        plans.values[i] = result; return;
    }
    sx = clamp(sx, double(1.0), double(p.dims.x - 2u));
    sy = clamp(sy, double(1.0), double(p.dims.y - 2u));
    result.x0 = min(uint(floor(sx)), p.dims.x - 3u);
    result.y0 = min(uint(floor(sy)), p.dims.y - 3u);
    result.fx = float(sx - double(result.x0));
    result.fy = float(sy - double(result.y0));
    plans.values[i] = result;
}
