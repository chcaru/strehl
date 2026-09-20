//! One-source CA staging; child of the existing GPU gather crate.
use super::*;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum Order { Before, StagedAfter }
#[derive(Clone,Copy)]
pub(crate) struct Stage { pub order:Order, pub pulls:[Similarity;3] }
pub(crate) struct Kernels { pre:wgpu::ComputePipeline, pub mhc:wgpu::ComputePipeline, pub gather:wgpu::ComputePipeline }

fn replaced(source:&str,old:&str,new:&str)->Result<String,String>{
    if source.matches(old).count()!=1 {return Err("CA shader source anchor changed".into());}
    Ok(source.replacen(old,new,1))
}
impl Kernels {
    fn new(gpu:&GpuGather)->Result<Self,String>{
        let base=include_str!("../native-gpu-gather/src/gather.wgsl").replace("\r\n","\n");
        // MHC stencil and summation are shared verbatim, only its source read changes.
        let corrected=replaced(&base,
            "return (f32(sensel(sy*p.dims.x+sx))-p.photometry.x)*p.photometry[channel(sx,sy)+1u];",
            "return bitcast<f32>(raw[sy*p.dims.x+sx]);")?;
        let guarded=replaced(&corrected,"let sensor=acc*p.inverse[ci]+p.photometry.x;",
            "if ((bitcast<u32>(acc)&0x7fffffffu)>=0x7f800000u) { return vec2(u32(p.inverse.w),0u); }\n let sensor=acc*p.inverse[ci]+p.photometry.x;")?;
        let start=base.find("@compute @workgroup_size(64)\nfn mhc(").ok_or("MHC start anchor")?;
        let end=base.find("fn weights(").ok_or("MHC end anchor")?;
        let pre=format!("{}{}{}",&base[..start],include_str!("prepass.wgsl"),&base[end..]);
        let pipeline=|source:&str,entry:&str|->Result<wgpu::ComputePipeline,String>{
            let (words,_)=strict_spirv::compile_source(true,source)?;
            let module=strict_spirv::module(&gpu.device,&words);
            let layout=gpu.device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor{
                label:None,bind_group_layouts:&[Some(&gpu.layout)],immediate_size:0});
            Ok(gpu.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor{
                label:Some("experimental CA ordering"),layout:Some(&layout),module:&module,
                entry_point:Some(entry),compilation_options:Default::default(),cache:None}))
        };
        Ok(Self{pre:pipeline(&pre,"mhc")?,mhc:pipeline(&guarded,"mhc")?,gather:pipeline(&guarded,"gather")?})
    }
    pub(crate) fn prepare(&self,gpu:&GpuGather,input:&Input<'_>,stage:Stage,
        source:&wgpu::Buffer,rgb:&wgpu::Buffer,out:&wgpu::Buffer,cover:&wgpu::Buffer,costs:&mut Costs)->Result<wgpu::Buffer,String>{
        let (w,h)=(input.geom.width*2,input.geom.height*2);let channels=if input.green_only{1}else{3};
        let bytes=(w*h*4*if stage.order==Order::Before{1}else{channels})as u64;
        let rows=32usize.min(h);let plan_bytes=(w*rows*3*16)as u64;
        let lim=gpu.device.limits();
        if [bytes,plan_bytes].iter().any(|&n|n>lim.max_storage_buffer_binding_size as u64||n>lim.max_buffer_size){return Err("CA staging buffer limit".into());}
        let buffer=|label,size,usage|gpu.device.create_buffer(&wgpu::BufferDescriptor{label:Some(label),size,usage,mapped_at_creation:false});
        let corrected=buffer("CA staged source",bytes,wgpu::BufferUsages::STORAGE);
        let plans=buffer("CA source coordinate strip",plan_bytes,wgpu::BufferUsages::STORAGE|wgpu::BufferUsages::COPY_DST);
        let mut p=Params{dims:[w as u32,h as u32,0,h as u32],photometry:[input.black,input.gain[0],input.gain[1],input.gain[2]],
            inverse:[input.inverse_gain[0],input.inverse_gain[1],input.inverse_gain[2],input.black.round().clamp(0.,65535.)],
            flags:[u32::from(input.green_only),u32::from(stage.order==Order::StagedAfter),0,0]};
        let uniform=gpu.device.create_buffer_init(&wgpu::util::BufferInitDescriptor{label:None,contents:bytemuck::bytes_of(&p),usage:wgpu::BufferUsages::UNIFORM|wgpu::BufferUsages::COPY_DST});
        let bind=|raw:&wgpu::Buffer,dst:&wgpu::Buffer|{
            let buffers=[&uniform,raw,dst,&plans,out,cover];let entries:Vec<_>=buffers.iter().enumerate().map(|(i,b)|wgpu::BindGroupEntry{binding:i as u32,resource:b.as_entire_binding()}).collect();
            gpu.device.create_bind_group(&wgpu::BindGroupDescriptor{label:None,layout:&gpu.layout,entries:&entries})
        };
        if stage.order==Order::StagedAfter {
            let initial=bind(source,rgb);let mut e=gpu.device.create_command_encoder(&Default::default());
            {let mut pass=e.begin_compute_pass(&Default::default());pass.set_pipeline(&gpu.mhc);pass.set_bind_group(0,&initial,&[]);pass.dispatch_workgroups(w.div_ceil(64)as u32,h as u32,1);}
            gpu.queue.submit([e.finish()]);gpu.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
        }
        let binding=bind(if stage.order==Order::Before{source}else{rgb},&corrected);
        let mut taps=vec![SamplePlan{x0:INVALID,y0:0,fx:0.,fy:0.};w*rows*3];
        for y0 in (0..h).step_by(rows){let count=rows.min(h-y0);let clock=Instant::now();
            taps.truncate(count*w*3);
            taps.par_chunks_mut(w*3).enumerate().for_each(|(dy,row)|{
                let y=y0+dy;
                for x in 0..w {for c in 0..3 {
                    row[3*x+c]=if stage.pulls[c]==Similarity::IDENTITY {
                        SamplePlan{x0:UNCONSUMED,y0:0,fx:0.,fy:0.}
                    }else{
                        let(sx,sy)=stage.pulls[c].apply_at(x as f64*0.5,y as f64*0.5,input.geom.width as f64*0.5,input.geom.height as f64*0.5);
                        if stage.order==Order::Before {plan_at(w/2,h/2,sx-(x%2)as f64*0.5,sy-(y%2)as f64*0.5)}else{plan_at(w,h,2.*sx,2.*sy)}
                    };
                }}
            });costs.coordinate_ms+=clock.elapsed().as_secs_f64()*1000.;
            p.dims[2]=y0 as u32;p.dims[3]=count as u32;
            gpu.queue.write_buffer(&uniform,0,bytemuck::bytes_of(&p));gpu.queue.write_buffer(&plans,0,bytemuck::cast_slice(&taps));
            let mut e=gpu.device.create_command_encoder(&Default::default());
            {let mut pass=e.begin_compute_pass(&Default::default());pass.set_pipeline(&self.pre);pass.set_bind_group(0,&binding,&[]);pass.dispatch_workgroups(w.div_ceil(64)as u32,count as u32,1);}
            gpu.queue.submit([e.finish()]);gpu.device.poll(wgpu::PollType::wait_indefinitely()).map_err(|e|e.to_string())?;
            costs.coordinate_upload_bytes+=(taps.len()*16)as u64;costs.parameter_upload_bytes+=std::mem::size_of::<Params>()as u64;
        }
        costs.device_buffer_bytes+=bytes+plan_bytes+std::mem::size_of::<Params>()as u64;
        Ok(corrected)
    }
}
impl GpuGather {
    pub fn run_ca_stage(&mut self,input:&Input<'_>,common:Similarity,ca_pulls:[Similarity;3],order:Order)->Result<Output,String>{
        if ca_pulls.iter().all(|t|*t==Similarity::IDENTITY){return self.run(input);}
        if ca_pulls.iter().chain([&common]).any(|t|[t.a.re,t.a.im,t.b.re,t.b.im].iter().any(|v|!v.is_finite())) {return Err("nonfinite CA transform".into());}
        if ca_pulls[1]!=Similarity::IDENTITY{return Err("CA green reference must be identity".into());}
        if self.ca_stage.is_none(){self.ca_stage=Some(Kernels::new(self)?);}
        let corrected=Input{data:input.data,stride:input.stride,active:input.active,geom:input.geom,black:input.black,
            gain:input.gain,inverse_gain:input.inverse_gain,pulls:[common;3],green_only:input.green_only,malvar:input.malvar,resampler:input.resampler};
        self.run_inner(&corrected,None,Some(Stage{order,pulls:ca_pulls}))
    }
}
