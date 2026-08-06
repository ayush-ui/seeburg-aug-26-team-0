import { useState } from 'react';
import Icon from '../components/Icon';
import { Chip } from '../components/Chip';
import { api } from '../lib/api';

/**
 * Reports the company's own SOP already mandates (AP-SOP-001 section 9.3),
 * generated from the batch that just ran. Nothing here is invented: every
 * report on offer appears in the SOP's reporting table with its cadence and
 * its audience.
 */
export default function Reports({ batch }) {
  const catalogue = api.reportCatalogue();
  const [active, setActive] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);

  const outcomes = batch.outcomes;
  const exceptions = outcomes.filter((o) => !o.canPark).length;
  const kpis = [
    {
      name: 'Exception rate',
      value: (exceptions / outcomes.length) * 100,
      target: 5,
      unit: '%',
    },
    {
      name: 'Duplicate invoice rate',
      value:
        (outcomes.filter((o) => o.findings.some((f) => f.ruleId === 'R16' && f.status === 'FAIL')).length /
          outcomes.length) *
        100,
      target: 0.5,
      unit: '%',
    },
    {
      name: 'No-PO invoice rate',
      value:
        (outcomes.filter((o) => o.findings.some((f) => f.ruleId === 'R01' && f.status === 'FAIL')).length /
          outcomes.length) *
        100,
      target: 2,
      unit: '%',
    },
  ];

  async function generate(id) {
    setActive(id);
    setBusy(true);
    setReport(null);
    const r = await api.generateReport(id, outcomes);
    setBusy(false);
    setReport(r);
  }

  return (
    <div className="view view-reports">
      <div className="reports-side">
        <div className="panel">
          <div className="panel-head">
            <Icon name="chart" size={16} />
            <span className="t-title">KPIs this batch</span>
          </div>
          <div className="kpis">
            {kpis.map((k) => {
              const breach = k.value > k.target;
              return (
                <div className="kpi" key={k.name}>
                  <div className="kpi-head">
                    <span className="t-body-sm">{k.name}</span>
                    {/* Target status carries an icon and a word, not just colour. */}
                    <Chip tone={breach ? 'error' : 'success'} icon={breach ? 'warning' : 'check'}>
                      {breach ? 'Over target' : 'On target'}
                    </Chip>
                  </div>
                  <div className="kpi-value">
                    <span className="num kpi-num">{k.value.toFixed(1)}</span>
                    <span className="t-body-sm t-faint">
                      {k.unit} · target &lt; {k.target}
                      {k.unit}
                    </span>
                  </div>
                  <div className="meter" role="img" aria-label={`${k.value.toFixed(1)}${k.unit} against a target of ${k.target}${k.unit}`}>
                    <span
                      className={`meter-fill ${breach ? 'is-breach' : ''}`}
                      style={{ width: `${Math.min(100, (k.value / Math.max(k.target * 2, 1)) * 100)}%` }}
                    />
                    <span className="meter-target" style={{ left: '50%' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <Icon name="doc" size={16} />
            <span className="t-title">Reports your SOP requires</span>
          </div>
          <ul className="report-list">
            {catalogue.map((r) => (
              <li key={r.id}>
                <button
                  className={`report-item ${active === r.id ? 'is-selected' : ''}`}
                  onClick={() => generate(r.id)}
                  aria-current={active === r.id}
                >
                  <span className="report-name t-body-sm">{r.name}</span>
                  <span className="report-meta t-body-sm t-faint">
                    {r.cadence} · {r.audience}
                  </span>
                  <Icon name="chevron" size={14} className="t-faint" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="panel report-canvas">
        {!active ? (
          <div className="empty">
            <Icon name="chart" size={28} />
            <p className="t-body">Pick a report to generate it from this batch.</p>
            <p className="t-body-sm t-faint">
              Every report listed is mandated by AP-SOP-001 section 9.3, with the cadence and
              audience the SOP specifies.
            </p>
          </div>
        ) : busy ? (
          <div className="empty">
            <span className="spinner" />
            <p className="t-body-sm">Generating…</p>
          </div>
        ) : report ? (
          <>
            <div className="panel-head">
              <span className="t-title">{report.title}</span>
              <span className="spacer" />
              <button className="btn btn-outlined" onClick={() => window.print()}>
                <Icon name="download" size={14} /> Export
              </button>
            </div>
            <div className="report-body">
              <p className="t-body-sm t-faint report-sub">{report.subtitle}</p>

              {report.chart && report.chart.length ? (
                <div className="bars" role="img" aria-label={report.columns.join(' by ')}>
                  {report.chart.map((c) => {
                    const max = Math.max(...report.chart.map((x) => x.value), 1);
                    return (
                      <div className="bar-row" key={c.label}>
                        <span className="bar-label t-body-sm">{c.label}</span>
                        <span className="bar-track">
                          <span className="bar-fill" style={{ width: `${(c.value / max) * 100}%` }} />
                        </span>
                        <span className="num bar-value">{c.value}</span>
                      </div>
                    );
                  })}
                </div>
              ) : null}

              {report.rows.length === 0 ? (
                <div className="empty">
                  <Icon name="check" size={24} />
                  <p className="t-body-sm">Nothing to report for this batch.</p>
                </div>
              ) : (
                <div className="table-scroll">
                  <table className="data report-table">
                    <thead>
                      <tr>
                        {report.columns.map((c, i) => (
                          <th key={c} className={i > 0 && typeof report.rows[0][i] === 'number' ? 'num' : ''}>
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {report.rows.map((row, i) => (
                        <tr key={i} className="no-hover">
                          {row.map((cell, j) => (
                            <td key={j} className={typeof cell === 'number' ? 'num' : ''}>
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
