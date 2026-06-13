use crate::settings::{bible_dir, bible_file_extension, list_bible_versions, normalize_bible_version};
use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BibleFilePayload {
    pub file_name: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BibleStatus {
    pub configured: bool,
    pub library_root_dir: Option<String>,
    pub version: String,
    pub loaded: bool,
    pub books: usize,
    pub references: usize,
    pub bible_dir: Option<String>,
    pub available_versions: Vec<String>,
    pub error: Option<String>,
}

pub fn get_bible_status(library_root: Option<&str>, version: Option<&str>) -> BibleStatus {
    let version = normalize_bible_version(version);
    let library_root_dir = library_root
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);

    let available_versions = library_root_dir
        .as_deref()
        .map(list_bible_versions)
        .unwrap_or_default();

    let Some(root) = library_root_dir.as_deref() else {
        return BibleStatus {
            configured: false,
            library_root_dir: None,
            version,
            loaded: false,
            books: 0,
            references: 0,
            bible_dir: None,
            available_versions,
            error: Some(
                "Seleccione la carpeta raíz de la biblioteca CGV (la misma que usa CGV Presenter)."
                    .to_string(),
            ),
        };
    };

    if !Path::new(root).is_dir() {
        return BibleStatus {
            configured: true,
            library_root_dir: Some(root.to_string()),
            version: version.clone(),
            loaded: false,
            books: 0,
            references: 0,
            bible_dir: None,
            available_versions,
            error: Some(format!("La carpeta no existe: {root}")),
        };
    }

    let dir = bible_dir(root, &version);
    let bible_dir_display = dir.to_str().map(str::to_string);

    match read_bible_files_from_dir(&dir, &version) {
        Ok(files) if !files.is_empty() => {
            let (books, references) = count_bible_entries(&files);
            BibleStatus {
                configured: true,
                library_root_dir: Some(root.to_string()),
                version,
                loaded: true,
                books,
                references,
                bible_dir: bible_dir_display,
                available_versions,
                error: None,
            }
        }
        Ok(_) => {
            let extension = bible_file_extension(&version);
            BibleStatus {
                configured: true,
                library_root_dir: Some(root.to_string()),
                version,
                loaded: false,
                books: 0,
                references: 0,
                bible_dir: bible_dir_display,
                available_versions,
                error: Some(format!(
                    "No hay archivos {extension} en {}",
                    dir.display()
                )),
            }
        }
        Err(error) => BibleStatus {
            configured: true,
            library_root_dir: Some(root.to_string()),
            version,
            loaded: false,
            books: 0,
            references: 0,
            bible_dir: bible_dir_display,
            available_versions,
            error: Some(error),
        },
    }
}

pub fn read_bible_files(library_root: &str, version: &str) -> Result<Vec<BibleFilePayload>, String> {
    let version = normalize_bible_version(Some(version));
    let dir = bible_dir(library_root, &version);

    if !dir.is_dir() {
        return Err(format!(
            "No se encontró la carpeta de biblias: {}",
            dir.display()
        ));
    }

    read_bible_files_from_dir(&dir, &version)
}

fn read_bible_files_from_dir(dir: &Path, version: &str) -> Result<Vec<BibleFilePayload>, String> {
    let extension = bible_file_extension(version);
    let mut files = Vec::new();

    for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if !path.is_file() {
            continue;
        }

        let Some(file_name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };

        if !file_name.to_lowercase().ends_with(&extension) {
            continue;
        }

        let content = fs::read_to_string(&path).map_err(|e| e.to_string())?;
        files.push(BibleFilePayload {
            file_name: file_name.to_string(),
            content,
        });
    }

    files.sort_by(|a, b| a.file_name.cmp(&b.file_name));
    Ok(files)
}

fn count_bible_entries(files: &[BibleFilePayload]) -> (usize, usize) {
    let mut books = std::collections::HashSet::new();
    let mut references = 0usize;

    for file in files {
        for line in file.content.replace("\r\n", "\n").lines() {
            if line.matches(':').count() < 2 {
                continue;
            }

            if let Some(caps) = regex_lite::Regex::new(r"^(.+?)\s+(\d+):(\d+)\s+(.+)$")
                .ok()
                .and_then(|re| re.captures(line))
            {
                let book = caps.get(1).map(|m| m.as_str()).unwrap_or("").trim();
                if !book.is_empty() {
                    books.insert(book.to_string());
                    references += 1;
                }
            }
        }
    }

    (books.len(), references)
}
