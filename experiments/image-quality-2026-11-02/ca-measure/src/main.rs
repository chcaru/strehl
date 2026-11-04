//! Run `strehl_core::ca_refine::measure` on a linear master TIFF, to compare
//! with `ca-residual.py` on the same file.
//! usage: iq-ca-measure MASTER.tif
fn main() {
    let path = std::env::args().nth(1).expect("MASTER.tif");
    let image = strehl_edit::load_tiff(std::path::Path::new(&path)).expect("load");
    let (w, h) = (image.width as usize, image.height as usize);
    let t = std::time::Instant::now();
    let r = strehl_core::ca_refine::measure(w, h, &image.pixels);
    let secs = t.elapsed().as_secs_f64();
    match r {
        None => println!("no fit ({secs:.2} s)"),
        Some(r) => {
            for (name, f) in [("R", r.red), ("B", r.blue)] {
                println!(
                    "{name}: t = ({:+.3},{:+.3}) px, scale {:+.1} ppm, rms {:.3}, tiles {}/{}",
                    f.translation.0, f.translation.1, f.scale * 1e6, f.rms, f.kept, f.measured
                );
            }
            println!("({secs:.2} s)");
        }
    }
}
