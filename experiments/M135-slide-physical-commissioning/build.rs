fn main() {
    if std::env::var_os("CARGO_CFG_TARGET_ENV").as_deref() == Some(std::ffi::OsStr::new("msvc")) {
        println!("cargo:rustc-link-arg=/Brepro");
    }
}
