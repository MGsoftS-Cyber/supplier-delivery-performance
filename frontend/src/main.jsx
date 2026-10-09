/** The server owns metric definitions; React coordinates reviewable workflows. */
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, setCsrfToken } from "./api";
import AuthScreen from "./components/AuthScreen";
import "./styles.css";
const num = (v) =>
  v == null
    ? "Unavailable"
    : Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
const pct = (v) => (v == null ? "—" : (v * 100).toFixed(1) + "%");
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
function Field({ label, children }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}
function ScoreTable({ rows, onOpen }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {[
              "Supplier",
              "Due records",
              "On time",
              "OTIF",
              "Usable fill",
              "Defects",
              "Score",
              "Rank",
            ].map((x) => (
              <th key={x}>{x}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((x) => (
            <tr key={x.supplier_id}>
              <td>
                <button
                  className="text-button"
                  onClick={() => onOpen(x.supplier_id)}
                >
                  {x.supplier_name}
                </button>
                <small className="block">{x.supplier_id}</small>
              </td>
              <td>{x.due_records}</td>
              <td>{pct(x.on_time_rate)}</td>
              <td>{pct(x.otif_rate)}</td>
              <td>{pct(x.usable_fill_rate)}</td>
              <td>{pct(x.defect_rate)}</td>
              <td>
                <span className="pill">{num(x.score)}</span>
              </td>
              <td>{x.rank ?? "Not ranked"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function App() {
  const [user, U] = useState(null),
    [busy, B] = useState(false),
    [error, E] = useState(""),
    [message, M] = useState(""),
    [tab, T] = useState("Overview"),
    [stores, S] = useState([]),
    [selected, P] = useState(""),
    [datasets, D] = useState([]),
    [dataset, K] = useState(""),
    [analyses, A] = useState([]),
    [result, R] = useState(null),
    [preview, V] = useState(null),
    [source, O] = useState("Purchasing export"),
    [coverage, CV] = useState(today()),
    [grace, G] = useState(0),
    [minimum, MIN] = useState(3),
    [scenario, N] = useState("Supplier review"),
    [supplier, F] = useState(""),
    [status, ST] = useState("All statuses"),
    [checked, C] = useState([]),
    [comparison, J] = useState(null);
  async function task(fn) {
    B(true);
    E("");
    M("");
    try {
      await fn();
    } catch (e) {
      E(e.message);
    } finally {
      B(false);
    }
  }
  const write = (path, body) =>
    api("/v1" + path, {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  async function load() {
    const [s, a] = await Promise.all([api("/v1/stores"), api("/v1/analyses")]);
    S(s);
    A(a);
    P((old) => old || s[0]?.id || "");
  }
  useEffect(() => {
    api("/auth/session")
      .then(async (s) => {
        U(s.user);
        setCsrfToken(s.csrf_token);
        await load();
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!selected) {
      D([]);
      K("");
      return;
    }
    let active = true;
    api("/v1/stores/" + selected + "/datasets")
      .then((d) => {
        if (active) {
          D(d);
          K(d[0]?.id || "");
        }
      })
      .catch((e) => {
        if (active) E(e.message);
      });
    return () => {
      active = false;
    };
  }, [selected]);
  async function auth(registering, body) {
    await task(async () => {
      const s = await api("/auth/" + (registering ? "register" : "login"), {
        method: "POST",
        body: JSON.stringify(body),
      });
      U(s.user);
      setCsrfToken(s.csrf_token);
      await load();
    });
  }
  async function run() {
    await task(async () => {
      const a = await write("/stores/" + selected + "/analyses", {
        dataset_id: dataset,
        scenario_name: scenario,
        grace_days: Number(grace),
        minimum_due: Number(minimum),
      });
      R(a);
      F("");
      await load();
      T("Overview");
    });
  }
  function openSupplier(id) {
    F(id);
    T("Supplier scorecards");
  }
  const current = datasets.find((x) => x.id === dataset),
    activeStore = stores.find((x) => x.id === selected),
    stats = result?.results.summary,
    detail = result?.results.suppliers.find((x) => x.supplier_id === supplier);
  if (!user) return <AuthScreen onSubmit={auth} busy={busy} error={error} />;
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span>◈</span>
          <div>
            SupplyIQ<small>Supplier & delivery performance</small>
          </div>
        </div>
        <nav>
          {[
            "Overview",
            "Delivery data",
            "Analysis setup",
            "Supplier scorecards",
            "Delivery exceptions",
            "Reports & comparisons",
          ].map((t) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => T(t)}
            >
              {t}
            </button>
          ))}
        </nav>
        <div className="account">
          <small>{user.email}</small>
          <button
            onClick={() =>
              task(async () => {
                await api("/auth/logout", { method: "POST" });
                U(null);
                setCsrfToken("");
              })
            }
          >
            Sign out
          </button>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">
              PURCHASING INTELLIGENCE / {tab.toUpperCase()}
            </p>
            <h1>
              {tab === "Overview"
                ? "See which suppliers deliver on their promises"
                : tab}
            </h1>
            <p className="muted">
              Timeliness, received quantities and quality with clear reasons
              behind every score.
            </p>
          </div>
          <Field label="Active workspace">
            <select
              aria-label="Active workspace"
              value={selected}
              onChange={(e) => P(e.target.value)}
            >
              <option value="">Select workspace</option>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.unit}
                </option>
              ))}
            </select>
          </Field>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="success" role="status">
            {message}
          </p>
        )}
        {busy && (
          <p role="status" className="muted">
            Calculating or saving…
          </p>
        )}
        {tab === "Overview" && (
          <>
            <section className="card">
              <div className="section-head">
                <div>
                  <h2>Supplier performance outlook</h2>
                  <p className="muted">
                    {activeStore?.name || "Create a purchasing workspace"} ·{" "}
                    {result
                      ? `Snapshot through ${result.inputs.coverage_end}`
                      : "Start with delivery records"}
                  </p>
                </div>
                <div className="controls">
                  {!stores.length ? (
                    <button
                      disabled={busy}
                      onClick={() =>
                        task(async () => {
                          const d = await write("/demo");
                          await load();
                          P(d.store_id);
                          M(d.message);
                        })
                      }
                    >
                      Load demo data
                    </button>
                  ) : (
                    <button disabled={busy || !dataset} onClick={run}>
                      Analyze supplier performance
                    </button>
                  )}
                  <button
                    className="text-button"
                    onClick={() => T("Analysis setup")}
                  >
                    Edit assumptions
                  </button>
                </div>
              </div>
            </section>
            {result ? (
              <>
                <div className="metrics">
                  {[
                    ["On-time in-full", pct(stats.otif_rate)],
                    ["Usable fulfillment", pct(stats.usable_fill_rate)],
                    ["Overdue pending", num(stats.pending_overdue)],
                    ["Defective units", num(stats.defect_qty)],
                  ].map(([k, v]) => (
                    <div className="metric" key={k}>
                      <small>{k}</small>
                      <strong>{v}</strong>
                    </div>
                  ))}
                </div>
                <section className="card">
                  <div className="section-head">
                    <div>
                      <h2>Supplier comparison</h2>
                      <p className="muted">
                        {stats.due_records} mature commitments · {stats.not_due}{" "}
                        not yet due · {stats.ranked_suppliers} suppliers ranked
                      </p>
                    </div>
                    <span className="pill">
                      {result.inputs.grace_days}-day grace
                    </span>
                  </div>
                  <ScoreTable
                    rows={result.results.suppliers}
                    onOpen={openSupplier}
                  />
                  <p className="muted">
                    Score = 40% OTIF + 30% usable fulfillment + 30% retained
                    quality. Minimum {result.inputs.minimum_due} due records for
                    ranking.
                  </p>
                </section>
                <div className="grid two">
                  <section className="card">
                    <h2>Deadline exceptions by supplier</h2>
                    {result.results.suppliers.map((x) => (
                      <div className="segment-row" key={x.supplier_id}>
                        <span>{x.supplier_name}</span>
                        <div className="segment-track">
                          <i
                            style={{
                              width: `${((x.pending_overdue + x.late_receipts) / Math.max(1, x.due_records)) * 100}%`,
                            }}
                          />
                        </div>
                        <b>{x.pending_overdue + x.late_receipts}</b>
                      </div>
                    ))}
                    <p className="muted">
                      Late receipts plus pending mature commitments;
                      early/not-yet-due rows excluded.
                    </p>
                  </section>
                  <section className="card">
                    <h2>Quality & fulfillment context</h2>
                    <p>
                      {stats.received_qty} received / {stats.ordered_qty}{" "}
                      ordered {result.inputs.store.unit} on mature commitments
                    </p>
                    <p>
                      Defect rate <b>{pct(stats.defect_rate)}</b> · Return rate{" "}
                      <b>{pct(stats.return_rate)}</b>
                    </p>
                    <p>
                      Gross fulfillment <b>{pct(stats.fulfillment_rate)}</b>
                    </p>
                    <p className="muted">
                      Pending deliveries count against timeliness and
                      fulfillment. Missing receipt evidence leaves quality and
                      composite score unavailable.
                    </p>
                  </section>
                </div>
                <section className="card">
                  <h2>Interpretation notes</h2>
                  {[
                    ...result.inputs.quality.warnings,
                    ...result.results.warnings,
                  ].map((w, i) => (
                    <p key={i} className="muted">
                      {w}
                    </p>
                  ))}
                </section>
              </>
            ) : (
              <section className="card empty">
                <h2>Start with promised and actual deliveries</h2>
                <p>
                  Import delivery snapshots or load synthetic demonstration
                  records, then review supplier performance.
                </p>
              </section>
            )}
          </>
        )}
        {tab === "Delivery data" && (
          <>
            <section className="card">
              <h2>Create a purchasing workspace</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget,
                    body = Object.fromEntries(new FormData(form));
                  task(async () => {
                    const s = await write("/stores", body);
                    P(s.id);
                    await load();
                    form.reset();
                    M("Workspace created. Import its delivery records below.");
                  });
                }}
              >
                <div className="grid two">
                  <Field label="Workspace name">
                    <input
                      aria-label="Workspace name"
                      name="name"
                      required
                      maxLength={120}
                    />
                  </Field>
                  <Field label="Base unit">
                    <input
                      aria-label="Base unit"
                      name="unit"
                      defaultValue="unit"
                      required
                      maxLength={20}
                    />
                  </Field>
                </div>
                <button disabled={busy}>Create workspace</button>
              </form>
            </section>
            <section className="card">
              <h2>Preview supplier deliveries</h2>
              <p>
                One record per single-receipt commitment. Use{" "}
                <code>examples/deliveries.csv</code> for the exact 10-column
                format.
              </p>
              <p className="muted">
                Blank actual date means pending with zero received units.
                Defects and returns must be disjoint counts. All quantities
                share the workspace base unit.
              </p>
              <div className="grid three">
                <Field label="Dataset source">
                  <input
                    aria-label="Dataset source"
                    value={source}
                    onChange={(e) => O(e.target.value)}
                  />
                </Field>
                <Field label="Coverage end">
                  <input
                    aria-label="Coverage end"
                    type="date"
                    max={today()}
                    value={coverage}
                    onChange={(e) => CV(e.target.value)}
                  />
                </Field>
                <Field label="Deliveries CSV">
                  <input
                    aria-label="Deliveries CSV"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(e) => {
                      const f = e.target.files[0];
                      if (f)
                        task(async () => {
                          if (f.size > 2000000)
                            throw Error("Maximum CSV size is 2 MB.");
                          V(
                            await write("/imports/deliveries/preview", {
                              csv_text: await f.text(),
                            }),
                          );
                        });
                    }}
                  />
                </Field>
              </div>
              <p className="muted">
                Coverage declares an end-of-day snapshot. Every order and actual
                receipt must lie on/before it. Future promises are allowed;
                split shipments need a separate event model.
              </p>
              {preview && (
                <div className="import-preview">
                  <p>{preview.rows.length} valid deliveries</p>
                  {preview.errors.map((x, i) => (
                    <p key={i} className="error">
                      Row {x.row}: {x.message}
                    </p>
                  ))}
                  <button
                    disabled={busy || !selected || !preview.valid}
                    onClick={() =>
                      task(async () => {
                        const d = await write(
                          "/stores/" + selected + "/datasets",
                          {
                            source,
                            coverage_end: coverage,
                            deliveries: preview.rows,
                          },
                        );
                        D(await api("/v1/stores/" + selected + "/datasets"));
                        K(d.id);
                        V(null);
                        M("Immutable delivery dataset saved.");
                      })
                    }
                  >
                    Save reviewed dataset
                  </button>
                </div>
              )}
            </section>
            <section className="card">
              <h2>Dataset versions</h2>
              {datasets.map((d) => (
                <div className="saved" key={d.id}>
                  <div>
                    <b>{d.source}</b>
                    <small>
                      {d.quality.count} records · {d.quality.suppliers}{" "}
                      suppliers · coverage through {d.coverage_end}
                    </small>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => {
                      K(d.id);
                      T("Analysis setup");
                    }}
                  >
                    Use dataset
                  </button>
                </div>
              ))}
            </section>
          </>
        )}
        {tab === "Analysis setup" && (
          <section className="card">
            <h2>Supplier review assumptions</h2>
            <div className="grid three">
              <Field label="Dataset version">
                <select
                  aria-label="Dataset version"
                  value={dataset}
                  onChange={(e) => K(e.target.value)}
                >
                  <option value="">Select dataset</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.source} · {d.coverage_end}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Review name">
                <input
                  aria-label="Review name"
                  value={scenario}
                  onChange={(e) => N(e.target.value)}
                  maxLength={120}
                />
              </Field>
              <Field label="Grace days">
                <input
                  aria-label="Grace days"
                  type="number"
                  min="0"
                  max="30"
                  value={grace}
                  onChange={(e) => G(e.target.value)}
                />
              </Field>
              <Field label="Minimum due records">
                <input
                  aria-label="Minimum due records"
                  type="number"
                  min="1"
                  max="100"
                  value={minimum}
                  onChange={(e) => MIN(e.target.value)}
                />
              </Field>
            </div>
            <p>
              Snapshot date:{" "}
              <b>{current?.coverage_end || "Select a dataset"}</b>. Evaluation
              uses its complete coverage date.
            </p>
            <p className="muted">
              Adjusted deadline = promised date + grace days. Only deadlines
              on/before the snapshot enter performance denominators. Grace can
              change the eligible population as well as the timeliness result.
            </p>
            <p>
              Score uses fixed 40/30/30 weights. Minimum sample size controls
              ranking eligibility; it is not a statistical confidence guarantee.
            </p>
            <button disabled={busy || !dataset} onClick={run}>
              Analyze and save review
            </button>
          </section>
        )}
        {tab === "Supplier scorecards" && (
          <section className="card">
            <h2>Review supplier reliability</h2>
            {result ? (
              <>
                <ScoreTable
                  rows={result.results.suppliers}
                  onOpen={openSupplier}
                />
                <Field label="Supplier detail">
                  <select
                    aria-label="Supplier detail"
                    value={supplier}
                    onChange={(e) => F(e.target.value)}
                  >
                    <option value="">Select a supplier</option>
                    {result.results.suppliers.map((x) => (
                      <option key={x.supplier_id} value={x.supplier_id}>
                        {x.supplier_name}
                      </option>
                    ))}
                  </select>
                </Field>
                {detail && (
                  <>
                    <h3>{detail.supplier_name}: reasons behind the score</h3>
                    <div className="metrics">
                      {[
                        ["Score", num(detail.score)],
                        ["Due records", detail.due_records],
                        ["Late receipts", detail.late_receipts],
                        ["Pending overdue", detail.pending_overdue],
                      ].map(([k, v]) => (
                        <div className="metric" key={k}>
                          <small>{k}</small>
                          <strong>{v}</strong>
                        </div>
                      ))}
                    </div>
                    {detail.reasons.map((x, i) => (
                      <p key={i}>{x}</p>
                    ))}
                    <p className="muted">
                      Mean delay across due received records:{" "}
                      {num(detail.average_late_days)} days (on-time = 0).
                      Maximum pending overdue age: {detail.max_overdue_days}{" "}
                      days.
                    </p>
                  </>
                )}
              </>
            ) : (
              <p>Save or open a review first.</p>
            )}
          </section>
        )}
        {tab === "Delivery exceptions" && (
          <section className="card">
            <h2>Delivery evidence and exceptions</h2>
            {result ? (
              <>
                <div className="grid two">
                  <Field label="Supplier filter">
                    <select
                      aria-label="Supplier filter"
                      value={supplier}
                      onChange={(e) => F(e.target.value)}
                    >
                      <option value="">All suppliers</option>
                      {result.results.suppliers.map((x) => (
                        <option key={x.supplier_id} value={x.supplier_id}>
                          {x.supplier_name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Status filter">
                    <select
                      aria-label="Status filter"
                      value={status}
                      onChange={(e) => ST(e.target.value)}
                    >
                      {[
                        "All statuses",
                        "Overdue pending",
                        "Late receipt",
                        "On-time short",
                        "On-time in full",
                        "Not yet due",
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </Field>
                </div>
                <p className="muted">
                  First 200 matching records shown. Export the delivery CSV for
                  the full snapshot.
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Delivery",
                          "Supplier",
                          "Promise",
                          "Receipt",
                          "Ordered",
                          "Received",
                          "Defects",
                          "Returns",
                          "Status",
                        ].map((x) => (
                          <th key={x}>{x}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.deliveries
                        .filter(
                          (x) =>
                            (!supplier || x.supplier_id === supplier) &&
                            (status === "All statuses" || x.status === status),
                        )
                        .slice(0, 200)
                        .map((x) => (
                          <tr key={x.delivery_id}>
                            <td>{x.delivery_id}</td>
                            <td>{x.supplier_id}</td>
                            <td>{x.promised_date}</td>
                            <td>{x.actual_date || "Pending"}</td>
                            <td>{x.ordered_qty}</td>
                            <td>{x.received_qty}</td>
                            <td>{x.defect_qty}</td>
                            <td>{x.returned_qty}</td>
                            <td>{x.status}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p>Save or open a review first.</p>
            )}
          </section>
        )}
        {tab === "Reports & comparisons" && (
          <section className="card">
            <h2>Saved supplier reviews</h2>
            <p className="muted">
              Compare grace and minimum sample assumptions using the same
              dataset.
            </p>
            {analyses.map((a) => (
              <div className="saved" key={a.id}>
                <input
                  type="checkbox"
                  aria-label={"Compare " + a.inputs.scenario_name}
                  checked={checked.includes(a.id)}
                  onChange={(e) =>
                    C(
                      e.target.checked
                        ? [...checked, a.id]
                        : checked.filter((x) => x !== a.id),
                    )
                  }
                />
                <div>
                  <b>{a.inputs.scenario_name}</b>
                  <small>
                    {a.inputs.store.name} · {a.inputs.coverage_end} · grace{" "}
                    {a.inputs.grace_days} days
                  </small>
                </div>
                <button
                  className="text-button"
                  onClick={() => {
                    R(a);
                    T("Overview");
                  }}
                >
                  Open review
                </button>
                {[
                  ["json", "JSON report"],
                  ["suppliers", "Supplier CSV"],
                  ["deliveries", "Delivery CSV"],
                ].map(([f, label]) => (
                  <a
                    key={f}
                    href={"/api/v1/analyses/" + a.id + "/report?format=" + f}
                  >
                    {label}
                  </a>
                ))}
              </div>
            ))}
            <button
              disabled={busy || checked.length < 2 || checked.length > 10}
              onClick={() =>
                task(async () =>
                  J(await write("/comparisons", { analysis_ids: checked })),
                )
              }
            >
              Compare selected reviews
            </button>
            {comparison && (
              <>
                <h3>Review comparison</h3>
                <p>{comparison.message}</p>
                <table>
                  <thead>
                    <tr>
                      <th>Review</th>
                      <th>Due records</th>
                      <th>OTIF</th>
                      <th>Usable fill</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.analyses.map((a) => (
                      <tr key={a.id}>
                        <td>{a.inputs.scenario_name}</td>
                        <td>{a.results.summary.due_records}</td>
                        <td>{pct(a.results.summary.otif_rate)}</td>
                        <td>{pct(a.results.summary.usable_fill_rate)}</td>
                        <td>{num(a.results.summary.score)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </section>
        )}
        <footer>
          SupplyIQ v1.0 · Supplier delivery analytics and saved scorecards
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
