//! One request over the existing local agent mailbox, without starting a GUI.

use super::{AgentCommand, AgentReply, AgentRequest, MAX_REQUEST_BYTES, bridge::BridgeClient};
use std::{
    ffi::{OsStr, OsString},
    fs::File,
    io::{self, Read, Write},
    path::PathBuf,
};

const HELP: &str = r#"Usage: Strehl --control --session <session.json> [--request <request.json|->]
       Strehl --control --help

Send exactly one request to a running Strehl workspace's connected agent session.
Copy the session.json path from the workspace's agent connection control.
Without --request, send {"command":{"operation":"snapshot"}}.
Use --request - to read one JSON AgentRequest from standard input until EOF.
Request input is bounded to 2112 KiB; trailing JSON and unknown fields are rejected.

Example request:
  {"expected_revision":19,"command":{"operation":"undo"}}

Mutations require expected_revision from a fresh snapshot. A stale revision is
returned as an error; this client never supplies a revision or retries a command.
The existing bridge enforces its session, deadline, and serialized envelope limits.

Stdout: one complete JSON AgentReply, including any image or operation error.
Stderr: usage, input I/O, or transport errors. --help prints this text to stdout.
Exit status: 0 success; 1 operation, I/O, or transport error; 2 invalid arguments
or invalid JSON input. This client does not start or connect a GUI session for you.
"#;

struct Options {
    session: PathBuf,
    request: Option<OsString>,
}

enum Action {
    Help,
    Request(Options),
}

/// Return `None` for other executable modes so main can continue its dispatch.
pub(crate) fn run_control_from_args() -> Option<i32> {
    run_control(
        std::env::args_os().skip(1),
        io::stdin().lock(),
        io::stdout().lock(),
        io::stderr().lock(),
    )
}

fn run_control(
    args: impl IntoIterator<Item = OsString>,
    input: impl Read,
    mut output: impl Write,
    mut errors: impl Write,
) -> Option<i32> {
    let mut args = args.into_iter();
    if args.next().as_deref() != Some(OsStr::new("--control")) {
        return None;
    }
    let options = match parse_options(args) {
        Ok(Action::Help) => {
            return Some(
                match output
                    .write_all(HELP.as_bytes())
                    .and_then(|()| output.flush())
                {
                    Ok(()) => 0,
                    Err(error) => {
                        report_error(&mut errors, 1, format!("Cannot write help: {error}"))
                    }
                },
            );
        }
        Ok(Action::Request(options)) => options,
        Err(error) => return Some(report_error(&mut errors, 2, error)),
    };
    let request = match read_request(options.request, input) {
        Ok(request) => request,
        Err((code, error)) => return Some(report_error(&mut errors, code, error)),
    };
    // Invalid operations are replies, just as they are when dispatched by the app.
    // In particular, never fill in a missing mutation revision from a snapshot.
    if let Err(error) = request.validate() {
        return Some(write_reply(
            AgentReply::error(error),
            &mut output,
            &mut errors,
        ));
    }
    let client = match BridgeClient::connect(&options.session) {
        Ok(client) => client,
        Err(error) => {
            return Some(report_error(
                &mut errors,
                1,
                format!("Cannot connect to Strehl: {error:#}"),
            ));
        }
    };
    Some(match client.call(request) {
        Ok(reply) => write_reply(reply, &mut output, &mut errors),
        Err(error) => report_error(&mut errors, 1, format!("Strehl control failed: {error:#}")),
    })
}

fn parse_options(mut args: impl Iterator<Item = OsString>) -> Result<Action, String> {
    let mut session = None;
    let mut request = None;
    while let Some(argument) = args.next() {
        if argument == "--help" && session.is_none() && request.is_none() && args.next().is_none() {
            return Ok(Action::Help);
        }
        match argument.to_str() {
            Some("--session") if session.is_none() => {
                session = Some(PathBuf::from(next_value(&mut args, "--session")?));
            }
            Some("--request") if request.is_none() => {
                request = Some(next_value(&mut args, "--request")?);
            }
            _ => {
                return Err(format!(
                    "Unexpected or repeated argument: {}. Use --control --help.",
                    argument.to_string_lossy()
                ));
            }
        }
    }
    Ok(Action::Request(Options {
        session: session.ok_or("Missing --session <session.json>. Use --control --help.")?,
        request,
    }))
}

fn next_value(args: &mut impl Iterator<Item = OsString>, flag: &str) -> Result<OsString, String> {
    args.next()
        .filter(|value| !value.is_empty() && !value.to_string_lossy().starts_with("--"))
        .ok_or_else(|| format!("Missing value for {flag}. Use --control --help."))
}

fn read_request(path: Option<OsString>, input: impl Read) -> Result<AgentRequest, (i32, String)> {
    let Some(path) = path else {
        return Ok(AgentRequest {
            expected_revision: None,
            command: AgentCommand::Snapshot {},
        });
    };
    let bytes = if path == "-" {
        read_bounded(input)?
    } else {
        let file =
            File::open(&path).map_err(|error| (1, format!("Cannot open request file: {error}")))?;
        let metadata = file
            .metadata()
            .map_err(|error| (1, format!("Cannot inspect request file: {error}")))?;
        if !metadata.is_file() {
            return Err((2, "The request must be a regular file or '-'.".into()));
        }
        read_bounded(file)?
    };
    serde_json::from_slice(&bytes).map_err(|error| {
        (
            2,
            format!("Expected exactly one JSON AgentRequest: {error}"),
        )
    })
}

fn read_bounded(input: impl Read) -> Result<Vec<u8>, (i32, String)> {
    let mut bytes = Vec::new();
    input
        .take(MAX_REQUEST_BYTES as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|error| (1, format!("Cannot read request: {error}")))?;
    if bytes.len() > MAX_REQUEST_BYTES {
        return Err((2, "Request exceeds the fixed 2112 KiB input limit.".into()));
    }
    Ok(bytes)
}

fn write_reply(reply: AgentReply, output: &mut impl Write, errors: &mut impl Write) -> i32 {
    let status = i32::from(reply.error.is_some());
    if let Err(error) = serde_json::to_writer(&mut *output, &reply) {
        return report_error(errors, 1, format!("Cannot write Strehl reply: {error}"));
    }
    if let Err(error) = output.write_all(b"\n").and_then(|()| output.flush()) {
        return report_error(errors, 1, format!("Cannot finish Strehl reply: {error}"));
    }
    status
}

fn report_error(errors: &mut impl Write, status: i32, message: String) -> i32 {
    let _ = writeln!(errors, "{message}");
    status
}

#[cfg(test)]
#[path = "agent-control-tests.rs"]
mod tests;
