const API = "";
let allData = [];
let sortKey = "ticker";
let sortAsc = true;
let betaChart = null;
let sectorChart = null;

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
        Error: ${e.message}. Make sure api.py is running at http://127.0.0.1:5000
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
  document.getElementById("s-high").textContent    =
    sorted[0].ticker + " (" + sorted[0].beta_calc + ")";
  document.getElementById("s-low").textContent     =
    sorted[sorted.length - 1].ticker + " (" + sorted[sorted.length - 1].beta_calc + ")";
}

function renderBetaChart(data) {
  const sorted = [...data].sort((a, b) => (b.beta_calc || 0) - (a.beta_calc || 0));
  const labels = sorted.map(d => d.ticker);
  const calc   = sorted.map(d => d.beta_calc);
  const yf     = sorted.map(d => d.beta_yahoo);

  if (betaChart) betaChart.destroy();
  betaChart = new Chart(document.getElementById("betaChart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Beta (calculated)",
          data: calc,
          backgroundColor: "#388bfd",
          borderRadius: 2
        },
        {
          label: "Beta (Yahoo Finance)",
          data: yf,
          backgroundColor: "#f8514966",
          borderRadius: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: "#8b949e", font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            afterBody: (items) => {
              const d = sorted[items[0].dataIndex];
              return "Delta: " + (d.delta ?? "—");
            }
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#8b949e", font: { size: 9 } },
          grid: { color: "#21262d" }
        },
        y: {
          ticks: { color: "#8b949e" },
          grid: { color: "#21262d" },
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
      datasets: [{
        label: "Avg beta by sector",
        data: avgs,
        backgroundColor: colors,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          ticks: { color: "#8b949e" },
          grid: { color: "#21262d" }
        },
        y: {
          ticks: { color: "#8b949e", font: { size: 11 } },
          grid: { color: "#21262d" }
        }
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
    return `<tr>
      <td><strong>${d.ticker}</strong></td>
      <td>${d.name   || "—"}</td>
      <td>${d.sector || "—"}</td>
      <td class="num">${bc}</td>
      <td class="num">${by}</td>
      <td class="num ${deltaClass}">${dl}</td>
      <td class="${riskClass}">${riskLabel}</td>
      <td><a href="${d.verify_url}" target="_blank">View on YF ↗</a></td>
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