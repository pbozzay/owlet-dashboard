// Owlet Dashboard desktop shell: spawns the bundled owlet-server sidecar,
// waits for it to come up on 127.0.0.1:8877, then opens a window on it.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::OpenOptions;
use std::io::Write;
use std::net::TcpStream;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

const SERVER_ADDR: (&str, u16) = ("127.0.0.1", 8877);

struct ServerProcess(Mutex<Option<CommandChild>>);

/// Breadcrumbs for "it ran but nothing appeared" reports — a windowed-subsystem
/// exe has no console, so failures are invisible without this.
fn log_line(msg: &str) {
    let dir = std::env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("owlet-dashboard");
    let _ = std::fs::create_dir_all(&dir);
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(dir.join("desktop.log")) {
        let ts = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
        let _ = writeln!(file, "[{ts}] {msg}");
    }
}

fn kill_sidecar(app: &tauri::AppHandle) {
    if let Some(child) = app.state::<ServerProcess>().0.lock().unwrap().take() {
        log_line("stopping sidecar");
        let _ = child.kill();
    }
}

fn main() {
    log_line("--- app start ---");
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ServerProcess(Mutex::new(None)))
        .setup(|app| {
            // Reuse an already-running server (e.g. dev instance); otherwise spawn the sidecar.
            if TcpStream::connect(SERVER_ADDR).is_err() {
                log_line("spawning sidecar");
                let sidecar = app.shell().sidecar("owlet-server")?;
                let (_rx, child) = sidecar.spawn()?;
                app.state::<ServerProcess>().0.lock().unwrap().replace(child);
                // A cold onefile exe self-extracts before booting — allow up to 45s.
                for _ in 0..300 {
                    if TcpStream::connect(SERVER_ADDR).is_ok() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(150));
                }
            } else {
                log_line("reusing already-running server on 8877");
            }
            let reachable = TcpStream::connect(SERVER_ADDR).is_ok();
            log_line(&format!("server reachable: {reachable}; creating window"));
            let url = format!("http://{}:{}/", SERVER_ADDR.0, SERVER_ADDR.1);
            let window = tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::External(url.parse().unwrap()),
            )
            .title("Owlet Dashboard")
            .inner_size(1280.0, 860.0)
            .center()
            .focused(true)
            .build();
            match window {
                Ok(win) => {
                    log_line("window created");
                    let _ = win.set_focus();
                    Ok(())
                }
                Err(err) => {
                    // The dashboard still works without our window — hand the
                    // user their browser rather than vanishing silently.
                    log_line(&format!("window creation FAILED: {err}"));
                    let _ = std::process::Command::new("cmd")
                        .args(["/C", "start", "", &url])
                        .spawn();
                    Err(err.into())
                }
            }
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                kill_sidecar(window.app_handle());
            }
        })
        .build(tauri::generate_context!());

    match app {
        Ok(app) => app.run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                // Covers every shutdown path — a setup failure or crash must
                // not leave an orphaned owlet-server running headless.
                kill_sidecar(app_handle);
                log_line("app exit");
            }
        }),
        Err(err) => {
            log_line(&format!("app failed to build: {err}"));
            std::process::exit(1);
        }
    }
}
