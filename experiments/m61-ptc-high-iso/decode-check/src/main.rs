//! M61 rule-32 cross-check: decode two frames with `strehl-raw` (rawler) and
//! dump raw active-area pixels so Python can compare them against `rawpy`
//! (LibRaw), which every M61 measurement script used.
//!
//! Two independent implementations of Sony's lossless compression. If the
//! patches match bit for bit, the whole milestone's decode is confirmed; if
//! they do not, every number in M61 is suspect.
//!
//! Writes `<out>/rawler-<tag>.bin`: u32 y0, u32 x0, u32 h, u32 w, then h*w
//! little-endian u16 taken from the ACTIVE area at (x0 + x, y0 + y).
//!
//! Usage: m61-decode-check <frame.ARW> <out-dir> <tag> [y0 x0 h w]

use std::io::Write;
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 4 {
        eprintln!("usage: m61-decode-check <frame.ARW> <out-dir> <tag> [y0 x0 h w]");
        std::process::exit(2);
    }
    let (y0, x0, h, w) = if a.len() >= 8 {
        (a[4].parse()?, a[5].parse()?, a[6].parse()?, a[7].parse()?)
    } else {
        (1000usize, 1000usize, 512usize, 512usize)
    };

    let f = strehl_raw::decode(Path::new(&a[1]))?;
    println!("file      : {}", a[1]);
    println!("camera    : {}", f.camera);
    println!("stride    : {}", f.stride);
    println!("buffer h  : {}", f.buffer_height);
    println!(
        "active    : {}x{} at ({},{})",
        f.active.width, f.active.height, f.active.x, f.active.y
    );
    println!("levels    : black {} white {}", f.levels.black, f.levels.white);

    let mut plane_sum = [0f64; 4];
    let mut plane_n = [0u64; 4];
    for y in 0..f.active.height {
        let row = f.active_row(y);
        for (x, &v) in row.iter().enumerate().take(f.active.width) {
            let idx = (y % 2) * 2 + (x % 2);
            plane_sum[idx] += v as f64;
            plane_n[idx] += 1;
        }
    }
    for (i, name) in ["R(even,even)", "G1(even,odd)", "G2(odd,even)", "B(odd,odd)"]
        .iter()
        .enumerate()
    {
        println!(
            "plane {name:<14}: n {} mean {:.4}",
            plane_n[i],
            plane_sum[i] / plane_n[i] as f64
        );
    }

    let mut buf: Vec<u8> = Vec::with_capacity(16 + h * w * 2);
    for v in [y0 as u32, x0 as u32, h as u32, w as u32] {
        buf.extend_from_slice(&v.to_le_bytes());
    }
    for y in y0..y0 + h {
        let row = f.active_row(y);
        for x in x0..x0 + w {
            buf.extend_from_slice(&row[x].to_le_bytes());
        }
    }
    let out = Path::new(&a[2]).join(format!("rawler-{}.bin", a[3]));
    std::fs::create_dir_all(&a[2])?;
    let mut fh = std::fs::File::create(&out)?;
    fh.write_all(&buf)?;
    println!("wrote     : {}", out.display());
    Ok(())
}
