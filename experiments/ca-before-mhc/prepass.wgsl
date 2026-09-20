// Replaces only the mhc entry in the owned source shader. Reuses weights().
fn stage_value(x:u32,y:u32,c:u32)->f32 {
 let i=y*p.dims.x+x; let plan=plans[3u*((y-p.dims.z)*p.dims.x+x)+c];
 if (plan.x0==INVALID) { return bitcast<f32>(0x7fc00000u); }
 if (plan.x0==UNCONSUMED) {
  if (p.flags.y==0u) { return (f32(sensel(i))-p.photometry.x)*p.photometry[c+1u]; }
  return bitcast<f32>(raw[select(3u*i+c,i,p.flags.x!=0u)]);
 }
 let wx=weights(plan.fx); let wy=weights(plan.fy);var acc=0.;
 for(var dy=0u;dy<4u;dy+=1u){var r=0.;
  for(var dx=0u;dx<4u;dx+=1u){
   var v:f32;
   if(p.flags.y==0u){
    let sx=2u*(plan.x0+dx-1u)+(x&1u);let sy=2u*(plan.y0+dy-1u)+(y&1u);
    v=(f32(sensel(sy*p.dims.x+sx))-p.photometry.x)*p.photometry[c+1u];
   }else{
    let j=(plan.y0+dy-1u)*p.dims.x+plan.x0+dx-1u;
    v=bitcast<f32>(raw[select(3u*j+c,j,p.flags.x!=0u)]);
   }
   r=r+v*wx[dx];
  }acc=acc+r*wy[dy];
 }return acc;
}
@compute @workgroup_size(64)
fn mhc(@builtin(global_invocation_id) id:vec3<u32>){
 if(id.x>=p.dims.x || id.y>=p.dims.w){return;}
 let x=id.x;let y=id.y+p.dims.z;let i=y*p.dims.x+x;
 if(p.flags.y==0u){rgb[i]=stage_value(x,y,channel(x,y));}
 else if(p.flags.x!=0u){rgb[i]=stage_value(x,y,1u);}
 else{for(var c=0u;c<3u;c+=1u){rgb[3u*i+c]=stage_value(x,y,c);}}
}
