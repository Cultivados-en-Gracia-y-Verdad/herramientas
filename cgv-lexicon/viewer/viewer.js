const GREEK_LETTERS = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ".split("");
const HEBREW_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת".split("");

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  for (const child of children) {
    if (typeof child === "string") node.appendChild(document.createTextNode(child));
    else if (child) node.appendChild(child);
  }
  return node;
}

function section(title, bodyChildren) {
  return el("section", {}, [
    el("h2", { text: title }),
    ...(Array.isArray(bodyChildren) ? bodyChildren : [bodyChildren]),
  ]);
}

function tableFromRows(headers, rows) {
  const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", { text: h })))]);
  const tbody = el("tbody", {}, rows.map((cells) =>
    el("tr", {}, cells.map((c) => el("td", { text: String(c ?? "") })))
  ));
  return el("table", {}, [thead, tbody]);
}

function setSubtitle(text) {
  const sub = document.getElementById("page-subtitle");
  if (sub) sub.textContent = text;
}

function setActiveLang(lang) {
  document.querySelectorAll(".lang-nav a").forEach((a) => {
    a.classList.toggle("active", a.dataset.lang === lang);
  });
}

function firstLetter(lemma, lang) {
  const stripped = lemma.replace(/^[\s⸀\-—·]+/, "");
  for (const ch of stripped) {
    if (lang === "hebrew" && /[\u0590-\u05FF]/.test(ch)) return ch;
    if (lang === "greek" && /\p{L}/u.test(ch)) {
      const base = ch.normalize("NFD").replace(/\p{M}/gu, "");
      return base.toLowerCase();
    }
  }
  return "#";
}

function groupByLetter(lemmas, lang) {
  const groups = new Map();
  for (const item of lemmas) {
    const letter = firstLetter(item.lemma, lang);
    if (!groups.has(letter)) groups.set(letter, []);
    groups.get(letter).push(item);
  }
  for (const list of groups.values()) {
    list.sort((a, b) => a.lemma.localeCompare(b.lemma, lang === "hebrew" ? "he" : "el"));
  }
  return groups;
}

function letterBar(lang, groups, activeLetter, basePath) {
  const alphabet = lang === "hebrew" ? HEBREW_LETTERS : GREEK_LETTERS.map((l) => l.toLowerCase());
  const links = [
    el("a", {
      href: basePath,
      className: activeLetter ? "" : "active",
      text: "All",
    }),
  ];
  for (const letter of alphabet) {
    const has = groups.has(letter);
    links.push(el("a", {
      href: `${basePath}?letter=${encodeURIComponent(letter)}`,
      className: `${activeLetter === letter ? "active" : ""} ${has ? "" : "disabled"}`.trim(),
      text: letter,
    }));
  }
  if (groups.has("#")) {
    links.push(el("a", {
      href: `${basePath}?letter=%23`,
      className: activeLetter === "#" ? "active" : "",
      text: "#",
    }));
  }
  return el("nav", { className: "letter-bar", "aria-label": "Browse by letter" }, links);
}

function renderLemmaGrid(items, lang, buildHref) {
  return el("div", { className: "lemma-grid" }, items.map((item) => {
    const meta = lang === "greek"
      ? `${item.occurrences}×`
      : [item.strongs, item.gloss_es].filter(Boolean).join(" · ");
    return el("a", { href: buildHref(item.lemma) }, [
      document.createTextNode(item.lemma),
      el("span", { className: "meta", text: ` ${meta}` }),
    ]);
  }));
}

async function fetchJson(url) {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.error || res.statusText;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

function renderHome() {
  setSubtitle("Observation Layer");
  setActiveLang("");
  const root = document.getElementById("content");
  root.replaceChildren(
    el("div", { className: "browse-header" }, [
      el("p", { className: "layer-label", text: "Observation Layer" }),
      el("p", { text: "Browse how lemmas appear in the biblical text — no definitions in Phase 1." }),
    ]),
    el("div", { className: "lang-cards" }, [
      el("a", { href: "/lexicon/greek", className: "lang-card" }, [
        el("h2", { text: "Greek" }),
        el("p", { text: "NT verb observations (Phase 1)" }),
      ]),
      el("a", { href: "/lexicon/hebrew", className: "lang-card" }, [
        el("h2", { text: "Hebrew" }),
        el("p", { text: "Lemma index with gloss lookup (observation layer coming)" }),
      ]),
    ])
  );
}

async function renderGreekBrowse(letter) {
  setSubtitle("Greek — NT verbs");
  setActiveLang("greek");
  const root = document.getElementById("content");
  root.replaceChildren(el("p", { text: "Loading Greek index…" }));

  try {
    const index = await fetchJson("/api/lexicon/greek/index");
    const lemmas = index.lemmas || [];
    const groups = groupByLetter(lemmas, "greek");
    const active = letter || null;
    const shown = active ? (groups.get(active) || []) : lemmas.slice().sort((a, b) => a.lemma.localeCompare(b.lemma, "el"));

    root.replaceChildren(
      el("a", { href: "/lexicon", className: "back-link", text: "← All languages" }),
      el("div", { className: "browse-header" }, [
        el("p", { className: "layer-label", text: "Observation Layer" }),
        el("h2", { className: "lemma-title", text: active ? `Greek — ${active}` : "Greek verbs" }),
        el("p", { text: `${shown.length} of ${lemmas.length} lemmas` }),
      ]),
      letterBar("greek", groups, active, "/lexicon/greek"),
      renderLemmaGrid(shown, "greek", (lemma) => `/lexicon/greek/${encodeURIComponent(lemma)}`)
    );
    document.title = "Greek — ROOTS Lexicon";
  } catch (err) {
    root.replaceChildren(
      el("div", { className: "notice error" }, [
        el("strong", { text: "Cannot load Greek data" }),
        el("p", { text: err.message }),
        el("p", { html: "From <code>cgv-lexicon</code> run: <code>npm run build:lexicon-phase1</code> then <code>npm run serve:lexicon</code>" }),
      ])
    );
  }
}

async function renderHebrewBrowse(letter) {
  setSubtitle("Hebrew — lemma index");
  setActiveLang("hebrew");
  const root = document.getElementById("content");
  root.replaceChildren(el("p", { text: "Loading Hebrew index…" }));

  try {
    const index = await fetchJson("/api/lexicon/hebrew/index");
    const lemmas = index.lemmas || [];
    const groups = groupByLetter(lemmas, "hebrew");
    const active = letter || null;
    const shown = active ? (groups.get(active) || []) : lemmas.slice().sort((a, b) => a.lemma.localeCompare(b.lemma, "he"));

    root.replaceChildren(
      el("a", { href: "/lexicon", className: "back-link", text: "← All languages" }),
      el("div", { className: "notice" }, [
        el("strong", { text: "Hebrew Phase 1 not built yet" }),
        el("p", { text: "This list shows gloss + Strong's lookup only. Observation data (forms, occurrences, collocations) will appear here when Hebrew Phase 1 is generated." }),
      ]),
      el("div", { className: "browse-header" }, [
        el("p", { className: "layer-label", text: "Lemma index" }),
        el("h2", { className: "lemma-title hebrew", text: active ? `Hebrew — ${active}` : "Hebrew lemmas" }),
        el("p", { text: `${shown.length} of ${lemmas.length} lemmas` }),
      ]),
      letterBar("hebrew", groups, active, "/lexicon/hebrew"),
      renderLemmaGrid(shown, "hebrew", (lemma) => `/lexicon/hebrew/${encodeURIComponent(lemma)}`)
    );
    document.title = "Hebrew — ROOTS Lexicon";
  } catch (err) {
    root.replaceChildren(
      el("div", { className: "notice error" }, [
        el("strong", { text: "Cannot load Hebrew data" }),
        el("p", { text: err.message }),
        el("p", { html: "Run: <code>npm run build:lexicon</code> then <code>npm run serve:lexicon</code>" }),
      ])
    );
  }
}

function renderGreekObservation(data) {
  const root = document.getElementById("content");
  const input = document.getElementById("lemma-input");
  if (input) input.value = data.lemma;
  setSubtitle("Greek — observation");
  setActiveLang("greek");

  root.replaceChildren(
    el("a", { href: "/lexicon/greek", className: "back-link", text: "← Greek index" }),
    el("p", { className: "layer-label", text: "Observation Layer" }),
    el("h2", { className: "lemma-title greek", text: data.lemma }),
    el("p", { text: `${data.total_occurrences} occurrences in the Greek NT` })
  );

  const append = (node) => root.appendChild(node);

  append(section("Forms", [
    tableFromRows(["Form", "Count"], (data.forms || []).slice(0, 30).map((f) => [f.form, f.count])),
  ]));

  const morph = data.morphology_summary || {};
  if (morph.moods) {
    const lines = [];
    for (const [k, label] of [["moods", "Moods"], ["tenses", "Tenses"], ["voices", "Voices"]]) {
      const obj = morph[k];
      if (!obj) continue;
      lines.push(el("p", {}, [
        el("strong", { text: `${label}: ` }),
        document.createTextNode(Object.entries(obj).map(([n, c]) => `${n} (${c})`).join(", ")),
      ]));
    }
    append(section("Morphology summary", lines));
  }

  append(section("Books", [
    el("ul", { className: "compact" }, Object.entries(data.books || {}).map(([b, c]) =>
      el("li", { text: `${b}: ${c}` })
    )),
  ]));

  if ((data.collocations || []).length) {
    append(section("Collocations", [
      tableFromRows(["Lemma", "Display", "Count"], data.collocations.map((c) => [c.lemma, c.display, c.count])),
    ]));
  }
  if ((data.commands || []).length) {
    append(section("Commands", [
      tableFromRows(["Reference", "Form", "Clause"], data.commands.map((c) => [c.ref, c.form, c.clause_text])),
    ]));
  }
  if ((data.negated_uses || []).length) {
    append(section("Negated uses", [
      tableFromRows(["Reference", "Negator", "Clause"], data.negated_uses.map((n) => [n.ref, n.negator, n.clause_text])),
    ]));
  }
  if ((data.representative_passages || []).length) {
    append(section("Representative passages", [
      el("ul", { className: "compact" }, data.representative_passages.map((p) =>
        el("li", {}, [el("strong", { text: p.ref }), document.createTextNode(` — ${p.reason}`)])
      )),
    ]));
  }
  append(section("All occurrences", [
    tableFromRows(
      ["Reference", "Form", "Morph", "Left context", "Right context"],
      (data.references || []).map((r) => [r.ref, r.form, r.morph, r.left_context, r.right_context])
    ),
  ]));
  document.title = `${data.lemma} — ROOTS Lexicon`;
}

function renderHebrewGloss(data) {
  const root = document.getElementById("content");
  const input = document.getElementById("lemma-input");
  if (input) input.value = data.lemma;
  setSubtitle("Hebrew — gloss lookup");
  setActiveLang("hebrew");

  root.replaceChildren(
    el("a", { href: "/lexicon/hebrew", className: "back-link", text: "← Hebrew index" }),
    el("div", { className: "notice" }, [
      el("strong", { text: "Observation layer not available" }),
      el("p", { text: "Hebrew Phase 1 has not been built. Below is gloss lookup only — not a definition from Phase 2." }),
    ]),
    el("p", { className: "layer-label", text: "Gloss lookup (temporary)" }),
    el("h2", { className: "lemma-title hebrew", text: data.lemma }),
    el("p", { text: data.strongs ? `Strong's ${data.strongs}` : "No Strong's number" }),
    el("p", { text: data.gloss_es ? `Spanish gloss: ${data.gloss_es}` : "No gloss in lexicon rules" })
  );
  document.title = `${data.lemma} — ROOTS Lexicon`;
}

async function loadGreekLemma(lemma) {
  const root = document.getElementById("content");
  root.replaceChildren(el("p", { text: "Loading…" }));
  try {
    const data = await fetchJson(`/api/lexicon/greek/${encodeURIComponent(lemma)}`);
    renderGreekObservation(data);
  } catch (err) {
    root.replaceChildren(
      el("div", { className: "notice error" }, [
        el("strong", { text: `Lemma not found: ${lemma}` }),
        el("p", { text: err.message }),
        el("p", { html: `<a href="/lexicon/greek">Browse the Greek index</a>` }),
      ])
    );
  }
}

async function loadHebrewLemma(lemma) {
  const root = document.getElementById("content");
  root.replaceChildren(el("p", { text: "Loading…" }));
  try {
    const data = await fetchJson(`/api/lexicon/hebrew/${encodeURIComponent(lemma)}`);
    renderHebrewGloss(data);
  } catch (err) {
    root.replaceChildren(
      el("div", { className: "notice error" }, [
        el("strong", { text: `Lemma not found: ${lemma}` }),
        el("p", { text: err.message }),
        el("p", { html: `<a href="/lexicon/hebrew">Browse the Hebrew index</a>` }),
      ])
    );
  }
}

function route() {
  const params = new URLSearchParams(location.search);
  const letter = params.get("letter") ? decodeURIComponent(params.get("letter")) : null;
  const path = decodeURIComponent(location.pathname).replace(/\/+$/, "") || "/";

  if (path === "/" || path === "/lexicon") {
    renderHome();
    return;
  }
  if (path === "/lexicon/greek") {
    renderGreekBrowse(letter);
    return;
  }
  if (path === "/lexicon/hebrew") {
    renderHebrewBrowse(letter);
    return;
  }

  const greekLemma = path.match(/^\/lexicon\/greek\/(.+)$/);
  if (greekLemma) {
    loadGreekLemma(decodeURIComponent(greekLemma[1]));
    return;
  }
  const hebrewLemma = path.match(/^\/lexicon\/hebrew\/(.+)$/);
  if (hebrewLemma) {
    loadHebrewLemma(decodeURIComponent(hebrewLemma[1]));
    return;
  }

  renderHome();
}

window.goLemma = function goLemma(event) {
  event.preventDefault();
  const lemma = document.getElementById("lemma-input").value.trim();
  if (!lemma) return false;
  const path = decodeURIComponent(location.pathname);
  const lang = path.includes("/hebrew") ? "hebrew" : "greek";
  location.href = `/lexicon/${lang}/${encodeURIComponent(lemma)}`;
  return false;
};

window.addEventListener("popstate", route);
route();
