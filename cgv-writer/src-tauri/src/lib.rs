mod bible;
mod settings;

use bible::{get_bible_status, read_bible_files, BibleStatus};
use settings::{read_settings, write_settings, WriterSettings};
use std::fs;
use tauri::Emitter;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem, Submenu};

#[tauri::command]
fn read_manual(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_manual(path: String, content: String) -> Result<(), String> {
    fs::write(&path, content.as_bytes()).map_err(|e| e.to_string())
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

fn build_app_menu(app: &tauri::App) -> tauri::Result<Menu<tauri::Wry>> {
    let handle = app.handle();

    let new_item = MenuItem::with_id(handle, "file_new", "Nuevo", true, Some("CmdOrCtrl+N"))?;
    let open_item = MenuItem::with_id(handle, "file_open", "Abrir…", true, Some("CmdOrCtrl+O"))?;
    let reopen_item = MenuItem::with_id(handle, "file_reopen", "Reabrir último", true, None::<&str>)?;
    let save_item = MenuItem::with_id(handle, "file_save", "Guardar", true, Some("CmdOrCtrl+S"))?;
    let template_item = MenuItem::with_id(
        handle,
        "file_template",
        "Nueva plantilla",
        true,
        None::<&str>,
    )?;
    let separator = PredefinedMenuItem::separator(handle)?;
    let quit_item = PredefinedMenuItem::quit(handle, Some("Salir"))?;

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

    Menu::with_items(handle, &[&file_menu, &edit_menu, &quit_item])
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
        .invoke_handler(tauri::generate_handler![
            read_manual,
            write_manual,
            read_writer_settings,
            save_writer_settings,
            get_bible_library_status,
            read_bible_files_command
        ])
        .run(tauri::generate_context!())
        .expect("error while running CGV Writer");
}
