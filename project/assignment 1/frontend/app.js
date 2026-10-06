// Use window.ENV.API_BASE for separate frontend/backend deployments.
// Otherwise, use local FastAPI during development and the Nginx /api proxy in Docker.
const API_BASE =
  window.ENV?.API_BASE ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? "http://127.0.0.1:8000"
    : "/api");

Chart.defaults.color = '#66706b';
Chart.defaults.font.family = "'Inter', sans-serif";

let forecastChartInstance = null;

async function loadForecast() {
  try {
    const res = await fetch(`${API_BASE}/forecast`);
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();

    const labels = data.forecast.map(f => {
      // f.timestamp is an ISO string like "2024-10-06T14:30:00+05:30"
      return f.timestamp.substring(11, 16);
    });
    const values = data.forecast.map(f => f.predicted_load_kw);

    const ctx = document.getElementById('forecastChart').getContext('2d');
    
    // Create the forecast area fill from the dashboard palette.
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(8, 127, 122, 0.22)');
    gradient.addColorStop(1, 'rgba(8, 127, 122, 0.0)');

    if (forecastChartInstance) {
      forecastChartInstance.destroy();
    }

    forecastChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Predicted Demand (kW)',
          data: values,
          borderColor: '#087f7a',
          backgroundColor: gradient,
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#fffdf8',
          pointBorderColor: '#087f7a',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(24, 32, 31, 0.95)',
            titleFont: { size: 14, family: "'Inter', sans-serif" },
            bodyFont: { size: 14, family: "'Inter', sans-serif" },
            padding: 12,
            borderColor: 'rgba(255,255,255,0.16)',
            borderWidth: 1,
            displayColors: false,
            callbacks: {
              label: function(context) {
                return `${context.parsed.y.toLocaleString()} kW`;
              }
            }
          }
        },
        interaction: {
          intersect: false,
          mode: 'index',
        },
        scales: {
          x: { 
            grid: { color: 'rgba(24, 32, 31, 0.08)' },
            ticks: { maxTicksLimit: 12 }
          },
          y: { 
            grid: { color: 'rgba(24, 32, 31, 0.08)' },
            beginAtZero: false
          }
        }
      }
    });
  } catch (error) {
    console.error("Forecast load failed:", error);
    document.getElementById('chart-section').innerHTML += '<p style="color: #b42318; margin-top:1rem;">Failed to load forecast data.</p>';
  }
}

async function loadWeather() {
  try {
    const res = await fetch(`${API_BASE}/weather`);
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    const w = data.weather[0]; // Current hour
    
    // Animate numbers
    animateValue("temp-card", w.temperature, " C");
    animateValue("humidity-card", w.humidity, "%");
    animateValue("cloud-card", w.cloud_cover, "%");
  } catch (error) {
    console.error("Weather load failed:", error);
  }
}

async function loadHolidays() {
  try {
    const res = await fetch(`${API_BASE}/holidays`);
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    const tbody = document.getElementById('holidays-body');
    
    if (data.holidays.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" class="loading-text">No upcoming holidays in the next 60 days</td></tr>';
    } else {
      tbody.innerHTML = '';
      data.holidays.forEach(h => {
        // Simple badge coloring based on type
        const typeColor = h.type.toLowerCase().includes('national') ? '#bf6a02' : '#087f7a';
        tbody.innerHTML += `<tr>
          <td style="font-weight: 600;">${h.date}</td>
          <td>${h.holiday_name}</td>
          <td><span style="background: ${typeColor}1f; color: ${typeColor}; padding: 0.25rem 0.55rem; border-radius: 999px; font-size: 0.72rem; font-weight: 800; border: 1px solid ${typeColor}55;">${h.type}</span></td>
        </tr>`;
      });
    }
  } catch (error) {
    console.error("Holiday load failed:", error);
    document.getElementById('holidays-body').innerHTML = '<tr><td colspan="3" style="color: #b42318;">Failed to load holidays.</td></tr>';
  }
}

// Micro-animation helper for numbers
function animateValue(id, end, suffix) {
  const obj = document.getElementById(id);
  let startTimestamp = null;
  const duration = 1500;
  
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    // Ease out quad
    const easeOut = progress * (2 - progress);
    const current = (easeOut * end).toFixed(1);
    obj.innerHTML = `${current}<span style="font-size: 0.95rem; font-weight:700; color: #66706b; margin-left: 2px;">${suffix}</span>`;
    if (progress < 1) {
      window.requestAnimationFrame(step);
    }
  };
  window.requestAnimationFrame(step);
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  loadForecast();
  loadWeather();
  loadHolidays();
});
