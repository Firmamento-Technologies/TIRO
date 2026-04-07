import { useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';

const styles = {
  root: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    background: '#0F172A',
    color: '#F8FAFC',
    fontFamily: 'sans-serif',
  } as React.CSSProperties,
  card: {
    background: '#1E293B',
    borderRadius: 12,
    padding: '40px 48px',
    width: 360,
    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  } as React.CSSProperties,
  title: {
    fontSize: 24,
    fontWeight: 700,
    marginBottom: 8,
    color: '#F8FAFC',
  } as React.CSSProperties,
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
    marginBottom: 32,
  } as React.CSSProperties,
  label: {
    display: 'block',
    fontSize: 13,
    color: '#CBD5E1',
    marginBottom: 6,
    fontWeight: 500,
  } as React.CSSProperties,
  input: {
    width: '100%',
    padding: '10px 12px',
    background: '#0F172A',
    border: '1px solid #334155',
    borderRadius: 8,
    color: '#F8FAFC',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box' as const,
    marginBottom: 20,
  } as React.CSSProperties,
  button: {
    width: '100%',
    padding: '11px 0',
    background: '#3B82F6',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: 4,
  } as React.CSSProperties,
  error: {
    background: '#450A0A',
    border: '1px solid #B91C1C',
    color: '#FCA5A5',
    borderRadius: 8,
    padding: '10px 14px',
    fontSize: 13,
    marginBottom: 20,
  } as React.CSSProperties,
};

export function TiroLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await tiroApi.login(email, password);
      // Redirect to dashboard after successful login
      window.location.hash = '#/tiro-cruscotto';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore di autenticazione');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.root}>
      <div style={styles.card}>
        <div style={styles.title}>TIRO</div>
        <div style={styles.subtitle}>Accedi al tuo account</div>

        {error && <div style={styles.error}>{error}</div>}

        <form onSubmit={e => { void handleSubmit(e); }}>
          <label style={styles.label} htmlFor="tiro-email">
            Email
          </label>
          <input
            id="tiro-email"
            style={styles.input}
            type="email"
            autoComplete="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />

          <label style={styles.label} htmlFor="tiro-password">
            Password
          </label>
          <input
            id="tiro-password"
            style={styles.input}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          <button style={styles.button} type="submit" disabled={loading}>
            {loading ? 'Accesso in corso...' : 'Accedi'}
          </button>
        </form>
      </div>
    </div>
  );
}

export const Component = TiroLoginPage;
