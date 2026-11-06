//! `foamy-native-demo-helper`: foamy-kit's fixture helper. It exercises the
//! shared `foamy-helper` crate on both architectures and is the reference for
//! a plugin helper's layout. Contract (one JSON line on stdout per call,
//! except `serve`, which answers one line per request line):
//!
//! - `version` → `{"ok":true,"helper":…,"arch":"x86_64"|"aarch64"}`
//! - `args <arg>…` → `{"ok":true,"args":[…]}`, the arguments verbatim
//! - `echo` → stdin (at most 64 KiB) as `{"ok":true,"bytes":n,"text":…}`;
//!   more is `INPUT_TOO_LARGE`, invalid UTF-8 `INVALID_INPUT`
//! - `serve` → JSON lines on stdin (at most 1024 bytes each):
//!   `{"id":n,"text":s}` → `{"id":n,"length":chars}`; a bad line →
//!   `{"error":"INVALID_REQUEST","message":…}`; ends at end of input
//! - `write <path> <text>` → writes `<text>\n` atomically, mode 0600
//! - `lock <hold-ms>` → takes `$XDG_RUNTIME_DIR/foamy-native-demo/action.lock`
//!   without waiting and holds it for `<hold-ms>`; `BUSY` when taken
//! - `run <timeout-ms> <max-output> <program> <arg>…` → runs `<program>`
//!   with `PATH` only, bounded; `{"ok":…,"code":…,"stdout":…,"timed_out":…,"overflowed":…}`
//! - `fail` → `DEMO_FAILURE`, exit 3; `panic` → an `INTERNAL` reply, exit 101
//! - `favicon` → `foamy_helper::favicon::run()`: browser-favicon.py's
//!   contract (a request object on stdin, `{"source": …, "status": …}`)
//! - `seccomp <program> <arg>…` → runs `<program>` under the image decoder's
//!   seccomp filter; `exec-only <program> <arg>…` → runs it with Landlock
//!   allowing only `<program>` (and its interpreter) to execute; both reply
//!   `{"ok":…,"code":…,"stderr":…}`, `UNSUPPORTED` without the kernel feature
//! - `bwrap-argv` → `{"ok":true,"argv":[…]}`, github_status's namespace
//! - non-UTF-8 arguments → `INVALID_ARGUMENT`, exit 2
//! - anything else → `INVALID_ARGUMENT`, exit 2
//!
//! Failures print `{"ok":false,"code":…,"error":…}` (exit 1 unless noted).
//! `main` installs the panic-exit hook first and reads argv (`args_os`)
//! only inside `json::run`, so nothing can panic before the hook.

use std::ffi::OsStr;
use std::io::{self, BufReader};
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::thread;
use std::time::Duration;

use foamy_helper::child::{Bounded, Output};
use foamy_helper::sandbox::{BpfFilter, Bwrap, ExecOnly};
use foamy_helper::{Failure, fs, io as bounded, json, lock, process};
use serde_json::{Value, json};

const MAX_INPUT: u64 = 64 * 1024;
const MAX_LINE: usize = 1024;

fn number(text: Option<&String>, what: &str) -> Result<u64, Failure> {
    text.and_then(|text| text.parse().ok()).ok_or_else(|| {
        Failure::coded("INVALID_ARGUMENT", format!("{what} must be a number")).with_exit_code(2)
    })
}

fn serve() -> Result<Value, Failure> {
    let stdin = io::stdin().lock();
    let stdout = io::stdout().lock();
    json::serve(
        BufReader::new(stdin),
        stdout,
        MAX_LINE,
        |request: Result<Value, Failure>| {
            Some(match request {
                Ok(request) => {
                    let length = request["text"]
                        .as_str()
                        .map_or(0, |text| text.chars().count());
                    json!({"id": request["id"], "length": length})
                }
                Err(failure) => json!({"error": failure.code, "message": failure.message}),
            })
        },
    )?;
    Ok(Value::Null)
}

fn args() -> Result<Vec<String>, Failure> {
    std::env::args_os()
        .map(|arg| {
            arg.into_string().map_err(|_| {
                Failure::coded("INVALID_ARGUMENT", "arguments must be UTF-8").with_exit_code(2)
            })
        })
        .collect()
}

/// The kernel (or qemu-user, for the aarch64 binary in tests) lacks the
/// feature: `Unsupported` from the kit, `ENOSYS` from the child's setup.
fn unsupported(error: io::Error) -> Failure {
    if error.kind() == io::ErrorKind::Unsupported || error.raw_os_error() == Some(38) {
        Failure::coded("UNSUPPORTED", error.to_string())
    } else {
        error.into()
    }
}

fn sandboxed(output: Output) -> Value {
    json!({
        "ok": output.success(),
        "code": output.status.code(),
        "stderr": String::from_utf8_lossy(&output.stderr),
    })
}

fn main_json(args: &[String]) -> Result<Value, Failure> {
    let rest = &args[1.min(args.len())..];
    match rest.first().map(String::as_str) {
        Some("version") => Ok(
            json!({"ok": true, "helper": "foamy-native-demo-helper", "arch": std::env::consts::ARCH}),
        ),
        Some("args") => Ok(json!({"ok": true, "args": &rest[1..]})),
        Some("echo") => {
            let data = bounded::read_stdin_limited(MAX_INPUT).map_err(|error| {
                let code = if bounded::is_over_limit(&error) {
                    "INPUT_TOO_LARGE"
                } else {
                    "INVALID_INPUT"
                };
                Failure::coded(code, error.to_string())
            })?;
            let text = String::from_utf8(data)
                .map_err(|_| Failure::coded("INVALID_INPUT", "input is not UTF-8"))?;
            Ok(json!({"ok": true, "bytes": text.len(), "text": text}))
        }
        Some("write") if rest.len() == 3 => {
            fs::write_atomic(
                Path::new(&rest[1]),
                format!("{}\n", rest[2]).as_bytes(),
                0o600,
            )?;
            Ok(json!({"ok": true}))
        }
        Some("lock") => {
            let hold = number(rest.get(1), "hold-ms")?;
            match lock::try_runtime_lock("foamy-native-demo", "action")? {
                None => Err(Failure::coded("BUSY", "another action is running")),
                Some(_held) => {
                    thread::sleep(Duration::from_millis(hold));
                    Ok(json!({"ok": true}))
                }
            }
        }
        Some("run") if rest.len() >= 4 => {
            let timeout = number(rest.get(1), "timeout-ms")?;
            let cap = number(rest.get(2), "max-output")?;
            let output = Bounded::new(&rest[3])
                .args(&rest[4..])
                .keep_env(&["PATH"])
                .timeout(Duration::from_millis(timeout))
                .max_output(cap as usize)
                .run()?;
            Ok(json!({
                "ok": output.success(),
                "code": output.status.code(),
                "stdout": output.stdout_lossy(),
                "timed_out": output.timed_out,
                "overflowed": output.overflowed,
            }))
        }
        Some("seccomp") if rest.len() >= 2 => {
            let filter = BpfFilter::decoder().map_err(unsupported)?;
            let output = Bounded::new(&rest[1])
                .args(&rest[2..])
                .env("LC_ALL", "C")
                .seccomp(&filter)
                .run()
                .map_err(unsupported)?;
            Ok(sandboxed(output))
        }
        Some("exec-only") if rest.len() >= 2 => {
            let program = PathBuf::from(&rest[1]);
            let only = ExecOnly::for_program(&program).map_err(unsupported)?;
            let output = Bounded::new(&program)
                .args(&rest[2..])
                .env("LC_ALL", "C")
                .exec_only(&only)
                .run()
                .map_err(unsupported)?;
            Ok(sandboxed(output))
        }
        Some("bwrap-argv") => {
            let argv = Bwrap::new("/usr/bin/bwrap")
                .readonly_host()
                .end_of_options()
                .argv(["git", "status"]);
            let argv: Vec<_> = argv.iter().map(|arg| arg.to_string_lossy()).collect();
            Ok(json!({"ok": true, "argv": argv}))
        }
        Some("fail") => Err(Failure::coded("DEMO_FAILURE", "failed on purpose").with_exit_code(3)),
        Some("panic") => panic!("panicked on purpose"),
        _ => Err(Failure::coded(
            "INVALID_ARGUMENT",
            "usage: foamy-native-demo-helper <subcommand> …",
        )
        .with_exit_code(2)),
    }
}

fn main() -> ExitCode {
    // First, before anything can panic: a panic exits 101 instead of
    // aborting (json::run and json::serve also install it).
    process::exit_on_panic(101);
    // Never std::env::args() out here: it panics on a non-UTF-8 argument.
    match std::env::args_os()
        .nth(1)
        .as_deref()
        .and_then(OsStr::to_str)
    {
        Some("serve") => match serve() {
            Ok(_) => ExitCode::SUCCESS,
            Err(failure) => {
                let _ = json::print_line(&json::error_reply(&failure));
                ExitCode::FAILURE
            }
        },
        Some("favicon") => foamy_helper::favicon::run(),
        _ => json::run(|| main_json(&args()?), json::error_reply),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn call(args: &[&str]) -> Result<Value, Failure> {
        let mut argv = vec!["foamy-native-demo-helper".to_string()];
        argv.extend(args.iter().map(|arg| arg.to_string()));
        main_json(&argv)
    }

    #[test]
    fn subcommands_parse_their_arguments() {
        assert_eq!(
            call(&["args", "a b", ""]).unwrap()["args"],
            json!(["a b", ""])
        );
        assert_eq!(
            call(&["lock", "soon"]).unwrap_err().code,
            "INVALID_ARGUMENT"
        );
        assert_eq!(call(&["nope"]).unwrap_err().exit_code, 2);
        assert_eq!(call(&[]).unwrap_err().code, "INVALID_ARGUMENT");
        assert_eq!(call(&["fail"]).unwrap_err().exit_code, 3);
    }
}
