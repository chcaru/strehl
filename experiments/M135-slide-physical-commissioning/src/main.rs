//! Independent active-area dump for the M135 rawpy/LibRaw crosscheck.
//!
//! This executable uses the project-owned `strehl-raw` API, which links
//! rawler.  It does not inspect rawler source.  Output is:
//!
//! `u32 y0, u32 x0, u32 height, u32 width`, then little-endian active-area
//! `u16` samples in row-major order.

use std::io::{BufWriter, Write};
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments: Vec<String> = std::env::args().collect();
    if arguments.len() != 6 {
        eprintln!(
            "usage: m135-slide-raw-crosscheck \
             <frame.ARW> <y0> <x0> <height> <width>"
        );
        std::process::exit(2);
    }
    let y0: usize = arguments[2].parse()?;
    let x0: usize = arguments[3].parse()?;
    let height: usize = arguments[4].parse()?;
    let width: usize = arguments[5].parse()?;

    let frame = strehl_raw::decode(Path::new(&arguments[1]))?;
    if height == 0
        || width == 0
        || y0 + height > frame.active.height
        || x0 + width > frame.active.width
    {
        return Err(format!(
            "requested active rectangle ({x0},{y0}) {width}x{height} exceeds {}x{}",
            frame.active.width, frame.active.height
        )
        .into());
    }

    eprintln!("file      : {}", arguments[1]);
    eprintln!("camera    : {}", frame.camera);
    eprintln!("stride    : {}", frame.stride);
    eprintln!("buffer h  : {}", frame.buffer_height);
    eprintln!(
        "active    : {}x{} at ({},{})",
        frame.active.width, frame.active.height, frame.active.x, frame.active.y
    );
    eprintln!(
        "levels    : black {} white {}",
        frame.levels.black, frame.levels.white
    );

    height
        .checked_mul(width)
        .and_then(|value| value.checked_mul(2))
        .and_then(|value| value.checked_add(16))
        .ok_or("output byte count overflow")?;
    let stdout = std::io::stdout();
    let mut output = BufWriter::new(stdout.lock());
    for value in [y0 as u32, x0 as u32, height as u32, width as u32] {
        output.write_all(&value.to_le_bytes())?;
    }
    for y in y0..y0 + height {
        let row = frame.active_row(y);
        for sample in &row[x0..x0 + width] {
            output.write_all(&sample.to_le_bytes())?;
        }
    }
    output.flush()?;
    Ok(())
}
