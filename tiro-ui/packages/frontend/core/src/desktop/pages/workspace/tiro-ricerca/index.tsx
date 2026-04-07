import { useEffect, useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import type { Flusso } from '../../../../modules/tiro-shared/types';

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
const formatRelative = (ts: string) => {
  const diff = Date.now() - new Date(ts).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'ora';
  if (minutes < 60) return `${minutes}m fa`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h fa`;
  return new Date(ts).toLocaleDateString('it-IT');
};

const canaleColor = (canale: string) => {
  switch (canale.toLowerCase()) {
    case 'email':     return C.primary;
    case 'whatsapp':  return C.success;
    case 'telefono':  return C.warning;
    case 'incontro':  return C.secondary;
    default:          return C.textMuted;
  }
};

const canaleIcon = (canale: string) => {
  switch (canale.toLowerCase()) {
    case 'email':    return '✉';
    case 'whatsapp': return '💬';
    case 'telefono': return '📞';
    case 'incontro': return '🤝';
    default:         return '📄';
  }
};

// ─── Canale Badge ─────────────────────────────────────────────────────────────
function CanaleBadge({ canale }: { canale: string }) {
  const color = canaleColor(canale);
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 500,
        background: `${color}22`,
        color,
        whiteSpace: 'nowrap',
        textTransform: 'capitalize',
      }}
    >
      {canaleIcon(canale)} {canale}
    </span>
  );
}

// ─── Result Card ──────────────────────────────────────────────────────────────
function FlussoCard({ flusso }: { flusso: Flusso }) {
  const preview = (flusso.contenuto ?? '').slice(0, 200);

  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.borderSubtle}`,
        borderRadius: 8,
        padding: '14px 16px',
        transition: 'border-color 200ms, background 200ms',
      }}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.borderColor = C.border;
        el.style.background = C.surfaceElevated;
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.borderColor = C.borderSubtle;
        el.style.background = C.surface;
      }}
    >
      {/* Row 1: oggetto + canale + timestamp */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          marginBottom: 8,
          flexWrap: 'wrap',
        }}
      >
        <span
          style={{
            flex: 1,
            fontSize: 14,
            fontWeight: 600,
            color: C.textPrimary,
            minWidth: 0,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {flusso.oggetto ?? '(nessun oggetto)'}
        </span>
        <CanaleBadge canale={flusso.canale} />
        <span style={{ fontSize: 11, color: C.textMuted, flexShrink: 0 }}>
          {formatRelative(flusso.ricevuto_il)}
        </span>
      </div>

      {/* Row 2: preview contenuto */}
      {preview && (
        <p
          style={{
            fontSize: 13,
            color: C.textMuted,
            margin: 0,
            lineHeight: 1.5,
            wordBreak: 'break-word',
          }}
        >
          {preview}
          {(flusso.contenuto ?? '').length > 200 && (
            <span style={{ color: C.textMuted }}> …</span>
          )}
        </p>
      )}

      {/* Row 3: meta */}
      <div
        style={{
          marginTop: 8,
          fontSize: 11,
          color: C.textMuted,
          display: 'flex',
          gap: 12,
        }}
      >
        <span>Soggetto #{flusso.soggetto_id}</span>
        <span style={{ textTransform: 'capitalize' }}>
          {flusso.direzione}
        </span>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type TabType = 'flussi' | 'risorse';

export function TiroRicercaPage() {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<TabType>('flussi');
  const [flussi, setFlussi] = useState<Flusso[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Fetch all data on mount (once per tab switch)
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        if (tab === 'flussi') {
          const data = await tiroApi.getFlussi();
          setFlussi(data);
        }
        // risorse: future endpoint — for now nothing to load
        setLoaded(true);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Errore caricamento dati');
      } finally {
        setLoading(false);
      }
    };
    void fetchData();
  }, [tab]);

  // Client-side filter
  const results: Flusso[] = tab === 'flussi'
    ? flussi.filter(f => {
        if (!query.trim()) return true;
        const q = query.toLowerCase();
        return (
          (f.oggetto ?? '').toLowerCase().includes(q) ||
          (f.contenuto ?? '').toLowerCase().includes(q) ||
          f.canale.toLowerCase().includes(q)
        );
      })
    : [];

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    fontSize: 13,
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    background: active ? C.primary : 'transparent',
    color: active ? '#fff' : C.textMuted,
    borderRadius: 6,
    fontFamily: 'inherit',
    transition: 'background 150ms, color 150ms',
  });

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
          Ricerca
        </h1>
        <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
          Cerca nei flussi di comunicazione e nelle risorse aziendali
        </p>
      </div>

      {/* Search input */}
      <div
        style={{
          maxWidth: 640,
          margin: '0 auto 24px',
          position: 'relative',
        }}
      >
        <span
          style={{
            position: 'absolute',
            left: 14,
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: 16,
            color: C.textMuted,
            pointerEvents: 'none',
          }}
        >
          🔍
        </span>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={`Cerca in ${tab}…`}
          autoFocus
          style={{
            width: '100%',
            boxSizing: 'border-box',
            background: C.surface,
            border: `1px solid ${C.border}`,
            borderRadius: 10,
            padding: '12px 16px 12px 42px',
            fontSize: 15,
            color: C.textPrimary,
            fontFamily: 'inherit',
            outline: 'none',
            transition: 'border-color 150ms',
          }}
          onFocus={e => ((e.target as HTMLInputElement).style.borderColor = C.primary)}
          onBlur={e => ((e.target as HTMLInputElement).style.borderColor = C.border)}
        />
      </div>

      {/* Tab toggle */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 4,
          marginBottom: 24,
          background: C.surface,
          borderRadius: 8,
          padding: 4,
          width: 'fit-content',
          margin: '0 auto 24px',
        }}
      >
        <button style={tabStyle(tab === 'flussi')} onClick={() => setTab('flussi')}>
          Flussi
        </button>
        <button style={tabStyle(tab === 'risorse')} onClick={() => setTab('risorse')}>
          Risorse
        </button>
      </div>

      {/* Status */}
      {loading && (
        <div style={{ textAlign: 'center', color: C.textMuted, fontSize: 13, marginTop: 40 }}>
          Caricamento...
        </div>
      )}

      {error && (
        <div
          style={{
            background: `${C.error}22`,
            border: `1px solid ${C.error}44`,
            borderRadius: 8,
            padding: '12px 16px',
            color: C.error,
            fontSize: 13,
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {/* Risorse placeholder */}
      {!loading && tab === 'risorse' && (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 16px',
            color: C.textMuted,
            fontSize: 13,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
          <div style={{ fontWeight: 500, marginBottom: 4, color: C.textSecondary }}>
            Ricerca Risorse
          </div>
          <div>Endpoint in sviluppo — disponibile nella prossima versione</div>
        </div>
      )}

      {/* Results */}
      {!loading && !error && tab === 'flussi' && loaded && (
        <>
          {query.trim() && (
            <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 12 }}>
              {results.length} risultati per &ldquo;{query}&rdquo;
            </div>
          )}

          {!query.trim() && flussi.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                padding: '60px 16px',
                color: C.textMuted,
                fontSize: 13,
              }}
            >
              Nessun flusso trovato
            </div>
          )}

          {query.trim() && results.length === 0 && (
            <div
              style={{
                textAlign: 'center',
                padding: '60px 16px',
                color: C.textMuted,
                fontSize: 13,
              }}
            >
              Nessun risultato per &ldquo;{query}&rdquo;
            </div>
          )}

          {(results.length > 0 || !query.trim()) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {(query.trim() ? results : flussi.slice(0, 50)).map(f => (
                <FlussoCard key={f.id} flusso={f} />
              ))}
              {!query.trim() && flussi.length > 50 && (
                <div
                  style={{
                    textAlign: 'center',
                    fontSize: 12,
                    color: C.textMuted,
                    padding: 8,
                  }}
                >
                  Mostrando 50 di {flussi.length} flussi — usa la ricerca per filtrare
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export const Component = TiroRicercaPage;
