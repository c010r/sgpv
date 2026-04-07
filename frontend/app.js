const state = {
  baseUrl: localStorage.getItem("sgpv_base_url") || "http://127.0.0.1:8000",
  accessToken: localStorage.getItem("sgpv_access_token") || "",
  refreshToken: localStorage.getItem("sgpv_refresh_token") || "",
  currentConfigId: null,
};

const $ = (id) => document.getElementById(id);

const toastEl = $("toast");
function toast(message, type = "ok") {
  toastEl.textContent = message;
  toastEl.className = `toast show ${type}`;
  setTimeout(() => {
    toastEl.className = "toast";
  }, 2600);
}

function setAuthStatus() {
  $("authStatus").textContent = state.accessToken ? "Autenticado" : "No autenticado";
}

function saveTokens(access, refresh) {
  state.accessToken = access || "";
  state.refreshToken = refresh || "";
  localStorage.setItem("sgpv_access_token", state.accessToken);
  localStorage.setItem("sgpv_refresh_token", state.refreshToken);
  setAuthStatus();
}

function setBaseUrl(url) {
  state.baseUrl = (url || "").replace(/\/$/, "");
  localStorage.setItem("sgpv_base_url", state.baseUrl);
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.accessToken) {
    headers.Authorization = `Bearer ${state.accessToken}`;
  }

  const res = await fetch(`${state.baseUrl}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!res.ok) {
    const detail = data?.detail || JSON.stringify(data);
    throw new Error(`${res.status} ${detail}`);
  }
  return data;
}

function renderTable(containerId, rows) {
  const container = $(containerId);
  if (!Array.isArray(rows) || rows.length === 0) {
    container.innerHTML = "<p class='hint'>Sin datos</p>";
    return;
  }

  const cols = Object.keys(rows[0]);
  const thead = `<tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  const tbody = rows
    .map(
      (row) =>
        `<tr>${cols
          .map((c) => `<td>${row[c] === null || row[c] === undefined ? "" : String(row[c])}</td>`)
          .join("")}</tr>`,
    )
    .join("");

  container.innerHTML = `<div class='table-wrap'><table><thead>${thead}</thead><tbody>${tbody}</tbody></table></div>`;
}

function activateTab(tabId) {
  document.querySelectorAll(".menu button").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === tabId));
}

async function login() {
  const username = $("username").value.trim();
  const password = $("password").value;
  if (!username || !password) {
    toast("Usuario y clave son requeridos", "error");
    return;
  }
  try {
    const data = await api("/api/token/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    saveTokens(data.access, data.refresh);
    toast("Login correcto");
    await loadDashboard();
  } catch (err) {
    toast(`Login falló: ${err.message}`, "error");
  }
}

function logout() {
  saveTokens("", "");
  toast("Sesión cerrada");
}

async function loadDashboard() {
  try {
    const data = await api("/api/reportes/dashboard/");
    const cards = [
      ["Fecha", data.date],
      ["Ventas hoy", data.sales_today],
      ["Tickets hoy", data.tickets_today],
      ["Barras abiertas", data.open_bar_sessions],
      ["Cajas abiertas", data.open_cash_sessions],
    ];
    $("dashCards").innerHTML = cards
      .map(([k, v]) => `<article class='card'><h4>${k}</h4><p>${v ?? "-"}</p></article>`)
      .join("");

    const hourly = data.hourly_sales_last_24h || [];
    $("hourlyList").innerHTML = hourly
      .map((h) => `<div class='line-item'><span>${h.hour}</span><strong>${h.sales} (${h.tickets} tk)</strong></div>`)
      .join("");

    const critical = data.critical_stock_by_bar || [];
    if (!critical.length) {
      $("criticalStock").innerHTML = "<p class='hint'>Sin stock crítico</p>";
    } else {
      $("criticalStock").innerHTML = critical
        .map(
          (bar) => `<div class='critical-block'>
            <h4>${bar.bar_name || bar.location_name} (${bar.items_count})</h4>
            <ul>${(bar.items || [])
              .map((it) => `<li>${it.product_name}: <strong>${it.quantity}</strong></li>`)
              .join("")}</ul>
          </div>`,
        )
        .join("");
    }
  } catch (err) {
    toast(`Dashboard error: ${err.message}`, "error");
  }
}

async function loadSales() {
  try {
    const data = await api("/api/ventas/");
    renderTable(
      "salesTable",
      (data.results || data).map((s) => ({
        id: s.id,
        bar_session: s.bar_session,
        cash_session: s.cash_session,
        status: s.status,
        total: s.total,
        created_at: s.created_at,
      })),
    );
  } catch (err) {
    toast(`Ventas error: ${err.message}`, "error");
  }
}

async function createSale() {
  const payload = {
    bar_session_id: Number($("saleBarSession").value),
    cash_session_id: Number($("saleCashSession").value),
    items: [
      {
        product_id: Number($("saleProduct").value),
        quantity: String($("saleQty").value || "1"),
        unit_price: String($("saleUnitPrice").value || "0"),
      },
    ],
    payments: [
      {
        method: $("salePayMethod").value,
        amount: String($("salePayAmount").value || "0"),
      },
    ],
  };

  try {
    const data = await api("/api/ventas/create_sale/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("saleCreateResult").textContent = JSON.stringify(data, null, 2);
    toast("Venta creada");
    await loadSales();
  } catch (err) {
    $("saleCreateResult").textContent = err.message;
    toast(`No se pudo crear venta: ${err.message}`, "error");
  }
}

async function loadStocks() {
  try {
    const data = await api("/api/inventario/stocks/");
    renderTable(
      "stocksTable",
      (data.results || data).map((s) => ({
        id: s.id,
        location: s.location_name,
        product: s.product_name,
        quantity: s.quantity,
        updated_at: s.updated_at,
      })),
    );
  } catch (err) {
    toast(`Stocks error: ${err.message}`, "error");
  }
}

async function loadMovements() {
  try {
    const data = await api("/api/inventario/movimientos/");
    renderTable(
      "movesTable",
      (data.results || data).map((m) => ({
        id: m.id,
        type: m.movement_type,
        product: m.product,
        qty: m.quantity,
        source: m.source,
        destination: m.destination,
        reason: m.reason,
        created_at: m.created_at,
      })),
    );
  } catch (err) {
    toast(`Movimientos error: ${err.message}`, "error");
  }
}

async function checkinGuest() {
  const qr_code = $("checkinQr").value.trim();
  const companions_used = Number($("checkinCompanions").value || 0);
  try {
    const data = await api("/api/invitados/checkin/", {
      method: "POST",
      body: JSON.stringify({ qr_code, companions_used }),
    });
    $("checkinResult").textContent = JSON.stringify(data, null, 2);
    toast("Check-in registrado");
    await loadGuests();
  } catch (err) {
    $("checkinResult").textContent = err.message;
    toast(`Check-in falló: ${err.message}`, "error");
  }
}

async function loadGuests() {
  try {
    const data = await api("/api/invitados/");
    renderTable(
      "guestsTable",
      (data.results || data).map((g) => ({
        id: g.id,
        name: g.full_name,
        document: g.document_id,
        status: g.status,
        companions_allowed: g.companions_allowed,
        companions_used: g.companions_used,
        checked_in_at: g.checked_in_at,
      })),
    );
  } catch (err) {
    toast(`Invitados error: ${err.message}`, "error");
  }
}

async function loadAlerts() {
  try {
    const data = await api("/api/reportes/alertas/?limit=50&offset=0");
    const rows = (data.results || []).map((a) => ({
      id: a.id,
      created_at: a.created_at,
      type: a.alert_type,
      severity: a.severity,
      status: a.status,
      occurrences: a.occurrence_count,
      sent_via: a.sent_via,
      message: a.message,
    }));
    renderTable("alertsTable", rows);
  } catch (err) {
    toast(`Alertas error: ${err.message}`, "error");
  }
}

async function loadFinancialSummary() {
  try {
    const data = await api("/api/reportes/resumen-financiero/");
    $("financialSummary").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    toast(`Resumen financiero error: ${err.message}`, "error");
  }
}

async function loadConfig() {
  try {
    const data = await api("/api/configuracion/");
    const cfg = (data.results || data)[0];
    if (!cfg) {
      $("cfgResult").textContent = "Sin configuración aún";
      return;
    }
    state.currentConfigId = cfg.id;
    $("cfgCountry").value = cfg.country_code || "";
    $("cfgCurrency").value = cfg.currency_code || "";
    $("cfgTimezone").value = cfg.timezone || "";
    $("cfgCosting").value = cfg.costing_method || "AVG";
    $("cfgResult").textContent = JSON.stringify(cfg, null, 2);
    toast("Configuración cargada");
  } catch (err) {
    toast(`Config error: ${err.message}`, "error");
  }
}

async function saveConfig() {
  const payload = {
    country_code: $("cfgCountry").value.trim(),
    currency_code: $("cfgCurrency").value.trim(),
    timezone: $("cfgTimezone").value.trim(),
    costing_method: $("cfgCosting").value,
  };

  try {
    let data;
    if (state.currentConfigId) {
      data = await api(`/api/configuracion/${state.currentConfigId}/`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    } else {
      data = await api("/api/configuracion/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.currentConfigId = data.id;
    }
    $("cfgResult").textContent = JSON.stringify(data, null, 2);
    toast("Configuración guardada");
  } catch (err) {
    $("cfgResult").textContent = err.message;
    toast(`No se guardó configuración: ${err.message}`, "error");
  }
}

function bindEvents() {
  $("baseUrl").value = state.baseUrl;
  $("baseUrl").addEventListener("change", (e) => {
    setBaseUrl(e.target.value);
    toast("Base URL actualizada");
  });

  $("loginBtn").addEventListener("click", login);
  $("logoutBtn").addEventListener("click", logout);

  $("menu").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-tab]");
    if (!btn) return;
    activateTab(btn.dataset.tab);
  });

  $("loadSalesBtn").addEventListener("click", loadSales);
  $("createSaleBtn").addEventListener("click", createSale);
  $("loadStocksBtn").addEventListener("click", loadStocks);
  $("loadMovesBtn").addEventListener("click", loadMovements);
  $("checkinBtn").addEventListener("click", checkinGuest);
  $("loadGuestsBtn").addEventListener("click", loadGuests);
  $("loadAlertsBtn").addEventListener("click", loadAlerts);
  $("loadFinancialBtn").addEventListener("click", loadFinancialSummary);
  $("loadCfgBtn").addEventListener("click", loadConfig);
  $("saveCfgBtn").addEventListener("click", saveConfig);
}

async function bootstrap() {
  bindEvents();
  setAuthStatus();
  if (state.accessToken) {
    await loadDashboard();
  }
}

bootstrap();
