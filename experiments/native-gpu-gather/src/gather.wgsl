// Current MHC/Catmull arithmetic only. Geometry/support/floor are CPU f64.
// One invocation owns both packed destination halves: no overlapping writes.
struct Params { dims: vec4<u32>, photometry: vec4<f32>, inverse: vec4<f32>, flags: vec4<u32> }
struct Plan { x0: u32, y0: u32, fx: f32, fy: f32 }
@group(0) @binding(0) var<uniform> p: Params;
@group(0) @binding(1) var<storage, read> raw: array<u32>;
@group(0) @binding(2) var<storage, read_write> rgb: array<f32>;
@group(0) @binding(3) var<storage, read> plans: array<Plan>;
@group(0) @binding(4) var<storage, read_write> output: array<u32>;
@group(0) @binding(5) var<storage, read_write> coverage: array<u32>;
const INVALID: u32 = 0xffffffffu;
const UNCONSUMED: u32 = 0xfffffffeu;
const FG = array<vec3<f32>,9>(
 vec3(0.,0.,4.),vec3(-1.,0.,2.),vec3(1.,0.,2.),vec3(0.,-1.,2.),vec3(0.,1.,2.),
 vec3(-2.,0.,-1.),vec3(2.,0.,-1.),vec3(0.,-2.,-1.),vec3(0.,2.,-1.));
const FH = array<vec3<f32>,11>(
 vec3(0.,0.,5.),vec3(-1.,0.,4.),vec3(1.,0.,4.),vec3(-2.,0.,-1.),vec3(2.,0.,-1.),
 vec3(-1.,-1.,-1.),vec3(1.,-1.,-1.),vec3(-1.,1.,-1.),vec3(1.,1.,-1.),
 vec3(0.,-2.,0.5),vec3(0.,2.,0.5));
const FV = array<vec3<f32>,11>(
 vec3(0.,0.,5.),vec3(0.,-1.,4.),vec3(0.,1.,4.),vec3(0.,-2.,-1.),vec3(0.,2.,-1.),
 vec3(-1.,-1.,-1.),vec3(1.,-1.,-1.),vec3(-1.,1.,-1.),vec3(1.,1.,-1.),
 vec3(-2.,0.,0.5),vec3(2.,0.,0.5));
const FX = array<vec3<f32>,9>(
 vec3(0.,0.,6.),vec3(-1.,-1.,2.),vec3(1.,-1.,2.),vec3(-1.,1.,2.),vec3(1.,1.,2.),
 vec3(-2.,0.,-1.5),vec3(2.,0.,-1.5),vec3(0.,-2.,-1.5),vec3(0.,2.,-1.5));
fn channel(x:u32,y:u32)->u32 {
 if ((y&1u)==0u && (x&1u)==0u) { return 0u; }
 if ((y&1u)==1u && (x&1u)==1u) { return 2u; }
 return 1u;
}
fn sensel(i:u32)->u32 { return (raw[i/2u] >> (16u*(i&1u))) & 65535u; }
fn reflect(index:i32,n:i32)->u32 {
 if (n<=1) { return 0u; }
 var i=index;
 while (i<0 || i>=n) {
  if (i<0) { i=-i; } else { i=2*(n-1)-i; }
 }
 return u32(i);
}
fn mosaic(x:i32,y:i32)->f32 {
 let sx=reflect(x,i32(p.dims.x)); let sy=reflect(y,i32(p.dims.y));
 return (f32(sensel(sy*p.dims.x+sx))-p.photometry.x)*p.photometry[channel(sx,sy)+1u];
}
fn conv(x:i32,y:i32,kind:u32)->f32 {
 var acc=0.; let count=select(9u,11u,kind==1u || kind==2u);
 for(var i=0u;i<count;i+=1u) {
  var t:vec3<f32>;
  switch kind { case 0u: { t=FG[i]; } case 1u: { t=FH[i]; }
   case 2u: { t=FV[i]; } default: { t=FX[i]; } }
  acc=acc+t.z*mosaic(x+i32(t.x),y+i32(t.y));
 }
 return acc*0.125;
}
@compute @workgroup_size(64)
fn mhc(@builtin(global_invocation_id) id:vec3<u32>) {
 if (id.x>=p.dims.x || id.y>=p.dims.y) { return; }
 let x=i32(id.x); let y=i32(id.y); let i=3u*(id.y*p.dims.x+id.x);
 let known=mosaic(x,y);
 if (p.flags.x!=0u) {
  if (channel(id.x,id.y)==1u) { rgb[id.y*p.dims.x+id.x]=known; }
  else { rgb[id.y*p.dims.x+id.x]=conv(x,y,0u); }
  return;
 }
 let phase=(id.y&1u)*2u+(id.x&1u);
 var v:vec3<f32>;
 switch phase {
  case 0u: { v=vec3(known,conv(x,y,0u),conv(x,y,3u)); }
  case 3u: { v=vec3(conv(x,y,3u),conv(x,y,0u),known); }
  case 1u: { v=vec3(conv(x,y,1u),known,conv(x,y,2u)); }
  default: { v=vec3(conv(x,y,2u),known,conv(x,y,1u)); }
 }
 rgb[i]=v.x; rgb[i+1u]=v.y; rgb[i+2u]=v.z;
}
fn weights(f:f32)->vec4<f32> {
 let f2=f*f; let f3=f2*f;
 return vec4(-0.5*f3+f2-0.5*f,1.5*f3-2.5*f2+1.,
             -1.5*f3+2.*f2+0.5*f,0.5*f3-0.5*f2);
}
// Rust f32::round is ties-away; WGSL round is not its replacement.
// Truncate first, then compare the exact fractional remainder (no x+0.5).
fn quantize(v:f32)->u32 {
 let magnitude=bitcast<u32>(v)&0x7fffffffu;
 if (magnitude>0x7f800000u) { return 0u; }
 if (v<=0.) { return 0u; }
 if (v>=65535.) { return 65535u; }
 let whole=u32(v);
 return whole+select(0u,1u,v-f32(whole)>=0.5);
}
fn gather_one(local:u32)->vec2<u32> {
 let i=p.dims.z*p.dims.x+local; let plan=plans[local];
 if (plan.x0==UNCONSUMED) { return vec2(sensel(i),0u); }
 if (plan.x0==INVALID) { return vec2(u32(p.inverse.w),0u); }
 let ci=channel(i%p.dims.x,i/p.dims.x);
 let wx=weights(plan.fx); let wy=weights(plan.fy); var acc=0.;
 for(var dy=0u;dy<4u;dy+=1u) {
  let row=(plan.y0+dy-1u)*p.dims.x+plan.x0-1u; var r=0.;
  for(var dx=0u;dx<4u;dx+=1u) { r=r+rgb[select(3u,1u,p.flags.x!=0u)*(row+dx)+select(ci,0u,p.flags.x!=0u)]*wx[dx]; }
  acc=acc+r*wy[dy];
 }
 let sensor=acc*p.inverse[ci]+p.photometry.x;
 return vec2(quantize(sensor),1u);
}
@compute @workgroup_size(64)
fn gather(@builtin(global_invocation_id) id:vec3<u32>) {
 let words=p.dims.x*p.dims.w/2u; if (id.x>=words) { return; }
 let a=gather_one(2u*id.x); let b=gather_one(2u*id.x+1u);
 output[id.x]=a.x | (b.x<<16u); coverage[id.x]=a.y | (b.y<<1u);
}

// Literal control seam: calls the very same quantizer used by gather_one.
@compute @workgroup_size(64)
fn quantize_vector(@builtin(global_invocation_id) id:vec3<u32>) {
 if (id.x<p.dims.w) { output[id.x]=quantize(plans[id.x].fx); }
}
