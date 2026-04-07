import { useEffect, useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import { getToken } from '../../../../modules/tiro-shared/auth-store';
import type { RegolaRischio } from '../../../../modules/tiro-shared/types';

// ─── Design tokens ────────────────────────────────────────────────────────────
const C = {
  bg: '#0F172A',
  surface: '#1E293B',
  surfaceElevated: '#334155',
  border: '#475569',
  borderSubtle: '#334155',
  textPrimary: '#F8FAFC',
  textSecondary: '#CBD5E1',
  textMuted: '#94A3B8',
  primary: '#0EA5E9',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  secondary: '#8B5CF6',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const rischioColor = (livello: string) => {
  switch (livello) {
    case 'basso':   return C.success;
    case 'medio':   return C.warning;
    case 'alto':    return '#F97316';
    case 'critico': return C.error;
    default:        return C.textMuted;
  }
};

// Check if current user has admin-level access.
// We check for token presence and a stored role hint; fall back to checking
// localStorage for a role key written by the login flow.
const hasAdminAccess = (): boolean => {
  if (!getToken()) return false;
  try {
    const role = localStorage.getItem('tiro_ruolo') ?? '';
    if (role === 'titolare' || role === 'responsabile') return true;
    // If role is not stored yet, default to allowed (token presence is enough)
    if (!role) return true;
    return false;
  } catch {
    return true; // localStorage not available — allow access
  }
};

// ─── RischioBadge ─────────────────────────────────────────────────────────────
function RischioBadge({ livello }: { livello: string }) {
  const color = rischioColor(livello);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        background: `${color}22`,
        color,
        textTransform: 'capitalize',
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: color,
          display: 'inline-block',
          flexShrink: 0,
        }}
      />
      {livello}
    </span>
  );
}

// ─── Tab bar ──────────────────────────────────────────────────────────────────
type TabId = 'regole' | 'utenti' | 'configurazione' | 'registro';

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'regole',         label: 'Regole Rischio',  icon: '⚖️' },
  { id: 'utenti',         label: 'Utenti',           icon: '👥' },
  { id: 'configurazione', label: 'Configurazione',   icon: '⚙️' },
  { id: 'registro',       label: 'Registro',         icon: '📋' },
];

// ─── Placeholder tab ──────────────────────────────────────────────────────────
function PlaceholderTab({ label }: { label: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 16px',
        color: C.textMuted,
        fontSize: 13,
        gap: 8,
      }}
    >
      <span style={{ fontSize: 36 }}>🚧</span>
      <span style={{ fontWeight: 500, color: C.textSecondary, fontSize: 15 }}>
        {label}
      </span>
      <span>Sezione in sviluppo</span>
    </div>
  );
}

// ─── Regole Rischio tab ───────────────────────────────────────────────────────
function RegoleTab() {
  const [regole, setRegole] = useState<RegolaRischio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await tiroApi.getRegole();
        setRegole(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Errore caricamento regole');
      } finally {
        setLoading(false);
      }
    };
    void fetch();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, color: C.textMuted, fontSize: 13 }}>
        Caricamento regole...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          margin: 16,
          background: `${C.error}22`,
          border: `1px solid ${C.error}44`,
          borderRadius: 8,
          padding: '12px 16px',
          color: C.error,
          fontSize: 13,
        }}
      >
        {error}
      </div>
    );
  }

  return (
    <div>
      {/* Table header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 2fr 1fr',
          gap: 0,
          padding: '10px 16px',
          borderBottom: `1px solid ${C.borderSubtle}`,
          fontSize: 11,
          fontWeight: 600,
          color: C.textMuted,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        <span>Pattern Azione</span>
        <span>Livello Rischio</span>
        <span>Descrizione</span>
        <span>Auto-Approvazione</span>
      </div>

      {regole.length === 0 ? (
        <div
          style={{
            padding: '32px 16px',
            color: C.textMuted,
            fontSize: 13,
            textAlign: 'center',
          }}
        >
          Nessuna regola di rischio configurata
        </div>
      ) : (
        regole.map(r => (
          <div
            key={r.id}
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 2fr 1fr',
              gap: 0,
              padding: '12px 16px',
              borderBottom: `1px solid ${C.borderSubtle}`,
              alignItems: 'center',
              transition: 'background 200ms',
            }}
            onMouseEnter={e =>
              ((e.currentTarget as HTMLDivElement).style.background =
                C.surfaceElevated)
            }
            onMouseLeave={e =>
              ((e.currentTarget as HTMLDivElement).style.background = 'transparent')
            }
          >
            {/* Pattern */}
            <div
              style={{
                fontFamily: 'monospace',
                fontSize: 13,
                color: C.primary,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {r.pattern_azione}
            </div>

            {/* Rischio */}
            <div>
              <RischioBadge livello={r.livello_rischio} />
            </div>

            {/* Descrizione */}
            <div
              style={{
                fontSize: 13,
                color: C.textSecondary,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {r.descrizione ?? <span style={{ color: C.textMuted }}>—</span>}
            </div>

            {/* Auto-approvazione */}
            <div style={{ display: 'flex', alignItems: 'center' }}>
              {r.approvazione_automatica ? (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 12,
                    fontWeight: 500,
                    color: C.success,
                  }}
                >
                  <span
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      background: `${C.success}22`,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 10,
                    }}
                  >
                    ✓
                  </span>
                  Sì
                </span>
              ) : (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 12,
                    fontWeight: 500,
                    color: C.textMuted,
                  }}
                >
                  <span
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: '50%',
                      background: `${C.textMuted}22`,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 10,
                    }}
                  >
                    ✕
                  </span>
                  No
                </span>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroSistemaPage() {
  const [activeTab, setActiveTab] = useState<TabId>('regole');

  if (!hasAdminAccess()) {
    return (
      <div
        style={{
          padding: 24,
          fontFamily: 'Inter, -apple-system, sans-serif',
          fontSize: 14,
          color: C.textPrimary,
          background: C.bg,
          minHeight: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 12,
            padding: '40px 48px',
            textAlign: 'center',
            maxWidth: 420,
          }}
        >
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔒</div>
          <h2
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: C.textPrimary,
              margin: '0 0 8px',
            }}
          >
            Accesso non autorizzato
          </h2>
          <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
            Questa sezione è riservata agli utenti con ruolo{' '}
            <strong style={{ color: C.textSecondary }}>Titolare</strong> o{' '}
            <strong style={{ color: C.textSecondary }}>Responsabile</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 24,
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontSize: 14,
        color: C.textPrimary,
        background: C.bg,
        minHeight: '100%',
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 20,
            fontWeight: 600,
            color: C.textPrimary,
            margin: 0,
            marginBottom: 4,
            letterSpacing: '-0.01em',
          }}
        >
          Sistema
        </h1>
        <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
          Amministrazione e configurazione del sistema TIRO
        </p>
      </div>

      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          gap: 2,
          marginBottom: 0,
          borderBottom: `1px solid ${C.borderSubtle}`,
        }}
      >
        {TABS.map(t => {
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '10px 16px',
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                cursor: 'pointer',
                border: 'none',
                borderBottom: active
                  ? `2px solid ${C.primary}`
                  : '2px solid transparent',
                background: 'transparent',
                color: active ? C.textPrimary : C.textMuted,
                fontFamily: 'inherit',
                transition: 'color 150ms, border-color 150ms',
                marginBottom: -1,
              }}
              onMouseEnter={e => {
                if (!active)
                  (e.currentTarget as HTMLButtonElement).style.color =
                    C.textSecondary;
              }}
              onMouseLeave={e => {
                if (!active)
                  (e.currentTarget as HTMLButtonElement).style.color = C.textMuted;
              }}
            >
              <span>{t.icon}</span>
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.borderSubtle}`,
          borderTop: 'none',
          borderRadius: '0 0 8px 8px',
          overflow: 'hidden',
        }}
      >
        {activeTab === 'regole'         && <RegoleTab />}
        {activeTab === 'utenti'         && <PlaceholderTab label="Gestione Utenti" />}
        {activeTab === 'configurazione' && <PlaceholderTab label="Configurazione" />}
        {activeTab === 'registro'       && <PlaceholderTab label="Registro Attività" />}
      </div>
    </div>
  );
}

export const Component = TiroSistemaPage;
