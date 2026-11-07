// Original read-only audit client of Strehl's independently linked RAW decoder.
// SPDX-License-Identifier: MIT OR Apache-2.0
use std::io::Write;
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        return Err("usage: raw-check INPUT.ARW OUTPUT.u16".into());
    }
    let frame = strehl_raw::decode(Path::new(&args[1]))?;
    let mut output = std::io::BufWriter::new(std::fs::File::create(&args[2])?);
    for y in 0..frame.active.height {
        let row: Vec<u8> = frame.active_row(y).iter().flat_map(|v| v.to_le_bytes()).collect();
        output.write_all(&row)?;
    }
    output.flush()?;
    println!("{{\"width\":{},\"height\":{},\"x\":{},\"y\":{},\"stride\":{}}}",
        frame.active.width, frame.active.height, frame.active.x, frame.active.y, frame.stride);
    Ok(())
}
