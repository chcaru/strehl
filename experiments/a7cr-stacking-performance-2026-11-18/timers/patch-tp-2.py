"""Timers and thread names in the GPU fold and the render (scratch copy only)."""
from patchlib import patch

MOD = '#[path = "../../../trace-points.rs"]\npub mod tp;'

# ---------------------------------------------------------------- strehl-gpu
patch('crates/strehl-gpu/src/lib.rs', [
    ('''        let (words, decorated_results) = strict::compile(SHADER)?;
        let mut descriptor = wgpu::InstanceDescriptor::new_without_display_handle();''',
     '''        let tp_compile = crate::tp::span("gpu.shader_compile", 0);
        let (words, decorated_results) = strict::compile(SHADER)?;
        drop(tp_compile);
        let tp_device = crate::tp::span("gpu.instance_adapter_device", 0);
        let mut descriptor = wgpu::InstanceDescriptor::new_without_display_handle();'''),
    ('''        .map_err(|e| e.to_string())?;
        let limits = device.limits();
''',
     '''        .map_err(|e| e.to_string())?;
        drop(tp_device);
        let tp_buffers = crate::tp::span("gpu.buffers_and_binds", 0);
        let limits = device.limits();
'''),
    ('''        // SAFETY: the words are this crate's own embedded shader, validated by
        // naga and altered only by added NoContraction decorations (`strict`).
        // Passthrough is required because naga's SPIR-V frontend drops them.
        let module = unsafe {''',
     '''        drop(tp_buffers);
        let tp_pipelines = crate::tp::span("gpu.module_and_pipelines", 0);
        // SAFETY: the words are this crate's own embedded shader, validated by
        // naga and altered only by added NoContraction decorations (`strict`).
        // Passthrough is required because naga's SPIR-V frontend drops them.
        let module = unsafe {'''),
    ('''        let profile = profiling.then(|| Profile::new(&device, &queue));
        let mut fold = Self {''',
     '''        drop(tp_pipelines);
        let _tp_reset = crate::tp::span("gpu.first_reset", 0);
        let profile = profiling.then(|| Profile::new(&device, &queue));
        let mut fold = Self {'''),
    ('''        if self.acc.len() > 1 {
            return Ok(());
        }
        let bytes = self.layout.acc_len.iter().sum::<u64>() * 4;''',
     '''        if self.acc.len() > 1 {
            return Ok(());
        }
        let _tp = crate::tp::span("gpu.second_accumulator", 0);
        let bytes = self.layout.acc_len.iter().sum::<u64>() * 4;'''),
    ('''        let up = &mut self.upload[slot];
        if let Some(index) = up.copy.take() {
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .map_err(|e| format!("GPU upload wait: {e:?}"))?;
        }''',
     '''        let up = &mut self.upload[slot];
        let tp_poll = crate::tp::span("gpu.stage_poll", 0);
        if let Some(index) = up.copy.take() {
            self.device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(index),
                    timeout: None,
                })
                .map_err(|e| format!("GPU upload wait: {e:?}"))?;
        }
        drop(tp_poll);
        let tp_copy = crate::tp::span("gpu.stage_copy", 0);'''),
    ('''        let size = (sources.len() * per) as u64;
        up.mapped.store(false, std::sync::atomic::Ordering::Release);
        up.buffer.unmap();''',
     '''        drop(tp_copy);
        let _tp_submit = crate::tp::span("gpu.stage_submit", 0);
        let size = (sources.len() * per) as u64;
        up.mapped.store(false, std::sync::atomic::Ordering::Release);
        up.buffer.unmap();'''),
    ('''    pub fn luma_collect(&mut self, pending: PendingLuma) -> Result<Vec<f32>, String> {
        self.device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(pending.index),
                timeout: None,
            })
            .map_err(|e| format!("GPU luma wait: {e:?}"))?;
        let out = {''',
     '''    pub fn luma_collect(&mut self, pending: PendingLuma) -> Result<Vec<f32>, String> {
        let tp_poll = crate::tp::span("gpu.luma_poll", 0);
        self.device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(pending.index),
                timeout: None,
            })
            .map_err(|e| format!("GPU luma wait: {e:?}"))?;
        drop(tp_poll);
        let _tp_copy = crate::tp::span("gpu.luma_copy", 0);
        let out = {'''),
    ('''    fn read_chunk(&mut self, merge: &mut BandMerge, ops: Option<FoldCombine>) {
        let l = &self.layout;''',
     '''    fn read_chunk(&mut self, merge: &mut BandMerge, ops: Option<FoldCombine>) {
        let _tp_all = crate::tp::span("gpu.read_chunk", 0);
        let mut tp_wait = crate::tp::sum("gpu.read_wait", 0);
        let mut tp_copy = crate::tp::sum("gpu.read_copy", 0);
        let l = &self.layout;'''),
    ('''                let index = self.queue.submit([encoder.finish()]);
                let slice = readback.slice(..n as u64 * 4);
                slice.map_async(wgpu::MapMode::Read, |r| r.expect("map fold readback"));
                self.device
                    .poll(wgpu::PollType::Wait {
                        submission_index: Some(index),
                        timeout: None,
                    })
                    .expect("GPU fold wait");
                {''',
     '''                let index = self.queue.submit([encoder.finish()]);
                let slice = readback.slice(..n as u64 * 4);
                slice.map_async(wgpu::MapMode::Read, |r| r.expect("map fold readback"));
                tp_wait.add(|| {
                    self.device
                        .poll(wgpu::PollType::Wait {
                            submission_index: Some(index),
                            timeout: None,
                        })
                        .expect("GPU fold wait")
                });
                let tp_c = std::time::Instant::now();
                {'''),
    ('''                readback.unmap();
                start += n;''',
     '''                tp_copy.total += tp_c.elapsed().as_secs_f64();
                readback.unmap();
                start += n;'''),
], append=MOD)

# ---------------------------------------------------------------- strehl-cli
patch('crates/strehl-cli/src/lib.rs', [], append=MOD)
patch('crates/strehl-cli/src/main.rs', [
    ('''    unsafe { strehl_cli::run_from(std::env::args_os()) }''',
     '''    let result = unsafe { strehl_cli::run_from(std::env::args_os()) };
    strehl_cli::tp_dump_all();
    result'''),
])
patch('crates/strehl-cli/src/lib.rs', [], append='''pub fn tp_dump_all() {
    tp::dump("cli");
    strehl_raw::tp_dump();
    #[cfg(feature = "gpu")]
    strehl_gpu::tp::dump("gpu");
}''')
patch('crates/strehl-raw/src/lib.rs', [], append='''pub fn tp_dump() {
    strehl_raw_codec::tp::dump("codec");
}''')

patch('crates/strehl-cli/src/merge_cmd/decode-ahead.rs', [
    ('''            let (index, spare) = {
                let mut st = self.lock();
                loop {
                    if !st.retired.is_empty() {''',
     '''            let tp_claim = crate::tp::span("ahead.decoder_wait", 0);
            let (index, spare) = {
                let mut st = self.lock();
                loop {
                    if !st.retired.is_empty() {'''),
    ('''                let index = self.plan[st.claimed];
                st.claimed += 1;
                (index, st.spare.pop())
            };''',
     '''                let index = self.plan[st.claimed];
                st.claimed += 1;
                (index, st.spare.pop())
            };
            drop(tp_claim);
            let _tp_plane = crate::tp::span("ahead.decode_plane", index as u64);'''),
    ('''            self.inner.prefetch(index);
        }''',
     '''            let _tp = crate::tp::span("ahead.prefetch_plane", index as u64);
            self.inner.prefetch(index);
        }'''),
])

patch('crates/strehl-cli/src/merge_cmd.rs', [
    # --- LumaTap
    ('''            let (index, pending) = self.pending.pop_front().expect("pending luma");
            let luma = gpu.luma_collect(pending).map_err(|e| anyhow::anyhow!(e))?;
            {
                let (count, signal) = &*self.busy;''',
     '''            let (index, pending) = self.pending.pop_front().expect("pending luma");
            let luma = gpu.luma_collect(pending).map_err(|e| anyhow::anyhow!(e))?;
            let tp_wait = crate::tp::span("luma.wait_recording", index as u64);
            {
                let (count, signal) = &*self.busy;'''),
    ('''            let busy = std::sync::Arc::clone(&self.busy);
            rayon::spawn(move || {
                depth_guide::record(index, &luma);''',
     '''            drop(tp_wait);
            let busy = std::sync::Arc::clone(&self.busy);
            rayon::spawn(move || {
                let _tp = crate::tp::span("luma.record", index as u64);
                depth_guide::record(index, &luma);'''),
    # --- gpu_start
    ('''        let frame = source
            .decode(index)
            .with_context(|| format!("frame {index}"))?;
        // A checked pixel-shift group's other members, parked by the decode
        // (`load_frame_impl_observed` takes them the same way).
        let measured = source.take_measured(index);''',
     '''        let tp_wait = crate::tp::span("fold.wait_decode", index as u64);
        let frame = source
            .decode(index)
            .with_context(|| format!("frame {index}"))?;
        drop(tp_wait);
        let _tp_start = crate::tp::span("fold.gpu_start_rest", index as u64);
        // A checked pixel-shift group's other members, parked by the decode
        // (`load_frame_impl_observed` takes them the same way).
        let measured = source.take_measured(index);'''),
    ('''        let staged = gpu
            .stage(&strehl_gpu::RawFrame {''',
     '''        let tp_stage = crate::tp::span("fold.stage", index as u64);
        let staged = gpu
            .stage(&strehl_gpu::RawFrame {'''),
    ('''        // The device holds its own copy now.
        if let Some(m) = measured {
            crate::pixel_shift_cmd::recycle_members(m.members);
        }
        source.retire(frame);
        let probe = match (self.floor.as_ref(), t) {''',
     '''        drop(tp_stage);
        let tp_retire = crate::tp::span("fold.retire", index as u64);
        // The device holds its own copy now.
        if let Some(m) = measured {
            crate::pixel_shift_cmd::recycle_members(m.members);
        }
        source.retire(frame);
        drop(tp_retire);
        let _tp_probe = crate::tp::span("fold.probe_submit", index as u64);
        let probe = match (self.floor.as_ref(), t) {'''),
    # --- gpu_finish
    ('''        if let (Some(floor), Some((pending, rects))) = (self.floor.as_mut(), probe) {
            let out = gpu.probe_collect(pending).map_err(|e| anyhow::anyhow!(e))?;''',
     '''        if let (Some(floor), Some((pending, rects))) = (self.floor.as_mut(), probe) {
            let tp_collect = crate::tp::span("fold.probe_collect", index as u64);
            let out = gpu.probe_collect(pending).map_err(|e| anyhow::anyhow!(e))?;
            drop(tp_collect);'''),
    ('''        let frame_beta = (!self.beta.is_empty()).then_some(self.beta.as_slice());
        let added = if depth_guide::tap_active() {''',
     '''        let frame_beta = (!self.beta.is_empty()).then_some(self.beta.as_slice());
        let tp_add = crate::tp::span("fold.add_staged", index as u64);
        let added = if depth_guide::tap_active() {'''),
    ('''        self.swap_half();
        self.next_half();
        added.map_err(|e| anyhow::anyhow!(e))?;
        let gpu = self
            .gpu
            .as_mut()
            .expect("GPU preparation without a GPU fold");
        self.luma_tap.collect(gpu, LumaTap::AHEAD)?;''',
     '''        drop(tp_add);
        self.swap_half();
        self.next_half();
        added.map_err(|e| anyhow::anyhow!(e))?;
        let gpu = self
            .gpu
            .as_mut()
            .expect("GPU preparation without a GPU fold");
        let tp_luma = crate::tp::span("fold.luma_collect", index as u64);
        self.luma_tap.collect(gpu, LumaTap::AHEAD)?;
        drop(tp_luma);'''),
    ('''        if let Some(gpu) = self.gpu.as_mut() {
            self.luma_tap.finish(gpu)?;
        }
        Ok(folded)''',
     '''        if let Some(gpu) = self.gpu.as_mut() {
            let _tp = crate::tp::span("fold.luma_finish", 0);
            self.luma_tap.finish(gpu)?;
        }
        Ok(folded)'''),
    # --- startup
    ('''    let stack_groups = crate::pixel_shift_cmd::StackGroups::from_env(&opts.dir, opts.limit)?;
    let paths = match &stack_groups {
        Some(g) => g.planes.clone(),
        None => crate::raw_paths(&opts.dir, opts.limit)?,
    };
    let paths = only_frame(paths);
    if let Some(g) = &stack_groups {
        eprintln!("{}", g.banner());
    }''',
     '''    let tp_groups = crate::tp::span("start.stack_groups", 0);
    let stack_groups = crate::pixel_shift_cmd::StackGroups::from_env(&opts.dir, opts.limit)?;
    drop(tp_groups);
    let paths = match &stack_groups {
        Some(g) => g.planes.clone(),
        None => crate::raw_paths(&opts.dir, opts.limit)?,
    };
    let paths = only_frame(paths);
    if let Some(g) = &stack_groups {
        eprintln!("{}", g.banner());
    }'''),
    ('''    crate::sony_focus_cmd::print_preflight(&paths);
    ensure!(
        paths.len() < u16::MAX as usize,''',
     '''    let tp_focus = crate::tp::span("start.sony_focus_preflight", 0);
    crate::sony_focus_cmd::print_preflight(&paths);
    drop(tp_focus);
    ensure!(
        paths.len() < u16::MAX as usize,''', 1),
    ('''    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;''',
     '''    let tp_first = crate::tp::span("start.first_decode", 0);
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    drop(tp_first);''', 1),
    ('''    progress.stage("alignment");
    let t_align = Instant::now();''',
     '''    progress.stage("alignment");
    let _tp_align = crate::tp::span("start.alignment_load", 0);
    let t_align = Instant::now();'''),
    # --- fold set-up and tail
    ('''    let mut worker = BandWorker::new(domain, cfg);
    eprintln!(
        "gpu fold        : {}",''',
     '''    let tp_bw = crate::tp::span("main.bandworker_new", 0);
    let mut worker = BandWorker::new(domain, cfg);
    drop(tp_bw);
    let tp_attach = crate::tp::span("main.attach_gpu", 0);
    eprintln!(
        "gpu fold        : {}",'''),
    ('''    // Preparing on the device folds frame by frame; decoding still runs ahead.
    let lookahead = if worker.gpu_prep { 1 } else { lookahead };''',
     '''    drop(tp_attach);
    // Preparing on the device folds frame by frame; decoding still runs ahead.
    let lookahead = if worker.gpu_prep { 1 } else { lookahead };'''),
    ('''    let pool = ThreadPoolBuilder::new()
        .num_threads(workers)
        .build()
        .context("building Pyramid execution pool")?;''',
     '''    let pool = ThreadPoolBuilder::new()
        .num_threads(workers)
        .thread_name(|i| format!("pool-{i}"))
        .build()
        .context("building Pyramid execution pool")?;'''),
    ('''                .num_threads(workers.min(GPU_PREP_FOLD_THREADS))
                .build()''',
     '''                .num_threads(workers.min(GPU_PREP_FOLD_THREADS))
                .thread_name(|i| format!("foldpool-{i}"))
                .build()'''),
    ('''            let ahead = &ahead;
            scope.spawn(move || {
                // Measured where decoding bounds the fold: GPU preparation.
                if pin {
                    decode_ahead::pin_decoder(i, decoders);
                }
                ahead.run_decoder()
            });
        }
        for _ in 0..original_source.prefetchers() {
            scope.spawn(|| ahead.run_prefetcher(decode_ahead::PREFETCH_AHEAD));
        }''',
     '''            let ahead = &ahead;
            std::thread::Builder::new()
                .name(format!("decoder-{i}"))
                .spawn_scoped(scope, move || {
                    // Measured where decoding bounds the fold: GPU preparation.
                    if pin {
                        decode_ahead::pin_decoder(i, decoders);
                    }
                    ahead.run_decoder()
                })
                .expect("spawn decoder");
        }
        for i in 0..original_source.prefetchers() {
            let ahead = &ahead;
            std::thread::Builder::new()
                .name(format!("prefetch-{i}"))
                .spawn_scoped(scope, move || {
                    ahead.run_prefetcher(decode_ahead::PREFETCH_AHEAD)
                })
                .expect("spawn prefetcher");
        }'''),
    ('''                {
                    worker.finish_chunk(&mut merged, &mut merged_alt);
                }''',
     '''                {
                    let _tp = crate::tp::span("main.finish_chunk", 0);
                    worker.finish_chunk(&mut merged, &mut merged_alt);
                }'''),
    ('''        depth_guide::finish_tap()?;
        drop(tap);''',
     '''        let tp_tap = crate::tp::span("main.finish_tap", 0);
        depth_guide::finish_tap()?;
        drop(tp_tap);
        drop(tap);'''),
    ('''        gather_restoration_references(
            source, domain, cfg, levels, &noise, warps, ca, workers, &pool,
        )?;
    }''',
     '''        let _tp = crate::tp::span("main.reference_tiles", 0);
        gather_restoration_references(
            source, domain, cfg, levels, &noise, warps, ca, workers, &pool,
        )?;
    }'''),
    ('''    } else {
        drop(worker);
    }
    let mut merge = merged.context("no frames were folded")?;''',
     '''    } else {
        let _tp = crate::tp::span("main.drop_worker", 0);
        drop(worker);
    }
    let mut merge = merged.context("no frames were folded")?;'''),
    ('''        let mut ws = Workspace::new(&sizes);
        let even_planes = merge.finish(&mut ws);
        let odd_planes = odd.finish(&mut ws);
        merge.absorb(&odd);
        drop(odd);''',
     '''        let tp = crate::tp::span("main.halves_workspace", 0);
        let mut ws = Workspace::new(&sizes);
        drop(tp);
        let tp = crate::tp::span("main.half_even_finish", 0);
        let even_planes = merge.finish(&mut ws);
        drop(tp);
        let tp = crate::tp::span("main.half_odd_finish", 0);
        let odd_planes = odd.finish(&mut ws);
        drop(tp);
        let tp = crate::tp::span("main.absorb_odd", 0);
        merge.absorb(&odd);
        drop(tp);
        let tp = crate::tp::span("main.drop_odd", 0);
        drop(odd);
        drop(tp);'''),
    ('''    let (mut planes, ensemble_report) = merge.finish_with_report(&mut ws);''',
     '''    let tp_full = crate::tp::span("main.finish_full", 0);
    let (mut planes, ensemble_report) = merge.finish_with_report(&mut ws);
    drop(tp_full);'''),
    # --- write path
    ('''        let mut planes: Vec<Vec<f32>> = Vec::with_capacity(4);
        for (p, gain) in spec {
            let mut v: Vec<f32> = (0..n).map(|i| norm(val(p, i), gain)).collect();''',
     '''        let tp_native = crate::tp::span("write.native_planes", 0);
        let mut planes: Vec<Vec<f32>> = Vec::with_capacity(4);
        for (p, gain) in spec {
            let mut v: Vec<f32> = (0..n).map(|i| norm(val(p, i), gain)).collect();'''),
    ('''        for py in 0..geom.height {
            let (top, bot) = mosaic[py * 2 * mw..].split_at_mut(mw);''',
     '''        drop(tp_native);
        let tp_mosaic = crate::tp::span("write.mosaic", 0);
        for py in 0..geom.height {
            let (top, bot) = mosaic[py * 2 * mw..].split_at_mut(mw);'''),
    ('''        if ca_refine::preview_active() {
            // A lateral-CA preview pass: measure what the correction leaves on
            // the white-balanced mosaic -- before any demosaic borrows one
            // channel's detail for another, or a colour matrix mixes them --
            // and write nothing.
            ca_refine::capture(mw, mh, &mosaic);''',
     '''        drop(tp_mosaic);
        if ca_refine::preview_active() {
            // A lateral-CA preview pass: measure what the correction leaves on
            // the white-balanced mosaic -- before any demosaic borrows one
            // channel's detail for another, or a colour matrix mixes them --
            // and write nothing.
            let _tp = crate::tp::span("preview.ca_measure", 0);
            ca_refine::capture(mw, mh, &mosaic);'''),
    ('''            let mut rgb = match carried {
                Some(raw) => {
                    let mut all = planes;''',
     '''            let tp_rgb = crate::tp::span("write.carried_rgb", 0);
            let mut rgb = match carried {
                Some(raw) => {
                    let mut all = planes;'''),
    ('''            drop(mosaic);
            let mut restored_ok = false;''',
     '''            drop(mosaic);
            drop(tp_rgb);
            let mut restored_ok = false;'''),
    ('''                let restored = optical_restore::restore(
                    &mut rgb,''',
     '''                let _tp = crate::tp::span("write.restore", 0);
                let restored = optical_restore::restore(
                    &mut rgb,'''),
    ('''                colour_carry::smooth_chroma(&mut rgb, mw, mh);
            }''',
     '''                let _tp = crate::tp::span("write.smooth_chroma", 0);
                colour_carry::smooth_chroma(&mut rgb, mw, mh);
            }'''),
    ('''            image_out::write_rgb_full(path, mw, mh, &rgb, &dev, linear_master, baked_recipe)?;
            if let Some(progress) = progress {
                progress.render_step("write", "finished");
            }
            eprintln!();
            eprintln!(
                "wrote           : {} ({mw} x {mh}, 16-bit RGB, {}, {}{})",''',
     '''            let tp_write = crate::tp::span("write.develop_and_tiff", 0);
            image_out::write_rgb_full(path, mw, mh, &rgb, &dev, linear_master, baked_recipe)?;
            drop(tp_write);
            if let Some(progress) = progress {
                progress.render_step("write", "finished");
            }
            eprintln!();
            eprintln!(
                "wrote           : {} ({mw} x {mh}, 16-bit RGB, {}, {}{})",'''),
])
print('ok')
