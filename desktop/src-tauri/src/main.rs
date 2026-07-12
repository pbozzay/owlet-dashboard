// Owlet Dashboard desktop shell: spawns the bundled owlet-server sidecar,
// waits for it to come up on 127.0.0.1:8877, then opens a window on it.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

const SERVER_ADDR: (&str, u16) = ("127.0.0.1", 8877);

struct ServerProcess(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ServerProcess(Mutex::new(None)))
        .setup(|app| {
            // Reuse an already-running server (e.g. dev instance); otherwise spawn the sidecar.
            if TcpStream::connect(SERVER_ADDR).is_err() {
                let sidecar = app.shell().sidecar("owlet-server")?;
                let (_rx, child) = sidecar.spawn()?;
                app.state::<ServerProcess>().0.lock().unwrap().replace(child);
                for _ in 0..100 {
                    if TcpStream::connect(SERVER_ADDR).is_ok() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(150));
                }
            }
            tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::External(
                    format!("http://{}:{}/", SERVER_ADDR.0, SERVER_ADDR.1).parse().unwrap(),
                ),
            )
            .title("Owlet Dashboard")
            .inner_size(1280.0, 860.0)
            .build()?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(child) = window
                    .app_handle()
                    .state::<ServerProcess>()
                    .0
                    .lock()
                    .unwrap()
                    .take()
                {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("failed to run Owlet Dashboard");
}
