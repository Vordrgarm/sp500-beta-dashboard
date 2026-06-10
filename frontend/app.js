const API = "https://web-production-38abb.up.railway.app";
let allData = [];
let sortKey = "ticker";
let sortAsc = true;
let betaChart = null;
let sectorChart = null;
let returnsChart = null;

// ─── MAIN VIEW ───────────────────────────────────────────────

async function loadAll() {
  const period = document.getElementById("periodSelect").value;
  const btn = document.getElementById("loadBtn");
  btn.textContent = "Loading...";
  btn.disabled = true;
  document.getElementById("tableBody").innerHTML =
    '<tr><td colspan="8" style="text-align:center;padding:40px;color:#8b949e;">Fetching data from Yahoo Finance — this takes about 60 seconds...</td></tr>';

  try {
    const res = await fetch(`${API}/beta?period=${period}`);
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
  btn.disabled = false;
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
  document.getElementById("s-high").textContent    = sorted[0].ticker + " (" + sorted[0].beta_calc + ")";
  document.getElementById("s-low").textContent     = sorted[sorted.length - 1].ticker + " (" + sorted[sorted.length - 1].beta_calc + ")";
}

function renderBetaChart(data) {
  const sorted = [...data].sort((a, b) => (b.beta_calc || 0) - (a.beta_calc || 0));
  if (betaChart) betaChart.destroy();
  betaChart = new Chart(document.getElementById("betaChart"), {
    type: "bar",
    data: {
      labels: sorted.map(d => d.ticker),
      datasets: [
        { label: "Beta (calculated — daily OLS)", data: sorted.map(d => d.beta_calc), backgroundColor: "#388bfd", borderRadius: 2 },
        { label: "Beta (Yahoo Finance — monthly 5y)", data: sorted.map(d => d.beta_yahoo), backgroundColor: "#f8514966", borderRadius: 2 }
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
        y: { ticks: { color: "#8b949e" }, grid: { color: "#21262d" }, title: { display: true, text: "Beta coefficient", color: "#8b949e" } }
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
    data: { labels, datasets: [{ label: "Avg beta", data: avgs, backgroundColor: colors, borderRadius: 4 }] },
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
    return sortAsc ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
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
  const filtered = allData.filter(d =>
    (d.ticker || "").toLowerCase().includes(q) ||
    (d.name   || "").toLowerCase().includes(q) ||
    (d.sector || "").toLowerCase().includes(q)
  );
  renderTable(filtered);
}

// ─── DETAIL VIEW ─────────────────────────────────────────────

function showMain() {
  document.getElementById("mainView").style.display   = "block";
  document.getElementById("detailView").style.display = "none";
}

async function openDetail(ticker) {
  document.getElementById("mainView").style.display   = "none";
  document.getElementById("detailView").style.display = "block";

  const period = document.getElementById("periodSelect").value;

  // Fill placeholders while loading
  ["d-ticker","d-name","d-beta-calc","d-beta-yahoo","d-delta",
   "d-risk","d-price","d-marketcap","d-high52","d-low52",
   "d-beta-big","d-beta-inline","d-beta-interp","d-yf-inline","d-delta-inline"
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = "Loading...";
  });

  try {
    const res  = await fetch(`${API}/beta/single?ticker=${ticker}&period=${period}`);
    const d    = await res.json();

    // Header
    document.getElementById("d-ticker").textContent  = d.ticker;
    document.getElementById("d-name").textContent    = d.name || "";
    document.getElementById("d-sector").textContent  = d.sector || "";
    document.getElementById("d-verify").href         = d.verify_url;

    // Cards
    const bc = d.beta_calc  != null ? d.beta_calc.toFixed(4)  : "—";
    const by = d.beta_yahoo != null ? d.beta_yahoo.toFixed(4) : "—";
    const dl = d.delta      != null ? d.delta.toFixed(4)      :
               (d.beta_calc != null && d.beta_yahoo != null)
                 ? Math.abs(d.beta_calc - d.beta_yahoo).toFixed(4) : "—";

    document.getElementById("d-beta-calc").textContent  = bc;
    document.getElementById("d-beta-yahoo").textContent = by;
    document.getElementById("d-delta").textContent      = dl;
    document.getElementById("d-price").textContent      = d.price ? "$" + d.price.toFixed(2) : "—";
    document.getElementById("d-high52").textContent     = d.high52 ? "$" + d.high52.toFixed(2) : "—";
    document.getElementById("d-low52").textContent      = d.low52  ? "$" + d.low52.toFixed(2)  : "—";

    // Market cap formatting
    const mc = d.marketCap;
    document.getElementById("d-marketcap").textContent =
      mc ? (mc >= 1e12 ? "$" + (mc/1e12).toFixed(2) + "T" :
            mc >= 1e9  ? "$" + (mc/1e9).toFixed(2)  + "B" :
                         "$" + (mc/1e6).toFixed(2)  + "M") : "—";

    // Risk
    const riskLabel = d.beta_calc > 1.2 ? "Aggressive 🔴" : d.beta_calc < 0.8 ? "Defensive 🟢" : "Neutral 🟡";
    const riskClass = d.beta_calc > 1.2 ? "risk-high"     : d.beta_calc < 0.8 ? "risk-low"     : "risk-mid";
    const riskEl = document.getElementById("d-risk");
    riskEl.textContent  = riskLabel;
    riskEl.className    = "val " + riskClass;

    // Methodology text
    document.getElementById("d-beta-inline").textContent  = bc;
    document.getElementById("d-beta-interp").textContent  =
      d.beta_calc > 1.2 ? "more than the market (aggressive)"  :
      d.beta_calc < 0   ? "inversely to the market"            :
      d.beta_calc < 0.8 ? "less than the market (defensive)"   : "roughly in line with the market";
    document.getElementById("d-yf-inline").textContent    = by;
    document.getElementById("d-delta-inline").textContent = dl;

    // Beta big display + bar
    document.getElementById("d-beta-big").textContent = bc;
    document.getElementById("d-beta-big").className   = "val " + riskClass;
    const pct = Math.min(Math.max(((d.beta_calc + 1) / 4) * 100, 0), 100);
    document.getElementById("betaBarMarker").style.left = pct + "%";

    // Highlight active guide row
    ["gi-aggressive","gi-neutral","gi-defensive","gi-negative"].forEach(id =>
      document.getElementById(id).classList.remove("active"));
    const activeGuide = d.beta_calc > 1.2 ? "gi-aggressive" :
                        d.beta_calc < 0   ? "gi-negative"   :
                        d.beta_calc < 0.8 ? "gi-defensive"  : "gi-neutral";
    document.getElementById(activeGuide).classList.add("active");

    // Monthly returns chart
    if (returnsChart) returnsChart.destroy();
    const returns = d.monthly_returns || [];
    returnsChart = new Chart(document.getElementById("returnsChart"), {
      type: "bar",
      data: {
        labels: returns.map(r => r.date),
        datasets: [{
          label: d.ticker + " monthly return (%)",
          data: returns.map(r => r.return),
          backgroundColor: returns.map(r => r.return >= 0 ? "#3fb950aa" : "#f85149aa"),
          borderColor:     returns.map(r => r.return >= 0 ? "#3fb950"   : "#f85149"),
          borderWidth: 1, borderRadius: 3
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, labels: { color: "#8b949e" } } },
        scales: {
          x: { ticks: { color: "#8b949e", font: { size: 10 }, maxRotation: 45 }, grid: { color: "#21262d" } },
          y: {
            ticks: { color: "#8b949e", callback: v => v + "%" },
            grid: { color: "#21262d" },
            title: { display: true, text: "Monthly return (%)", color: "#8b949e" }
          }
        }
      }
    });

  } catch (e) {
    document.getElementById("d-beta-calc").textContent = "Error loading data";
  }
}