/* BLE browser interlinear reader */

const TOKEN_RE = /^(.+)<([^|]*)\|([^|]*)\|([^|]*)\|([^>]*)>$/;
const RESULT_LIMIT = 120;

const els = {
  testament: document.getElementById("testament"),
  book: document.getElementById("book"),
  chapter: document.getElementById("chapter"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  heading: document.getElementById("heading"),
  status: document.getElementById("status"),
  verses: document.getElementById("verses"),
  readerMain: document.getElementById("readerMain"),
  showMorph: document.getElementById("showMorph"),
  showStrongs: document.getElementById("showStrongs"),
  showLemma: document.getElementById("showLemma"),
  detail: document.getElementById("detail"),
  detailClose: document.getElementById("detailClose"),
  detailSurface: document.getElementById("detailSurface"),
  detailEs: document.getElementById("detailEs"),
  detailStrongs: document.getElementById("detailStrongs"),
  detailLemma: document.getElementById("detailLemma"),
  detailMorph: document.getElementById("detailMorph"),
  detailLex: document.getElementById("detailLex"),
  detailLexEs: document.getElementById("detailLexEs"),
  detailLexXlit: document.getElementById("detailLexXlit"),
  detailLexDef: document.getElementById("detailLexDef"),
  detailLexUsage: document.getElementById("detailLexUsage"),
  searchForm: document.getElementById("searchForm"),
  searchInput: document.getElementById("searchInput"),
  searchScope: document.getElementById("searchScope"),
  searchBtn: document.getElementById("searchBtn"),
  searchClear: document.getElementById("searchClear"),
  searchEs: document.getElementById("searchEs"),
  searchStrongs: document.getElementById("searchStrongs"),
  searchMorph: document.getElementById("searchMorph"),
  searchSurface: document.getElementById("searchSurface"),
  searchPanel: document.getElementById("searchPanel"),
  searchHeading: document.getElementById("searchHeading"),
  searchMeta: document.getElementById("searchMeta"),
  searchResults: document.getElementById("searchResults"),
  searchClose: document.getElementById("searchClose"),
};

let catalog = null;
let bookLabels = new Map();
let bookOrder = new Map();
let bookAliases = []; // longest-first: {alias, t, slug}
let activeTokenEl = null;
let searchIndex = null;
let searchIndexPromise = null;
let strongsLex = null;
let strongsLexPromise = null;
let pendingHighlight = null;
let pendingVerse = null;
let suppressHashPush = false;

function showStatus(msg) {
  els.status.hidden = !msg;
  els.status.textContent = msg || "";
}

function currentTestament() {
  return catalog.testaments.find((t) => t.code === els.testament.value);
}

function currentBook() {
  const t = currentTestament();
  return t?.books.find((b) => b.slug === els.book.value);
}

function fillSelect(select, items, getValue, getLabel, selected) {
  select.innerHTML = "";
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = getValue(item);
    opt.textContent = getLabel(item);
    select.appendChild(opt);
  }
  if (selected != null) select.value = String(selected);
}

function syncBookOptions(preferredSlug) {
  const t = currentTestament();
  if (!t) return;
  const slug = preferredSlug && t.books.some((b) => b.slug === preferredSlug)
    ? preferredSlug
    : t.books[0]?.slug;
  fillSelect(els.book, t.books, (b) => b.slug, (b) => b.label, slug);
  syncChapterOptions();
}

function syncChapterOptions(preferredChapter) {
  const book = currentBook();
  if (!book) return;
  const ch = preferredChapter && book.chapters.includes(Number(preferredChapter))
    ? Number(preferredChapter)
    : book.chapters[0];
  fillSelect(els.chapter, book.chapters, (n) => n, (n) => String(n), ch);
}

function parseToken(raw) {
  const m = TOKEN_RE.exec(raw.trim());
  if (!m) return null;
  return {
    surface: m[1],
    lemma: m[2],
    strongs: m[3],
    morph: m[4],
    es: m[5],
  };
}

function parseChapterText(text) {
  const verses = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    const tab = line.indexOf("\t");
    if (tab < 0) continue;
    const ref = line.slice(0, tab).trim();
    const body = line.slice(tab + 1).trim();
    const tokens = body
      .split(/\s+/)
      .map(parseToken)
      .filter(Boolean);
    const m = /:(\d+)\s*$/.exec(ref);
    verses.push({
      ref,
      vs: m ? Number(m[1]) : verses.length + 1,
      tokens,
    });
  }
  return verses;
}

function chapterUrl(testamentCode, bookSlug, chapter) {
  const num = String(chapter).padStart(2, "0");
  return `../output/interlinear/${testamentCode}/${bookSlug}-${num}.interlinear.txt`;
}

function metaLines(token) {
  const lines = [];
  if (els.showStrongs.checked && token.strongs) lines.push(token.strongs);
  if (els.showLemma.checked && token.lemma) lines.push(token.lemma);
  if (els.showMorph.checked && token.morph) lines.push(token.morph);
  return lines;
}

function normalizeStrongsKey(code) {
  const raw = String(code || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!raw) return "";
  if (/^[HG]\d+[A-Z]?$/.test(raw)) return raw;
  if (/^\d+[A-Z]?$/.test(raw)) return raw;
  return raw;
}

function lookupStrongs(code) {
  if (!strongsLex) return null;
  const key = normalizeStrongsKey(code);
  if (!key) return null;
  if (strongsLex[key]) return strongsLex[key];
  // H1004A → try H1004
  const m = /^([HG]\d+)([A-Z])$/.exec(key);
  if (m && strongsLex[m[1]]) return strongsLex[m[1]];
  return null;
}

async function ensureStrongsLex() {
  if (strongsLex) return strongsLex;
  if (strongsLexPromise) return strongsLexPromise;
  strongsLexPromise = (async () => {
    const res = await fetch("strongs.json");
    if (!res.ok) throw new Error(`strongs.json HTTP ${res.status}`);
    const data = await res.json();
    strongsLex = data.entries || data;
    return strongsLex;
  })();
  try {
    return await strongsLexPromise;
  } catch (err) {
    strongsLexPromise = null;
    throw err;
  }
}

function setHidden(el, hidden) {
  el.hidden = Boolean(hidden);
}

function renderLexEntry(entry) {
  if (!entry) {
    setHidden(els.detailLex, true);
    els.detailLexDef.textContent = "";
    els.detailLexEs.textContent = "";
    els.detailLexXlit.textContent = "";
    els.detailLexUsage.textContent = "";
    return;
  }
  setHidden(els.detailLex, false);

  const es = entry.es || "";
  setHidden(els.detailLexEs, !es);
  els.detailLexEs.textContent = es;

  const xlit = entry.xlit || entry.pron || "";
  setHidden(els.detailLexXlit, !xlit);
  els.detailLexXlit.textContent = xlit;

  els.detailLexDef.textContent = entry.def || "Sin definición disponible.";

  const usage = entry.usage || "";
  setHidden(els.detailLexUsage, !usage);
  els.detailLexUsage.textContent = usage;
}

function openDetail(token, tokenEl) {
  if (activeTokenEl) activeTokenEl.classList.remove("active");
  activeTokenEl = tokenEl;
  tokenEl.classList.add("active");
  els.detail.hidden = false;
  els.detailSurface.textContent = token.surface;
  els.detailEs.textContent = token.es;
  els.detailStrongs.textContent = token.strongs || "—";
  els.detailLemma.textContent = token.lemma || "—";
  els.detailMorph.textContent = token.morph || "—";

  const cached = lookupStrongs(token.strongs);
  if (cached) {
    renderLexEntry(cached);
    return;
  }
  if (!token.strongs) {
    renderLexEntry(null);
    return;
  }

  // Show panel while lexicon loads (lazy, once).
  setHidden(els.detailLex, false);
  setHidden(els.detailLexEs, true);
  setHidden(els.detailLexXlit, true);
  setHidden(els.detailLexUsage, true);
  els.detailLexDef.textContent = "Cargando definición…";

  const requested = token.strongs;
  ensureStrongsLex()
    .then(() => {
      // Ignore stale loads if user clicked another word.
      if (els.detailStrongs.textContent !== (requested || "—")) return;
      renderLexEntry(lookupStrongs(requested));
    })
    .catch(() => {
      if (els.detailStrongs.textContent !== (requested || "—")) return;
      renderLexEntry(null);
      setHidden(els.detailLex, false);
      els.detailLexDef.textContent = "No se pudo cargar el léxico Strong's.";
    });
}

function closeDetail() {
  els.detail.hidden = true;
  if (activeTokenEl) activeTokenEl.classList.remove("active");
  activeTokenEl = null;
  renderLexEntry(null);
}

function normalizeText(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/·/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeStrongsQuery(q) {
  const raw = q.trim().toUpperCase().replace(/\s+/g, "");
  if (/^[HG]\d+[A-Z]?$/.test(raw)) return raw;
  if (/^\d+[A-Z]?$/.test(raw)) return raw;
  return normalizeText(q);
}

function normalizeMorphQuery(q) {
  return String(q || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "")
    .replace(/·/g, "");
}

function makeClause(text, phrase) {
  const es = normalizeText(text);
  const morph = normalizeMorphQuery(text);
  let strongs;
  if (phrase) {
    // Contiguous Strong's sequence: "H430 H853"
    strongs = text
      .trim()
      .split(/\s+/)
      .map((t) => normalizeStrongsQuery(t))
      .filter(Boolean)
      .join(" ");
  } else {
    strongs = normalizeStrongsQuery(text);
  }
  return {
    phrase: Boolean(phrase),
    raw: text,
    es,
    strongs,
    surface: es,
    morph,
  };
}

/**
 * Phrase / term parser.
 * - "los cielos" → exact phrase (contiguous)
 * - en principio → phrase (multi-word unquoted)
 * - Dios → single term
 * - "en principio" crear → phrase AND term
 */
function parseQuery(raw) {
  const input = raw.trim();
  if (!input) return [];

  const parts = [];
  const re = /"([^"]+)"|(\S+)/g;
  let m;
  while ((m = re.exec(input))) {
    if (m[1] != null) parts.push({ quoted: true, text: m[1].trim() });
    else parts.push({ quoted: false, text: m[2] });
  }
  parts.forEach((p) => {
    if (!p.text) return;
  });
  const cleaned = parts.filter((p) => p.text);
  if (!cleaned.length) return [];

  const anyQuoted = cleaned.some((p) => p.quoted);
  if (!anyQuoted && cleaned.length > 1) {
    return [makeClause(cleaned.map((p) => p.text).join(" "), true)];
  }

  return cleaned.map((p) => makeClause(p.text, p.quoted || /\s/.test(p.text)));
}

function fieldMatch(hayNorm, clauseVal, phrase) {
  if (!clauseVal || !hayNorm) return false;
  if (!hayNorm.includes(clauseVal)) return false;
  if (!phrase) return true;
  // Phrase: prefer word-boundary-ish match (spaces around) when possible
  if (hayNorm === clauseVal) return true;
  if (hayNorm.startsWith(`${clauseVal} `) || hayNorm.endsWith(` ${clauseVal}`)) return true;
  if (hayNorm.includes(` ${clauseVal} `)) return true;
  // Fallback: contiguous substring (handles mid-token · already normalized)
  return hayNorm.includes(clauseVal);
}

function strongsMatch(rowSN, clause, phrase) {
  if (!clause.strongs) return false;
  if (phrase) {
    return rowSN.includes(clause.strongs);
  }
  const q = clause.strongs;
  const parts = rowSN.split(" ");
  if (parts.includes(q)) return true;
  if (/^\d/.test(q) && (parts.includes(`H${q}`) || parts.includes(`G${q}`))) return true;
  return rowSN.includes(q);
}

function morphMatch(rowMorphN, clause) {
  if (!clause.morph || !rowMorphN) return false;
  return rowMorphN.includes(clause.morph);
}

function tokenMatchesHighlight(token, clauses, fields) {
  if (!clauses.length) return false;
  const es = fields.es ? normalizeText(token.es) : "";
  const strongs = fields.strongs ? String(token.strongs || "").toUpperCase() : "";
  const surface = fields.surface ? normalizeText(token.surface) : "";
  const morph = fields.morph ? String(token.morph || "").toUpperCase().replace(/\s+/g, "") : "";

  return clauses.some((clause) => {
    if (fields.es && clause.es) {
      if (clause.phrase) {
        const words = clause.es.split(/\s+/).filter(Boolean);
        if (words.some((w) => es === w || es.includes(w))) return true;
      } else if (es.includes(clause.es)) {
        return true;
      }
    }
    if (fields.strongs && clause.strongs) {
      if (clause.phrase) {
        const codes = clause.strongs.split(/\s+/);
        if (codes.includes(strongs)) return true;
      } else if (strongsMatch(strongs, clause, false)) {
        return true;
      }
    }
    if (fields.surface && clause.surface) {
      if (clause.phrase) {
        const words = clause.surface.split(/\s+/).filter(Boolean);
        if (words.some((w) => surface.includes(w))) return true;
      } else if (surface.includes(clause.surface)) {
        return true;
      }
    }
    if (fields.morph && morphMatch(morph, clause)) return true;
    return false;
  });
}

function applyTokenHighlight(btn, token) {
  if (!pendingHighlight) return;
  if (tokenMatchesHighlight(token, pendingHighlight.clauses, pendingHighlight.fields)) {
    btn.classList.add("hit");
  }
}

function renderVerses(verses, rtl) {
  els.verses.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const verse of verses) {
    const section = document.createElement("section");
    section.className = "verse";
    section.id = `v${verse.vs}`;

    const ref = document.createElement("p");
    ref.className = "verse-ref";
    ref.textContent = verse.ref;
    section.appendChild(ref);

    const row = document.createElement("div");
    row.className = `tokens${rtl ? " rtl" : ""}`;

    for (const token of verse.tokens) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "token";

      const surface = document.createElement("span");
      surface.className = "tok-surface";
      surface.textContent = token.surface;

      const es = document.createElement("span");
      es.className = "tok-es";
      es.textContent = token.es;

      btn.appendChild(surface);
      btn.appendChild(es);

      for (const line of metaLines(token)) {
        const meta = document.createElement("span");
        meta.className = "tok-meta";
        meta.textContent = line;
        btn.appendChild(meta);
      }

      applyTokenHighlight(btn, token);
      btn.addEventListener("click", () => openDetail(token, btn));
      row.appendChild(btn);
    }

    section.appendChild(row);
    frag.appendChild(section);
  }
  els.verses.appendChild(frag);
}

function hideSearchPanel() {
  els.searchPanel.hidden = true;
  els.readerMain.hidden = false;
}

function showSearchPanel() {
  els.searchPanel.hidden = false;
  els.readerMain.hidden = true;
  closeDetail();
}

async function loadChapter() {
  const t = currentTestament();
  const book = currentBook();
  const chapter = Number(els.chapter.value);
  if (!t || !book || !chapter) return;

  hideSearchPanel();
  const rtl = t.code === "OT";
  els.heading.textContent = `${book.label} ${chapter}`;
  document.title = `${book.label} ${chapter} · BLE Interlinear`;
  showStatus("");
  els.verses.innerHTML = `<p class="status">Cargando ${book.label} ${chapter}…</p>`;
  closeDetail();

  const url = chapterUrl(t.code, book.slug, chapter);
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    const text = await res.text();
    const verses = parseChapterText(text);
    if (!verses.length) throw new Error("Capítulo vacío o formato inesperado");
    const verseForHash = pendingVerse;
    renderVerses(verses, rtl);
    if (verseForHash != null) {
      const target = document.getElementById(`v${verseForHash}`);
      if (target) {
        target.classList.add("verse-hit");
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      pendingVerse = null;
    }
    if (!suppressHashPush) updateHash(false, verseForHash);
    suppressHashPush = false;
  } catch (err) {
    els.verses.innerHTML = "";
    showStatus(
      `No se pudo cargar el capítulo. Abre el reader con un servidor local (no file://). ${err.message}`
    );
  }
}

function updateHash(replace, verse) {
  let hash = `#${els.testament.value}/${els.book.value}/${els.chapter.value}`;
  if (verse != null) hash += `/${verse}`;
  if (replace) history.replaceState(null, "", hash);
  else history.pushState(null, "", hash);
}

function applyHash() {
  const raw = location.hash.replace(/^#/, "");
  if (!raw) return false;
  const parts = raw.split("/");
  const [testament, book, chapter, verse] = parts;
  if (!testament || !book || !chapter) return false;
  if (!catalog.testaments.some((t) => t.code === testament)) return false;
  els.testament.value = testament;
  syncBookOptions(book);
  syncChapterOptions(Number(chapter));
  pendingVerse = verse ? Number(verse) : null;
  return true;
}

function stepChapter(delta) {
  const book = currentBook();
  if (!book) return;
  pendingHighlight = null;
  pendingVerse = null;
  const idx = book.chapters.indexOf(Number(els.chapter.value));
  const next = book.chapters[idx + delta];
  if (next == null) {
    const t = currentTestament();
    const bIdx = t.books.findIndex((b) => b.slug === book.slug);
    const neighbor = t.books[bIdx + delta];
    if (!neighbor) return;
    els.book.value = neighbor.slug;
    syncChapterOptions(delta > 0 ? neighbor.chapters[0] : neighbor.chapters.at(-1));
  } else {
    els.chapter.value = String(next);
  }
  loadChapter();
}

function rerenderVisibleMeta() {
  loadChapter();
}

async function ensureSearchIndex() {
  if (searchIndex) return searchIndex;
  if (searchIndexPromise) return searchIndexPromise;
  searchIndexPromise = (async () => {
    els.searchMeta.textContent = "Cargando índice de búsqueda…";
    const res = await fetch("search-index.json");
    if (!res.ok) throw new Error(`search-index.json HTTP ${res.status}`);
    const data = await res.json();
    searchIndex = (data.v || []).map((row) => {
      const [t, b, c, v, es, s, surf, morph = ""] = row;
      return {
        t,
        b,
        c,
        v,
        es,
        s,
        surf,
        morph,
        esN: normalizeText(es),
        sN: String(s || "").toUpperCase(),
        surfN: normalizeText(surf),
        morphN: String(morph || "").toUpperCase().replace(/\s+/g, " "),
      };
    });
    return searchIndex;
  })();
  try {
    return await searchIndexPromise;
  } catch (err) {
    searchIndexPromise = null;
    throw err;
  }
}

function searchFields() {
  return {
    es: els.searchEs.checked,
    strongs: els.searchStrongs.checked,
    morph: els.searchMorph.checked,
    surface: els.searchSurface.checked,
  };
}

function clauseMatchesRow(row, clause, fields) {
  if (fields.es && fieldMatch(row.esN, clause.es, clause.phrase)) return true;
  if (fields.strongs && strongsMatch(row.sN, clause, clause.phrase)) return true;
  if (fields.morph && morphMatch(row.morphN.replace(/ /g, ""), clause)) return true;
  // Also allow morph substring with slashes kept: search HR/Ncfsa in "HR/NCFSA HVQP3MS"
  if (fields.morph && clause.morph && row.morphN.includes(clause.morph)) return true;
  if (fields.surface && fieldMatch(row.surfN, clause.surface, clause.phrase)) return true;
  return false;
}

function rowMatches(row, clauses, fields) {
  return clauses.every((clause) => clauseMatchesRow(row, clause, fields));
}

function scopeFilter(row) {
  const scope = els.searchScope.value;
  if (scope === "all") return true;
  if (scope === "testament") return row.t === els.testament.value;
  return row.t === els.testament.value && row.b === els.book.value;
}

function snippetAround(text, term, radius = 42) {
  const hay = text;
  const needle = term;
  const idx = normalizeText(hay).indexOf(needle);
  if (idx < 0) {
    return hay.length > 110 ? `${hay.slice(0, 110)}…` : hay;
  }
  // Approximate using original string length (close enough for display).
  const start = Math.max(0, idx - radius);
  const end = Math.min(hay.length, idx + needle.length + radius);
  let out = hay.slice(start, end);
  if (start > 0) out = `…${out}`;
  if (end < hay.length) out = `${out}…`;
  return out;
}

function resultSnippet(row, clauses, fields) {
  const first = clauses[0];
  if (fields.morph && first?.morph) {
    return row.morph.slice(0, 110) + (row.morph.length > 110 ? "…" : "");
  }
  if (fields.es && first?.es) return snippetAround(row.es, first.es);
  if (fields.strongs && first?.strongs) return row.es.slice(0, 110) + (row.es.length > 110 ? "…" : "");
  if (fields.surface && first?.surface) return snippetAround(row.surf, first.surface);
  return row.es.slice(0, 110) + (row.es.length > 110 ? "…" : "");
}

function bookLabel(slug) {
  return bookLabels.get(slug) || slug;
}

function renderSearchResults(hits, clauses, fields, total) {
  els.searchResults.innerHTML = "";
  if (!hits.length) {
    els.searchMeta.textContent = "Sin resultados.";
    return;
  }
  els.searchMeta.textContent =
    total > hits.length
      ? `${total} versículos · mostrando ${hits.length}`
      : `${total} versículo${total === 1 ? "" : "s"}`;

  const frag = document.createDocumentFragment();
  for (const row of hits) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "search-hit";
    const label = `${bookLabel(row.b)} ${row.c}:${row.v}`;
    const snip = resultSnippet(row, clauses, fields);
    btn.innerHTML = `<span class="hit-ref">${label}</span><span class="hit-snip"></span>`;
    btn.querySelector(".hit-snip").textContent = snip;
    btn.addEventListener("click", () => openSearchHit(row, clauses, fields));
    frag.appendChild(btn);
  }
  els.searchResults.appendChild(frag);
}

async function openSearchHit(row, clauses, fields) {
  pendingHighlight = { clauses, fields };
  pendingVerse = row.v;
  els.testament.value = row.t;
  syncBookOptions(row.b);
  syncChapterOptions(row.c);
  els.searchClear.hidden = false;
  await loadChapter();
}

async function runSearch(event) {
  event?.preventDefault();
  const query = els.searchInput.value.trim();
  const fields = searchFields();
  if (!query) return;

  const ref = parseReference(query);
  if (ref) {
    els.searchHeading.textContent = `“${query}”`;
    await goToReference(ref);
    return;
  }

  if (!fields.es && !fields.strongs && !fields.morph && !fields.surface) {
    els.searchMeta.textContent = "Activa al menos un campo: Español, Strong's, Morph u Original.";
    showSearchPanel();
    return;
  }

  const clauses = parseQuery(query);
  if (!clauses.length) return;

  showSearchPanel();
  els.searchHeading.textContent = `“${query}”`;
  els.searchResults.innerHTML = "";
  els.searchClear.hidden = false;
  els.searchBtn.disabled = true;

  try {
    const index = await ensureSearchIndex();
    const hits = [];
    for (const row of index) {
      if (!scopeFilter(row)) continue;
      if (!rowMatches(row, clauses, fields)) continue;
      hits.push(row);
    }
    hits.sort(compareCanon);
    const total = hits.length;
    renderSearchResults(hits.slice(0, RESULT_LIMIT), clauses, fields, total);
  } catch (err) {
    els.searchMeta.textContent =
      `No se pudo cargar el índice. Ejecuta: python3 scripts/build_reader_catalog.py (${err.message})`;
  } finally {
    els.searchBtn.disabled = false;
  }
}

function clearSearch() {
  els.searchInput.value = "";
  els.searchClear.hidden = true;
  pendingHighlight = null;
  hideSearchPanel();
  els.searchResults.innerHTML = "";
  els.searchMeta.textContent = "";
  loadChapter();
}

function buildBookLabelMap() {
  bookLabels = new Map();
  bookOrder = new Map();
  bookAliases = [];
  let i = 0;
  for (const t of catalog.testaments) {
    for (const b of t.books) {
      bookLabels.set(b.slug, b.label);
      bookOrder.set(`${t.code}:${b.slug}`, i);
      // Numbered books: accept "1 Reyes", "1reyes", "1 reyes"
      const spacedSlug = b.slug.replace(/^(\d)(?=[a-z])/, "$1 ");
      const aliases = new Set([
        normalizeText(b.label),
        normalizeText(b.slug),
        normalizeText(spacedSlug),
      ]);
      for (const alias of aliases) {
        if (alias) bookAliases.push({ alias, t: t.code, slug: b.slug });
      }
      i += 1;
    }
  }
  // Longest alias first so "1 juan" wins over "juan"
  bookAliases.sort((a, b) => b.alias.length - a.alias.length || a.alias.localeCompare(b.alias));
}

function compareCanon(a, b) {
  const ao = bookOrder.get(`${a.t}:${a.b}`) ?? 9999;
  const bo = bookOrder.get(`${b.t}:${b.b}`) ?? 9999;
  if (ao !== bo) return ao - bo;
  if (a.c !== b.c) return a.c - b.c;
  return a.v - b.v;
}

/** Parse "1 Reyes 8:27", "2juan", "1 Samuel 3" — numbered books included. */
function parseReference(query) {
  const n = normalizeText(query);
  if (!n) return null;
  for (const entry of bookAliases) {
    if (n === entry.alias) {
      return { t: entry.t, slug: entry.slug, c: 1, v: null, wholeBook: true };
    }
    if (!n.startsWith(`${entry.alias} `)) continue;
    const rest = n.slice(entry.alias.length).trim();
    const m = rest.match(/^(\d+)(?:\s*[:.]\s*(\d+))?$/);
    if (!m) continue;
    return {
      t: entry.t,
      slug: entry.slug,
      c: Number(m[1]),
      v: m[2] ? Number(m[2]) : null,
      wholeBook: false,
    };
  }
  return null;
}

async function goToReference(ref) {
  els.testament.value = ref.t;
  syncBookOptions(ref.slug);
  syncChapterOptions(ref.c);
  pendingVerse = ref.v;
  pendingHighlight = null;
  els.searchClear.hidden = false;
  hideSearchPanel();
  await loadChapter();
}

async function init() {
  try {
    const res = await fetch("catalog.json");
    if (!res.ok) throw new Error(`catalog.json HTTP ${res.status}`);
    catalog = await res.json();
  } catch (err) {
    els.heading.textContent = "BLE Interlinear";
    showStatus(
      `No se pudo cargar catalog.json. Desde Biblia-BLE ejecuta: python3 scripts/build_reader_catalog.py && python3 -m http.server 8765 — luego abre http://localhost:8765/reader/ (${err.message})`
    );
    return;
  }

  buildBookLabelMap();

  fillSelect(
    els.testament,
    catalog.testaments,
    (t) => t.code,
    (t) => (t.code === "OT" ? "Antiguo Testamento" : "Nuevo Testamento"),
    "OT"
  );

  const hadHash = applyHash();
  if (!hadHash) {
    syncBookOptions("genesis");
    syncChapterOptions(1);
  }

  els.testament.addEventListener("change", () => {
    pendingHighlight = null;
    pendingVerse = null;
    syncBookOptions();
    loadChapter();
  });
  els.book.addEventListener("change", () => {
    pendingHighlight = null;
    pendingVerse = null;
    syncChapterOptions();
    loadChapter();
  });
  els.chapter.addEventListener("change", () => {
    pendingHighlight = null;
    pendingVerse = null;
    loadChapter();
  });
  els.prev.addEventListener("click", () => stepChapter(-1));
  els.next.addEventListener("click", () => stepChapter(1));
  els.detailClose.addEventListener("click", closeDetail);
  els.showMorph.addEventListener("change", rerenderVisibleMeta);
  els.showStrongs.addEventListener("change", rerenderVisibleMeta);
  els.showLemma.addEventListener("change", rerenderVisibleMeta);
  els.searchForm.addEventListener("submit", runSearch);
  els.searchClear.addEventListener("click", clearSearch);
  els.searchClose.addEventListener("click", () => {
    hideSearchPanel();
  });
  window.addEventListener("popstate", () => {
    suppressHashPush = true;
    applyHash();
    loadChapter();
  });

  await loadChapter();
}

init();
