//! Print the capture identity of every RAW file named on the command line.
//!
//! The verification harness for `strehl_raw::identity`: it is what was run
//! against `exiftool` — a second, independent reader — over the owner's corpus
//! in M119. Output is one tab-separated line per file so that a diff against
//! `exiftool -T` is a diff and not a parse.
//!
//! ```text
//! cargo run --release -p strehl-raw --example identity -- D:\path\to\*.ARW
//! ```

use std::path::PathBuf;

fn main() {
    let paths: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    if paths.is_empty() {
        eprintln!("usage: identity <raw file>...");
        std::process::exit(2);
    }
    println!("file\tmake\tmodel\tlens_model\tlens_type3\tlens_info\tfocal_mm\tf_number\tmax_ap");
    for p in &paths {
        let id = strehl_raw::identity(p);
        let s = |v: &Option<String>| v.clone().unwrap_or_else(|| "-".into());
        let f = |v: Option<f32>| v.map(|x| format!("{x}")).unwrap_or_else(|| "-".into());
        let info = id
            .lens_info
            .map(|v| format!("{} {} {} {}", v[0], v[1], v[2], v[3]))
            .unwrap_or_else(|| "-".into());
        println!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            p.display(),
            s(&id.make),
            s(&id.model),
            s(&id.lens_model),
            id.lens_type3
                .map(|v| v.to_string())
                .unwrap_or_else(|| "-".into()),
            info,
            f(id.focal_len_mm),
            f(id.f_number),
            f(id.max_aperture_f),
        );
    }
}
