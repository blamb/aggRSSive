/* Heart-Cart: pick sources across pages, then make an aggRSSive out of them. */
(function () {
  var KEY = "aggrssive-cart";
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  function save(c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) {} render(); }
  var cart = load();

  var box = document.getElementById("cart"), list = document.getElementById("cart-list"), count = document.getElementById("cart-count");
  var newForm = document.getElementById("cart-new"), addForm = document.getElementById("cart-add"), sel = document.getElementById("cart-bundle");

  function hidden(form, ids) {
    form.querySelectorAll("input[name=source_ids]").forEach(function (e) { e.remove(); });
    ids.forEach(function (id) { var i = document.createElement("input"); i.type = "hidden"; i.name = "source_ids"; i.value = id; form.appendChild(i); });
  }

  function render() {
    if (!box) return;
    var ids = Object.keys(cart);
    box.hidden = ids.length === 0;
    count.textContent = ids.length;
    list.innerHTML = "";
    ids.forEach(function (id) {
      var li = document.createElement("li"); li.textContent = cart[id] + " ";
      var x = document.createElement("button"); x.className = "link"; x.textContent = "×"; x.onclick = function () { delete cart[id]; save(cart); sync(); };
      li.appendChild(x); list.appendChild(li);
    });
    if (newForm) hidden(newForm, ids);
    if (addForm) hidden(addForm, ids);
    document.querySelectorAll(".cart-check").forEach(function (cb) { cb.checked = !!cart[cb.dataset.id]; });
  }
  function sync() { render(); }

  document.addEventListener("change", function (e) {
    var cb = e.target;
    if (!cb.classList || !cb.classList.contains("cart-check")) return;
    if (cb.checked) cart[cb.dataset.id] = cb.dataset.title; else delete cart[cb.dataset.id];
    save(cart);
  });

  var all = document.getElementById("cart-all");
  if (all) all.onclick = function () { document.querySelectorAll(".cart-check").forEach(function (cb) { cart[cb.dataset.id] = cb.dataset.title; }); save(cart); };

  var clear = document.getElementById("cart-clear");
  if (clear) clear.onclick = function () { cart = {}; save(cart); };

  if (sel && window.MY_BUNDLES) {
    window.MY_BUNDLES.forEach(function (slug, i) { var o = document.createElement("option"); o.value = slug; o.textContent = window.MY_BUNDLE_TITLES[i]; sel.appendChild(o); });
    addForm.onsubmit = function (e) { if (!sel.value) { e.preventDefault(); return; } addForm.action = "/bundles/" + sel.value + "/sources"; };
  } else if (addForm) { addForm.hidden = true; }

  if (newForm) newForm.addEventListener("submit", function () { setTimeout(function () { cart = {}; save(cart); }, 0); });
  if (addForm) addForm.addEventListener("submit", function () { setTimeout(function () { cart = {}; save(cart); }, 0); });

  render();

  /* Tag suggestions: click to append to the nearest tag input */
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest(".tag-suggest");
    if (!a) return;
    e.preventDefault();
    var input = document.querySelector(".tag-input");
    if (!input) return;
    var cur = input.value.trim();
    input.value = cur ? cur.replace(/,\s*$/, "") + ", " + a.dataset.tag : a.dataset.tag;
    input.focus();
  });
})();
