"""Timers in the archive decode and the RAW front end (scratch copy only)."""
from patchlib import patch

MOD = '#[path = "../../../trace-points.rs"]\npub mod tp;'

patch('crates/strehl-raw-codec/src/lib.rs', [], append=MOD)
patch('crates/strehl-raw-codec/src/cfa.rs', [
    ('''    if cfg!(target_endian = "big") {
        return Ok(None);
    }
    // The serial decode's thread state, taken for this call and put back at''',
     '''    if cfg!(target_endian = "big") {
        return Ok(None);
    }
    let _tp_all = crate::tp::span(
        if serial {
            "codec.decode_serial"
        } else if rows.is_some() {
            "codec.decode_rows"
        } else {
            "codec.decode_par"
        },
        0,
    );
    // The serial decode's thread state, taken for this call and put back at'''),
    ('''            let mut file = std::mem::take(&mut r.file);
            file.clear();
            File::open(path)''',
     '''            let mut file = std::mem::take(&mut r.file);
            file.clear();
            let _tp = crate::tp::span("codec.read", 0);
            File::open(path)'''),
    ('''        let mut hash = Sha256::new();
        hash.update(&prefix);
        for (c, dst) in jobs {''',
     '''        let mut hash = Sha256::new();
        hash.update(&prefix);
        let mut tp_z = crate::tp::sum("codec.zstd", 0);
        let mut tp_p = crate::tp::sum("codec.unpredict", 0);
        let mut tp_h = crate::tp::sum("codec.sha", 0);
        for (c, dst) in jobs {'''),
    ('''                    let got = r
                        .zstd
                        .decompress_to_buffer(payload, &mut r.scratch[..c.n])?;
                    ensure!(got == c.n, "Decoded chunk length mismatch");
                    unpredict_into(&r.scratch[..c.n], c.width, dst);''',
     '''                    let got = tp_z.add(|| {
                        r.zstd
                            .decompress_to_buffer(payload, &mut r.scratch[..c.n])
                    })?;
                    ensure!(got == c.n, "Decoded chunk length mismatch");
                    tp_p.add(|| unpredict_into(&r.scratch[..c.n], c.width, dst));'''),
    ('''            #[cfg(target_endian = "little")]
            hash.update(sample_bytes(dst));
        }''',
     '''            #[cfg(target_endian = "little")]
            tp_h.add(|| hash.update(sample_bytes(dst)));
        }'''),
])

patch('crates/strehl-raw/src/lib.rs', [
    ('''    let params = RawDecodeParams::default();
    let mut buffer = buffer;
    let archived = strehl_raw_codec::archive::is_archive(path);''',
     '''    let _tp_all = strehl_raw_codec::tp::span("raw.decode", u64::from(serial));
    let params = RawDecodeParams::default();
    let mut buffer = buffer;
    let archived = strehl_raw_codec::archive::is_archive(path);'''),
    ('''            let prefix = RawSource::new_from_slice(&cfa.prefix);
            if let Some(img) = metadata_image(&prefix, &params, cfa.width, cfa.height) {''',
     '''            let prefix = RawSource::new_from_slice(&cfa.prefix);
            let tp_meta = strehl_raw_codec::tp::span("raw.meta_image", 0);
            let meta = metadata_image(&prefix, &params, cfa.width, cfa.height);
            drop(tp_meta);
            if let Some(img) = meta {'''),
    ('''    let iso = rawler::get_decoder(&source)
        .and_then(|d| d.raw_metadata(&source, &params))
        .ok()
        .and_then(|m| m.exif.iso_speed_ratings.map(u32::from).or(m.exif.iso_speed))
        .map(|v| v as f32);''',
     '''    let tp_iso = strehl_raw_codec::tp::span("raw.meta_iso", 0);
    let iso = rawler::get_decoder(&source)
        .and_then(|d| d.raw_metadata(&source, &params))
        .ok()
        .and_then(|m| m.exif.iso_speed_ratings.map(u32::from).or(m.exif.iso_speed))
        .map(|v| v as f32);
    drop(tp_iso);'''),
])
