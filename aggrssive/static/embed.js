/* aggRSSive embed. Feed2JS for the 2020s. Placeholders are filled in by the server. */
(function () {
  var BASE = "__BASE__", SLUG = "__SLUG__";
  var s = document.currentScript;
  var d = (s && s.dataset) || {};
  var n = parseInt(d.n || "10", 10) || 10;
  var showDesc = d.desc !== "0", fullDesc = d.desc === "full", showImg = d.img !== "0", showSrc = d.src !== "0", showDate = d.date !== "0";
  var theme = d.theme || "light";

  var root;
  if (d.target) root = document.querySelector(d.target);
  if (!root) { root = document.createElement("div"); s.parentNode.insertBefore(root, s.nextSibling); }
  root.className = "aggrssive aggrssive-" + theme;

  if (!document.getElementById("aggrssive-css")) {
    var css = document.createElement("style");
    css.id = "aggrssive-css";
    css.textContent =
      ".aggrssive{--ag-fg:#1b1b1b;--ag-muted:#666;--ag-link:#0b5fa5;--ag-line:#e5e5e5;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ag-fg)}" +
      ".aggrssive-dark{--ag-fg:#eee;--ag-muted:#aaa;--ag-link:#8ab4f8;--ag-line:#333}" +
      "@media (prefers-color-scheme:dark){.aggrssive-auto{--ag-fg:#eee;--ag-muted:#aaa;--ag-link:#8ab4f8;--ag-line:#333}}" +
      ".aggrssive ul{list-style:none;margin:0;padding:0}.aggrssive li{padding:10px 0;border-bottom:1px solid var(--ag-line);display:grid;grid-template-columns:auto 1fr;gap:10px}.aggrssive li:last-child{border:0}" +
      ".aggrssive a{color:var(--ag-link);text-decoration:none}.aggrssive a:hover{text-decoration:underline}.aggrssive .ag-t{font-weight:600}.aggrssive .ag-m{color:var(--ag-muted);font-size:.85em}" +
      ".aggrssive .ag-d{margin-top:4px;font-size:.92em}.aggrssive .ag-d img{max-width:100%;height:auto}.aggrssive img.ag-th{width:72px;height:72px;object-fit:cover;border-radius:6px}" +
      ".aggrssive .ag-note{font-style:italic;color:var(--ag-muted);font-size:.9em;margin:2px 0}.aggrssive .ag-foot{margin-top:8px;font-size:.75em;color:var(--ag-muted)}";
    document.head.appendChild(css);
  }

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fmt(iso) { if (!iso) return ""; var dt = new Date(iso); return isNaN(dt) ? "" : dt.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }

  var xhr = new XMLHttpRequest();
  xhr.open("GET", BASE + "/b/" + SLUG + ".json?n=" + n);
  xhr.onload = function () {
    var data; try { data = JSON.parse(xhr.responseText); } catch (e) { root.textContent = "aggRSSive: could not load."; return; }
    var ul = el("ul");
    (data.items || []).forEach(function (it) {
      var li = el("li");
      if (showImg && it.image) { var a = el("a"); a.href = it.url; var im = el("img", "ag-th"); im.src = it.image; im.alt = ""; im.loading = "lazy"; a.appendChild(im); li.appendChild(a); } else { li.appendChild(el("span")); }
      var box = el("div");
      var t = el("a", "ag-t", it.title || it.url); t.href = it.url; t.target = "_blank"; t.rel = "noopener"; box.appendChild(t);
      var meta = []; if (showSrc && it.source && it.source.title) meta.push(it.source.title); if (showDate) meta.push(fmt(it.published));
      if (meta.length) box.appendChild(el("div", "ag-m", meta.filter(Boolean).join(" · ")));
      if (it.note) box.appendChild(el("p", "ag-note", it.note));
      if (showDesc && fullDesc && it.summary) { var dd = el("div", "ag-d"); dd.innerHTML = it.summary; /* sanitized server-side */ box.appendChild(dd); }
      else if (showDesc && it.excerpt) { box.appendChild(el("div", "ag-d", it.excerpt)); }
      li.appendChild(box); ul.appendChild(li);
    });
    root.innerHTML = ""; root.appendChild(ul);
    var f = el("div", "ag-foot"); var fa = el("a", null, data.title || "aggRSSive"); fa.href = data.url; fa.target = "_blank"; f.appendChild(fa); f.appendChild(document.createTextNode(" · via aggRSSive")); root.appendChild(f);
  };
  xhr.onerror = function () { root.textContent = "aggRSSive: could not load."; };
  xhr.send();
})();
