struct Parameters {
    uv: vec4<f32>,
    // native units per developed white, peak in native units, opacity, mode
    light: vec4<f32>,
};
@group(0) @binding(0) var photograph: texture_2d<f32>;
@group(0) @binding(1) var<uniform> parameters: Parameters;

struct Vertex {
    @builtin(position) position: vec4<f32>,
    @location(0) uv: vec2<f32>,
};
@vertex
fn vertex(@builtin(vertex_index) index: u32) -> Vertex {
    let positions = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, 1.0), vec2<f32>(3.0, 1.0), vec2<f32>(-1.0, -3.0));
    let p = positions[index];
    var out: Vertex;
    out.position = vec4<f32>(p, 0.0, 1.0);
    out.uv = mix(parameters.uv.xy, parameters.uv.zw, vec2<f32>((p.x + 1.0) * 0.5, (1.0 - p.y) * 0.5));
    return out;
}

// RGBA32Float is not universally filterable. Four exact f32 loads provide
// bilinear interpolation without a float16 working texture or optional feature.
fn sample_linear(uv: vec2<f32>) -> vec3<f32> {
    let dimensions = vec2<i32>(textureDimensions(photograph));
    let p = uv * vec2<f32>(dimensions) - 0.5;
    let a = vec2<i32>(floor(p));
    let t = fract(p);
    let end = dimensions - vec2<i32>(1);
    let c00 = textureLoad(photograph, clamp(a, vec2<i32>(0), end), 0).rgb;
    let c10 = textureLoad(photograph, clamp(a + vec2<i32>(1, 0), vec2<i32>(0), end), 0).rgb;
    let c01 = textureLoad(photograph, clamp(a + vec2<i32>(0, 1), vec2<i32>(0), end), 0).rgb;
    let c11 = textureLoad(photograph, clamp(a + vec2<i32>(1, 1), vec2<i32>(0), end), 0).rgb;
    return mix(mix(c00, c10, t.x), mix(c01, c11, t.x), t.y);
}

@fragment
fn fragment(in: Vertex) -> @location(0) vec4<f32> {
    var light = sample_linear(in.uv);
    if parameters.light.w >= 1.0 {
        if parameters.light.w >= 2.0 {
            light = select(light / 12.92, pow((light + 0.055) / 1.055, vec3<f32>(2.4)), light > vec3<f32>(0.04045));
        }
        let alpha = parameters.light.z;
        return vec4<f32>(light * parameters.light.x * alpha, alpha);
    }
    light *= parameters.light.x;
    // Preserve hue when fitting measured display headroom. Negative components
    // remain representable in scRGB, rather than clipping wide-gamut colors.
    let peak = max(max(light.r, light.g), light.b);
    light *= min(1.0, parameters.light.y / max(peak, 0.000001));
    let alpha = parameters.light.z;
    return vec4<f32>(light * alpha, alpha);
}
