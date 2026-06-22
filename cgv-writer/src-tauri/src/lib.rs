mod bible;
mod settings;

use bible::{get_bible_status, read_bible_files, BibleStatus};
use settings::{read_settings, write_settings, WriterSettings};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tauri::Emitter;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};
use std::sync::atomic::{AtomicBool, Ordering};
use tauri::{Manager, RunEvent, WindowEvent};

static ALLOW_EXIT: AtomicBool = AtomicBool::new(false);

#[tauri::command]
fn read_manual(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_manual(path: String, content: String) -> Result<(), String> {
    write_manual_safely(Path::new(&path), content.as_bytes())
}

const MAX_MANUAL_BACKUPS: usize = 20;

fn backup_manual(path: &Path) -> Result<(), String> {
    if !path.exists() {
        return Ok(());
    }

    let parent = path.parent().ok_or_else(|| "La ruta del manual no tiene carpeta.".to_string())?;
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| "El nombre del manual no es válido.".to_string())?;
    let backup_dir = parent.join(".cgv-writer-backups");
    fs::create_dir_all(&backup_dir).map_err(|e| e.to_string())?;

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_millis();
    let backup_path = backup_dir.join(format!("{file_name}.{timestamp}.bak"));
    fs::copy(path, backup_path).map_err(|e| e.to_string())?;

    let mut backups: Vec<PathBuf> = fs::read_dir(&backup_dir)
        .map_err(|e| e.to_string())?
        .flatten()
        .map(|entry| entry.path())
        .filter(|candidate| {
            candidate
                .file_name()
                .and_then(|name| name.to_str())
                .map(|name| name.starts_with(&format!("{file_name}.")) && name.ends_with(".bak"))
                .unwrap_or(false)
        })
        .collect();
    backups.sort();
    let remove_count = backups.len().saturating_sub(MAX_MANUAL_BACKUPS);
    for old in backups.into_iter().take(remove_count) {
        let _ = fs::remove_file(old);
    }

    Ok(())
}

fn write_manual_safely(path: &Path, content: &[u8]) -> Result<(), String> {
    let parent = path.parent().ok_or_else(|| "La ruta del manual no tiene carpeta.".to_string())?;
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;

    if path.exists() {
        let existing = fs::read(path).map_err(|e| e.to_string())?;
        if existing == content {
            return Ok(());
        }
        backup_manual(path)?;
    }

    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| "El nombre del manual no es válido.".to_string())?;
    let temp_path = parent.join(format!(".{file_name}.cgv-writer.tmp"));
    let mut temp = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&temp_path)
        .map_err(|e| e.to_string())?;
    temp.write_all(content).map_err(|e| e.to_string())?;
    temp.sync_all().map_err(|e| e.to_string())?;
    drop(temp);

    #[cfg(not(target_os = "windows"))]
    {
        fs::rename(&temp_path, path).map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "windows")]
    {
        let previous_path = parent.join(format!(".{file_name}.cgv-writer.previous"));
        if path.exists() {
            let _ = fs::remove_file(&previous_path);
            fs::rename(path, &previous_path).map_err(|e| e.to_string())?;
        }
        if let Err(error) = fs::rename(&temp_path, path) {
            if previous_path.exists() {
                let _ = fs::rename(&previous_path, path);
            }
            return Err(error.to_string());
        }
        let _ = fs::remove_file(previous_path);
    }

    Ok(())
}

#[cfg(test)]
mod manual_write_tests {
    use super::*;

    #[test]
    fn safe_write_preserves_previous_version_and_skips_unchanged_backups() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let dir = std::env::temp_dir().join(format!("cgv-writer-save-test-{unique}"));
        fs::create_dir_all(&dir).unwrap();
        let manual = dir.join("manual.md");

        write_manual_safely(&manual, b"version one\n").unwrap();
        write_manual_safely(&manual, b"version two\n").unwrap();
        assert_eq!(fs::read(&manual).unwrap(), b"version two\n");

        let backup_dir = dir.join(".cgv-writer-backups");
        let backups_after_change: Vec<_> = fs::read_dir(&backup_dir).unwrap().flatten().collect();
        assert_eq!(backups_after_change.len(), 1);
        assert_eq!(fs::read(backups_after_change[0].path()).unwrap(), b"version one\n");

        write_manual_safely(&manual, b"version two\n").unwrap();
        let backups_after_unchanged: Vec<_> = fs::read_dir(&backup_dir).unwrap().flatten().collect();
        assert_eq!(backups_after_unchanged.len(), 1);

        fs::remove_dir_all(dir).unwrap();
    }
}

#[tauri::command]
fn read_writer_settings(app: tauri::AppHandle) -> Result<WriterSettings, String> {
    read_settings(&app)
}

#[tauri::command]
fn save_writer_settings(app: tauri::AppHandle, settings: WriterSettings) -> Result<(), String> {
    write_settings(&app, &settings)
}

#[tauri::command]
fn get_bible_library_status(app: tauri::AppHandle) -> Result<BibleStatus, String> {
    let settings = read_settings(&app)?;
    Ok(get_bible_status(
        settings.library_root_dir.as_deref(),
        settings.bible_version.as_deref(),
    ))
}

#[tauri::command]
fn read_bible_files_command(app: tauri::AppHandle) -> Result<Vec<bible::BibleFilePayload>, String> {
    let settings = read_settings(&app)?;
    let library_root = settings
        .library_root_dir
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| {
            "Configure la carpeta de biblioteca CGV en Ajustes antes de consultar referencias."
                .to_string()
        })?;

    let version = settings.bible_version.as_deref().unwrap_or("NBLA");
    read_bible_files(library_root, version)
}

#[tauri::command]
fn quit_app(app: tauri::AppHandle) {
    ALLOW_EXIT.store(true, Ordering::SeqCst);
    app.exit(0);
}

fn request_app_quit(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.emit("app-request-quit", ());
    }
}

fn build_app_menu(app: &tauri::App) -> tauri::Result<Menu<tauri::Wry>> {
    let handle = app.handle();

    let new_item = MenuItem::with_id(handle, "file_new", "Nuevo", true, Some("CmdOrCtrl+N"))?;
    let open_item = MenuItem::with_id(handle, "file_open", "Abrir…", true, Some("CmdOrCtrl+O"))?;
    let reopen_item = MenuItem::with_id(
        handle,
        "file_reopen",
        "Reabrir último",
        true,
        Some("CmdOrCtrl+Shift+O"),
    )?;
    let save_item = MenuItem::with_id(handle, "file_save", "Guardar", true, Some("CmdOrCtrl+S"))?;
    let template_item = MenuItem::with_id(
        handle,
        "file_template",
        "Nueva plantilla",
        true,
        None::<&str>,
    )?;
    let separator = PredefinedMenuItem::separator(handle)?;
    let quit_item = MenuItem::with_id(
        handle,
        "app_quit",
        "Salir de CGV Writer",
        true,
        Some("CmdOrCtrl+Q"),
    )?;

    let edit_separator = PredefinedMenuItem::separator(handle)?;
    let edit_menu = Submenu::with_items(
        handle,
        "Editar",
        true,
        &[
            &PredefinedMenuItem::undo(handle, None)?,
            &PredefinedMenuItem::redo(handle, None)?,
            &edit_separator,
            &PredefinedMenuItem::cut(handle, None)?,
            &PredefinedMenuItem::copy(handle, None)?,
            &PredefinedMenuItem::paste(handle, None)?,
            &PredefinedMenuItem::select_all(handle, None)?,
        ],
    )?;

    #[cfg(target_os = "macos")]
    {
        let app_menu = Submenu::with_items(
            handle,
            "CGV Writer",
            true,
            &[
                &PredefinedMenuItem::about(handle, Some("Acerca de CGV Writer"), None)?,
                &PredefinedMenuItem::separator(handle)?,
                &PredefinedMenuItem::hide(handle, None)?,
                &PredefinedMenuItem::hide_others(handle, None)?,
                &PredefinedMenuItem::show_all(handle, None)?,
                &PredefinedMenuItem::separator(handle)?,
                &quit_item,
            ],
        )?;

        let file_menu = Submenu::with_items(
            handle,
            "Archivo",
            true,
            &[
                &new_item,
                &open_item,
                &reopen_item,
                &separator,
                &save_item,
                &separator,
                &template_item,
            ],
        )?;

        return Menu::with_items(handle, &[&app_menu, &file_menu, &edit_menu]);
    }

    #[cfg(not(target_os = "macos"))]
    {
        let file_menu = Submenu::with_items(
            handle,
            "Archivo",
            true,
            &[
                &new_item,
                &open_item,
                &reopen_item,
                &separator,
                &save_item,
                &separator,
                &template_item,
                &separator,
                &quit_item,
            ],
        )?;

        Menu::with_items(handle, &[&file_menu, &edit_menu])
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            app.set_menu(build_app_menu(app)?)?;
            Ok(())
        })
        .on_menu_event(|app, event| {
            let id = event.id().0.as_str();
            let _ = app.emit(&format!("menu-{id}"), ());
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                if ALLOW_EXIT.load(Ordering::SeqCst) {
                    return;
                }
                api.prevent_close();
                let _ = window.emit("app-request-quit", ());
            }
        })
        .invoke_handler(tauri::generate_handler![
            read_manual,
            write_manual,
            read_writer_settings,
            save_writer_settings,
            get_bible_library_status,
            read_bible_files_command,
            quit_app
        ])
        .build(tauri::generate_context!())
        .expect("error while building CGV Writer")
        .run(|app_handle, event| {
            match event {
                RunEvent::ExitRequested { api, .. } => {
                    if ALLOW_EXIT.load(Ordering::SeqCst) {
                        return;
                    }
                    api.prevent_exit();
                    request_app_quit(app_handle);
                }
                RunEvent::Reopen { .. } => {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        let _ = window.unminimize();
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                _ => {}
            }
        });
}
