/* LTC WATCH — interactions: count-up numbers + live board filter. */
(function () {
  // count-up for [data-count] tiles (interval-based; rAF is throttled in
  // some contexts, so a final hard-set guarantees the true value lands)
  function countUp(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    var t0 = Date.now();
    var iv = setInterval(function () {
      var p = Math.min(1, (Date.now() - t0) / 800);
      el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString();
      if (p >= 1) clearInterval(iv);
    }, 40);
    setTimeout(function () {
      clearInterval(iv);
      el.textContent = target.toLocaleString();
    }, 950);
  }
  document.querySelectorAll("[data-count]").forEach(countUp);

  // live filter on the board
  var filter = document.getElementById("filter");
  var rows = document.querySelectorAll("#board tbody tr.row");
  if (filter && rows.length) {
    filter.addEventListener("input", function () {
      var q = filter.value.trim().toLowerCase();
      rows.forEach(function (r) {
        r.classList.toggle("hidden", q && !r.textContent.toLowerCase().includes(q));
      });
    });
  }
})();
