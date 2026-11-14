fn main() {
    if let Err(error) = strehl_capture::ptp::serve() {
        println!(
            "{}",
            serde_json::json!({"ok":false,"error":format!("{error:#}")})
        );
        std::process::exit(1);
    }
}
