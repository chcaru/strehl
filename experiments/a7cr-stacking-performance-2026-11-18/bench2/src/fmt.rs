//! What a second archive format could cost in bits per sample, measured on
//! real frames: the residual's entropy under format 1's predictor and under a
//! predictor that reads only the same-colour row above, with and without a
//! context, and the size of codes built for fast decoding.
use std::path::Path;

fn zig(d: i32) -> u32 {
    let d = d as i16;
    (((d as u16) << 1) ^ ((d >> 15) as u16)) as u32
}

fn entropy(counts: &[u32]) -> f64 {
    let n: f64 = counts.iter().map(|&c| c as f64).sum();
    if n == 0.0 {
        return 0.0;
    }
    counts.iter().filter(|&&c| c > 0).map(|&c| -(c as f64) * (c as f64 / n).log2()).sum::<f64>()
}

const CONTEXTS: usize = 16 * 12;
const SYMBOLS: usize = 4096;

#[derive(Clone)]
struct Model {
    order0: Vec<u32>,
    by_context: Vec<u32>,
    /// High part `z >> k` counts per k (the split code's entropy-coded half).
    high: Vec<u32>,
    rice: f64,
    split_raw: f64,
    pack: f64,
    patched: f64,
    blocks: u64,
    n: u64,
    block: Vec<u32>,
}

impl Model {
    fn new() -> Self {
        Self {
            order0: vec![0; 65536],
            by_context: vec![0; CONTEXTS * SYMBOLS],
            high: vec![0; 16 * 1024],
            rice: 0.0,
            split_raw: 0.0,
            pack: 0.0,
            patched: 0.0,
            blocks: 0,
            n: 0,
            block: Vec::with_capacity(32),
        }
    }

    fn add(&mut self, z: u32, context: usize) {
        self.order0[z as usize] += 1;
        self.by_context[context * SYMBOLS + (z as usize).min(SYMBOLS - 1)] += 1;
        self.n += 1;
        self.block.push(z);
        if self.block.len() == 32 {
            self.flush();
        }
    }

    /// One block of 32 same-colour residuals from one row.
    fn flush(&mut self) {
        let b = std::mem::take(&mut self.block);
        if b.is_empty() {
            return;
        }
        self.blocks += 1;
        // Rice with the block's best k.
        self.rice += (0..15)
            .map(|k| b.iter().map(|&z| ((z >> k) + 1 + k) as f64).sum::<f64>())
            .fold(f64::INFINITY, f64::min);
        // Split code: k from the block's mean, low k bits raw, high part entropy-coded per k.
        let mean = b.iter().sum::<u32>() / b.len() as u32;
        let k = (32 - (mean + 1).leading_zeros()).saturating_sub(2).min(15) as usize;
        self.split_raw += (k * b.len()) as f64;
        for &z in &b {
            self.high[k * 1024 + ((z >> k) as usize).min(1023)] += 1;
        }
        // Fixed width per block.
        let max = b.iter().copied().max().unwrap_or(0);
        let width = |v: u32| (32 - v.leading_zeros()) as f64;
        self.pack += width(max) * b.len() as f64;
        // Fixed width with up to three stored exceptions (21 bits each).
        let mut sorted = b.clone();
        sorted.sort_unstable();
        self.patched += (0..=3usize.min(sorted.len() - 1))
            .map(|e| width(sorted[sorted.len() - 1 - e]) * b.len() as f64 + 21.0 * e as f64 + 2.0)
            .fold(f64::INFINITY, f64::min);
        self.block = b;
        self.block.clear();
    }

    fn report(&self, label: &str) {
        let n = self.n as f64;
        let header = 4.0 * self.blocks as f64;
        let ctx: f64 = self.by_context.chunks(SYMBOLS).map(entropy).sum();
        let high: f64 = self.high.chunks(1024).map(entropy).sum();
        println!(
            "  {label}: order-0 entropy {:.3} | entropy given context {:.3} | split code (raw low bits + coded high part) {:.3} | Rice per block {:.3} | fixed width per block {:.3} | with 3 exceptions {:.3}",
            entropy(&self.order0) / n,
            ctx / n,
            (self.split_raw + high + header) / n,
            (self.rice + header) / n,
            (self.pack + header) / n,
            (self.patched + header) / n,
        );
    }
}

fn context(pred: u32, spread: u32) -> usize {
    let level = (32 - pred.max(1).leading_zeros()).min(15) as usize;
    let activity = (32 - (spread + 1).leading_zeros()).min(11) as usize;
    level * 12 + activity
}

pub fn run(dir: &Path, decode: impl Fn(&Path) -> (Vec<u16>, usize, u64)) {
    let paths = super::files(dir);
    let (mut four, mut above) = (Model::new(), Model::new());
    let (mut bytes, mut samples) = (0u64, 0u64);
    for p in [&paths[41], &paths[300], &paths[700]] {
        let (s, width, size) = decode(p);
        let height = s.len() / width;
        bytes += size;
        samples += s.len() as u64;
        for y in 2..height {
            let (up, cur) = (&s[(y - 2) * width..(y - 1) * width], &s[y * width..(y + 1) * width]);
            for parity in 0..2 {
                let mut x = 2 + parity;
                while x + 2 < width {
                    let (a, b, c) = (u32::from(up[x - 2]), u32::from(up[x]), u32::from(up[x + 2]));
                    let v = i32::from(cur[x]);
                    let spread = a.abs_diff(c).max(a.abs_diff(b));
                    let p4 = (u32::from(cur[x - 2]) + a + b + c) / 4;
                    four.add(zig(v - p4 as i32), context(p4, spread));
                    let p3 = (a + 2 * b + c + 2) >> 2;
                    above.add(zig(v - p3 as i32), context(p3, spread));
                    x += 2;
                }
                four.flush();
                above.flush();
            }
        }
    }
    println!(
        "three files, {:.1} M samples; bits per sample. Format 1 as stored: {:.3} (files of {:.1} MB)",
        samples as f64 / 1e6,
        bytes as f64 * 8.0 / samples as f64,
        bytes as f64 / 3e6
    );
    four.report("format 1's predictor (left, up, up-left, up-right)");
    above.report("row-above predictor ((a + 2b + c + 2) >> 2)  ");
}
