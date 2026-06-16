const API = "https://web-production-38abb.up.railway.app";
let allData      = [];
let sortKey      = "ticker";
let sortAsc      = true;
let betaChart    = null;
let sectorChart  = null;
let returnsChart = null;
let rollingChart = null;

// ── Market events with exact real-world date ranges ────────────
// These dates are compared directly against the rolling chart's
// x-axis dates (which are the END dates of each 5-year window),
// so the colored segments appear at the correct real-world moment.
const MARKET_EVENTS = [
  {
    label: "2008 Financial Crisis",
    start: "2007-12-01",
    end:   "2009-06-30",
    color: "#f85149",
    cls:   "crisis"
  },
  {
    label: "COVID-19",
    start: "2019-11-01",
    end:   "2023-05-31",
    color: "#d29922",
    cls:   "covid"
  },
  {
    label: "Rate hike cycle",
    start: "2022-03-01",
    end:   "2023-07-31",
    color: "#9e6bdb",
    cls:   "rate"
  },
  {
    label: "Recession fears",
    start: "2025-01-01",
    end:   "2099-12-31",
    color: "#3fb950",
    cls:   "recession"
  },
  {
    label: "2026 Oil War",
    start: "2026-02-01",
    end:   "2099-12-31",
    color: "#f97316",
    cls:   "oilwar"
  }
];

// Returns the color for a given date string and point index.
// Handles the COVID + Rate hike overlap by alternating colors.
// For all other overlaps, the event that appears first in
// MARKET_EVENTS (highest priority) wins.
function getSegmentColor(dateStr, pointIndex) {
  const active = MARKET_EVENTS.filter(ev =>
    dateStr >= ev.start && dateStr <= ev.end
  );
  if (!active.length) return "#388bfd";

  const isCovid = active.find(e => e.label === "COVID-19");
  const isRate  = active.find(e => e.label === "Rate hike cycle");

  if (isCovid && isRate) {
    return pointIndex % 2 === 0 ? isCovid.color : isRate.color;
  }

  // Highest priority = lowest index in MARKET_EVENTS array
  return active.reduce((prev, curr) =>
    MARKET_EVENTS.indexOf(prev) < MARKET_EVENTS.indexOf(curr) ? prev : curr
  ).color;
}

// Returns active event labels for a date (used in tooltip)
function getActiveEvents(dateStr) {
  return MARKET_EVENTS
    .filter(ev => dateStr >= ev.start && dateStr <= ev.end)
    .map(ev => ev.label);
}

// ── MAIN VIEW ─────────────────────────────────────────────────

async function loadAll() {
  const btn = document.getElementById("loadBtn");
  btn.textContent = "Loading...";
  btn.disabled    = true;
  document.getElementById("tableBody").innerHTML =
    '<tr><td colspan="8" style="text-align:center;padding:40px;color:#8b949e;">' +
    'Fetching 5 years of monthly data from Yahoo Finance — this takes about 60–90 seconds...</td></tr>';

  try {
    const res = await fetch(`${API}/beta`);
    if (!res.ok) throw new Error("API returned " + res.status);
    allData = await res.json();
    renderSummary(allData);
    renderBetaChart(allData);
    renderSectorChart(allData);
    renderTable(allData);
    document.getElementById("timestamp").textContent =
      "Updated: " + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById("tableBody").innerHTML =
      `<tr><td colspan="8" style="text-align:center;padding:40px;color:#f85149;">
        Error: ${e.message}. Make sure the API is running.
      </td></tr>`;
  }

  btn.textContent = "Reload";
  btn.disabled    = false;
}

function avg(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function renderSummary(data) {
  const betas  = data.map(d => d.beta_calc).filter(v => v != null);
  const deltas = data.map(d => d.delta).filter(v => v != null);
  const sorted = [...data].sort((a, b) => (b.beta_calc || 0) - (a.beta_calc || 0));
  document.getElementById("s-count").textContent   = data.length;
  document.getElementById("s-avgbeta").textContent = avg(betas).toFixed(3);
  document.getElementById("s-delta").textContent   = avg(deltas).toFixed(4);
  document.getElementById("s-high").textContent    =
    sorted[0].ticker + " (" + sorted[0].beta_calc + ")";
  document.getElementById("s-low").textContent     =
    sorted[sorted.length - 1].ticker + " (" + sorted[sorted.length - 1].beta_calc + ")";
}

function renderBetaChart(data) {
  const sorted = [...data].sort((a, b) => (b.beta_calc || 0) - (a.beta_calc || 0));
  if (betaChart) betaChart.destroy();
  betaChart = new Chart(document.getElementById("betaChart"), {
    type: "bar",
    data: {
      labels: sorted.map(d => d.ticker),
      datasets: [
        {
          label: "Beta (our calculation)",
          data:  sorted.map(d => d.beta_calc),
          backgroundColor: "#388bfd", borderRadius: 2
        },
        {
          label: "Beta (Yahoo Finance)",
          data:  sorted.map(d => d.beta_yahoo),
          backgroundColor: "#f8514966", borderRadius: 2
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: true, labels: { color: "#8b949e", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            afterBody: (items) => "Delta: " + (sorted[items[0].dataIndex].delta ?? "—")
          }
        }
      },
      scales: {
        x: { ticks: { color: "#8b949e", font: { size: 9 } }, grid: { color: "#21262d" } },
        y: {
          ticks: { color: "#8b949e" }, grid: { color: "#21262d" },
          title: { display: true, text: "Beta coefficient", color: "#8b949e" }
        }
      }
    }
  });
}

function renderSectorChart(data) {
  const sectors = {};
  data.forEach(d => {
    if (!d.sector || d.beta_calc == null) return;
    if (!sectors[d.sector]) sectors[d.sector] = [];
    sectors[d.sector].push(d.beta_calc);
  });
  const labels = Object.keys(sectors).sort();
  const avgs   = labels.map(s => parseFloat(avg(sectors[s]).toFixed(3)));
  const colors = avgs.map(v => v > 1.2 ? "#f85149" : v < 0.8 ? "#3fb950" : "#d29922");
  if (sectorChart) sectorChart.destroy();
  sectorChart = new Chart(document.getElementById("sectorChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Avg Beta by sector", data: avgs, backgroundColor: colors, borderRadius: 4 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8b949e" }, grid: { color: "#21262d" } },
        y: { ticks: { color: "#8b949e", font: { size: 11 } }, grid: { color: "#21262d" } }
      }
    }
  });
}

function renderTable(data) {
  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? "";
    const bv = b[sortKey] ?? "";
    if (typeof av === "number") return sortAsc ? av - bv : bv - av;
    return sortAsc
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av));
  });
  document.getElementById("tableBody").innerHTML = sorted.map(d => {
    const bc = d.beta_calc  != null ? d.beta_calc.toFixed(4)  : "—";
    const by = d.beta_yahoo != null ? d.beta_yahoo.toFixed(4) : "—";
    const dl = d.delta      != null ? d.delta.toFixed(4)      : "—";
    const riskClass = d.beta_calc > 1.2 ? "risk-high" : d.beta_calc < 0.8 ? "risk-low" : "risk-mid";
    const riskLabel = d.beta_calc > 1.2 ? "Aggressive" : d.beta_calc < 0.8 ? "Defensive" : "Neutral";
    const deltaClass = d.delta != null && d.delta > 0.3 ? "big-delta" : "";
    return `<tr onclick="openDetail('${d.ticker}')">
      <td><strong>${d.ticker}</strong></td>
      <td>${d.name   || "—"}</td>
      <td>${d.sector || "—"}</td>
      <td class="num">${bc}</td>
      <td class="num">${by}</td>
      <td class="num ${deltaClass}">${dl}</td>
      <td class="${riskClass}">${riskLabel}</td>
      <td><a href="${d.verify_url}" target="_blank" onclick="event.stopPropagation()">View on YF ↗</a></td>
    </tr>`;
  }).join("");
}

function sortBy(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  sortKey = key;
  renderTable(allData);
}

function filterTable() {
  const q = document.getElementById("search").value.toLowerCase();
  renderTable(allData.filter(d =>
    (d.ticker || "").toLowerCase().includes(q) ||
    (d.name   || "").toLowerCase().includes(q) ||
    (d.sector || "").toLowerCase().includes(q)
  ));
}

// ── ROLLING BETA CHART ────────────────────────────────────────
// Uses Chart.js `segment` option to color each line segment based
// on the actual real-world date of the data point — no offset needed.
// The x-axis dates are the END dates of each 5-year calculation window,
// which are real calendar dates that map directly to event date ranges.

function buildRollingChart(rolling) {
  if (rollingChart) rollingChart.destroy();
  if (!rolling.length) return;

  const dates    = rolling.map(r => r.date);
  const betas    = rolling.map(r => r.beta);
  const betaVals = betas.filter(v => v != null);
  const minY     = parseFloat((Math.min(...betaVals, 0) - 0.15).toFixed(2));
  const maxY     = parseFloat((Math.max(...betaVals, 1.5) + 0.15).toFixed(2));

  // Per-point colors for dots
  const pointColors = dates.map((date, i) => getSegmentColor(date, i));

  // Build legend — only include events visible in this stock's date range
  const firstDate     = dates[0] || "";
  const lastDate      = dates[dates.length - 1] || "";
  const visibleEvents = MARKET_EVENTS.filter(ev =>
    ev.start <= lastDate && ev.end >= firstDate
  );

  rollingChart = new Chart(document.getElementById("rollingBetaChart"), {
    type: "line",
    data: {
      labels: dates,
      datasets: [{
        label:            "Rolling 5-year Beta",
        data:             betas,
        borderWidth:      3,
        pointRadius:      4,
        pointHoverRadius: 8,
        pointBackgroundColor: pointColors,
        pointBorderColor:     pointColors,
        fill:             true,
        backgroundColor:  "#388bfd0a",
        tension:          0.35,
        // segment.borderColor colors the LINE between consecutive points.
        // ctx.p1DataIndex is the index of the LATER point in the segment,
        // so we use its date to determine which event was active at that time.
        segment: {
          borderColor: ctx => {
            const i    = ctx.p1DataIndex;
            const date = dates[i] || "";
            return getSegmentColor(date, i);
          }
        }
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "#8b949e",
            font:  { size: 11 },
            usePointStyle: true,
            generateLabels: () => {
              const entries = [{
                text:        "No event",
                strokeStyle: "#388bfd",
                fillStyle:   "#388bfd",
                lineWidth:   3,
                pointStyle:  "line"
              }];
              visibleEvents.forEach(ev => {
                const isOpenEnded = ev.end === "2099-12-31";
                entries.push({
                  text:        ev.label + (isOpenEnded ? " (ongoing)" : ""),
                  strokeStyle: ev.color,
                  fillStyle:   ev.color,
                  lineWidth:   3,
                  pointStyle:  "line"
                });
              });
              return entries;
            }
          }
        },
        tooltip: {
          callbacks: {
            title: ctx => {
              const date   = ctx[0]?.label || "";
              const active = getActiveEvents(date);
              if (active.length) return [date, "Event: " + active.join(" + ")];
              return date;
            },
            label: ctx => {
              const b = ctx.parsed.y;
              const interp =
                b > 1.2 ? "Aggressive — moves more than the market"  :
                b < 0   ? "Inverse — moves opposite the market"      :
                b < 0.8 ? "Defensive — moves less than the market"   :
                          "Neutral — tracks the market";
              return `Beta = ${b.toFixed(4)}  →  ${interp}`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: "#8b949e", font: { size: 10 },
            maxRotation: 45, maxTicksLimit: 16
          },
          grid: { color: "#21262d" }
        },
        y: {
          min: minY,
          max: maxY,
          ticks: { color: "#8b949e", callback: v => "β " + v.toFixed(2) },
          grid:  { color: "#21262d" },
          title: { display: true, text: "Beta coefficient", color: "#8b949e" }
        }
      }
    }
  });
}

// ── DETAIL VIEW ───────────────────────────────────────────────

function showMain() {
  document.getElementById("mainView").style.display   = "block";
  document.getElementById("detailView").style.display = "none";
}

async function openDetail(ticker) {
  document.getElementById("mainView").style.display   = "none";
  document.getElementById("detailView").style.display = "block";
  window.scrollTo(0, 0);

  // Reset fields
  ["d-ticker","d-name","d-beta-calc","d-beta-yahoo","d-delta",
   "d-risk","d-price","d-marketcap","d-high52","d-low52","d-beta-big"
  ].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "Loading..."; });
  document.getElementById("d-analysis-current").textContent = "Loading...";
  document.getElementById("d-analysis-history").textContent = "Loading...";
  document.getElementById("d-history-note").textContent     = "";

  // Show placeholder chart while data loads
  buildRollingChart([]);

  try {
    const res = await fetch(`${API}/beta/single?ticker=${ticker}`);
    const d   = await res.json();

    // ── KPI cards ──────────────────────────────────────────
    document.getElementById("d-ticker").textContent = d.ticker;
    document.getElementById("d-name").textContent   = d.name   || "";
    document.getElementById("d-sector").textContent = d.sector || "";
    document.getElementById("d-verify").href        = d.verify_url;

    const bc = d.beta_calc  != null ? d.beta_calc.toFixed(4)  : "—";
    const by = d.beta_yahoo != null ? d.beta_yahoo.toFixed(4) : "—";
    const dl = (d.beta_calc != null && d.beta_yahoo != null)
      ? Math.abs(d.beta_calc - d.beta_yahoo).toFixed(4) : "—";

    document.getElementById("d-beta-calc").textContent  = bc;
    document.getElementById("d-beta-yahoo").textContent = by;
    document.getElementById("d-delta").textContent      = dl;
    document.getElementById("d-price").textContent      = d.price  ? "$" + d.price.toFixed(2)  : "—";
    document.getElementById("d-high52").textContent     = d.high52 ? "$" + d.high52.toFixed(2) : "—";
    document.getElementById("d-low52").textContent      = d.low52  ? "$" + d.low52.toFixed(2)  : "—";

    const mc = d.marketCap;
    document.getElementById("d-marketcap").textContent =
      mc ? (mc >= 1e12 ? "$" + (mc/1e12).toFixed(2) + "T" :
            mc >= 1e9  ? "$" + (mc/1e9).toFixed(2)  + "B" :
                         "$" + (mc/1e6).toFixed(2)  + "M") : "—";

    const riskLabel = d.beta_calc > 1.2 ? "Aggressive 🔴" : d.beta_calc < 0.8 ? "Defensive 🟢" : "Neutral 🟡";
    const riskClass = d.beta_calc > 1.2 ? "risk-high"     : d.beta_calc < 0.8 ? "risk-low"     : "risk-mid";
    const riskEl    = document.getElementById("d-risk");
    riskEl.textContent = riskLabel;
    riskEl.className   = "val " + riskClass;

    // ── Analysis text ───────────────────────────────────────
    document.getElementById("d-analysis-current").textContent =
      d.analysis_current || "No analysis available.";
    document.getElementById("d-analysis-history").textContent =
      d.analysis_history || "No historical analysis available.";

    // ── History note ────────────────────────────────────────
    const yrs = d.years_available || 0;
    document.getElementById("d-history-note").textContent =
      yrs < 5
        ? "⚠ Less than 5 years of data (" + yrs.toFixed(1) + "y)"
        : "✓ " + yrs.toFixed(1) + " years of price history";

    // ── Beta bar + guide ────────────────────────────────────
    document.getElementById("d-beta-big").textContent = bc;
    document.getElementById("d-beta-big").className   = "val " + riskClass;
    const pct = Math.min(Math.max(((d.beta_calc + 1) / 4) * 100, 0), 100);
    document.getElementById("betaBarMarker").style.left = pct + "%";

    ["gi-aggressive","gi-neutral","gi-defensive","gi-negative"].forEach(id =>
      document.getElementById(id).classList.remove("active"));
    document.getElementById(
      d.beta_calc > 1.2 ? "gi-aggressive" :
      d.beta_calc < 0   ? "gi-negative"   :
      d.beta_calc < 0.8 ? "gi-defensive"  : "gi-neutral"
    ).classList.add("active");

    // ── Rolling Beta chart (full max history) ───────────────
    buildRollingChart(d.rolling_betas || []);

    // ── Monthly returns chart ───────────────────────────────
    if (returnsChart) returnsChart.destroy();
    const returns = d.monthly_returns || [];
    returnsChart = new Chart(document.getElementById("returnsChart"), {
      type: "bar",
      data: {
        labels: returns.map(r => r.date),
        datasets: [{
          label:           d.ticker + " monthly return (%)",
          data:            returns.map(r => r.return),
          backgroundColor: returns.map(r => r.return >= 0 ? "#3fb950aa" : "#f85149aa"),
          borderColor:     returns.map(r => r.return >= 0 ? "#3fb950"   : "#f85149"),
          borderWidth: 1, borderRadius: 3
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, labels: { color: "#8b949e" } } },
        scales: {
          x: {
            ticks: { color: "#8b949e", font: { size: 10 }, maxRotation: 45 },
            grid:  { color: "#21262d" }
          },
          y: {
            ticks: { color: "#8b949e", callback: v => v + "%" },
            grid:  { color: "#21262d" },
            title: { display: true, text: "Monthly return (%)", color: "#8b949e" }
          }
        }
      }
    });

  } catch (e) {
    document.getElementById("d-beta-calc").textContent = "Error: " + e.message;
    console.error(e);
  }
}