import { useState } from 'react';
import Icon from './Icon';
import { api } from '../lib/api';

/**
 * Demo sign-in. admin / admin.
 *
 * This is a stub, not a security boundary: there is no session token, no
 * server-side check and no authorisation. It exists so the workspace opens the
 * way a real one would. Documented as such in the README.
 */
export default function Login({ onSignedIn }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('clerk');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    const result = await api.login(username.trim(), password);
    setBusy(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    onSignedIn({ ...result.user, role });
  }

  return (
    <div className="login">
      <div className="login-brand">
        <div className="login-mark" aria-hidden="true">
          <Icon name="inbox" size={22} />
        </div>
        <div>
          <h1 className="t-title-lg">Accounts Payable Copilot</h1>
          <p className="t-body-sm t-muted">Autonomous invoice validation for SAP S/4HANA</p>
        </div>
      </div>

      <form className="login-card panel" onSubmit={submit} noValidate>
        <div className="login-card-body">
          <h2 className="t-title">Sign in</h2>

          <div className="field">
            <label className="t-label" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="input"
              value={username}
              autoComplete="username"
              autoFocus
              onChange={(e) => setUsername(e.target.value)}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'login-error' : undefined}
            />
          </div>

          <div className="field">
            <label className="t-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className="input"
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'login-error' : undefined}
            />
          </div>

          <div className="field">
            <span className="t-label" id="role-label">
              Sign in as
            </span>
            <div className="segmented" role="radiogroup" aria-labelledby="role-label">
              {[
                ['clerk', 'AP Clerk'],
                ['exception', 'Exception team'],
                ['manager', 'AP Manager'],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={role === value}
                  className={`segment ${role === value ? 'is-selected' : ''}`}
                  onClick={() => setRole(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="t-body-sm t-faint field-help">
              Determines which queues you can act on.
            </p>
          </div>

          {/* Errors sit next to the fields they concern, not only at the top. */}
          {error ? (
            <p className="form-error" id="login-error" role="alert">
              <Icon name="error" size={14} />
              {error}
            </p>
          ) : null}

          <button className="btn btn-filled btn-lg login-submit" type="submit" disabled={busy}>
            {busy ? <span className="spinner" /> : <Icon name="lock" size={16} />}
            {busy ? 'Signing in' : 'Sign in'}
          </button>
        </div>

        <div className="login-hint">
          <Icon name="info" size={14} />
          <span>
            Demo credentials <code className="mono">admin</code> / <code className="mono">admin</code>
          </span>
        </div>
      </form>

      <p className="login-foot t-body-sm t-faint">
        DMI Hackathon 2026 &middot; Topic 3, provided by AWS
      </p>
    </div>
  );
}
