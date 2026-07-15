function normalizeForSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function getSongSearchHaystack(song) {
  if (!song || typeof song !== "object") return "";
  if (typeof song._searchHaystack === "string") return song._searchHaystack;

  song._searchHaystack = normalizeForSearch(
    `${song.file || ""}\n${song.title || ""}\n${song.lyrics || ""}\n${song.chordLyrics || ""}`
  );
  return song._searchHaystack;
}

function songMatchesQuery(song, query) {
  const normalizedQuery = normalizeForSearch(query).trim();
  if (!normalizedQuery) return true;
  return getSongSearchHaystack(song).includes(normalizedQuery);
}
