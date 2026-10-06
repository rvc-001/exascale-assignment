// Use the Nginx /api proxy by default. When opened via VS Code Live Server,
// call the FastAPI backend directly because port 5500 only serves static files.
const API =
  window.ENV?.API_BASE ||
  (["5500", "5501"].includes(window.location.port) ? "http://127.0.0.1:8000/api" : "/api");
let charts = {}; // Store chart instances to destroy them on update

Chart.defaults.color = "#657066";
Chart.defaults.font.family = "'Inter', sans-serif";

const chartPalette = [
  "#c46a00", "#2f6f8f", "#238b5d", "#6b7280", "#c43d3d",
  "#d8a500", "#7f5539", "#437c90", "#4f6f52", "#8a5a44"
];

const formatCompact = (value, maximumFractionDigits = 1) =>
  new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits
  }).format(value);

const formatTco2e = (value, maximumFractionDigits = 1) =>
  `${formatCompact(value, maximumFractionDigits)} tCO2e`;

const getChartScales = () => ({
  x: {
    grid: { display: false },
    ticks: { color: "#657066", font: { size: 11, weight: "600" } }
  },
  y: {
    beginAtZero: true,
    border: { display: false },
    grid: { color: "rgba(23, 33, 28, 0.08)" },
    ticks: {
      color: "#657066",
      font: { size: 11, weight: "600" },
      callback: value => formatCompact(value)
    }
  }
});

// Retry helper: Waits for backend container to finish seeding on initial startup
async function fetchWithRetry(url, options = {}, retries = 5, backoff = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (res.ok) return res;
    } catch (err) {
      if (i === retries - 1) throw err;
    }
    await new Promise(r => setTimeout(r, backoff));
  }
  throw new Error(`Backend unavailable after ${retries} attempts.`);
}

async function renderYoYChart(year) {
  const res = await fetchWithRetry(`${API}/analytics/yoy?year=${year}`);
  const data = await res.json();

  const total_tco2e = data.current_year.total_kgco2e / 1000;
  document.getElementById("total-value").textContent = formatTco2e(total_tco2e);
    
  if (data.change_percent !== null) {
    document.getElementById("change-value").textContent =
      `${data.change_percent > 0 ? "+" : ""}${data.change_percent}%`;
    document.getElementById("change-value").style.color =
      data.change_percent < 0 ? "#1f8a5b" : "#ba2f2f";
      
    // Label YTD if applicable
    if (data.year === new Date().getFullYear()) {
      document.getElementById("change-value").textContent += " (YTD vs YTD)";
    }
  } else {
    document.getElementById("change-value").textContent = "N/A";
    document.getElementById("change-value").style.color = "#657066";
  }

  if (charts.yoy) charts.yoy.destroy();
  const ctx = document.getElementById("yoyChart").getContext("2d");
  const scales = getChartScales();
  charts.yoy = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [`${data.year - 1}`, `${data.year}`],
      datasets: [
        {
          label: "Scope 1 (Direct)",
          data: [data.previous_year.scope1_kgco2e / 1000, data.current_year.scope1_kgco2e / 1000],
          backgroundColor: "#c46a00",
          borderRadius: 4,
          maxBarThickness: 72
        },
        {
          label: "Scope 2 (Indirect)",
          data: [data.previous_year.scope2_kgco2e / 1000, data.current_year.scope2_kgco2e / 1000],
          backgroundColor: "#2f6f8f",
          borderRadius: 4,
          maxBarThickness: 72
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 12, boxHeight: 12, usePointStyle: true, pointStyle: "rectRounded" }
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${formatTco2e(ctx.parsed.y)}`
          }
        }
      },
      scales: {
        x: { ...scales.x, stacked: true },
        y: { ...scales.y, stacked: true }
      }
    }
  });
}

async function renderHotspotChart(year) {
  const res = await fetchWithRetry(`${API}/analytics/hotspot?year=${year}`);
  const data = await res.json();
  const visibleSources = data.hotspots.slice(0, 7);
  const hiddenSources = data.hotspots.slice(7);
  const otherTotal = hiddenSources.reduce((sum, item) => sum + item.emissions_kgco2e, 0);
  const otherPercentage = hiddenSources.reduce((sum, item) => sum + item.percentage, 0);
  const sources = otherTotal > 0
    ? [...visibleSources, { source: "Other sources", emissions_kgco2e: otherTotal, percentage: otherPercentage }]
    : visibleSources;

  if (charts.hotspot) charts.hotspot.destroy();
  const ctx = document.getElementById("hotspotChart").getContext("2d");
  charts.hotspot = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: sources.map(h => h.source),
      datasets: [{
        data: sources.map(h => h.emissions_kgco2e / 1000),
        backgroundColor: chartPalette,
        borderColor: "#fffefa",
        borderWidth: 3,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ${formatTco2e(ctx.parsed)} (${sources[ctx.dataIndex].percentage.toFixed(1)}%)`
          }
        }
      }
    }
  });

  const legend = document.getElementById("hotspotLegend");
  legend.innerHTML = sources.map((source, index) => `
    <div class="source-item" title="${source.source}">
      <span class="source-swatch" style="background:${chartPalette[index % chartPalette.length]}"></span>
      <span class="source-name">${source.source}</span>
      <span class="source-value">${source.percentage.toFixed(1)}%</span>
    </div>
  `).join("");
}

async function renderIntensityKPI(year) {
  const res = await fetchWithRetry(`${API}/analytics/intensity?metric=Tons+of+Steel+Produced&year=${year}`);
  const data = await res.json();
  const display = data.intensity != null ? `${(data.intensity / 1000).toLocaleString(undefined, {maximumFractionDigits: 2})} tCO2e/Ton` : "No data yet";
  document.getElementById("intensity-value").textContent = display;
}

async function renderMonthlyChart(year) {
  const res = await fetchWithRetry(`${API}/analytics/monthly?year=${year}`);
  const data = await res.json();
  
  document.getElementById("monthly-title").textContent = `Monthly emissions trend (${year})`;

  if (charts.monthly) charts.monthly.destroy();
  const ctx = document.getElementById("monthlyChart").getContext("2d");
  const scales = getChartScales();
  charts.monthly = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.monthly.map(m => m.month),
      datasets: [{
        label: "Monthly emissions (tCO2e)",
        data: data.monthly.map(m => m.emissions_kgco2e / 1000),
        borderColor: "#1f8a5b",
        backgroundColor: "rgba(31, 138, 91, 0.12)",
        borderWidth: 3,
        pointRadius: 3,
        pointHoverRadius: 5,
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => formatTco2e(ctx.parsed.y)
          }
        }
      },
      scales: {
        x: scales.x,
        y: scales.y
      }
    }
  });
}

const allActivityOptions = [
  { val: "Anthracite Coal", label: "Anthracite Coal", unit: "tonnes", scope: "1", group: "Scope 1 (Direct)" },
  { val: "Iron Scrap", label: "Iron Scrap", unit: "tonnes", scope: "1", group: "Scope 1 (Direct)" },
  { val: "Petroleum Coke", label: "Petroleum Coke", unit: "tonnes", scope: "1", group: "Scope 1 (Direct)" },
  { val: "Purchased Electricity - Grid - State Utility", label: "Grid - State Utility", unit: "kWh", scope: "2", group: "Scope 2 (Purchased Energy)" },
  { val: "Purchased Electricity - Grid - Open Access", label: "Grid - Open Access", unit: "kWh", scope: "2", group: "Scope 2 (Purchased Energy)" },
  { val: "Purchased Electricity - Captive Solar + Grid", label: "Captive Solar + Grid", unit: "kWh", scope: "2", group: "Scope 2 (Purchased Energy)" }
];

document.getElementById("emission-scope").addEventListener("change", (e) => {
  const scope = e.target.value;
  const select = document.getElementById("activity-type");
  select.innerHTML = ""; 
  
  const filtered = allActivityOptions.filter(o => o.scope === scope);
  if (filtered.length === 0) return;
  
  const optgroup = document.createElement("optgroup");
  optgroup.label = filtered[0].group;
  
  filtered.forEach(o => {
    const opt = document.createElement("option");
    opt.value = o.val;
    opt.textContent = o.label;
    opt.dataset.unit = o.unit;
    optgroup.appendChild(opt);
  });
  
  select.appendChild(optgroup);
  select.dispatchEvent(new Event("change"));
});

document.getElementById("activity-type").addEventListener("change", (e) => {
  const selected = e.target.selectedOptions[0];
  const unit = selected.dataset.unit || "units";
  const label = document.getElementById("amount-label");
  label.childNodes[0].textContent = `Amount (${unit}): `;
});
document.getElementById("emission-scope").dispatchEvent(new Event("change"));

document.getElementById("emission-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const resultDiv = document.getElementById("form-result");
  const scope = document.getElementById("emission-scope").value;
  const endpoint = scope === "2" ? `${API}/emissions/scope2` : `${API}/emissions/scope1`;

  const payload = {
    activity_date: document.getElementById("activity-date").value,
    activity_type: document.getElementById("activity-type").value,
    activity_amount: parseFloat(document.getElementById("activity-amount").value)
  };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      const errDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      throw new Error(errDetail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    resultDiv.textContent = `Recorded. Emissions: ${(data.calculated_emissions_kgco2e / 1000).toFixed(2)} tCO2e` + (data.factor_used ? ` | Factor: ${data.factor_used.source}` : "");
    resultDiv.style.color = "#1f8a5b";

    // Auto-switch dashboard to the year of the submitted record
    const submittedYear = payload.activity_date.split("-")[0];
    const yearSelect = document.getElementById("year-selector");
    
    // Add option if it doesn't exist
    if (!Array.from(yearSelect.options).some(opt => opt.value === submittedYear)) {
      const newOpt = document.createElement("option");
      newOpt.value = submittedYear;
      newOpt.textContent = submittedYear;
      yearSelect.appendChild(newOpt);
    }
    
    yearSelect.value = submittedYear;
    loadAllCharts(submittedYear);
  } catch (err) {
    resultDiv.textContent = err.message || "Error submitting record. Check console.";
    resultDiv.style.color = "#ba2f2f";
  }
});

document.getElementById("metric-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const resultDiv = document.getElementById("metric-result");
  const payload = {
    date: document.getElementById("metric-date").value,
    metric_name: document.getElementById("metric-name").value,
    value: parseFloat(document.getElementById("metric-value").value)
  };

  try {
    const res = await fetch(`${API}/metrics/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      const errDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      throw new Error(errDetail || `HTTP ${res.status}`);
    }

    resultDiv.textContent = "Metric saved.";
    resultDiv.style.color = "#1f8a5b";

    if (payload.metric_name === "Tons of Steel Produced") {
      const submittedYear = payload.date.split("-")[0];
      const yearSelect = document.getElementById("year-selector");
      if (!Array.from(yearSelect.options).some(opt => opt.value === submittedYear)) {
        const newOpt = document.createElement("option");
        newOpt.value = submittedYear;
        newOpt.textContent = submittedYear;
        yearSelect.appendChild(newOpt);
      }
      yearSelect.value = submittedYear;
      loadAllCharts(submittedYear);
    }
  } catch (err) {
    resultDiv.textContent = err.message || "Error saving metric. Check console.";
    resultDiv.style.color = "#ba2f2f";
  }
});

async function loadAllCharts(year) {
  const errorBanner = document.getElementById("error-banner");
  if (errorBanner) errorBanner.remove();
  
  try {
    await Promise.all([
      renderYoYChart(year),
      renderHotspotChart(year),
      renderIntensityKPI(year),
      renderMonthlyChart(year)
    ]);
  } catch (err) {
    const banner = document.createElement("div");
    banner.id = "error-banner";
    banner.style = "color: #ba2f2f; padding: 1rem; margin: 1rem 0 0; text-align: center; border: 1px solid #f4b3a9; border-radius: 8px;";
    banner.innerHTML = `<strong>Data loading error:</strong> ${err.message} <br> The backend may still be starting or seeding data. Please refresh in a moment.`;
    document.getElementById("dashboard-controls").insertAdjacentElement("afterend", banner);
  }
}

document.getElementById("year-selector").addEventListener("change", (e) => {
  loadAllCharts(e.target.value);
});

if (window.lucide) lucide.createIcons();
loadAllCharts(document.getElementById("year-selector").value);
