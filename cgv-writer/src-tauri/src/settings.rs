use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::Manager;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct WriterSettings {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub library_root_dir: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bible_version: Option<String>,
}

pub fn settings_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map_err(|e| e.to_string())
        .map(|dir| dir.join("writer-settings.json"))
}

pub fn read_settings(app: &tauri::AppHandle) -> Result<WriterSettings, String> {
    let path = settings_path(app)?;
    if !path.exists() {
        return Ok(WriterSettings::default());
    }

    let raw = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    serde_json::from_str(&raw).map_err(|e| e.to_string())
}

pub fn write_settings(app: &tauri::AppHandle, settings: &WriterSettings) -> Result<(), String> {
    let path = settings_path(app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    let json = serde_json::to_string_pretty(settings).map_err(|e| e.to_string())?;
    fs::write(path, format!("{json}\n")).map_err(|e| e.to_string())
}

pub fn normalize_bible_version(value: Option<&str>) -> String {
    value
        .unwrap_or("NBLA")
        .trim()
        .chars()
        .filter(|c| c.is_ascii_alphanumeric() || *c == '_' || *c == '-')
        .collect::<String>()
        .to_uppercase()
}

pub fn bible_file_extension(version: &str) -> String {
    format!(".{}.md", version.to_lowercase())
}

pub fn bible_dir(library_root: &str, version: &str) -> PathBuf {
    Path::new(library_root)
        .join("bibles")
        .join(normalize_bible_version(Some(version)))
}

pub fn list_bible_versions(library_root: &str) -> Vec<String> {
    let bibles_root = Path::new(library_root).join("bibles");
    let Ok(entries) = fs::read_dir(&bibles_root) else {
        return Vec::new();
    };

    let mut versions = Vec::new();
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
            continue;
        };

        let version = normalize_bible_version(Some(name));
        let ext = bible_file_extension(&version);
        let file_count = fs::read_dir(&path)
            .map(|read| {
                read.flatten()
                    .filter(|e| {
                        e.path()
                            .file_name()
                            .and_then(|n| n.to_str())
                            .map(|n| n.to_lowercase().ends_with(&ext))
                            .unwrap_or(false)
                    })
                    .count()
            })
            .unwrap_or(0);

        if file_count > 0 {
            versions.push(version);
        }
    }

    versions.sort();
    versions.dedup();
    versions
}
