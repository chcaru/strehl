//! Camera-rendered JPEG previews from RAW containers, without decoding the CFA.
//!
//! These pixels help browse a bracket. They are neither a RAW-accurate rendering
//! nor a preview of the eventual fused stack. Only classic TIFF directory links
//! and the documented JPEG offset/length fields are inspected; MakerNotes and
//! compressed RAW strips are never interpreted.

use std::collections::HashSet;
use std::fs::File;
use std::io::{Cursor, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

use anyhow::{Context, Result, bail, ensure};
use image::{DynamicImage, ImageFormat, ImageReader, imageops::FilterType};

use crate::jobs::{Task, spawn_task};
use crate::preview::PreviewImage;

#[path = "source-preview-cache.rs"]
mod cache;
#[path = "source-preview-decode.rs"]
mod decode;

const MAX_IFDS: usize = 64;
const MAX_IFD_DEPTH: usize = 8;
const MAX_IFD_ENTRIES: usize = 4_096;
const MAX_TOTAL_ENTRIES: usize = 16_384;
const MAX_JPEG_BYTES: u64 = 32 * 1024 * 1024;
const MAX_JPEG_ATTEMPTS: usize = 4;
const MAX_TOTAL_JPEG_BYTES: u64 = 64 * 1024 * 1024;
const MAX_IMAGE_SIDE: u32 = 32_768;
const MAX_IMAGE_PIXELS: u64 = 80_000_000;
const MAX_DECODE_BYTES: u64 = 512 * 1024 * 1024;
const THUMBNAIL_MAX_SIDE: u32 = 320;
pub(crate) const FILMSTRIP_BATCH_MAX: usize = 8;
const FILMSTRIP_WORKERS: usize = 3;
pub(crate) type FilmstripBatch = Vec<(usize, std::result::Result<SourcePreview, String>)>;

#[cfg(test)]
#[path = "source-preview-v25-tests.rs"]
mod v25_tests;

pub(crate) struct SourcePreview {
    pub image: PreviewImage,
    pub thumbnail: Option<PreviewImage>,
}

/// A detail decode supplies a filmstrip derivative only when the caller does
/// not already retain one. All resizing stays off the UI thread.
pub(crate) fn load_browser_preview(
    path: PathBuf,
    max_side: u32,
    overview: bool,
    thumbnail_side: Option<u32>,
) -> Task<SourcePreview> {
    spawn_task("strehl-source-detail", move |cancelled| {
        let image = load_with_policy(&path, max_side, overview, &cancelled)?;
        let thumbnail = thumbnail_side
            .map(|side| thumbnail_of(&image, side, &cancelled))
            .transpose()?;
        Ok(SourcePreview { image, thumbnail })
    })
}

/// Filmstrip-only camera thumbnails keep their native crop. They are never
/// eligible for the canvas or inspection views. A separate, bounded batch
/// lets visible cells complete together while a large detail JPEG decodes.
pub(crate) fn load_filmstrip_batch(
    paths: Vec<(usize, PathBuf)>,
    max_side: u32,
) -> Task<FilmstripBatch> {
    spawn_task("strehl-filmstrip", move |cancelled| {
        ensure!(
            paths.len() <= FILMSTRIP_BATCH_MAX,
            "Too many filmstrip previews requested"
        );
        let workers = std::thread::available_parallelism()
            .map_or(1, usize::from)
            .min(FILMSTRIP_WORKERS);
        filmstrip_images(&paths, max_side, &cancelled, workers)
    })
}

fn filmstrip_images(
    paths: &[(usize, PathBuf)],
    max_side: u32,
    cancelled: &AtomicBool,
    workers: usize,
) -> Result<FilmstripBatch> {
    bounded_map(paths.len(), workers, cancelled, |slot| {
        let (index, path) = &paths[slot];
        let image = load_browser(path, max_side, true, false, cancelled)
            .map(|image| SourcePreview {
                image,
                thumbnail: None,
            })
            .map_err(|error| format!("{error:#}"));
        (*index, image)
    })
}

/// At most three decoders share one batch. A slow or corrupt source cannot
/// serialize the other photographs; publication is still one ordered batch.
/// Cancellation joins the workers before the task releases its decoder lane.
fn bounded_map<T: Send>(
    count: usize,
    workers: usize,
    cancelled: &AtomicBool,
    load: impl Fn(usize) -> T + Sync,
) -> Result<Vec<T>> {
    check_cancelled(cancelled)?;
    if workers <= 1 {
        let mut result = Vec::with_capacity(count);
        for slot in 0..count {
            check_cancelled(cancelled)?;
            result.push(load(slot));
        }
        check_cancelled(cancelled)?;
        return Ok(result);
    }
    let next = AtomicUsize::new(0);
    let mut result = std::thread::scope(|scope| {
        let mut tasks = Vec::new();
        for _ in 0..workers.clamp(1, FILMSTRIP_WORKERS).min(count) {
            let next = &next;
            let load = &load;
            tasks.push(scope.spawn(move || {
                let mut completed = Vec::new();
                while !cancelled.load(Ordering::Relaxed) {
                    let slot = next.fetch_add(1, Ordering::Relaxed);
                    if slot >= count {
                        break;
                    }
                    completed.push((slot, load(slot)));
                }
                completed
            }));
        }
        let mut result = Vec::with_capacity(count);
        let mut failed = false;
        for task in tasks {
            match task.join() {
                Ok(completed) => result.extend(completed),
                Err(_) => failed = true,
            }
        }
        ensure!(!failed, "A filmstrip decoder stopped unexpectedly");
        Ok::<_, anyhow::Error>(result)
    })?;
    check_cancelled(cancelled)?;
    result.sort_unstable_by_key(|(slot, _)| *slot);
    Ok(result.into_iter().map(|(_, image)| image).collect())
}

/// A selected-frame rescue can use the fast lane between thumbnail batches
/// while an older large JPEG is still occupying the detail decoder.
pub(crate) fn load_overview_batch(
    paths: Vec<(usize, PathBuf)>,
    max_side: u32,
    thumbnail_side: Option<u32>,
) -> Task<FilmstripBatch> {
    spawn_task("strehl-source-overview-rescue", move |cancelled| {
        ensure!(
            paths.len() == 1,
            "An overview rescue needs one source frame"
        );
        let (index, path) = paths.into_iter().next().expect("one requested overview");
        let image = load_with_policy(&path, max_side, true, &cancelled)
            .and_then(|image| {
                let thumbnail = thumbnail_side
                    .map(|side| thumbnail_of(&image, side, &cancelled))
                    .transpose()?;
                Ok(SourcePreview { image, thumbnail })
            })
            .map_err(|error| format!("{error:#}"));
        Ok(vec![(index, image)])
    })
}

/// A resident scrub photograph always uses the canonical camera aperture.
/// Native contact JPEGs may be letterboxed or cropped differently and are not
/// substitutes. Reuse the existing bounded batch workers, never another pool.
pub(crate) fn load_scrub_batch(
    paths: Vec<(usize, PathBuf)>,
    max_side: u32,
    thumbnail_side: Option<u32>,
) -> Task<FilmstripBatch> {
    spawn_task("strehl-source-scrub-warm", move |cancelled| {
        ensure!(
            paths.len() <= 4,
            "Too many resident scrub previews requested"
        );
        let workers = std::thread::available_parallelism()
            .map_or(1, usize::from)
            .min(FILMSTRIP_WORKERS);
        bounded_map(paths.len(), workers, &cancelled, |slot| {
            let (index, path) = &paths[slot];
            let preview = load_with_policy(path, max_side, true, &cancelled)
                .and_then(|image| {
                    let thumbnail = thumbnail_side
                        .map(|side| thumbnail_of(&image, side, &cancelled))
                        .transpose()?;
                    Ok(SourcePreview { image, thumbnail })
                })
                .map_err(|error| format!("{error:#}"));
            (*index, preview)
        })
    })
}

fn thumbnail_of(
    image: &PreviewImage,
    max_side: u32,
    cancelled: &AtomicBool,
) -> Result<PreviewImage> {
    ensure!(max_side > 0, "The filmstrip has no usable display size");
    ensure!(
        !image.size.contains(&0),
        "The camera preview has no display pixels"
    );
    check_cancelled(cancelled)?;
    let view = image::ImageBuffer::<image::Rgba<u8>, &[u8]>::from_raw(
        image.size[0] as u32,
        image.size[1] as u32,
        image.rgba.as_slice(),
    )
    .context("The camera preview has incomplete pixels")?;
    let scale = (max_side as f64 / image.size[0].max(image.size[1]) as f64).min(1.0);
    let width = (image.size[0] as f64 * scale).round().max(1.0) as u32;
    let height = (image.size[1] as f64 * scale).round().max(1.0) as u32;
    let rgba = image::imageops::resize(&view, width, height, FilterType::Triangle);
    check_cancelled(cancelled)?;
    Ok(PreviewImage {
        path: image.path.clone(),
        source_size: image.source_size,
        size: [width as usize, height as usize],
        rgba: rgba.into_raw(),
        is_overview: image.is_overview || image.size != [width as usize, height as usize],
    })
}

/// Load a camera-rendered embedded JPEG in a cancellable background task.
/// `source_size` is the largest embedded JPEG's oriented display aperture,
/// never the sensor's RAW dimensions. Small requests choose the smallest JPEG
/// with a compatible aspect ratio. Some cameras put a 3:2 photograph inside a
/// letterboxed 4:3 thumbnail; switching that thumbnail with the full preview
/// changes the visible image rectangle. Incompatible thumbnail crops are not
/// displayed as progressive substitutes for the main preview.
#[cfg(test)]
pub fn load_source_preview(path: PathBuf, max_side: u32) -> Task<PreviewImage> {
    spawn_task("strehl-source-preview", move |cancelled| {
        load(&path, max_side, &cancelled)
    })
}

/// Synchronous reader for the cancellable JPEG draft worker. Unlike browsing,
/// prefer the smallest embedded JPEG with enough pixels for this small draft.
/// Inspect bounded JPEG headers before allocating or decoding their payloads.
pub(crate) fn load_draft_source(
    path: &Path,
    max_side: u32,
    cancelled: &AtomicBool,
) -> Result<PreviewImage> {
    ensure!(max_side > 0, "The draft has no usable display size");
    check_cancelled(cancelled)?;
    let mut file = File::open(path).with_context(|| format!("Opening {}", path.display()))?;
    let file_len = file.metadata()?.len();
    let candidates = jpeg_candidates(&mut file, file_len, cancelled)?;
    let mut ranked = Vec::with_capacity(candidates.len());
    for candidate in candidates {
        let mut header = vec![0; candidate.length.min(64 * 1024) as usize];
        read_at(
            &mut file,
            file_len,
            candidate.offset,
            &mut header,
            cancelled,
        )?;
        let dimensions = jpeg_reader(&header).into_dimensions().ok();
        let key = match dimensions {
            Some((w, h)) if w.max(h) >= max_side => (0, u64::from(w) * u64::from(h)),
            Some((w, h)) => (1, u64::MAX - u64::from(w) * u64::from(h)),
            None => (2, candidate.length),
        };
        ranked.push((key, candidate));
    }
    ranked.sort_by_key(|(key, _)| *key);
    let mut read_bytes = 0;
    let mut last_error = None;
    for (_, candidate) in ranked.into_iter().take(MAX_JPEG_ATTEMPTS) {
        read_bytes += candidate.length;
        if read_bytes > MAX_TOTAL_JPEG_BYTES {
            break;
        }
        let mut bytes = vec![0; candidate.length as usize];
        read_at(&mut file, file_len, candidate.offset, &mut bytes, cancelled)?;
        match decode_jpeg(&bytes) {
            Ok(image) => {
                check_cancelled(cancelled)?;
                let image = orient(image, candidate.orientation);
                let source_size = [image.width(), image.height()];
                let is_overview = source_size.iter().any(|&side| side > max_side);
                let rgba = if is_overview {
                    image.resize(max_side, max_side, FilterType::Triangle)
                } else {
                    image
                }
                .into_rgba8();
                return Ok(PreviewImage {
                    path: path.to_path_buf(),
                    source_size,
                    size: [rgba.width() as usize, rgba.height() as usize],
                    rgba: rgba.into_raw(),
                    is_overview,
                });
            }
            Err(error) => last_error = Some(error),
        }
    }
    if let Some(error) = last_error {
        bail!("The camera JPEG draft could not be decoded: {error:#}");
    }
    bail!("This frame has no supported embedded camera preview")
}

#[cfg(test)]
fn load(path: &Path, max_side: u32, cancelled: &AtomicBool) -> Result<PreviewImage> {
    load_with_policy(path, max_side, max_side <= THUMBNAIL_MAX_SIDE, cancelled)
}

fn load_with_policy(
    path: &Path,
    max_side: u32,
    small_first: bool,
    cancelled: &AtomicBool,
) -> Result<PreviewImage> {
    load_browser(path, max_side, small_first, true, cancelled)
}

fn load_browser(
    path: &Path,
    max_side: u32,
    small_first: bool,
    canonical_crop: bool,
    cancelled: &AtomicBool,
) -> Result<PreviewImage> {
    ensure!(
        max_side > 0,
        "The camera preview has no usable display size"
    );
    check_cancelled(cancelled)?;
    let mut file = File::open(path).with_context(|| format!("Opening {}", path.display()))?;
    let metadata = file
        .metadata()
        .context("Reading the source frame metadata")?;
    ensure!(metadata.is_file(), "Choose a source image file");
    let stamp = cache::Stamp::new(path, &metadata);
    let catalog = cache::catalog(&mut file, metadata.len(), stamp.as_ref(), cancelled)?;
    let (candidates, source_size) =
        rank_candidates(catalog.to_vec(), small_first, canonical_crop, max_side)?;
    let mut read_bytes = 0;
    let mut last_error = None;
    for candidate in candidates.into_iter().take(MAX_JPEG_ATTEMPTS) {
        check_cancelled(cancelled)?;
        read_bytes += candidate.length;
        if read_bytes > MAX_TOTAL_JPEG_BYTES {
            break;
        }
        let bytes = cache::payload(
            &mut file,
            metadata.len(),
            stamp.as_ref(),
            candidate,
            cancelled,
        )?;
        match decode::decode(&bytes, max_side, cancelled) {
            Ok((image, original_size)) => {
                check_cancelled(cancelled)?;
                let image = orient(image, candidate.orientation);
                let decoded_size = [image.width(), image.height()];
                let original_size = if (5..=8).contains(&candidate.orientation) {
                    [original_size[1], original_size[0]]
                } else {
                    original_size
                };
                ensure!(
                    !canonical_crop || compatible_aspect(original_size, source_size),
                    "The camera preview has a different crop from its full JPEG"
                );
                let source_size = if canonical_crop {
                    source_size
                } else {
                    original_size
                };
                let reduced = decoded_size.iter().any(|&side| side > max_side);
                let is_overview = reduced || decoded_size != source_size;
                let rgba = if reduced {
                    image.resize(max_side, max_side, FilterType::Triangle)
                } else {
                    image
                }
                .into_rgba8();
                check_cancelled(cancelled)?;
                return Ok(PreviewImage {
                    path: path.to_path_buf(),
                    source_size,
                    size: [rgba.width() as usize, rgba.height() as usize],
                    rgba: rgba.into_raw(),
                    is_overview,
                });
            }
            Err(error) => last_error = Some(error),
        }
    }
    if let Some(error) = last_error {
        bail!("The camera's embedded JPEG preview could not be decoded: {error:#}");
    }
    bail!("This frame has no supported embedded camera preview. Stacking is still available.")
}

/// Header dimensions distinguish genuinely different crops from small integer
/// rounding differences. The 0.5% allowance admits the measured 1616x1080
/// medium preview alongside 7008x4672, but rejects the 160x120 letterbox.
fn compatible_aspect(size: [u32; 2], aperture: [u32; 2]) -> bool {
    if size.contains(&0) || aperture.contains(&0) {
        return false;
    }
    let a = u64::from(size[0]) * u64::from(aperture[1]);
    let b = u64::from(size[1]) * u64::from(aperture[0]);
    a.abs_diff(b) <= b / 200
}

fn sized_candidates(
    reader: &mut (impl Read + Seek),
    file_len: u64,
    candidates: Vec<JpegCandidate>,
    cancelled: &AtomicBool,
) -> Result<Vec<(JpegCandidate, [u32; 2])>> {
    let mut sized = Vec::with_capacity(candidates.len());
    for candidate in candidates {
        let mut header = vec![0; candidate.length.min(64 * 1024) as usize];
        read_at(reader, file_len, candidate.offset, &mut header, cancelled)?;
        if let Ok((width, height)) = jpeg_reader(&header).into_dimensions()
            && width > 0
            && height > 0
            && width <= MAX_IMAGE_SIDE
            && height <= MAX_IMAGE_SIDE
            && u64::from(width) * u64::from(height) <= MAX_IMAGE_PIXELS
        {
            let size = if (5..=8).contains(&candidate.orientation) {
                [height, width]
            } else {
                [width, height]
            };
            sized.push((candidate, size));
        }
    }
    Ok(sized)
}

fn rank_candidates(
    mut sized: Vec<(JpegCandidate, [u32; 2])>,
    small_first: bool,
    canonical_crop: bool,
    requested_side: u32,
) -> Result<(Vec<JpegCandidate>, [u32; 2])> {
    let source_size = sized
        .iter()
        .max_by_key(|(_, size)| u64::from(size[0]) * u64::from(size[1]))
        .map(|(_, size)| *size)
        .context("This frame has no supported embedded camera preview with readable dimensions. Stacking is still available.")?;
    if canonical_crop {
        sized.retain(|(_, size)| compatible_aspect(*size, source_size));
    }
    sized.sort_by_key(|(_, size)| {
        let pixels = u64::from(size[0]) * u64::from(size[1]);
        // Decode only as many camera pixels as the requested display tier
        // can use. A compatible 2K JPEG already satisfies a 1920px image; the
        // largest JPEG still defines its immutable canonical aperture.
        if !small_first || requested_side > THUMBNAIL_MAX_SIDE {
            if size[0].max(size[1]) >= requested_side {
                (0, pixels)
            } else {
                (1, u64::MAX - pixels)
            }
        } else {
            (0, pixels)
        }
    });
    Ok((
        sized.into_iter().map(|(candidate, _)| candidate).collect(),
        source_size,
    ))
}

#[derive(Clone, Copy)]
enum ByteOrder {
    Little,
    Big,
}

impl ByteOrder {
    fn u16(self, bytes: &[u8]) -> u16 {
        let bytes = [bytes[0], bytes[1]];
        match self {
            Self::Little => u16::from_le_bytes(bytes),
            Self::Big => u16::from_be_bytes(bytes),
        }
    }

    fn u32(self, bytes: &[u8]) -> u32 {
        let bytes = [bytes[0], bytes[1], bytes[2], bytes[3]];
        match self {
            Self::Little => u32::from_le_bytes(bytes),
            Self::Big => u32::from_be_bytes(bytes),
        }
    }
}

#[derive(Clone, Copy)]
struct JpegCandidate {
    offset: u64,
    length: u64,
    orientation: u16,
}

fn jpeg_candidates(
    reader: &mut (impl Read + Seek),
    file_len: u64,
    cancelled: &AtomicBool,
) -> Result<Vec<JpegCandidate>> {
    let mut header = [0; 8];
    read_at(reader, file_len, 0, &mut header, cancelled)?;
    let order = match &header[..2] {
        b"II" => ByteOrder::Little,
        b"MM" => ByteOrder::Big,
        _ => bail!("This RAW container has no supported TIFF camera preview"),
    };
    ensure!(
        order.u16(&header[2..4]) == 42,
        "This RAW container has no supported classic TIFF camera preview"
    );
    let mut pending = Vec::new();
    let mut discovered = HashSet::new();
    schedule_ifd(&mut pending, &mut discovered, order.u32(&header[4..8]), 0)?;
    let mut total_entries = 0;
    let mut candidates = Vec::new();
    let mut root_orientation = 1;
    while let Some((offset, depth)) = pending.pop() {
        check_cancelled(cancelled)?;
        let mut count = [0; 2];
        read_at(reader, file_len, u64::from(offset), &mut count, cancelled)?;
        let count = usize::from(order.u16(&count));
        total_entries += count;
        ensure!(
            count <= MAX_IFD_ENTRIES && total_entries <= MAX_TOTAL_ENTRIES,
            "The camera preview directory exceeds the metadata safety limit"
        );
        // The count is bounded before multiplication or allocation. Each classic
        // TIFF directory entry is 12 bytes, followed by one next-IFD offset.
        let mut entries = vec![0; count * 12 + 4];
        read_at(
            reader,
            file_len,
            u64::from(offset) + 2,
            &mut entries,
            cancelled,
        )?;
        let mut jpeg_offset = None;
        let mut jpeg_length = None;
        let mut orientation = None;
        for entry in entries[..count * 12].as_chunks::<12>().0 {
            check_cancelled(cancelled)?;
            let tag = order.u16(&entry[..2]);
            let kind = order.u16(&entry[2..4]);
            let values = order.u32(&entry[4..8]);
            match tag {
                274 if kind == 3 && values == 1 => {
                    let value = order.u16(&entry[8..10]);
                    if (1..=8).contains(&value) {
                        orientation = Some(value);
                    }
                }
                513 | 514 if kind == 4 && values == 1 => {
                    let value = u64::from(order.u32(&entry[8..12]));
                    if tag == 513 {
                        jpeg_offset = Some(value);
                    } else {
                        jpeg_length = Some(value);
                    }
                }
                // SubIFDs and ExifIFD pointers use absolute TIFF offsets. The
                // IFD (13) type is also accepted for SubIFD links.
                330 | 34665 if kind == 4 || kind == 13 => {
                    ensure!(
                        values > 0 && values as usize <= MAX_IFDS,
                        "The camera preview contains too many directory links"
                    );
                    if values == 1 {
                        schedule_ifd(
                            &mut pending,
                            &mut discovered,
                            order.u32(&entry[8..12]),
                            depth + 1,
                        )?;
                    } else {
                        let mut offsets = vec![0; values as usize * 4];
                        read_at(
                            reader,
                            file_len,
                            u64::from(order.u32(&entry[8..12])),
                            &mut offsets,
                            cancelled,
                        )?;
                        for child in offsets.as_chunks::<4>().0 {
                            schedule_ifd(
                                &mut pending,
                                &mut discovered,
                                order.u32(child),
                                depth + 1,
                            )?;
                        }
                    }
                }
                _ => {}
            }
        }
        if offset == order.u32(&header[4..8]) {
            root_orientation = orientation.unwrap_or(1);
        }
        if let (Some(jpeg_offset), Some(length)) = (jpeg_offset, jpeg_length) {
            ensure!(
                length > 0 && length <= MAX_JPEG_BYTES,
                "The embedded camera preview exceeds the 32 MiB safety limit"
            );
            ensure_range(jpeg_offset, length, file_len)?;
            candidates.push(JpegCandidate {
                offset: jpeg_offset,
                length,
                orientation: orientation.unwrap_or(root_orientation),
            });
        }
        schedule_ifd(
            &mut pending,
            &mut discovered,
            order.u32(&entries[count * 12..]),
            depth,
        )?;
    }
    Ok(candidates)
}

fn schedule_ifd(
    pending: &mut Vec<(u32, usize)>,
    discovered: &mut HashSet<u32>,
    offset: u32,
    depth: usize,
) -> Result<()> {
    if offset == 0 || discovered.contains(&offset) {
        return Ok(());
    }
    ensure!(
        offset >= 8,
        "The camera preview directory offset is invalid"
    );
    ensure!(
        depth <= MAX_IFD_DEPTH && discovered.len() < MAX_IFDS,
        "The camera preview contains too many nested directories"
    );
    discovered.insert(offset);
    pending.push((offset, depth));
    Ok(())
}

fn ensure_range(offset: u64, length: u64, file_len: u64) -> Result<()> {
    ensure!(
        offset
            .checked_add(length)
            .is_some_and(|end| end <= file_len),
        "The embedded camera preview points outside the source file"
    );
    Ok(())
}

fn read_at(
    reader: &mut (impl Read + Seek),
    file_len: u64,
    offset: u64,
    bytes: &mut [u8],
    cancelled: &AtomicBool,
) -> Result<()> {
    check_cancelled(cancelled)?;
    ensure_range(offset, bytes.len() as u64, file_len)?;
    reader.seek(SeekFrom::Start(offset))?;
    reader
        .read_exact(bytes)
        .context("Reading the embedded camera preview")?;
    check_cancelled(cancelled)
}

fn check_cancelled(cancelled: &AtomicBool) -> Result<()> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Camera preview cancelled"
    );
    Ok(())
}

fn jpeg_reader(bytes: &[u8]) -> ImageReader<Cursor<&[u8]>> {
    let mut reader = ImageReader::with_format(Cursor::new(bytes), ImageFormat::Jpeg);
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(MAX_IMAGE_SIDE);
    limits.max_image_height = Some(MAX_IMAGE_SIDE);
    limits.max_alloc = Some(MAX_DECODE_BYTES);
    reader.limits(limits);
    reader
}

fn decode_jpeg(bytes: &[u8]) -> Result<DynamicImage> {
    let (width, height) = jpeg_reader(bytes)
        .into_dimensions()
        .context("Reading camera JPEG dimensions")?;
    ensure!(width > 0 && height > 0, "The camera preview has no pixels");
    ensure!(
        u64::from(width) * u64::from(height) <= MAX_IMAGE_PIXELS,
        "The camera preview exceeds the decoded pixel safety limit"
    );
    jpeg_reader(bytes).decode().context("Decoding camera JPEG")
}

fn orient(image: DynamicImage, orientation: u16) -> DynamicImage {
    match orientation {
        2 => image.fliph(),
        3 => image.rotate180(),
        4 => image.flipv(),
        5 => image.rotate90().fliph(),
        6 => image.rotate90(),
        7 => image.rotate90().flipv(),
        8 => image.rotate270(),
        _ => image,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::jobs::tests::TestDirectory;

    fn put_u16(bytes: &mut [u8], value: u16, order: ByteOrder) {
        bytes.copy_from_slice(&match order {
            ByteOrder::Little => value.to_le_bytes(),
            ByteOrder::Big => value.to_be_bytes(),
        });
    }

    fn put_u32(bytes: &mut [u8], value: u32, order: ByteOrder) {
        bytes.copy_from_slice(&match order {
            ByteOrder::Little => value.to_le_bytes(),
            ByteOrder::Big => value.to_be_bytes(),
        });
    }

    fn entry(tag: u16, kind: u16, count: u32, value: u32, order: ByteOrder) -> [u8; 12] {
        let mut entry = [0; 12];
        put_u16(&mut entry[..2], tag, order);
        put_u16(&mut entry[2..4], kind, order);
        put_u32(&mut entry[4..8], count, order);
        if kind == 3 && count == 1 {
            put_u16(&mut entry[8..10], value as u16, order);
        } else {
            put_u32(&mut entry[8..], value, order);
        }
        entry
    }

    fn tiff(order: ByteOrder, size: usize) -> Vec<u8> {
        let mut bytes = vec![0; size];
        bytes[..2].copy_from_slice(match order {
            ByteOrder::Little => b"II",
            ByteOrder::Big => b"MM",
        });
        put_u16(&mut bytes[2..4], 42, order);
        put_u32(&mut bytes[4..8], 8, order);
        bytes
    }

    fn ifd(bytes: &mut [u8], offset: usize, entries: &[[u8; 12]], next: u32, order: ByteOrder) {
        put_u16(&mut bytes[offset..offset + 2], entries.len() as u16, order);
        for (index, entry) in entries.iter().enumerate() {
            bytes[offset + 2 + index * 12..offset + 14 + index * 12].copy_from_slice(entry);
        }
        let end = offset + 2 + entries.len() * 12;
        put_u32(&mut bytes[end..end + 4], next, order);
    }

    fn jpeg(width: u32, height: u32) -> Vec<u8> {
        let pixels = image::RgbImage::from_fn(width, height, |x, y| {
            image::Rgb([(x * 7) as u8, (y * 11) as u8, 123])
        });
        let mut bytes = Vec::new();
        image::codecs::jpeg::JpegEncoder::new_with_quality(&mut bytes, 90)
            .encode_image(&pixels)
            .unwrap();
        bytes
    }

    fn parse(bytes: &[u8]) -> Result<Vec<JpegCandidate>> {
        jpeg_candidates(
            &mut Cursor::new(bytes),
            bytes.len() as u64,
            &AtomicBool::new(false),
        )
    }

    #[test]
    fn both_byte_orders_load_embedded_pixels_and_preserve_source_bytes() {
        // A broken offset, byte-order assumption, or source write must fail this
        // fixture. The image is non-square so orientation/size errors are visible.
        let directory = TestDirectory::new("camera-preview");
        let jpeg = jpeg(24, 16);
        for (name, order) in [
            ("little.arw", ByteOrder::Little),
            ("big.arw", ByteOrder::Big),
        ] {
            let mut bytes = tiff(order, 128 + jpeg.len());
            ifd(
                &mut bytes,
                8,
                &[
                    entry(513, 4, 1, 128, order),
                    entry(514, 4, 1, jpeg.len() as u32, order),
                    entry(274, 3, 1, 6, order),
                ],
                0,
                order,
            );
            bytes[128..].copy_from_slice(&jpeg);
            let path = directory.path().join(name);
            std::fs::write(&path, &bytes).unwrap();
            let preview = load_source_preview(path.clone(), 12)
                .receiver
                .recv()
                .unwrap()
                .unwrap();
            assert_eq!(preview.source_size, [16, 24]);
            assert_eq!(preview.size, [8, 12]);
            assert!(preview.is_overview);
            assert_eq!(preview.rgba.len(), 8 * 12 * 4);
            assert_eq!(std::fs::read(path).unwrap(), bytes);
        }
    }

    #[test]
    fn draft_reader_prefers_smallest_adequate_jpeg_and_retains_browser_policy() {
        // A largest-first decoder would return the 240px source; a thumbnail-
        // only shortcut would return 24px. Neither satisfies this fixture.
        let directory = TestDirectory::new("camera-draft-preview-size");
        let order = ByteOrder::Little;
        let images = [jpeg(24, 16), jpeg(120, 80), jpeg(240, 160)];
        let mut bytes = tiff(order, 256 + images.iter().map(Vec::len).sum::<usize>());
        let mut payload = 256;
        for (i, jpeg) in images.iter().enumerate() {
            ifd(
                &mut bytes,
                8 + i * 64,
                &[
                    entry(513, 4, 1, payload as u32, order),
                    entry(514, 4, 1, jpeg.len() as u32, order),
                ],
                if i == 2 { 0 } else { (8 + (i + 1) * 64) as u32 },
                order,
            );
            bytes[payload..payload + jpeg.len()].copy_from_slice(jpeg);
            payload += jpeg.len();
        }
        let path = directory.path().join("three-previews.arw");
        std::fs::write(&path, &bytes).unwrap();
        let preview = load_draft_source(&path, 100, &AtomicBool::new(false)).unwrap();
        assert_eq!(preview.source_size, [120, 80]);
        assert_eq!(preview.size, [100, 67]);
        let thumbnail = load(&path, 100, &AtomicBool::new(false)).unwrap();
        assert_eq!(thumbnail.source_size, [240, 160]);
        assert_eq!(thumbnail.size, [24, 16]);
        assert!(thumbnail.is_overview);
        let browsing = load(&path, 400, &AtomicBool::new(false)).unwrap();
        assert_eq!(browsing.source_size, [240, 160]);
        let canvas_overview = load_with_policy(&path, 960, true, &AtomicBool::new(false)).unwrap();
        assert_eq!(
            canvas_overview.size,
            [240, 160],
            "when no JPEG is large enough, choose the largest available, never the tiny compatible thumbnail"
        );
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }

    #[test]
    fn next_exif_and_array_subifd_links_are_followed_without_looping() {
        let order = ByteOrder::Big;
        let mut bytes = tiff(order, 512);
        ifd(&mut bytes, 8, &[entry(330, 4, 2, 100, order)], 200, order);
        put_u32(&mut bytes[100..104], 120, order);
        put_u32(&mut bytes[104..108], 160, order);
        ifd(&mut bytes, 120, &[entry(34665, 4, 1, 240, order)], 8, order);
        ifd(&mut bytes, 160, &[], 0, order);
        ifd(&mut bytes, 200, &[], 0, order);
        ifd(
            &mut bytes,
            240,
            &[entry(513, 4, 1, 400, order), entry(514, 4, 1, 20, order)],
            0,
            order,
        );
        let candidates = parse(&bytes).unwrap();
        assert_eq!(
            candidates.len(),
            1,
            "The nested JPEG must actually be visited"
        );
        assert_eq!(candidates[0].offset, 400);
        assert_eq!(candidates[0].length, 20);
    }

    #[test]
    fn malformed_offsets_counts_and_oversized_jpegs_fail_before_allocating_payloads() {
        let order = ByteOrder::Little;
        let mut bytes = tiff(order, 128);
        ifd(
            &mut bytes,
            8,
            &[entry(330, 4, u32::MAX, 100, order)],
            0,
            order,
        );
        assert!(parse(&bytes).is_err());
        ifd(
            &mut bytes,
            8,
            &[entry(330, 4, 1, u32::MAX, order)],
            0,
            order,
        );
        assert!(parse(&bytes).is_err());
        ifd(
            &mut bytes,
            8,
            &[entry(513, 4, 1, 100, order), entry(514, 4, 1, 100, order)],
            0,
            order,
        );
        assert!(parse(&bytes).is_err());
        ifd(
            &mut bytes,
            8,
            &[
                entry(513, 4, 1, 100, order),
                entry(514, 4, 1, MAX_JPEG_BYTES as u32 + 1, order),
            ],
            0,
            order,
        );
        assert!(parse(&bytes).is_err());
        put_u16(&mut bytes[8..10], MAX_IFD_ENTRIES as u16 + 1, order);
        assert!(parse(&bytes).is_err());
        assert!(ensure_range(u64::MAX, 2, u64::MAX).is_err());
    }

    #[test]
    fn missing_jpeg_truncation_cycles_and_cancellation_report_errors() {
        let directory = TestDirectory::new("camera-preview-invalid");
        let order = ByteOrder::Little;
        let mut bytes = tiff(order, 32);
        ifd(&mut bytes, 8, &[], 8, order);
        assert!(
            parse(&bytes).unwrap().is_empty(),
            "A self-cycle must terminate"
        );
        let path = directory.path().join("no-preview.arw");
        std::fs::write(&path, &bytes).unwrap();
        let error = load(&path, 100, &AtomicBool::new(false)).err().unwrap();
        assert!(
            error
                .to_string()
                .contains("no supported embedded camera preview")
        );
        assert!(load(&path, 0, &AtomicBool::new(false)).is_err());
        assert!(load(&path, 100, &AtomicBool::new(true)).is_err());
        assert!(parse(b"II*\0\x08\0\0\0").is_err());
        bytes[2] = 43; // BigTIFF is deliberately outside this small reader.
        assert!(parse(&bytes).is_err());
    }

    #[test]
    fn corrupt_larger_candidate_falls_back_to_valid_camera_jpeg() {
        let directory = TestDirectory::new("camera-preview-fallback");
        let order = ByteOrder::Little;
        let jpeg = jpeg(20, 12);
        let mut bytes = tiff(order, 256 + jpeg.len() * 3);
        ifd(
            &mut bytes,
            8,
            &[
                entry(513, 4, 1, 256, order),
                entry(514, 4, 1, (jpeg.len() * 2) as u32, order),
            ],
            64,
            order,
        );
        ifd(
            &mut bytes,
            64,
            &[
                entry(513, 4, 1, (256 + jpeg.len() * 2) as u32, order),
                entry(514, 4, 1, jpeg.len() as u32, order),
            ],
            0,
            order,
        );
        bytes[256 + jpeg.len() * 2..].copy_from_slice(&jpeg);
        let path = directory.path().join("fallback.arw");
        std::fs::write(&path, bytes).unwrap();
        let preview = load(&path, 1_024, &AtomicBool::new(false)).unwrap();
        assert_eq!(preview.source_size, [20, 12]);
        assert!(!preview.is_overview);
    }

    #[test]
    fn browser_uses_small_compatible_jpeg_with_the_full_display_aperture_and_fallback() {
        // The two real JPEG encodings have different dimensions and lengths.
        // Reversing candidate preference changes decoded pixels/size while the
        // canonical display aperture remains fixed through refinement.
        let directory = TestDirectory::new("camera-preview-size-choice");
        let order = ByteOrder::Little;
        let small = jpeg(24, 15);
        let large = jpeg(128, 80);
        assert!(
            large.len() > small.len(),
            "The fixture must exercise the sort"
        );
        let small_offset = 256 + large.len();
        let mut bytes = tiff(order, small_offset + small.len());
        ifd(
            &mut bytes,
            8,
            &[
                entry(513, 4, 1, 256, order),
                entry(514, 4, 1, large.len() as u32, order),
            ],
            64,
            order,
        );
        ifd(
            &mut bytes,
            64,
            &[
                entry(513, 4, 1, small_offset as u32, order),
                entry(514, 4, 1, small.len() as u32, order),
            ],
            0,
            order,
        );
        bytes[256..small_offset].copy_from_slice(&large);
        bytes[small_offset..].copy_from_slice(&small);
        let path = directory.path().join("two-camera-previews.arw");
        std::fs::write(&path, &bytes).unwrap();
        let cancelled = AtomicBool::new(false);
        let filmstrip = load(&path, 240, &cancelled).unwrap();
        assert_eq!(filmstrip.source_size, [128, 80]);
        assert_eq!(filmstrip.size, [24, 15]);
        assert!(filmstrip.is_overview);
        let main_view = load(&path, 1_024, &cancelled).unwrap();
        assert_eq!(main_view.source_size, [128, 80]);
        assert_eq!(main_view.size, [128, 80]);
        assert_eq!(std::fs::read(&path).unwrap(), bytes);

        // A corrupt small candidate must not hide the intact larger preview.
        bytes[small_offset..small_offset + 2].fill(0);
        std::fs::write(&path, bytes).unwrap();
        let fallback = load(&path, 240, &cancelled).unwrap();
        assert_eq!(fallback.source_size, [128, 80]);
        assert_eq!(fallback.size, [128, 80]);
    }

    #[test]
    fn refinement_decodes_smallest_sufficient_camera_jpeg_but_keeps_largest_aperture() {
        // Different solid colors are an independent candidate-identity witness:
        // selecting the largest JPEG or an undersized JPEG makes this fail.
        let directory = TestDirectory::new("camera-preview-target-decode");
        let order = ByteOrder::Little;
        let images: Vec<_> = [
            (240, 160, [10, 220, 20]),
            (480, 320, [220, 10, 20]),
            (960, 640, [10, 20, 220]),
        ]
        .into_iter()
        .map(|(w, h, color)| {
            let pixels = image::RgbImage::from_pixel(w, h, image::Rgb(color));
            let mut bytes = Vec::new();
            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut bytes, 90)
                .encode_image(&pixels)
                .unwrap();
            bytes
        })
        .collect();
        let mut bytes = tiff(order, 256 + images.iter().map(Vec::len).sum::<usize>());
        let mut payload = 256;
        let mut offsets = Vec::new();
        for (index, image) in images.iter().enumerate() {
            offsets.push(payload);
            ifd(
                &mut bytes,
                8 + index * 64,
                &[
                    entry(513, 4, 1, payload as u32, order),
                    entry(514, 4, 1, image.len() as u32, order),
                ],
                if index == 2 {
                    0
                } else {
                    (8 + (index + 1) * 64) as u32
                },
                order,
            );
            bytes[payload..payload + image.len()].copy_from_slice(image);
            payload += image.len();
        }
        let path = directory.path().join("sufficient-camera-preview.arw");
        std::fs::write(&path, &bytes).unwrap();
        let cancelled = AtomicBool::new(false);
        let medium = load_with_policy(&path, 330, false, &cancelled).unwrap();
        assert_eq!(medium.source_size, [960, 640]);
        assert_eq!(medium.size, [330, 220]);
        assert!(
            medium.rgba[0] > 200 && medium.rgba[1] < 30 && medium.rgba[2] < 30,
            "target tier must decode red 480px image, not green undersized or blue excessive image"
        );
        let large = load_with_policy(&path, 700, false, &cancelled).unwrap();
        assert_eq!(large.source_size, medium.source_size);
        assert!(
            large.rgba[2] > 200 && large.rgba[0] < 30,
            "a genuinely larger requested tier must still decode the larger source"
        );
        let native = load_with_policy(&path, 2_000, false, &cancelled).unwrap();
        assert_eq!(native.size, [960, 640]);
        assert!(!native.is_overview);
        assert_eq!(std::fs::read(&path).unwrap(), bytes);

        // Candidate failure must still reach intact photographic pixels.
        bytes[offsets[1]..offsets[1] + 2].fill(0);
        std::fs::write(&path, &bytes).unwrap();
        let fallback = load_with_policy(&path, 330, false, &cancelled).unwrap();
        assert_eq!(fallback.source_size, [960, 640]);
        assert!(fallback.rgba[2] > 200 && fallback.rgba[0] < 30);
    }

    #[test]
    fn cancellation_checkpoint_skips_resize_derivative_and_joins_before_new_lane() {
        use std::sync::{Arc, Barrier};
        let entered = Arc::new(Barrier::new(2));
        let finish_codec = Arc::new(Barrier::new(2));
        let expensive_followups = Arc::new(AtomicUsize::new(0));
        let worker_entered = entered.clone();
        let worker_finish = finish_codec.clone();
        let worker_followups = expensive_followups.clone();
        let task = spawn_task("preview-cancel-checkpoint-test", move |cancelled| {
            worker_entered.wait();
            // A codec already running cannot be preempted inside the library.
            worker_finish.wait();
            check_cancelled(&cancelled)?;
            worker_followups.fetch_add(1, Ordering::SeqCst);
            Ok(())
        });
        entered.wait();
        task.cancel();
        assert!(task.is_cancelled());
        assert!(
            matches!(
                task.receiver.try_recv(),
                Err(std::sync::mpsc::TryRecvError::Empty)
            ),
            "cancel may not pretend an in-progress codec has returned"
        );
        finish_codec.wait();
        assert!(matches!(
            task.receiver
                .recv_timeout(std::time::Duration::from_secs(3)),
            Err(std::sync::mpsc::RecvTimeoutError::Disconnected)
        ));
        assert_eq!(expensive_followups.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn letterboxed_four_three_thumbnail_is_rejected_for_the_three_two_aperture() {
        // The actual Sony capture has160x120,1616x1080 and7008x4672 JPEGs.
        // Green4:3 must never be displayed as the small substitute for the
        // red compatible medium or blue3:2 full preview. Solid colour is an
        // independent identity witness; source_size is intentionally constant.
        fn solid(width: u32, height: u32, color: [u8; 3]) -> Vec<u8> {
            let pixels = image::RgbImage::from_pixel(width, height, image::Rgb(color));
            let mut jpeg = Vec::new();
            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 90)
                .encode_image(&pixels)
                .unwrap();
            jpeg
        }
        let directory = TestDirectory::new("camera-preview-compatible-aperture");
        let order = ByteOrder::Little;
        let images = [
            solid(160, 120, [10, 220, 20]),
            solid(1_616, 1_080, [220, 10, 20]),
            solid(1_920, 1_280, [10, 20, 220]),
        ];
        let mut bytes = tiff(order, 256 + images.iter().map(Vec::len).sum::<usize>());
        let mut payload = 256;
        let mut medium_offset = 0;
        for (index, jpeg) in images.iter().enumerate() {
            if index == 1 {
                medium_offset = payload;
            }
            ifd(
                &mut bytes,
                8 + index * 64,
                &[
                    entry(513, 4, 1, payload as u32, order),
                    entry(514, 4, 1, jpeg.len() as u32, order),
                ],
                if index == 2 {
                    0
                } else {
                    (8 + (index + 1) * 64) as u32
                },
                order,
            );
            bytes[payload..payload + jpeg.len()].copy_from_slice(jpeg);
            payload += jpeg.len();
        }
        let path = directory.path().join("letterboxed-thumbnail.arw");
        std::fs::write(&path, &bytes).unwrap();
        let cancelled = AtomicBool::new(false);
        let small = load(&path, 240, &cancelled).unwrap();
        let overview = load_with_policy(&path, 960, true, &cancelled).unwrap();
        let full = load(&path, 1_920, &cancelled).unwrap();
        assert_eq!(small.source_size, [1_920, 1_280]);
        assert_eq!(full.source_size, small.source_size);
        assert_eq!(small.size, [240, 160]);
        assert_eq!(overview.source_size, small.source_size);
        assert!(
            overview.size[0] >= 900 && overview.rgba[0] > 200 && overview.rgba[2] < 30,
            "useful-sized overview must still use red medium JPEG, not blue full JPEG"
        );
        assert!(
            small.rgba[0] > 200 && small.rgba[1] < 30,
            "small preview must come from red mediumJPEG"
        );
        assert!(
            full.rgba[2] > 200 && full.rgba[0] < 30,
            "full preview must come from blue fullJPEG"
        );
        assert!(compatible_aspect([1_616, 1_080], [7_008, 4_672]));
        assert!(!compatible_aspect([160, 120], [7_008, 4_672]));
        assert!(!compatible_aspect([160, 90], [7_008, 4_672]));

        let batch = load_filmstrip_batch(
            vec![
                (73, path.clone()),
                (91, directory.path().join("missing-frame.arw")),
            ],
            240,
        )
        .receiver
        .recv()
        .unwrap()
        .unwrap();
        assert_eq!(
            batch.iter().map(|(index, _)| *index).collect::<Vec<_>>(),
            [73, 91]
        );
        let native = &batch[0].1.as_ref().unwrap().image;
        assert_eq!(native.source_size, [160, 120]);
        assert_eq!(
            native.size,
            [160, 120],
            "filmstrip bypasses the much larger compatible JPEG decode"
        );
        assert!(
            native.rgba[1] > 200 && native.rgba[0] < 30,
            "green tiny JPEG is a rejecting identity witness against accidentally decoding red medium"
        );
        assert!(
            batch[1].1.is_err(),
            "one bad frame must not discard the rest of a visible batch"
        );
        let detail = load_browser_preview(path.clone(), 960, true, Some(240))
            .receiver
            .recv()
            .unwrap()
            .unwrap();
        assert_eq!(
            detail.image.rgba, overview.rgba,
            "bundling a filmstrip derivative cannot perturb detail pixels"
        );
        let derivative = detail.thumbnail.unwrap();
        assert_eq!(derivative.source_size, overview.source_size);
        assert!(derivative.size.into_iter().all(|side| side <= 240));
        assert!(
            derivative.rgba[0] > 200 && derivative.rgba[1] < 30,
            "detail derivative keeps the already decoded red camera image, without a second extraction"
        );
        assert!(thumbnail_of(&overview, 240, &AtomicBool::new(true)).is_err());
        let cached_contact = load_browser_preview(path.clone(), 960, true, None)
            .receiver
            .recv()
            .unwrap()
            .unwrap();
        assert!(
            cached_contact.thumbnail.is_none(),
            "an existing native contact skips the derivative allocation"
        );
        assert_eq!(
            cached_contact.image.rgba, overview.rgba,
            "omitting the derivative cannot change canonical camera pixels"
        );
        let rescue = load_overview_batch(vec![(73, path.clone())], 960, None)
            .receiver
            .recv()
            .unwrap()
            .unwrap();
        assert_eq!(rescue[0].0, 73);
        let rescue = rescue[0].1.as_ref().unwrap();
        assert!(rescue.thumbnail.is_none());
        assert_eq!(
            rescue.image.rgba, overview.rgba,
            "the fast rescue honors the same retained-contact policy"
        );
        assert_eq!(
            std::fs::read(&path).unwrap(),
            bytes,
            "both readers leave the source container unchanged"
        );

        // If the medium is damaged, waiting for/reducing the blue full JPEG is
        // preferable to installing the incompatible green thumbnail.
        bytes[medium_offset..medium_offset + 2].fill(0);
        std::fs::write(&path, &bytes).unwrap();
        let fallback = load(&path, 240, &cancelled).unwrap();
        assert_eq!(fallback.source_size, [1_920, 1_280]);
        assert!(fallback.rgba[2] > 200 && fallback.rgba[1] < 30);
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }

    #[test]
    fn filmstrip_batches_reject_unbounded_requests_before_opening_any_source() {
        let paths = (0..=FILMSTRIP_BATCH_MAX)
            .map(|index| (index, PathBuf::from("does-not-exist.arw")))
            .collect();
        let error = load_filmstrip_batch(paths, 240)
            .receiver
            .recv()
            .unwrap()
            .err()
            .unwrap();
        assert!(
            error.contains("Too many filmstrip"),
            "invalid batch size must reject before any per-frame file failure"
        );
    }

    #[test]
    fn parallel_batch_is_bounded_and_publishes_input_order_after_out_of_order_completion() {
        use std::sync::{Barrier, Condvar, Mutex};
        let gate = Barrier::new(3);
        let wake = (Mutex::new(false), Condvar::new());
        let active = AtomicUsize::new(0);
        let peak = AtomicUsize::new(0);
        let completions = Mutex::new(Vec::new());
        let output = bounded_map(8, 20, &AtomicBool::new(false), |slot| {
            let now = active.fetch_add(1, Ordering::SeqCst) + 1;
            peak.fetch_max(now, Ordering::SeqCst);
            if slot < 3 {
                gate.wait();
            }
            if slot == 0 {
                let mut released = wake.0.lock().unwrap();
                while !*released {
                    released = wake.1.wait(released).unwrap();
                }
            }
            completions.lock().unwrap().push(slot);
            if slot == 1 {
                *wake.0.lock().unwrap() = true;
                wake.1.notify_one();
            }
            active.fetch_sub(1, Ordering::SeqCst);
            if slot == 5 {
                Err("fixture unreadable frame")
            } else {
                Ok(slot)
            }
        })
        .unwrap();
        assert_eq!(
            peak.load(Ordering::SeqCst),
            3,
            "the fixture must actually overlap work and enforce the cap despite an excessive worker request"
        );
        assert_ne!(
            completions.lock().unwrap()[0],
            0,
            "the fixture must actually complete out of source order"
        );
        assert_eq!(
            output,
            (0..8)
                .map(|slot| if slot == 5 {
                    Err("fixture unreadable frame")
                } else {
                    Ok(slot)
                })
                .collect::<Vec<_>>()
        );
        assert_eq!(active.load(Ordering::SeqCst), 0);
    }

    #[test]
    fn cancelled_parallel_batch_does_not_publish_a_partial_strip_or_leak_workers() {
        let cancelled = AtomicBool::new(true);
        let loaded = AtomicUsize::new(0);
        assert!(bounded_map(8, 3, &cancelled, |_| loaded.fetch_add(1, Ordering::SeqCst)).is_err());
        assert_eq!(loaded.load(Ordering::SeqCst), 0);
        cancelled.store(false, Ordering::SeqCst);
        assert!(
            bounded_map(8, 3, &cancelled, |_| {
                loaded.fetch_add(1, Ordering::SeqCst);
                cancelled.store(true, Ordering::SeqCst);
            })
            .is_err()
        );
        let observed = loaded.load(Ordering::SeqCst);
        assert!(
            (1..=3).contains(&observed),
            "only the bounded already-started jobs may see cancellation"
        );
        assert_eq!(
            loaded.load(Ordering::SeqCst),
            observed,
            "returning joins all owned workers"
        );
    }

    #[test]
    #[ignore = "explicit read-only benchmark on a named 12-RAW sample"]
    fn benchmark_real_filmstrip_parallel() {
        use std::time::Instant;
        let source = PathBuf::from(
            std::env::var_os("STREHL_UI_BENCH_SOURCE").expect("name the read-only sample folder"),
        );
        let report = PathBuf::from(
            std::env::var_os("STREHL_UI_BENCH_REPORT").expect("name the benchmark JSON output"),
        );
        let mut files: Vec<_> = std::fs::read_dir(&source)
            .unwrap()
            .filter_map(|entry| {
                let path = entry.ok()?.path();
                path.extension()
                    .is_some_and(|e| e.eq_ignore_ascii_case("arw"))
                    .then_some(path)
            })
            .collect();
        files.sort();
        assert_eq!(
            files.len(),
            12,
            "benchmark only the named compact sample, not an accidental complete source collection"
        );
        let paths: Vec<_> = files.into_iter().enumerate().collect();
        let cancelled = AtomicBool::new(false);
        let mut reference: Option<Vec<(usize, PreviewImage)>> = None;
        let mut timings = Vec::new();
        for round in 0..6 {
            for workers in if round % 2 == 0 { [1, 3] } else { [3, 1] } {
                let start = Instant::now();
                let batch: Vec<_> = paths
                    .chunks(FILMSTRIP_BATCH_MAX)
                    .flat_map(|chunk| filmstrip_images(chunk, 240, &cancelled, workers).unwrap())
                    .collect();
                let elapsed = start.elapsed().as_secs_f64() * 1000.0;
                let images: Vec<_> = batch
                    .into_iter()
                    .map(|(index, image)| (index, image.unwrap().image))
                    .collect();
                if let Some(reference) = &reference {
                    for ((index, image), (expected, prior)) in images.iter().zip(reference) {
                        assert_eq!(index, expected);
                        assert_eq!(image.path, prior.path);
                        assert_eq!(image.source_size, prior.source_size);
                        assert_eq!(image.size, prior.size);
                        assert_eq!(
                            image.rgba, prior.rgba,
                            "parallel publication cannot change decoded photographic pixels"
                        );
                    }
                } else {
                    reference = Some(images);
                }
                timings.push(serde_json::json!({"round": round, "workers": workers, "milliseconds": elapsed}));
            }
        }
        let minimum = |workers| {
            timings
                .iter()
                .filter(|row| row["workers"] == workers)
                .map(|row| row["milliseconds"].as_f64().unwrap())
                .fold(f64::INFINITY, f64::min)
        };
        let result = serde_json::json!({
            "source": source, "captures": 12, "batch_limit": FILMSTRIP_BATCH_MAX,
            "order": "six alternating sequential/parallel rounds; min per setting",
            "sequential_min_ms": minimum(1), "parallel_min_ms": minimum(3),
            "identical_preview_pixels_and_apertures": true, "runs": timings,
        });
        std::fs::write(&report, serde_json::to_vec_pretty(&result).unwrap()).unwrap();
        println!("{}", serde_json::to_string_pretty(&result).unwrap());
    }
}
