import { useCallback, useEffect, useState } from 'react';
import Icon from './components/Icon';
import { Chip } from './components/Chip';
import Login from './components/Login';
import Approvals from './views/Approvals';
import Exceptions from './views/Exceptions';
import Reports from './views/Reports';
import { api, runtime, selectProvider } from './lib/api';

const TABS = [
  { id: 'approvals', label: 'Approvals', icon: 'inbox' },
  { id: 'exceptions', label: 'Exceptions', icon: 'flag' },
  { id: 'reports', label: 'Reports', icon: 'chart' },
];

/** Tab and selected invoice live in the URL hash, so a view can be linked to. */
function readHash() {
  const [tab, ref] = window.location.hash.replace(/^#\/?/, '').split('/');
  return { tab: TABS.some((t) => t.id === tab) ? tab : 'approvals', ref: ref || null };
}

export default function App() {
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('ap-theme') || 'dark');
  const [route, setRoute] = useState(readHash);
  const [batch, setBatch] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ap-theme', theme);
  }, [theme]);

  useEffect(() => {
    const onHash = () => setRoute(readHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const go = useCallback((tab, ref) => {
    window.location.hash = ref ? `/${tab}/${ref}` : `/${tab}`;
  }, []);

  const [source, setSource] = useState(null);

  const loadBatch = useCallback(async (rerun = false) => {
    setLoading(true);
    try {
      const b = rerun ? await api.runBatch() : await api.getBatch();
      setBatch(b);
      setSource({ ...runtime });
    } catch (err) {
      setBatch({ error: err.message, outcomes: [] });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!user) return;
    selectProvider().then(() => loadBatch());
  }, [user, loadBatch]);

  function onParked(results) {
    setBatch((b) => ({
      ...b,
      outcomes: b.outcomes.map((o) => {
        const hit = results.find((r) => r.reference === o.invoice.reference);
        return hit ? { ...o, parked: hit } : o;
      }),
    }));
  }

  if (!user) {
    return (
      <>
        <ThemeToggle theme={theme} setTheme={setTheme} floating />
        <Login onSignedIn={setUser} />
      </>
    );
  }

  const approvals = batch ? batch.outcomes.filter((o) => o.canPark).length : 0;
  const exceptions = batch ? batch.outcomes.filter((o) => !o.canPark).length : 0;
  const counts = { approvals, exceptions, reports: null };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Icon name="inbox" size={16} />
          </span>
          <span className="t-title">AP Copilot</span>
        </div>

        <nav className="tabs" role="tablist" aria-label="Workspace">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={route.tab === t.id}
              className={`tab ${route.tab === t.id ? 'is-selected' : ''}`}
              onClick={() => go(t.id)}
            >
              <Icon name={t.icon} size={16} />
              {t.label}
              {counts[t.id] !== null && counts[t.id] !== undefined ? (
                <span className={`tab-count ${t.id === 'exceptions' && counts[t.id] > 0 ? 'is-alert' : ''}`}>
                  {counts[t.id]}
                </span>
              ) : null}
            </button>
          ))}
        </nav>

        <div className="topbar-end">
          {batch ? (
            <span className="batch-meta t-body-sm t-faint">
              {source?.source === 'live' ? (
                <span className="chip chip-success source-chip">
                  <Icon name="check" size={12} /> Live SAP
                </span>
              ) : (
                <span className="chip chip-warn source-chip" title="The backend is not running; showing seeded data">
                  <Icon name="warning" size={12} /> Seeded data
                </span>
              )}
              {batch.label} · {batch.outcomes.length} invoices · {batch.sapCalls} SAP calls ·{' '}
              {(batch.durationMs / 1000).toFixed(1)}s
            </span>
          ) : null}
          <button className="btn btn-icon" onClick={() => loadBatch(true)} aria-label="Re-run today's batch against SAP" disabled={loading}>
            {loading ? <span className="spinner" /> : <Icon name="refresh" size={16} />}
          </button>
          <ThemeToggle theme={theme} setTheme={setTheme} />
          <div className="user">
            <span className="avatar" aria-hidden="true">
              {user.initials}
            </span>
            <span className="t-body-sm">{ROLE_LABEL[user.role]}</span>
          </div>
          <button className="btn btn-icon" onClick={() => setUser(null)} aria-label="Sign out">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </header>

      <main className="content">
        {!batch ? (
          <div className="panel empty">
            <span className="spinner" />
            <p className="t-body">Reading today's invoices and validating against SAP…</p>
            <p className="t-body-sm t-faint">Each invoice is checked against live purchase order and goods receipt data.</p>
          </div>
        ) : batch.error ? (
          <div className="panel empty">
            <Icon name="error" size={28} />
            <p className="t-body">{batch.error}</p>
            <button className="btn btn-outlined" onClick={() => loadBatch(true)}>
              <Icon name="refresh" size={14} /> Try again
            </button>
          </div>
        ) : route.tab === 'approvals' ? (
          <Approvals
            batch={batch}
            selected={route.ref}
            onSelect={(ref) => go('approvals', ref)}
            onParked={onParked}
            role={user.role}
          />
        ) : route.tab === 'exceptions' ? (
          <Exceptions batch={batch} selected={route.ref} onSelect={(ref) => go('exceptions', ref)} />
        ) : (
          <Reports batch={batch} />
        )}
      </main>
    </div>
  );
}

const ROLE_LABEL = {
  clerk: 'AP Clerk',
  exception: 'Exception team',
  manager: 'AP Manager',
};

function ThemeToggle({ theme, setTheme, floating }) {
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <button
      className={`btn btn-icon ${floating ? 'theme-floating' : ''}`}
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
    </button>
  );
}
