//! Tiled lossless JPEG raw data, decoded here instead of by the linked
//! decoder.
//!
//! Sony's lossless-compressed raw (A7C II and later bodies) stores the CFA as
//! TIFF `Compression = 7` tiles, each a lossless JPEG (ITU-T T.81 process 14,
//! Annex H): 512x512 CFA samples coded as 256 lines of 256 four-component
//! samples, one Huffman table, predictor 1. Each four-component sample is one
//! 2x2 CFA quad, components 0 and 1 on its upper row and 2 and 3 on its lower
//! (MEASURED: the only layout under which every sample of the corpus equals
//! the linked decoder's). Decoding is a pure function of the
//! file, so a second implementation can be checked exactly against the first:
//! every sample of every file must equal the linked decoder's
//! (`tests/lossless-jpeg.rs` runs a corpus; the unit tests below run an encoder
//! written from the same specification against this decoder).
//!
//! Written from T.81 and the TIFF 6.0 tile tags only.
//!
//! # Why
//!
//! With the GPU preparing frames, decoding became the fold's limit: the linked
//! decoder took ~165 ms of CPU per 33 MP frame (MEASURED on bug-7, one rayon
//! thread), and with eight frames in flight on a 16-core machine throughput
//! stopped at ~78 frames/s whatever the thread count. This decoder does the
//! same work with a table lookup per sample, a bit reader that never handles
//! byte stuffing in the inner loop (stuffing is removed per tile first), and
//! several tiles decoded in one loop so a core runs independent dependency
//! chains side by side.
//!
//! # Scope
//!
//! Anything this module does not recognise exactly — another compression,
//! predictor, point transform, restart markers, component layout, a table it
//! cannot build — returns `None` or an error, and the caller decodes with the
//! linked decoder instead. It never guesses.

/// The raw image's tile layout, read from its TIFF IFD.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Tiles {
    pub width: usize,
    pub height: usize,
    pub tile_width: usize,
    pub tile_height: usize,
    pub bits: u32,
    /// Byte ranges of each tile's JPEG stream, row-major over the tile grid.
    pub ranges: Vec<(usize, usize)>,
}

const TAG_SUBFILE: u16 = 0x00FE;
const TAG_WIDTH: u16 = 0x0100;
const TAG_HEIGHT: u16 = 0x0101;
const TAG_BITS: u16 = 0x0102;
const TAG_COMPRESSION: u16 = 0x0103;
const TAG_PHOTOMETRIC: u16 = 0x0106;
const TAG_SAMPLES: u16 = 0x0115;
const TAG_TILE_WIDTH: u16 = 0x0142;
const TAG_TILE_LENGTH: u16 = 0x0143;
const TAG_TILE_OFFSETS: u16 = 0x0144;
const TAG_TILE_COUNTS: u16 = 0x0145;
const TAG_SUB_IFDS: u16 = 0x014A;
const COMPRESSION_JPEG: u32 = 7;
const PHOTOMETRIC_CFA: u32 = 32803;

fn u16le(b: &[u8], at: usize) -> Option<u16> {
    Some(u16::from_le_bytes(b.get(at..at + 2)?.try_into().ok()?))
}

fn u32le(b: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_le_bytes(b.get(at..at + 4)?.try_into().ok()?))
}

/// One IFD entry's integer values (SHORT or LONG), wherever they are stored.
fn values(b: &[u8], entry: usize) -> Option<Vec<u32>> {
    let typ = u16le(b, entry + 2)?;
    let count = u32le(b, entry + 4)? as usize;
    let size: usize = match typ {
        3 => 2,
        4 | 13 => 4,
        _ => return None,
    };
    let total = size.checked_mul(count)?;
    let at = if total <= 4 {
        entry + 8
    } else {
        u32le(b, entry + 8)? as usize
    };
    let data = b.get(at..at.checked_add(total)?)?;
    Some(
        (0..count)
            .map(|i| match size {
                2 => u32::from(u16::from_le_bytes([data[2 * i], data[2 * i + 1]])),
                _ => u32::from_le_bytes(data[4 * i..4 * i + 4].try_into().unwrap()),
            })
            .collect(),
    )
}

/// Find the full-resolution CFA image stored as lossless JPEG tiles: a
/// little-endian TIFF, walked through the IFD chain and SubIFDs.
pub(crate) fn find_tiles(b: &[u8]) -> Option<Tiles> {
    if b.get(0..4)? != b"II*\0" {
        return None;
    }
    let mut stack = vec![u32le(b, 4)? as usize];
    let mut seen = Vec::new();
    while let Some(ifd) = stack.pop() {
        if ifd == 0 || seen.contains(&ifd) || seen.len() > 64 {
            continue;
        }
        seen.push(ifd);
        let n = u16le(b, ifd)? as usize;
        let mut tags = std::collections::BTreeMap::new();
        for i in 0..n {
            let entry = ifd + 2 + 12 * i;
            let tag = u16le(b, entry)?;
            if let Some(v) = values(b, entry) {
                tags.insert(tag, v);
            }
        }
        if let Some(next) = u32le(b, ifd + 2 + 12 * n) {
            stack.push(next as usize);
        }
        if let Some(subs) = tags.get(&TAG_SUB_IFDS) {
            stack.extend(subs.iter().map(|&s| s as usize));
        }
        let one = |t: u16| tags.get(&t).filter(|v| v.len() == 1).map(|v| v[0]);
        if one(TAG_COMPRESSION) != Some(COMPRESSION_JPEG)
            || one(TAG_PHOTOMETRIC) != Some(PHOTOMETRIC_CFA)
            || one(TAG_SUBFILE).unwrap_or(0) != 0
            || one(TAG_SAMPLES).unwrap_or(1) != 1
        {
            continue;
        }
        let (width, height) = (one(TAG_WIDTH)? as usize, one(TAG_HEIGHT)? as usize);
        let (tile_width, tile_height) = (
            one(TAG_TILE_WIDTH)? as usize,
            one(TAG_TILE_LENGTH)? as usize,
        );
        let bits = one(TAG_BITS)?;
        let offsets = tags.get(&TAG_TILE_OFFSETS)?;
        let counts = tags.get(&TAG_TILE_COUNTS)?;
        let tiles = width.div_ceil(tile_width.max(1)) * height.div_ceil(tile_height.max(1));
        if width == 0
            || height == 0
            || tile_width == 0
            || tile_height == 0
            || !(2..=16).contains(&bits)
            || offsets.len() != tiles
            || counts.len() != tiles
        {
            return None;
        }
        let ranges = offsets
            .iter()
            .zip(counts)
            .map(|(&o, &c)| {
                let (o, c) = (o as usize, c as usize);
                (o + c <= b.len()).then_some((o, o + c))
            })
            .collect::<Option<Vec<_>>>()?;
        return Some(Tiles {
            width,
            height,
            tile_width,
            tile_height,
            bits,
            ranges,
        });
    }
    None
}

/// One Huffman table (T.81 Annex C), as a lookup table indexed by the next
/// `bits` bits of the stream, `bits` being its longest code (at most 16;
/// Sony's are 10): each entry is `code length << 8 | SSSS`, zero for no code.
/// Every code decodes with one lookup.
///
/// `fast` goes further for the common case: indexed by the next
/// [`FAST_BITS`] bits, an entry is the whole decoded difference (upper 16
/// bits) and the bits it used (code and extra bits, lowest byte), for every
/// code whose extra bits fit too; zero otherwise. That is one lookup, one
/// shift and one add per sample for SSSS up to 9 on Sony's table.
struct Huffman {
    bits: u32,
    lut: Vec<u16>,
    fast: Box<[u32; 1 << FAST_BITS]>,
}

/// Index width of [`Huffman::fast`]: 8192 four-byte entries, in L1.
const FAST_BITS: u32 = 13;

/// A Huffman table as defined in the stream: code counts per length and
/// symbols, the key under which a built table is reused across tiles.
type Definition = ([u8; 16], Vec<u8>);

/// T.81 Table H.2 / F.12 EXTEND: the difference whose SSSS extra bits are `v`.
fn extend(v: u32, ssss: u32) -> u16 {
    if ssss == 0 {
        0
    } else if v < 1 << (ssss - 1) {
        v.wrapping_sub((1u32 << ssss) - 1) as u16
    } else {
        v as u16
    }
}

impl Huffman {
    /// T.81 Annex C: code lengths from `counts`, canonical codes in order.
    fn new(counts: &[u8; 16], symbols: &[u8]) -> Option<Self> {
        let total: usize = counts.iter().map(|&c| c as usize).sum();
        if total == 0 || total != symbols.len() || symbols.iter().any(|&s| s > 16) {
            return None;
        }
        let bits = 16 - counts.iter().rev().take_while(|&&c| c == 0).count() as u32;
        let mut lut = vec![0u16; 1 << bits];
        let mut fast = Box::new([0u32; 1 << FAST_BITS]);
        let mut code = 0u32;
        let mut k = 0usize;
        for (i, &n) in counts.iter().enumerate() {
            let len = i as u32 + 1;
            for _ in 0..n {
                if code >= 1 << len {
                    return None; // over-subscribed
                }
                let shift = bits - len;
                let first = (code << shift) as usize;
                let entry = (len << 8) as u16 | u16::from(symbols[k]);
                lut[first..first + (1 << shift)].fill(entry);
                let ssss = u32::from(symbols[k]);
                if ssss < 16 && len + ssss <= FAST_BITS {
                    let used = len + ssss;
                    for v in 0..1u32 << ssss {
                        let at = (((code << ssss) | v) << (FAST_BITS - used)) as usize;
                        let e = u32::from(extend(v, ssss)) << 16 | used;
                        fast[at..at + (1 << (FAST_BITS - used))].fill(e);
                    }
                }
                code += 1;
                k += 1;
            }
            code <<= 1;
        }
        Some(Self { bits, lut, fast })
    }
}
/// One tile's coding parameters.
struct Scan<'a> {
    lines: usize,
    samples: usize,
    comps: usize,
    precision: u32,
    /// Huffman table per component, an index into `defs`.
    tables: [usize; 4],
    /// The tables used, as defined (code counts per length, symbols).
    defs: Vec<Definition>,
    /// Entropy-coded data, byte stuffing still in place.
    data: &'a [u8],
}

fn be16(b: &[u8], at: usize) -> Option<usize> {
    Some(u16::from_be_bytes(b.get(at..at + 2)?.try_into().ok()?) as usize)
}

/// Read the markers of one tile up to its scan.
fn scan(t: &[u8]) -> Result<Scan<'_>, String> {
    if t.get(0..2) != Some(&[0xFF, 0xD8]) {
        return Err("tile does not start with SOI".into());
    }
    let mut p = 2;
    let mut frame: Option<(u32, usize, usize, Vec<u8>)> = None;
    let mut defined: [Option<([u8; 16], Vec<u8>)>; 4] = Default::default();
    loop {
        if t.get(p) != Some(&0xFF) {
            return Err(format!("expected a marker at byte {p}"));
        }
        let marker = *t.get(p + 1).ok_or("truncated marker")?;
        let len = be16(t, p + 2).ok_or("truncated segment")?;
        let seg = t.get(p + 4..p + 2 + len).ok_or("truncated segment")?;
        match marker {
            0xC3 => {
                let precision = u32::from(seg[0]);
                let lines = be16(seg, 1).ok_or("SOF3")?;
                let samples = be16(seg, 3).ok_or("SOF3")?;
                let n = *seg.get(5).ok_or("SOF3")? as usize;
                let ids = (0..n)
                    .map(|i| seg.get(6 + 3 * i).copied())
                    .collect::<Option<Vec<u8>>>()
                    .ok_or("SOF3 components")?;
                frame = Some((precision, lines, samples, ids));
            }
            0xC4 => {
                let mut q = 0;
                while q < seg.len() {
                    let class_id = seg[q];
                    let counts: [u8; 16] = seg
                        .get(q + 1..q + 17)
                        .ok_or("DHT")?
                        .try_into()
                        .map_err(|_| "DHT")?;
                    let n: usize = counts.iter().map(|&c| c as usize).sum();
                    let symbols = seg.get(q + 17..q + 17 + n).ok_or("DHT")?.to_vec();
                    if class_id >> 4 != 0 || class_id & 15 > 3 {
                        return Err("DHT is not a lossless (DC) table".into());
                    }
                    defined[(class_id & 15) as usize] = Some((counts, symbols));
                    q += 17 + n;
                }
            }
            0xDA => {
                let (precision, lines, samples, ids) = frame.ok_or("SOS before SOF3")?;
                let ns = *seg.first().ok_or("SOS")? as usize;
                if ns != ids.len() || !(1..=4).contains(&ns) {
                    return Err(format!("scan of {ns} components, frame of {}", ids.len()));
                }
                let mut tables = [0usize; 4];
                let mut huffman: Vec<Definition> = Vec::new();
                let mut built: [Option<usize>; 4] = [None; 4];
                for (c, (table, id)) in tables.iter_mut().zip(&ids).enumerate() {
                    if seg.get(1 + 2 * c) != Some(id) {
                        return Err("scan components out of frame order".into());
                    }
                    let td = (seg.get(2 + 2 * c).ok_or("SOS")? >> 4) as usize;
                    if td > 3 {
                        return Err("table selector".into());
                    }
                    *table = match built[td] {
                        Some(k) => k,
                        None => {
                            let (counts, symbols) =
                                defined[td].as_ref().ok_or("undefined Huffman table")?;
                            huffman.push((*counts, symbols.clone()));
                            built[td] = Some(huffman.len() - 1);
                            huffman.len() - 1
                        }
                    };
                }
                let predictor = *seg.get(1 + 2 * ns).ok_or("SOS")?;
                let point_transform = seg.get(3 + 2 * ns).ok_or("SOS")? & 15;
                if predictor != 1 || point_transform != 0 {
                    return Err(format!(
                        "predictor {predictor}, point transform {point_transform}"
                    ));
                }
                if !(2..=16).contains(&precision) || lines == 0 || samples == 0 {
                    return Err("frame size or precision".into());
                }
                return Ok(Scan {
                    lines,
                    samples,
                    comps: ns,
                    precision,
                    tables,
                    defs: huffman,
                    data: &t[p + 2 + len..],
                });
            }
            0xDD => {
                if be16(seg, 0) != Some(0) {
                    return Err("restart intervals".into());
                }
            }
            0xC0..=0xCF => return Err(format!("frame type 0x{marker:02X}")),
            _ => {}
        }
        p += 2 + len;
    }
}

/// Copy entropy-coded data up to the next marker without its byte stuffing,
/// then `pad` zero bytes, so the decoder can read whole words anywhere.
fn unstuff(data: &[u8], out: &mut Vec<u8>, pad: usize) -> Result<(), String> {
    out.clear();
    let mut rest = data;
    loop {
        match rest.iter().position(|&b| b == 0xFF) {
            None => return Err("entropy-coded data has no end marker".into()),
            Some(i) => {
                out.extend_from_slice(&rest[..i]);
                match rest.get(i + 1) {
                    Some(0x00) => {
                        out.push(0xFF);
                        rest = &rest[i + 2..];
                    }
                    Some(0xD0..=0xD7) => return Err("restart marker".into()),
                    Some(_) => break,
                    None => return Err("truncated entropy-coded data".into()),
                }
            }
        }
    }
    out.resize(out.len() + pad, 0);
    Ok(())
}

/// One stream's MSB-first bit reader over unstuffed data: a 64-bit buffer
/// refilled without branches before every sample (a sample needs at most 31
/// bits; a refill leaves at least 56). Refilling unconditionally measured
/// faster than testing first, whose outcome the branch predictor cannot
/// learn. `Copy`, and only ever a local in the decoding loop, so it lives in
/// registers.
#[derive(Clone, Copy)]
struct Bits {
    /// Next byte not wholly in `buf`.
    ptr: usize,
    buf: u64,
    /// Valid bits at the top of `buf`.
    count: u32,
}

impl Bits {
    /// Bits consumed so far.
    fn consumed(&self) -> usize {
        self.ptr * 8 - self.count as usize
    }
}

/// One component's decoding table: the lookup table and the shift that
/// leaves its index at the bottom of the bit buffer.
#[derive(Clone, Copy)]
struct Table<'a> {
    fast: &'a [u32; 1 << FAST_BITS],
    lut: &'a [u16],
    shift: u32,
}

/// Decode one difference (T.81 H.1.2.2, Table H.2): a code for SSSS, then
/// SSSS bits. A code not in the table sets `bad` and consumes nothing.
#[inline(always)]
fn diff(data: &[u8], b: &mut Bits, t: Table<'_>, bad: &mut u32) -> u16 {
    debug_assert!(b.ptr + 8 <= data.len());
    // SAFETY: `ptr` is at most one word past the bits consumed, and the caller
    // stops a stream at the end of any line in which it passed its data; one
    // line consumes at most 32 bits per sample, which the padding behind the
    // data covers (`pad` in `decode_group`).
    let w =
        u64::from_be_bytes(unsafe { data.as_ptr().add(b.ptr).cast::<[u8; 8]>().read_unaligned() });
    b.buf |= w >> b.count;
    b.ptr += (63 - b.count as usize) >> 3;
    b.count |= 56;
    let f = t.fast[(b.buf >> (64 - FAST_BITS)) as usize];
    if f != 0 {
        let used = f & 0xFF;
        b.buf <<= used;
        b.count -= used;
        return (f >> 16) as u16;
    }
    let i = (b.buf >> t.shift) as usize;
    debug_assert!(i < t.lut.len());
    // SAFETY: `shift` is 64 minus the table's index width.
    let e = u32::from(unsafe { *t.lut.get_unchecked(i) });
    *bad |= u32::from(e == 0);
    let len = e >> 8;
    let ssss = e & 0xFF;
    if ssss == 16 {
        b.buf <<= len;
        b.count -= len;
        return 32768;
    }
    // `ssss` bits after the code; zero when `ssss` is zero.
    let v = (((b.buf << len) >> 1) >> (63 - ssss)) as u32;
    let used = len + ssss;
    b.buf <<= used;
    b.count -= used;
    let half = (1u32 << ssss) >> 1;
    (if v < half {
        v.wrapping_sub((1u32 << ssss) - 1)
    } else {
        v
    }) as u16
}

/// One four-component sample of stream `$k`: four differences added to the
/// running predictors `$p[$k]`.
macro_rules! sample {
    ($data:ident, $b:ident, $tables:ident, $p:ident, $bad:ident, $k:literal) => {
        $p[$k][0] = $p[$k][0].wrapping_add(diff($data[$k], &mut $b[$k], $tables[$k][0], &mut $bad));
        $p[$k][1] = $p[$k][1].wrapping_add(diff($data[$k], &mut $b[$k], $tables[$k][1], &mut $bad));
        $p[$k][2] = $p[$k][2].wrapping_add(diff($data[$k], &mut $b[$k], $tables[$k][2], &mut $bad));
        $p[$k][3] = $p[$k][3].wrapping_add(diff($data[$k], &mut $b[$k], $tables[$k][3], &mut $bad));
    };
}

/// Decode one coded line of each of `K` streams, in lockstep, into `lines`
/// (four values per sample), from the running readers in `bits` and the
/// first-sample predictors in `first` (H.1.2.1; updated for the next line).
/// Returns non-zero after a code not in its table. Generated per `K`, the
/// streams named, so every reader and predictor is a register.
macro_rules! line_fn {
    ($name:ident, $kc:literal, [$($k:literal),+]) => {
        #[inline(never)]
        fn $name(
            data: [&[u8]; $kc],
            tables: [[Table<'_>; 4]; $kc],
            bits: &mut [Bits; $kc],
            first: &mut [[u16; 4]; $kc],
            lines: &mut [Vec<u16>; $kc],
            samples: usize,
        ) -> u32 {
            let mut bad = 0u32;
            let mut b = *bits;
            let mut p = *first;
            $( sample!(data, b, tables, p, bad, $k); )+
            *first = p;
            $(
                debug_assert!(lines[$k].len() >= 4 * samples);
                // SAFETY: each line buffer holds `4 * samples` values.
                unsafe { lines[$k].as_mut_ptr().cast::<[u16; 4]>().write_unaligned(p[$k]) };
            )+
            for x in 1..samples {
                $( sample!(data, b, tables, p, bad, $k); )+
                $(
                    // SAFETY: as above, `x < samples`.
                    unsafe { lines[$k].as_mut_ptr().add(4 * x).cast::<[u16; 4]>().write_unaligned(p[$k]) };
                )+
            }
            *bits = b;
            bad
        }
    };
}

line_fn!(line_1, 1, [0]);
line_fn!(line_2, 2, [0, 1]);

/// Dispatch to the generated line decoder for `K` streams.
trait Lines<const K: usize> {
    fn line(
        data: [&[u8]; K],
        tables: [[Table<'_>; 4]; K],
        bits: &mut [Bits; K],
        first: &mut [[u16; 4]; K],
        lines: &mut [Vec<u16>; K],
        samples: usize,
    ) -> u32;
}

struct Width;
impl Lines<1> for Width {
    fn line(
        d: [&[u8]; 1],
        t: [[Table<'_>; 4]; 1],
        b: &mut [Bits; 1],
        f: &mut [[u16; 4]; 1],
        l: &mut [Vec<u16>; 1],
        s: usize,
    ) -> u32 {
        line_1(d, t, b, f, l, s)
    }
}
impl Lines<2> for Width {
    fn line(
        d: [&[u8]; 2],
        t: [[Table<'_>; 4]; 2],
        b: &mut [Bits; 2],
        f: &mut [[u16; 4]; 2],
        l: &mut [Vec<u16>; 2],
        s: usize,
    ) -> u32 {
        line_2(d, t, b, f, l, s)
    }
}
/// Decode the tiles in `group` into `out` (row stride `stride`), `K` streams
/// advancing in lockstep. Every tile in the group must share one scan shape.
fn decode_group<const K: usize>(
    file: &[u8],
    tiles: &Tiles,
    group: [usize; K],
    out: &mut [u16],
    stride: usize,
    work: &mut Work<K>,
    cache: &mut Vec<(Definition, Huffman)>,
) -> Result<(), String>
where
    Width: Lines<K>,
{
    let scans: Vec<Scan<'_>> = group
        .iter()
        .map(|&i| {
            let (a, b) = tiles.ranges[i];
            scan(&file[a..b])
        })
        .collect::<Result<_, _>>()?;
    let Work {
        scratch,
        lines: lines_buf,
    } = work;
    if !tiles.width.is_multiple_of(2) || !tiles.height.is_multiple_of(2) {
        return Err("odd image size".into());
    }
    let s0 = &scans[0];
    let (lines, samples, comps) = (s0.lines, s0.samples, s0.comps);
    if scans.iter().any(|s| {
        (s.lines, s.samples, s.comps, s.precision) != (lines, samples, comps, s0.precision)
    }) {
        return Err("tiles of one group differ in shape".into());
    }
    if s0.precision != tiles.bits {
        return Err(format!(
            "JPEG precision {} differs from BitsPerSample {}",
            s0.precision, tiles.bits
        ));
    }
    // Each coded sample is a 2x2 quad of the tile: two tile rows per line.
    if comps != 4 || 2 * samples != tiles.tile_width || 2 * lines != tiles.tile_height {
        return Err(format!(
            "{lines} lines of {samples}x{comps} are not quads of a {}x{} tile",
            tiles.tile_width, tiles.tile_height
        ));
    }
    let row = samples * 4;
    // A sample's code and value are at most 32 bits: a line of garbage cannot
    // read past this padding before the per-line check stops it.
    let pad = row * 4 + 16;
    for (k, s) in scans.iter().enumerate() {
        unstuff(s.data, &mut scratch[k], pad)?;
        lines_buf[k].clear();
        lines_buf[k].resize(row, 0);
    }
    let end: [usize; K] = std::array::from_fn(|k| (scratch[k].len() - pad) * 8);
    let data: [&[u8]; K] = std::array::from_fn(|k| &scratch[k][..]);
    // Build each table once per decode: tiles repeat their definitions.
    let mut which = [[0usize; 4]; K];
    for (k, s) in scans.iter().enumerate() {
        for (w, &table) in which[k].iter_mut().zip(&s.tables) {
            let def = &s.defs[table];
            *w = match cache.iter().position(|(d, _)| d == def) {
                Some(i) => i,
                None => {
                    let h = Huffman::new(&def.0, &def.1).ok_or("bad Huffman table")?;
                    cache.push((def.clone(), h));
                    cache.len() - 1
                }
            };
        }
    }
    let cache = &*cache;
    let tables: [[Table<'_>; 4]; K] = std::array::from_fn(|k| {
        std::array::from_fn(|c| {
            let h = &cache[which[k][c]].1;
            Table {
                fast: &h.fast,
                lut: &h.lut,
                shift: 64 - h.bits,
            }
        })
    });
    let mut bits = [Bits {
        ptr: 0,
        buf: 0,
        count: 0,
    }; K];
    let tiles_across = tiles.width.div_ceil(tiles.tile_width);
    // The predictor of each line's first sample: the initial value on the
    // first line, the sample above after it (H.1.2.1).
    let mut first = [[1u16 << (s0.precision - 1); 4]; K];
    for y in 0..lines {
        let bad =
            <Width as Lines<K>>::line(data, tables, &mut bits, &mut first, lines_buf, samples) != 0;
        for k in 0..K {
            if bad {
                return Err("a code not in its Huffman table".into());
            }
            if bits[k].consumed() > end[k] {
                return Err("entropy-coded data ended early".into());
            }
            let tile = group[k];
            let (tx, ty) = (
                (tile % tiles_across) * tiles.tile_width,
                (tile / tiles_across) * tiles.tile_height,
            );
            // Width clipped to the image, in whole quads (the image size is
            // even; an odd one is refused above).
            let w = tiles.tile_width.min(tiles.width - tx);
            for r in 0..2 {
                let oy = ty + 2 * y + r;
                if oy >= tiles.height {
                    break;
                }
                let dst = &mut out[oy * stride + tx..oy * stride + tx + w];
                let (pairs, _) = dst.as_chunks_mut::<2>();
                let (quads, _) = lines_buf[k].as_chunks::<4>();
                for (d, q) in pairs.iter_mut().zip(quads) {
                    *d = [q[2 * r], q[2 * r + 1]];
                }
            }
        }
    }
    Ok(())
}

/// Per-stream buffers reused across tile groups: unstuffed entropy-coded
/// data, and one decoded line.
struct Work<const K: usize> {
    scratch: [Vec<u8>; K],
    lines: [Vec<u16>; K],
}

impl<const K: usize> Work<K> {
    fn new() -> Self {
        Self {
            scratch: std::array::from_fn(|_| Vec::new()),
            lines: std::array::from_fn(|_| Vec::new()),
        }
    }
}

/// Decode `n` tiles from `i`, `K` at a time, then the rest one at a time.
fn decode_from<const K: usize>(
    file: &[u8],
    tiles: &Tiles,
    out: &mut [u16],
    mut i: usize,
) -> Result<(), String>
where
    Width: Lines<K>,
{
    let stride = tiles.width;
    let n = tiles.ranges.len();
    let mut work = Work::<K>::new();
    let mut cache = Vec::new();
    while i + K <= n {
        let group: [usize; K] = std::array::from_fn(|k| i + k);
        decode_group(file, tiles, group, out, stride, &mut work, &mut cache)?;
        i += K;
    }
    let mut one = Work::<1>::new();
    while i < n {
        decode_group::<1>(file, tiles, [i], out, stride, &mut one, &mut cache)?;
        i += 1;
    }
    Ok(())
}

/// Tiles decoded in one loop. Two independent streams per core measured
/// fastest on bug-7 (one 78 ms, two 49 ms, three 52 ms, four 53 ms per frame).
const INTERLEAVE: usize = 2;

/// Decode every tile into `out`, `width x height` samples at row stride
/// `width`.
pub(crate) fn decode(file: &[u8], tiles: &Tiles, out: &mut [u16]) -> Result<(), String> {
    if out.len() != tiles.width * tiles.height {
        return Err("output size".into());
    }
    decode_from::<INTERLEAVE>(file, tiles, out, 0)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A lossless JPEG encoder written from T.81 (predictor 1, one table),
    /// for testing the decoder on inputs the corpus does not contain.
    struct Bits {
        out: Vec<u8>,
        acc: u64,
        n: u32,
    }

    impl Bits {
        fn put(&mut self, value: u32, len: u32) {
            if len == 0 {
                return;
            }
            self.acc = (self.acc << len) | u64::from(value & ((1u32 << len) - 1));
            self.n += len;
            while self.n >= 8 {
                let b = (self.acc >> (self.n - 8)) as u8;
                self.out.push(b);
                if b == 0xFF {
                    self.out.push(0x00);
                }
                self.n -= 8;
            }
        }
        fn flush(&mut self) {
            if self.n > 0 {
                let pad = 8 - self.n;
                self.put((1 << pad) - 1, pad);
            }
        }
    }

    /// Huffman table with a code for every SSSS 0..=16: lengths chosen so
    /// some are long (up to 16 bits) and the table is complete enough.
    fn table() -> ([u8; 16], Vec<u8>) {
        // 17 symbols: lengths 2,3,3,4,4,5,5,6,6,7,8,9,10,11,12,13,16.
        let mut counts = [0u8; 16];
        let symbols: Vec<u8> = vec![0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
        let lengths = [2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 8, 9, 10, 11, 12, 13, 16];
        for l in lengths {
            counts[l - 1] += 1;
        }
        (counts, symbols)
    }

    fn codes(counts: &[u8; 16], symbols: &[u8]) -> Vec<(u32, u32)> {
        let mut by_symbol = vec![(0, 0); 17];
        let mut code = 0u32;
        let mut k = 0;
        for (i, &n) in counts.iter().enumerate() {
            for _ in 0..n {
                by_symbol[symbols[k] as usize] = (code, i as u32 + 1);
                code += 1;
                k += 1;
            }
            code <<= 1;
        }
        by_symbol
    }

    /// Encode `coded` (`lines` lines of `samples` samples of `comps`
    /// components, in coding order).
    fn encode(coded: &[u16], samples: usize, comps: usize, lines: usize, precision: u8) -> Vec<u8> {
        let tile = coded;
        let (counts, symbols) = table();
        let code = codes(&counts, &symbols);
        let mut b = Bits {
            out: Vec::new(),
            acc: 0,
            n: 0,
        };
        let row = samples * comps;
        for y in 0..lines {
            for x in 0..row {
                let pred = if x < comps {
                    if y == 0 {
                        1u16 << (precision - 1)
                    } else {
                        tile[(y - 1) * row + x]
                    }
                } else {
                    tile[y * row + x - comps]
                };
                let d = tile[y * row + x].wrapping_sub(pred) as i16 as i32;
                let (ssss, extra) = if d == -32768 {
                    (16u32, 0u32)
                } else {
                    let m = d.unsigned_abs();
                    let s = 32 - m.leading_zeros();
                    (s, if d < 0 { (d - 1) as u32 } else { d as u32 })
                };
                let (c, l) = code[ssss as usize];
                b.put(c, l);
                if ssss != 16 {
                    b.put(extra, ssss);
                }
            }
        }
        b.flush();
        let mut j = vec![0xFF, 0xD8];
        let mut sof = vec![0xFF, 0xC3, 0, (8 + 3 * comps) as u8, precision];
        sof.extend_from_slice(&(lines as u16).to_be_bytes());
        sof.extend_from_slice(&(samples as u16).to_be_bytes());
        sof.push(comps as u8);
        for c in 0..comps {
            sof.extend_from_slice(&[c as u8 + 1, 0x11, 0]);
        }
        j.extend(sof);
        let n: usize = symbols.len();
        j.extend_from_slice(&[0xFF, 0xC4]);
        j.extend_from_slice(&((19 + n) as u16).to_be_bytes());
        j.push(0x00);
        j.extend_from_slice(&counts);
        j.extend_from_slice(&symbols);
        j.extend_from_slice(&[0xFF, 0xDA]);
        j.extend_from_slice(&((6 + 2 * comps) as u16).to_be_bytes());
        j.push(comps as u8);
        for c in 0..comps {
            j.extend_from_slice(&[c as u8 + 1, 0x00]);
        }
        j.extend_from_slice(&[1, 0, 0]);
        j.extend(b.out);
        j.extend_from_slice(&[0xFF, 0xD9]);
        j
    }

    /// A TIFF holding `tiles_across x tiles_down` encoded tiles of an image.
    fn tiff(image: &[u16], w: usize, h: usize, tw: usize, th: usize) -> (Vec<u8>, usize) {
        let (ta, td) = (w.div_ceil(tw), h.div_ceil(th));
        let mut streams = Vec::new();
        for ty in 0..td {
            for tx in 0..ta {
                let mut tile = vec![0u16; tw * th];
                for y in 0..th {
                    for x in 0..tw {
                        let (ix, iy) = (tx * tw + x, ty * th + y);
                        if ix < w && iy < h {
                            tile[y * tw + x] = image[iy * w + ix];
                        }
                    }
                }
                // Each coded sample is a 2x2 quad, as Sony's are.
                let coded: Vec<u16> = (0..th / 2)
                    .flat_map(|y| (0..tw / 2).map(move |x| (y, x)))
                    .flat_map(|(y, x)| {
                        let t = &tile;
                        (0..4).map(move |c| t[(2 * y + c / 2) * tw + 2 * x + c % 2])
                    })
                    .collect();
                streams.push(encode(&coded, tw / 2, 4, th / 2, 14));
            }
        }
        let entries: Vec<(u16, u16, Vec<u32>)> = vec![
            (TAG_SUBFILE, 4, vec![0]),
            (TAG_WIDTH, 3, vec![w as u32]),
            (TAG_HEIGHT, 3, vec![h as u32]),
            (TAG_BITS, 3, vec![14]),
            (TAG_COMPRESSION, 3, vec![7]),
            (TAG_PHOTOMETRIC, 3, vec![PHOTOMETRIC_CFA]),
            (TAG_SAMPLES, 3, vec![1]),
            (TAG_TILE_WIDTH, 3, vec![tw as u32]),
            (TAG_TILE_LENGTH, 3, vec![th as u32]),
            (TAG_TILE_OFFSETS, 4, vec![0; streams.len()]),
            (
                TAG_TILE_COUNTS,
                4,
                streams.iter().map(|s| s.len() as u32).collect(),
            ),
        ];
        let ifd = 8usize;
        let ifd_len = 2 + 12 * entries.len() + 4;
        let mut extra_at = ifd + ifd_len;
        let mut extra = Vec::new();
        let mut body = Vec::new();
        let data_at = extra_at + 8 * streams.len() + 64;
        let mut offsets = Vec::new();
        let mut at = data_at;
        for s in &streams {
            offsets.push(at as u32);
            at += s.len();
        }
        body.extend_from_slice(&(entries.len() as u16).to_le_bytes());
        for (tag, typ, vals) in &entries {
            let vals = if *tag == TAG_TILE_OFFSETS {
                &offsets
            } else {
                vals
            };
            body.extend_from_slice(&tag.to_le_bytes());
            body.extend_from_slice(&typ.to_le_bytes());
            body.extend_from_slice(&(vals.len() as u32).to_le_bytes());
            let size = if *typ == 3 { 2 } else { 4 };
            if size * vals.len() <= 4 {
                let mut v = [0u8; 4];
                for (i, x) in vals.iter().enumerate() {
                    if size == 2 {
                        v[2 * i..2 * i + 2].copy_from_slice(&(*x as u16).to_le_bytes());
                    } else {
                        v.copy_from_slice(&x.to_le_bytes());
                    }
                }
                body.extend_from_slice(&v);
            } else {
                body.extend_from_slice(&(extra_at as u32).to_le_bytes());
                for x in vals.iter() {
                    extra.extend_from_slice(&x.to_le_bytes());
                }
                extra_at += 4 * vals.len();
            }
        }
        body.extend_from_slice(&0u32.to_le_bytes());
        let mut file = b"II*\0".to_vec();
        file.extend_from_slice(&(ifd as u32).to_le_bytes());
        file.extend(body);
        file.extend(extra);
        file.resize(data_at, 0);
        for s in streams {
            file.extend(s);
        }
        (file, ta * td)
    }

    fn noise(w: usize, h: usize, seed: u64, spread: u32) -> Vec<u16> {
        let mut s = seed;
        (0..w * h)
            .map(|i| {
                s = s
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                let r = (s >> 33) as u32;
                let base = 512 + ((i % w) as u32 * 7) % 3000;
                ((base + r % spread) & 0x3FFF) as u16
            })
            .collect()
    }

    #[test]
    fn decodes_what_the_specification_encoder_wrote() {
        // Partial edge tiles, every SSSS from 0 to 16 (full-range noise
        // produces 14- and 15-bit differences; a jump of 32768 is SSSS 16 at
        // 16-bit precision, impossible at 14), stuffing in the stream.
        // Partial edge tiles, codes up to 16 bits, small and full-range
        // differences, byte stuffing, and both the single-tile and the
        // interleaved loops (tile counts not a multiple of four).
        for (w, h, spread) in [
            (100, 60, 1),
            (100, 60, 9),
            (130, 70, 300),
            (64, 32, 16384),
            (200, 34, 50),
        ] {
            let image = noise(w, h, w as u64 * 31 + spread as u64, spread);
            let (file, n) = tiff(&image, w, h, 32, 16);
            let tiles = find_tiles(&file).expect("tiles");
            assert_eq!(tiles.ranges.len(), n);
            // A reused buffer (`decode_into`) holds the previous frame: every
            // sample must be overwritten.
            let mut out = vec![0xABCDu16; tiles.width * tiles.height];
            decode(&file, &tiles, &mut out).expect("decode");
            assert_eq!(out, image, "{w}x{h} spread {spread}");
        }
    }

    #[test]
    fn a_damaged_stream_is_an_error_not_a_picture() {
        let image = noise(64, 32, 5, 300);
        let (mut file, _) = tiff(&image, 64, 32, 32, 16);
        let tiles = find_tiles(&file).unwrap();
        // Cut the first tile's entropy data short: overwrite its middle with
        // an end-of-image marker.
        let (a, b) = tiles.ranges[0];
        let mid = (a + b) / 2;
        file[mid] = 0xFF;
        file[mid + 1] = 0xD9;
        let mut out = vec![0u16; 64 * 32];
        assert!(decode(&file, &tiles, &mut out).is_err());
    }

    #[test]
    fn unsupported_scans_are_refused() {
        let image = noise(32, 16, 9, 30);
        let (file, _) = tiff(&image, 32, 16, 32, 16);
        let tiles = find_tiles(&file).unwrap();
        let (a, b) = tiles.ranges[0];
        let tile = &file[a..b];
        let sos = tile.windows(2).position(|w| w == [0xFF, 0xDA]).unwrap();
        // Predictor 2 instead of 1.
        let mut changed = tile.to_vec();
        let ns = changed[sos + 4] as usize;
        changed[sos + 5 + 2 * ns] = 2;
        assert!(scan(&changed).is_err());
        // A non-lossless frame type.
        let mut changed = tile.to_vec();
        let sof = changed.windows(2).position(|w| w == [0xFF, 0xC3]).unwrap();
        changed[sof + 1] = 0xC0;
        assert!(scan(&changed).is_err());
    }
}
