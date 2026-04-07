import { useMemo, useState } from "react";
import { apiRequest, asList } from "./api";

const TABS = [
  ["dashboard", "Dashboard"],
  ["ventas", "Caja y Ventas"],
  ["inventario", "Inventario"],
  ["invitados", "Invitados"],
  ["reportes", "Reportes"],
  ["config", "Configuración"],
];

function Table({ rows }) {
  if (!rows?.length) return <p className="hint">Sin datos</p>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => <td key={c}>{String(row[c] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pager({ limit, offset, setLimit, setOffset }) {
  return (
    <div className="pager">
      <label>
        limit
        <input type="number" value={limit} min={1} max={500} onChange={(e) => setLimit(Number(e.target.value || 20))} />
      </label>
      <label>
        offset
        <input type="number" value={offset} min={0} onChange={(e) => setOffset(Math.max(0, Number(e.target.value || 0)))} />
      </label>
      <button onClick={() => setOffset(Math.max(0, offset - limit))}>Prev</button>
      <button onClick={() => setOffset(offset + limit)}>Next</button>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [baseUrl, setBaseUrl] = useState(localStorage.getItem("sgpv_react_base") || "http://127.0.0.1:8000");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("sgpv_react_token") || "");
  const [toast, setToast] = useState("");

  const [dashboard, setDashboard] = useState(null);

  const [sales, setSales] = useState([]);
  const [salesLimit, setSalesLimit] = useState(20);
  const [salesOffset, setSalesOffset] = useState(0);
  const [salePayload, setSalePayload] = useState({
    bar_session_id: "",
    cash_session_id: "",
    product_id: "",
    quantity: "1",
    unit_price: "",
    method: "CASH",
    amount: "",
  });
  const [saleResult, setSaleResult] = useState("");

  const [stocks, setStocks] = useState([]);
  const [stockLimit, setStockLimit] = useState(20);
  const [stockOffset, setStockOffset] = useState(0);

  const [moves, setMoves] = useState([]);
  const [moveLimit, setMoveLimit] = useState(20);
  const [moveOffset, setMoveOffset] = useState(0);

  const [guests, setGuests] = useState([]);
  const [guestLimit, setGuestLimit] = useState(20);
  const [guestOffset, setGuestOffset] = useState(0);
  const [checkin, setCheckin] = useState({ qr_code: "", companions_used: 0 });
  const [checkinResult, setCheckinResult] = useState("");

  const [alerts, setAlerts] = useState([]);
  const [alertLimit, setAlertLimit] = useState(20);
  const [alertOffset, setAlertOffset] = useState(0);
  const [financial, setFinancial] = useState(null);

  const [configId, setConfigId] = useState(null);
  const [config, setConfig] = useState({
    country_code: "UY",
    currency_code: "USD",
    timezone: "America/Montevideo",
    costing_method: "AVG",
  });

  const authLabel = token ? "Autenticado" : "No autenticado";

  const client = useMemo(() => ({
    call: (path, opts = {}) => apiRequest({ baseUrl, token, path, ...opts }),
  }), [baseUrl, token]);

  function notify(message) {
    setToast(message);
    setTimeout(() => setToast(""), 2600);
  }

  function persistBaseUrl(v) {
    setBaseUrl(v);
    localStorage.setItem("sgpv_react_base", v.replace(/\/$/, ""));
  }

  async function login() {
    try {
      const data = await apiRequest({
        baseUrl,
        path: "/api/token/",
        method: "POST",
        body: { username, password },
      });
      setToken(data.access);
      localStorage.setItem("sgpv_react_token", data.access);
      notify("Login exitoso");
    } catch (err) {
      notify(`Login error: ${err.message}`);
    }
  }

  function logout() {
    setToken("");
    localStorage.removeItem("sgpv_react_token");
    notify("Sesión cerrada");
  }

  async function loadDashboard() {
    try {
      const data = await client.call("/api/reportes/dashboard/");
      setDashboard(data);
    } catch (err) {
      notify(`Dashboard error: ${err.message}`);
    }
  }

  async function loadSales() {
    try {
      const data = await client.call(`/api/ventas/?limit=${salesLimit}&offset=${salesOffset}`);
      const rows = asList(data).map((x) => ({
        id: x.id,
        bar_session: x.bar_session,
        cash_session: x.cash_session,
        status: x.status,
        total: x.total,
        created_at: x.created_at,
      }));
      setSales(rows);
    } catch (err) {
      notify(`Ventas error: ${err.message}`);
    }
  }

  async function createSale() {
    try {
      const payload = {
        bar_session_id: Number(salePayload.bar_session_id),
        cash_session_id: Number(salePayload.cash_session_id),
        items: [
          {
            product_id: Number(salePayload.product_id),
            quantity: String(salePayload.quantity || "1"),
            unit_price: String(salePayload.unit_price || "0"),
          },
        ],
        payments: [
          {
            method: salePayload.method,
            amount: String(salePayload.amount || "0"),
          },
        ],
      };
      const data = await client.call("/api/ventas/create_sale/", { method: "POST", body: payload });
      setSaleResult(JSON.stringify(data, null, 2));
      notify("Venta creada");
      await loadSales();
    } catch (err) {
      setSaleResult(err.message);
      notify(`Crear venta error: ${err.message}`);
    }
  }

  async function loadStocks() {
    try {
      const data = await client.call(`/api/inventario/stocks/?limit=${stockLimit}&offset=${stockOffset}`);
      const rows = asList(data).map((x) => ({
        id: x.id,
        location: x.location_name,
        product: x.product_name,
        quantity: x.quantity,
        updated_at: x.updated_at,
      }));
      setStocks(rows);
    } catch (err) {
      notify(`Stocks error: ${err.message}`);
    }
  }

  async function loadMoves() {
    try {
      const data = await client.call(`/api/inventario/movimientos/?limit=${moveLimit}&offset=${moveOffset}`);
      const rows = asList(data).map((x) => ({
        id: x.id,
        type: x.movement_type,
        product: x.product,
        quantity: x.quantity,
        source: x.source,
        destination: x.destination,
        created_at: x.created_at,
      }));
      setMoves(rows);
    } catch (err) {
      notify(`Movimientos error: ${err.message}`);
    }
  }

  async function doCheckin() {
    try {
      const data = await client.call("/api/invitados/checkin/", { method: "POST", body: checkin });
      setCheckinResult(JSON.stringify(data, null, 2));
      notify("Check-in ok");
      await loadGuests();
    } catch (err) {
      setCheckinResult(err.message);
      notify(`Check-in error: ${err.message}`);
    }
  }

  async function loadGuests() {
    try {
      const data = await client.call(`/api/invitados/?limit=${guestLimit}&offset=${guestOffset}`);
      const rows = asList(data).map((x) => ({
        id: x.id,
        full_name: x.full_name,
        document_id: x.document_id,
        status: x.status,
        companions_allowed: x.companions_allowed,
        companions_used: x.companions_used,
        checked_in_at: x.checked_in_at,
      }));
      setGuests(rows);
    } catch (err) {
      notify(`Invitados error: ${err.message}`);
    }
  }

  async function loadAlerts() {
    try {
      const data = await client.call(`/api/reportes/alertas/?limit=${alertLimit}&offset=${alertOffset}&order_by=-id`);
      const rows = (data.results || []).map((x) => ({
        id: x.id,
        created_at: x.created_at,
        type: x.alert_type,
        severity: x.severity,
        status: x.status,
        occurrences: x.occurrence_count,
        sent_via: x.sent_via,
        message: x.message,
      }));
      setAlerts(rows);
    } catch (err) {
      notify(`Alertas error: ${err.message}`);
    }
  }

  async function loadFinancial() {
    try {
      const data = await client.call("/api/reportes/resumen-financiero/");
      setFinancial(data);
    } catch (err) {
      notify(`Resumen financiero error: ${err.message}`);
    }
  }

  async function loadConfig() {
    try {
      const data = await client.call("/api/configuracion/");
      const first = asList(data)[0];
      if (!first) {
        setConfigId(null);
        notify("No hay configuración aún");
        return;
      }
      setConfigId(first.id);
      setConfig({
        country_code: first.country_code || "UY",
        currency_code: first.currency_code || "USD",
        timezone: first.timezone || "America/Montevideo",
        costing_method: first.costing_method || "AVG",
      });
      notify("Configuración cargada");
    } catch (err) {
      notify(`Config error: ${err.message}`);
    }
  }

  async function saveConfig() {
    try {
      if (configId) {
        await client.call(`/api/configuracion/${configId}/`, { method: "PATCH", body: config });
      } else {
        const data = await client.call("/api/configuracion/", { method: "POST", body: config });
        setConfigId(data.id);
      }
      notify("Configuración guardada");
    } catch (err) {
      notify(`Guardar config error: ${err.message}`);
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>SGPV React</h1>
        <p className="subtitle">Front operativo</p>

        <label>API Base URL</label>
        <input value={baseUrl} onChange={(e) => persistBaseUrl(e.target.value)} />

        <div className="auth-box">
          <input placeholder="usuario" value={username} onChange={(e) => setUsername(e.target.value)} />
          <input type="password" placeholder="clave" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button className="primary" onClick={login}>Entrar</button>
          <button onClick={logout}>Salir</button>
          <small>{authLabel}</small>
        </div>

        <nav className="menu">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
      </aside>

      <main className="content">
        {tab === "dashboard" && (
          <section>
            <header className="title-row">
              <h2>Dashboard</h2>
              <button className="primary" onClick={loadDashboard}>Cargar</button>
            </header>
            {!dashboard ? <p className="hint">Sin datos</p> : (
              <>
                <div className="cards">
                  <article className="card"><h4>Fecha</h4><p>{dashboard.date}</p></article>
                  <article className="card"><h4>Ventas hoy</h4><p>{dashboard.sales_today}</p></article>
                  <article className="card"><h4>Tickets hoy</h4><p>{dashboard.tickets_today}</p></article>
                  <article className="card"><h4>Barras abiertas</h4><p>{dashboard.open_bar_sessions}</p></article>
                  <article className="card"><h4>Cajas abiertas</h4><p>{dashboard.open_cash_sessions}</p></article>
                </div>
                <div className="panel">
                  <h3>Ventas últimas 24h</h3>
                  <Table rows={(dashboard.hourly_sales_last_24h || []).slice(-12)} />
                </div>
              </>
            )}
          </section>
        )}

        {tab === "ventas" && (
          <section className="grid-two">
            <div className="panel">
              <h3>Crear venta simple</h3>
              <input placeholder="bar_session_id" value={salePayload.bar_session_id} onChange={(e) => setSalePayload({ ...salePayload, bar_session_id: e.target.value })} />
              <input placeholder="cash_session_id" value={salePayload.cash_session_id} onChange={(e) => setSalePayload({ ...salePayload, cash_session_id: e.target.value })} />
              <input placeholder="product_id" value={salePayload.product_id} onChange={(e) => setSalePayload({ ...salePayload, product_id: e.target.value })} />
              <input placeholder="quantity" value={salePayload.quantity} onChange={(e) => setSalePayload({ ...salePayload, quantity: e.target.value })} />
              <input placeholder="unit_price" value={salePayload.unit_price} onChange={(e) => setSalePayload({ ...salePayload, unit_price: e.target.value })} />
              <select value={salePayload.method} onChange={(e) => setSalePayload({ ...salePayload, method: e.target.value })}>
                <option value="CASH">CASH</option>
                <option value="CARD">CARD</option>
                <option value="TRANSFER">TRANSFER</option>
              </select>
              <input placeholder="payment amount" value={salePayload.amount} onChange={(e) => setSalePayload({ ...salePayload, amount: e.target.value })} />
              <button className="primary" onClick={createSale}>Crear venta</button>
              <pre>{saleResult}</pre>
            </div>
            <div className="panel">
              <header className="title-row">
                <h3>Ventas</h3>
                <button onClick={loadSales}>Refrescar</button>
              </header>
              <Pager limit={salesLimit} offset={salesOffset} setLimit={setSalesLimit} setOffset={setSalesOffset} />
              <Table rows={sales} />
            </div>
          </section>
        )}

        {tab === "inventario" && (
          <section className="grid-two">
            <div className="panel">
              <header className="title-row"><h3>Stocks</h3><button onClick={loadStocks}>Refrescar</button></header>
              <Pager limit={stockLimit} offset={stockOffset} setLimit={setStockLimit} setOffset={setStockOffset} />
              <Table rows={stocks} />
            </div>
            <div className="panel">
              <header className="title-row"><h3>Movimientos</h3><button onClick={loadMoves}>Refrescar</button></header>
              <Pager limit={moveLimit} offset={moveOffset} setLimit={setMoveLimit} setOffset={setMoveOffset} />
              <Table rows={moves} />
            </div>
          </section>
        )}

        {tab === "invitados" && (
          <section className="grid-two">
            <div className="panel">
              <h3>Check-in QR</h3>
              <input placeholder="qr_code" value={checkin.qr_code} onChange={(e) => setCheckin({ ...checkin, qr_code: e.target.value })} />
              <input placeholder="companions_used" value={checkin.companions_used} onChange={(e) => setCheckin({ ...checkin, companions_used: Number(e.target.value || 0) })} />
              <button className="primary" onClick={doCheckin}>Registrar check-in</button>
              <pre>{checkinResult}</pre>
            </div>
            <div className="panel">
              <header className="title-row"><h3>Invitados</h3><button onClick={loadGuests}>Refrescar</button></header>
              <Pager limit={guestLimit} offset={guestOffset} setLimit={setGuestLimit} setOffset={setGuestOffset} />
              <Table rows={guests} />
            </div>
          </section>
        )}

        {tab === "reportes" && (
          <section className="grid-two">
            <div className="panel">
              <header className="title-row"><h3>Alertas</h3><button onClick={loadAlerts}>Refrescar</button></header>
              <Pager limit={alertLimit} offset={alertOffset} setLimit={setAlertLimit} setOffset={setAlertOffset} />
              <Table rows={alerts} />
            </div>
            <div className="panel">
              <header className="title-row"><h3>Resumen financiero</h3><button onClick={loadFinancial}>Cargar</button></header>
              <pre>{financial ? JSON.stringify(financial, null, 2) : "Sin datos"}</pre>
            </div>
          </section>
        )}

        {tab === "config" && (
          <section className="panel">
            <header className="title-row">
              <h3>Configuración del sistema</h3>
              <div className="inline-actions">
                <button onClick={loadConfig}>Cargar</button>
                <button className="primary" onClick={saveConfig}>Guardar</button>
              </div>
            </header>
            <div className="grid-two">
              <div>
                <label>country_code</label>
                <input value={config.country_code} onChange={(e) => setConfig({ ...config, country_code: e.target.value })} />
                <label>currency_code</label>
                <input value={config.currency_code} onChange={(e) => setConfig({ ...config, currency_code: e.target.value })} />
              </div>
              <div>
                <label>timezone</label>
                <input value={config.timezone} onChange={(e) => setConfig({ ...config, timezone: e.target.value })} />
                <label>costing_method</label>
                <select value={config.costing_method} onChange={(e) => setConfig({ ...config, costing_method: e.target.value })}>
                  <option value="AVG">AVG</option>
                  <option value="FIFO">FIFO</option>
                </select>
              </div>
            </div>
          </section>
        )}
      </main>

      {toast && <div className="toast show">{toast}</div>}
    </div>
  );
}
