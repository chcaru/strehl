"""Timers in the CPU frame preparation and the reference pass (scratch copy only)."""
from patchlib import patch

patch('crates/strehl-cli/src/merge_cmd.rs', [
    ('''        let mut frame = source
            .decode(index)
            .with_context(|| format!("frame {index}"))?;
        scratch.measured = source.take_measured(index);''',
     '''        let tp_dec = crate::tp::span("prep.decode", index as u64);
        let mut frame = source
            .decode(index)
            .with_context(|| format!("frame {index}"))?;
        drop(tp_dec);
        scratch.measured = source.take_measured(index);'''),
    ('''                        if !research_consumed {
                            align_cmd::warp_frame_in_place(
                                &mut frame,
                                *t,
                                domain.full,
                                map.resampler(),
                                scratch,
                            )?;
                        }''',
     '''                        if !research_consumed {
                            let _tp = crate::tp::span("prep.gather", index as u64);
                            align_cmd::warp_frame_in_place(
                                &mut frame,
                                *t,
                                domain.full,
                                map.resampler(),
                                scratch,
                            )?;
                        }'''),
    ('''                        #[cfg(not(feature = "research-lens-warp"))]
                        p.measure(&frame, index, *t, map.resampler(), scratch)?;''',
     '''                        #[cfg(not(feature = "research-lens-warp"))]
                        let tp_probe = crate::tp::span("prep.probe", index as u64);
                        #[cfg(not(feature = "research-lens-warp"))]
                        p.measure(&frame, index, *t, map.resampler(), scratch)?;
                        #[cfg(not(feature = "research-lens-warp"))]
                        drop(tp_probe);'''),
    ('''        let black = levels.black;
        if !direct_consumed {
            extract_planes_bands(''',
     '''        let black = levels.black;
        let _tp_extract = crate::tp::span("prep.extract_carry", index as u64);
        if !direct_consumed {
            extract_planes_bands('''),
    ('''    #[cfg(feature = "native-signed-black")]
    let clamped_decisions = native_signed_black::clamped_decisions()?;
    luma.par_iter_mut()
        .zip(planes[1].par_iter().zip(planes[2].par_iter()))''',
     '''    #[cfg(feature = "native-signed-black")]
    let clamped_decisions = native_signed_black::clamped_decisions()?;
    let _tp_luma = crate::tp::span("prep.luma", index as u64);
    luma.par_iter_mut()
        .zip(planes[1].par_iter().zip(planes[2].par_iter()))'''),
    ('''    depth_guide::record(index, luma);
    // STREHL_AXIAL_CA: red and blue from the frames where they focus. After''',
     '''    let tp_rec = crate::tp::span("prep.depth_record", index as u64);
    depth_guide::record(index, luma);
    drop(tp_rec);
    // STREHL_AXIAL_CA: red and blue from the frames where they focus. After'''),
    ('''    luma_variance(luma, noise, var);
    #[cfg(feature = "native-pyramid-profile")]
    drop(variance_phase);
''',
     '''    let tp_var = crate::tp::span("prep.variance", index as u64);
    luma_variance(luma, noise, var);
    drop(tp_var);
    #[cfg(feature = "native-pyramid-profile")]
    drop(variance_phase);
'''),
    ('''                let index = *index;
                slot.warp.bands = Some(mask.clone());
                let fast = slot.prepare(domain, &partial, index, levels, noise, warps, None, None);''',
     '''                let index = *index;
                let _tp_frame = crate::tp::span("ref.frame", index as u64);
                slot.warp.bands = Some(mask.clone());
                let fast = slot.prepare(domain, &partial, index, levels, noise, warps, None, None);'''),
    ('''                optical_restore::observe(index, &slot.planes);
            }
            Ok(())''',
     '''                let _tp_obs = crate::tp::span("ref.observe", index as u64);
                optical_restore::observe(index, &slot.planes);
            }
            Ok(())'''),
])
print('ok')
