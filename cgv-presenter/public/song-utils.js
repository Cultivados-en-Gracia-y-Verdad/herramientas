function normalizeForSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function songMatchesQuery(song, query) {
  const normalizedQuery = normalizeForSearch(query).trim();
  if (!normalizedQuery) return true;

  const haystack = normalizeForSearch(
    `${song.file || ""}\n${song.title || ""}\n${song.lyrics || ""}`
  );
  return haystack.includes(normalizedQuery);
}
