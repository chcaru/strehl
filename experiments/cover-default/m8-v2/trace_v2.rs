//! M8-v2 value-only trace producer.
//!
//! The payload deliberately retains the historical block-v1 layout so a new
//! independent checker can reuse that parser:
//!
//! ```text
//! <8s9I6d2fI
//! magic, wire_version, kernel,
//! source_width, source_height, destination_width, destination_height,
//! site_x, site_y, channel,
//! transform.a.re, transform.a.im, transform.b.re, transform.b.im, cx, cy,
//! black_white_range, site_gain, frame_path_bytes,
//! frame_path, source_f32_bits, destination_f32_bits
//! ```
//!
//! `WIRE_VERSION == 2` is the version already carried by block-v1. The producer
//! generation is explicit in `PRODUCER_TAG`, the `STREHL_M8_V2_TRACE_DIR`
//! environment name, and every completed filename. There is intentionally no
//! support, hull, tolerance, contributor, or verdict field.
//! Frame order is not duplicated into block-v1: the exact UTF-8 path maps to
//! the frozen ordered source inventory, which is the authority for frame index
//! and exact-tie precedence.
//!
//! Completed files are retained. A deterministic frame-path/site claim refuses
//! concurrent or repeated writes. The fully flushed staging file is published
//! with a create-only hard link, which is the no-overwrite atomic equivalent of
//! a rename on the same filesystem. A leftover claim or staging file is
//! ambiguous state and therefore causes a loud failure rather than recovery.
//!
//! The registered render must use `STREHL_PYRAMID_WORKERS=1`. Auxiliary product
//! passes that warp the same frame again (notably the default gate-floor probe
//! or a confidence-map pass) must be disabled by the runner: a second
//! frame/site is deliberately rejected rather than silently hidden.

use std::fs::{self, File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use anyhow::{Context, Result, bail, ensure};
use strehl_core::align::{Resampler, Similarity};
use strehl_core::plane::PlaneGeometry;

#[cfg(not(target_endian = "little"))]
compile_error!("M8 block-v1 requires a little-endian target");

const MAGIC: &[u8; 8] = b"M8SITE01";
const WIRE_VERSION: u32 = 2;
const PRODUCER_TAG: &str = "m8-v2-block-v1-p2";
#[rustfmt::skip]
const SHA256_INITIAL: [u32; 8] = [
    0x6a09e667,
    0xbb67ae85,
    0x3c6ef372,
    0xa54ff53a,
    0x510e527f,
    0x9b05688c,
    0x1f83d9ab,
    0x5be0cd19,
];
#[rustfmt::skip]
const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
    0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
    0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
    0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2,
];
static NEXT_STAGING_ID: AtomicU64 = AtomicU64::new(0);

/// One block-v1 payload. This public shape is also used by the synthetic
/// producer fixture when this module is included from a private snapshot.
pub struct ValueBlock<'a> {
    pub resampler: Resampler,
    pub source_width: usize,
    pub source_height: usize,
    pub destination_width: usize,
    pub destination_height: usize,
    pub site_x: usize,
    pub site_y: usize,
    pub channel: usize,
    pub transform: Similarity,
    pub cx: f64,
    pub cy: f64,
    pub black_white_range: f32,
    pub site_gain: f32,
    pub frame_path: &'a str,
    pub source: &'a [f32],
    pub destination: &'a [f32],
}

#[derive(Clone)]
struct Sha256 {
    state: [u32; 8],
    buffer: [u8; 64],
    used: usize,
    bytes: u64,
}

impl Sha256 {
    fn new() -> Self {
        Self {
            state: SHA256_INITIAL,
            buffer: [0; 64],
            used: 0,
            bytes: 0,
        }
    }

    fn update(&mut self, mut input: &[u8]) {
        self.bytes = self
            .bytes
            .checked_add(u64::try_from(input.len()).expect("slice length fits u64"))
            .expect("M8 block exceeds SHA-256 length capacity");

        if self.used != 0 {
            let take = (64 - self.used).min(input.len());
            self.buffer[self.used..self.used + take].copy_from_slice(&input[..take]);
            self.used += take;
            input = &input[take..];
            if self.used < 64 {
                return;
            }
            let block = self.buffer;
            self.compress(&block);
            self.used = 0;
        }

        while input.len() >= 64 {
            let block: &[u8; 64] = input[..64].try_into().expect("64-byte SHA-256 block");
            self.compress(block);
            input = &input[64..];
        }
        self.buffer[..input.len()].copy_from_slice(input);
        self.used = input.len();
    }

    fn compress(&mut self, block: &[u8; 64]) {
        let mut words = [0u32; 64];
        let (chunks, remainder) = block.as_chunks::<4>();
        debug_assert!(remainder.is_empty());
        for (word, chunk) in words[..16].iter_mut().zip(chunks) {
            *word = u32::from_be_bytes(*chunk);
        }
        for i in 16..64 {
            let s0 = words[i - 15].rotate_right(7)
                ^ words[i - 15].rotate_right(18)
                ^ (words[i - 15] >> 3);
            let s1 = words[i - 2].rotate_right(17)
                ^ words[i - 2].rotate_right(19)
                ^ (words[i - 2] >> 10);
            words[i] = words[i - 16]
                .wrapping_add(s0)
                .wrapping_add(words[i - 7])
                .wrapping_add(s1);
        }

        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = self.state;
        for i in 0..64 {
            let big_e = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choose = (e & f) ^ ((!e) & g);
            let t1 = h
                .wrapping_add(big_e)
                .wrapping_add(choose)
                .wrapping_add(SHA256_K[i])
                .wrapping_add(words[i]);
            let big_a = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let t2 = big_a.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (state, value) in self.state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *state = state.wrapping_add(value);
        }
    }

    fn finish(mut self) -> [u8; 32] {
        let bit_length = self
            .bytes
            .checked_mul(8)
            .expect("M8 block exceeds SHA-256 bit-length capacity");
        self.buffer[self.used] = 0x80;
        self.used += 1;
        if self.used > 56 {
            self.buffer[self.used..].fill(0);
            let block = self.buffer;
            self.compress(&block);
            self.buffer = [0; 64];
        } else {
            self.buffer[self.used..].fill(0);
        }
        self.buffer[56..].copy_from_slice(&bit_length.to_be_bytes());
        let block = self.buffer;
        self.compress(&block);

        let mut out = [0u8; 32];
        let (chunks, remainder) = out.as_chunks_mut::<4>();
        debug_assert!(remainder.is_empty());
        for (chunk, value) in chunks.iter_mut().zip(self.state) {
            chunk.copy_from_slice(&value.to_be_bytes());
        }
        out
    }
}

struct DigestWriter<W> {
    inner: W,
    sha256: Sha256,
}

impl<W: Write> Write for DigestWriter<W> {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        let n = self.inner.write(buf)?;
        self.sha256.update(&buf[..n]);
        Ok(n)
    }

    fn flush(&mut self) -> std::io::Result<()> {
        self.inner.flush()
    }
}

fn sha256(bytes: &[u8]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(bytes);
    hash.finish()
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(char::from(DIGITS[usize::from(byte >> 4)]));
        out.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    out
}

fn write_u32(writer: &mut impl Write, value: usize, field: &str) -> Result<()> {
    let value = u32::try_from(value).with_context(|| format!("{field} exceeds u32"))?;
    writer.write_all(&value.to_le_bytes())?;
    Ok(())
}

fn f32_bytes(values: &[f32]) -> &[u8] {
    // SAFETY: f32 has no invalid bit patterns, the byte length is exact, this
    // target is compile-time constrained to little endian, and the byte slice
    // cannot outlive `values`.
    unsafe {
        std::slice::from_raw_parts(values.as_ptr().cast::<u8>(), std::mem::size_of_val(values))
    }
}

fn kernel_code(resampler: Resampler) -> Result<u32> {
    match resampler {
        Resampler::CatmullRom => Ok(0),
        Resampler::Bilinear => Ok(1),
        other => bail!("M8-v2 supports Catmull-Rom and bilinear traces, got {other:?}"),
    }
}

fn completed_blocks(blocks: &Path, prefix: &str) -> Result<Vec<PathBuf>> {
    let mut found = Vec::new();
    for entry in fs::read_dir(blocks).with_context(|| format!("reading {}", blocks.display()))? {
        let path = entry?.path();
        let Some(name) = path.file_name().and_then(|name| name.to_str()) else {
            bail!("{} contains a non-UTF-8 trace filename", blocks.display());
        };
        if name.starts_with(prefix) && name.ends_with(".m8site") {
            found.push(path);
        }
    }
    found.sort();
    Ok(found)
}

fn refuse_completed(blocks: &Path, prefix: &str) -> Result<()> {
    let found = completed_blocks(blocks, prefix)?;
    match found.as_slice() {
        [] => Ok(()),
        [path] => bail!(
            "duplicate M8-v2 frame/site: completed block already exists: {}",
            path.display()
        ),
        _ => bail!(
            "ambiguous duplicate M8-v2 frame/site: {} completed blocks share key {prefix}",
            found.len()
        ),
    }
}

fn create_staging_file(staging: &Path, prefix: &str) -> Result<(PathBuf, File)> {
    for _ in 0..1024 {
        let id = NEXT_STAGING_ID.fetch_add(1, Ordering::Relaxed);
        let path = staging.join(format!("{prefix}.{}.{}.partial", std::process::id(), id));
        match OpenOptions::new().write(true).create_new(true).open(&path) {
            Ok(file) => return Ok((path, file)),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => {
                return Err(error)
                    .with_context(|| format!("creating unique staging file {}", path.display()));
            }
        }
    }
    bail!("could not allocate a unique M8-v2 staging filename")
}

fn validate_payload(block: &ValueBlock<'_>) -> Result<()> {
    let source_pixels = block
        .source_width
        .checked_mul(block.source_height)
        .context("M8-v2 source dimensions overflow usize")?;
    let destination_pixels = block
        .destination_width
        .checked_mul(block.destination_height)
        .context("M8-v2 destination dimensions overflow usize")?;
    ensure!(
        block.source.len() == source_pixels,
        "M8-v2 source length {} does not match {}x{}",
        block.source.len(),
        block.source_width,
        block.source_height
    );
    ensure!(
        block.destination.len() == destination_pixels,
        "M8-v2 destination length {} does not match {}x{}",
        block.destination.len(),
        block.destination_width,
        block.destination_height
    );
    ensure!(
        block.site_x < 2 && block.site_y < 2,
        "M8-v2 CFA site must be in a 2x2 cell"
    );
    ensure!(block.channel < 3, "M8-v2 channel must be R=0, G=1, or B=2");
    ensure!(
        block.black_white_range.is_finite() && block.black_white_range > 0.0,
        "M8-v2 black/white range must be positive and finite"
    );
    ensure!(
        block.site_gain.is_finite() && block.site_gain > 0.0,
        "M8-v2 site gain must be positive and finite"
    );
    ensure!(
        !block.frame_path.is_empty(),
        "M8-v2 frame path must not be empty"
    );
    kernel_code(block.resampler)?;
    for (value, field) in [
        (block.source_width, "source width"),
        (block.source_height, "source height"),
        (block.destination_width, "destination width"),
        (block.destination_height, "destination height"),
        (block.site_x, "site x"),
        (block.site_y, "site y"),
        (block.channel, "channel"),
        (block.frame_path.len(), "frame path byte length"),
    ] {
        u32::try_from(value).with_context(|| format!("{field} exceeds u32"))?;
    }
    Ok(())
}

fn write_payload(writer: &mut impl Write, block: &ValueBlock<'_>) -> Result<()> {
    validate_payload(block)?;
    writer.write_all(MAGIC)?;
    writer.write_all(&WIRE_VERSION.to_le_bytes())?;
    writer.write_all(&kernel_code(block.resampler)?.to_le_bytes())?;
    for (value, field) in [
        (block.source_width, "source width"),
        (block.source_height, "source height"),
        (block.destination_width, "destination width"),
        (block.destination_height, "destination height"),
        (block.site_x, "site x"),
        (block.site_y, "site y"),
        (block.channel, "channel"),
    ] {
        write_u32(writer, value, field)?;
    }
    for value in [
        block.transform.a.re,
        block.transform.a.im,
        block.transform.b.re,
        block.transform.b.im,
        block.cx,
        block.cy,
    ] {
        writer.write_all(&value.to_bits().to_le_bytes())?;
    }
    writer.write_all(&block.black_white_range.to_bits().to_le_bytes())?;
    writer.write_all(&block.site_gain.to_bits().to_le_bytes())?;
    write_u32(writer, block.frame_path.len(), "frame path byte length")?;
    writer.write_all(block.frame_path.as_bytes())?;
    writer.write_all(f32_bytes(block.source))?;
    writer.write_all(f32_bytes(block.destination))?;
    Ok(())
}

/// Write and retain one collision-safe, content-hashed value block.
///
/// No existing completion or in-progress claim is treated as success. This
/// function never computes anything from the samples besides the SHA-256 used
/// to name their immutable container.
pub fn write_value_block(root: &Path, block: &ValueBlock<'_>) -> Result<PathBuf> {
    // Refuse all deterministic payload/configuration errors before claiming a
    // frame/site. Claims are retained only when an actual write/publish fails
    // and the on-disk state is therefore genuinely ambiguous.
    validate_payload(block)?;
    let blocks = root.join("blocks");
    let claims = root.join("claims");
    let staging = root.join("staging");
    fs::create_dir_all(&blocks).with_context(|| format!("creating {}", blocks.display()))?;
    fs::create_dir_all(&claims).with_context(|| format!("creating {}", claims.display()))?;
    fs::create_dir_all(&staging).with_context(|| format!("creating {}", staging.display()))?;

    let frame_hash = hex(&sha256(block.frame_path.as_bytes()));
    let prefix = format!(
        "{PRODUCER_TAG}-{frame_hash}-s{}{}",
        block.site_x, block.site_y
    );
    refuse_completed(&blocks, &prefix)?;

    let claim_path = claims.join(format!("{prefix}.claim"));
    let mut claim = match OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&claim_path)
    {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
            bail!(
                "ambiguous duplicate M8-v2 frame/site: in-progress claim exists: {}",
                claim_path.display()
            )
        }
        Err(error) => {
            return Err(error)
                .with_context(|| format!("creating frame/site claim {}", claim_path.display()));
        }
    };
    writeln!(
        claim,
        "{PRODUCER_TAG}\npid={}\nsite={},{}\nframe={}",
        std::process::id(),
        block.site_x,
        block.site_y,
        block.frame_path
    )?;
    claim.sync_all()?;
    drop(claim);

    // The claim closes the scan/create race. Any discovery here is necessarily
    // ambiguous external or stale state, and the claim is retained on failure.
    refuse_completed(&blocks, &prefix)?;

    let (staging_path, staging_file) = create_staging_file(&staging, &prefix)?;
    let digest_writer = DigestWriter {
        inner: staging_file,
        sha256: Sha256::new(),
    };
    let mut writer = BufWriter::new(digest_writer);
    write_payload(&mut writer, block)
        .with_context(|| format!("writing value block {}", staging_path.display()))?;
    writer.flush()?;
    let digest_writer = writer
        .into_inner()
        .map_err(|error| error.into_error())
        .with_context(|| format!("finishing value block {}", staging_path.display()))?;
    let DigestWriter {
        inner: staging_file,
        sha256,
    } = digest_writer;
    staging_file.sync_all()?;
    let content_hash = hex(&sha256.finish());
    drop(staging_file);

    let completed = blocks.join(format!("{prefix}-{content_hash}.m8site"));
    fs::hard_link(&staging_path, &completed).with_context(|| {
        format!(
            "publishing M8-v2 block without overwrite {}",
            completed.display()
        )
    })?;
    fs::remove_file(&staging_path)
        .with_context(|| format!("removing published staging link {}", staging_path.display()))?;
    fs::remove_file(&claim_path)
        .with_context(|| format!("removing completed claim {}", claim_path.display()))?;
    Ok(completed)
}

#[allow(clippy::too_many_arguments)]
pub fn trace_site(
    frame: &strehl_raw::Frame,
    site_x: usize,
    site_y: usize,
    geom: PlaneGeometry,
    transform: Similarity,
    cx: f64,
    cy: f64,
    channel: usize,
    site_gain: f32,
    resampler: Resampler,
    source: &[f32],
    destination: &[f32],
) -> Result<()> {
    // The disabled path performs one environment lookup and touches no render
    // value, filesystem path, hash state, or allocation.
    let Some(root) = std::env::var_os("STREHL_M8_V2_TRACE_DIR") else {
        return Ok(());
    };
    let source_width = geom
        .width
        .checked_mul(2)
        .context("M8-v2 source width overflow")?;
    let source_height = geom
        .height
        .checked_mul(2)
        .context("M8-v2 source height overflow")?;
    let frame_path = frame
        .path
        .to_str()
        .context("M8-v2 frame path is not UTF-8")?;
    let expected_channel = match (site_x, site_y) {
        (0, 0) => 0,
        (1, 0) | (0, 1) => 1,
        (1, 1) => 2,
        _ => bail!("M8-v2 CFA site must be in a 2x2 cell"),
    };
    ensure!(
        channel == expected_channel,
        "M8-v2 CFA site ({site_x},{site_y}) requires channel {expected_channel}, got {channel}"
    );
    write_value_block(
        &PathBuf::from(root),
        &ValueBlock {
            resampler,
            source_width,
            source_height,
            destination_width: geom.width,
            destination_height: geom.height,
            site_x,
            site_y,
            channel,
            transform,
            cx,
            cy,
            black_white_range: frame.levels.range(),
            site_gain,
            frame_path,
            source,
            destination,
        },
    )?;
    Ok(())
}
