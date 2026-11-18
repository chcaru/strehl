//! The device self-test the CLI's `auto` route relies on passes on this
//! device, and a recorded verdict is reused. Needs a Vulkan GPU with f64:
//! `cargo test -p strehl-gpu -- --ignored`.

#[test]
#[ignore = "needs a Vulkan GPU with f64"]
fn the_self_test_passes_and_is_recorded() {
    let dir = std::env::temp_dir().join(format!("strehl-gpu-selftest-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    strehl_gpu::self_test(Some(&dir)).expect("the device folds as the CPU does");
    let recorded: Vec<_> = std::fs::read_dir(&dir)
        .expect("verdict directory")
        .flatten()
        .filter(|e| e.file_name().to_string_lossy().starts_with("selftest-"))
        .collect();
    assert_eq!(recorded.len(), 1, "one verdict for this adapter and shader");
    strehl_gpu::self_test(Some(&dir)).expect("the recorded verdict");
    let _ = std::fs::remove_dir_all(&dir);
}
