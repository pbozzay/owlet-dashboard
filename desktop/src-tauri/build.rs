fn main() {
    // Register our app command with the ACL so the capability can grant it
    // (autogenerates the `allow-show-native-toast` permission).
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&["show_native_toast"]),
        ),
    )
    .expect("failed to run tauri-build");
}
