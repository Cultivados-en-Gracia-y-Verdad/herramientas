const form = document.getElementById("songRepositoryForm");
const input = document.getElementById("songRepositoryInput");
const button = document.getElementById("downloadSongsButton");
const statusText = document.getElementById("songStatus");
const suggestedRepositoryLink = document.getElementById("suggestedRepositoryLink");

let defaultSongRepository = {
  repository: "Cultivados-en-Gracia-y-Verdad/canciones",
  url: "https://github.com/Cultivados-en-Gracia-y-Verdad/canciones/",
  branch: "main",
  songsPath: "songs/chordpro"
};

const t = key => window.CGVI18N?.t(key) || key;

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", isError);
}

async function loadDefaultRepository() {
  try {
    const config = await readJson(await fetch("/songs/repository"));
    defaultSongRepository = {
      ...defaultSongRepository,
      ...config,
      url: config.url || `https://github.com/${config.repository || defaultSongRepository.repository}/`
    };
  } catch {
    defaultSongRepository.url = "https://github.com/Cultivados-en-Gracia-y-Verdad/canciones/";
  }

  input.value = defaultSongRepository.url;
  input.placeholder = defaultSongRepository.url;
  suggestedRepositoryLink.textContent = defaultSongRepository.url;
  suggestedRepositoryLink.href = defaultSongRepository.url;
}

async function downloadSongs(event) {
  event.preventDefault();
  const repository = input.value.trim() || defaultSongRepository.url;

  button.disabled = true;
  setStatus(t("songsDownloading"));

  try {
    const result = await readJson(await fetch("/songs/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository,
        branch: defaultSongRepository.branch,
        songsPath: defaultSongRepository.songsPath
      })
    }));
    setStatus(t("songsDownloadedMessage").replace("{count}", result.fileCount || 0));
  } catch (error) {
    setStatus(error.message || t("songsDownloadFailedTitle"), true);
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await window.CGVI18N.loadLanguage();
  await loadDefaultRepository();
  form.addEventListener("submit", downloadSongs);
  input.focus();
});
