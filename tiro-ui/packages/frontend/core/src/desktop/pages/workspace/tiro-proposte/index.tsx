import { useEffect, useRef, useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import type { Proposta } from '../../../../modules/tiro-shared/types';

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
const formatDate = (ts: string) =>
  new Date(ts).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

const rischioColor = (livello: string) => {
  switch (livello) {
    case 'basso':   return C.success;
    case 'medio':   return C.warning;
    case 'alto':    return '#F97316';
    case 'critico': return C.error;
    default:        return C.textMuted;
  }
};

const statoColor = (stato: string) => {
  switch (stato) {
    case 'in_attesa':  return C.warning;
    case 'approvata':  return C.success;
    case 'rifiutata':  return C.error;
    case 'eseguita':   return C.primary;
    default:           return C.textMuted;
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
          flexShrink: 0,
          display: 'inline-block',
        }}
      />
      {livello}
    </span>
  );
}

// ─── StatoBadge ───────────────────────────────────────────────────────────────
function StatoBadge({ stato }: { stato: string }) {
  const color = statoColor(stato);
  const labels: Record<string, string> = {
    in_attesa: 'In Attesa',
    approvata: 'Approvata',
    rifiutata: 'Rifiutata',
    eseguita:  'Eseguita',
  };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 500,
        background: `${color}22`,
        color,
        whiteSpace: 'nowrap',
      }}
    >
      {labels[stato] ?? stato}
    </span>
  );
}

// ─── Filter Select ────────────────────────────────────────────────────────────
function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 11, color: C.textMuted, fontWeight: 500 }}>
        {label}
      </span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: C.surfaceElevated,
          color: C.textPrimary,
          border: `1px solid ${C.border}`,
          borderRadius: 6,
          padding: '6px 10px',
          fontSize: 13,
          fontFamily: 'inherit',
          cursor: 'pointer',
          outline: 'none',
          minWidth: 140,
        }}
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroPropostePage() {
  const [proposte, setProposte] = useState<Proposta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioningId, setActioningId] = useState<number | null>(null);
  const [filtroStato, setFiltroStato] = useState('tutti');
  const [filtroRischio, setFiltroRischio] = useState('tutti');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'open' | 'closed' | 'off'>('off');
  const wsRef = useRef<WebSocket | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, string> = {};
      if (filtroStato !== 'tutti') filters['stato'] = filtroStato;
      if (filtroRischio !== 'tutti') filters['livello_rischio'] = filtroRischio;
      const data = await tiroApi.getProposte(filters);
      setProposte(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Errore caricamento proposte');
    } finally {
      setLoading(false);
    }
  };

  // WebSocket — real-time updates
  useEffect(() => {
    setWsStatus('connecting');
    let ws: WebSocket;
    try {
      ws = new WebSocket('ws://localhost:8000/ws/eventi');
      wsRef.current = ws;

      ws.onopen = () => setWsStatus('open');
      ws.onclose = () => setWsStatus('closed');
      ws.onerror = () => {
        setWsStatus('closed');
        // silently degrade — page still works via polling
      };
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data as string) as { tipo?: string };
          // Refresh proposte when agent creates a new proposal
          if (msg.tipo === 'proposta_creata' || msg.tipo === 'proposta_aggiornata') {
            void load();
          }
        } catch {
          // ignore parse errors
        }
      };
    } catch {
      setWsStatus('off');
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroStato, filtroRischio]);

  const handleApprova = async (id: number) => {
    setActioningId(id);
    try {
      await tiroApi.approvaProposte(id);
      setProposte(prev => prev.filter(p => p.id !== id));
    } catch {
      // ignore
    } finally {
      setActioningId(null);
    }
  };

  const handleRifiuta = async (id: number) => {
    setActioningId(id);
    try {
      await tiroApi.rifiutaProposta(id, 'Rifiutato manualmente');
      setProposte(prev => prev.filter(p => p.id !== id));
    } catch {
      // ignore
    } finally {
      setActioningId(null);
    }
  };

  const wsIndicatorColor =
    wsStatus === 'open' ? C.success : wsStatus === 'connecting' ? C.warning : C.textMuted;

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
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 20,
        }}
      >
        <div>
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
            Proposte Agenti
          </h1>
          <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
            Revisione e approvazione delle azioni proposte dagli agenti AI
          </p>
        </div>

        {/* WS status indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            color: wsIndicatorColor,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: wsIndicatorColor,
              display: 'inline-block',
            }}
          />
          {wsStatus === 'open'
            ? 'Live'
            : wsStatus === 'connecting'
            ? 'Connessione...'
            : 'Offline'}
        </div>
      </div>

      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          gap: 16,
          alignItems: 'flex-end',
          marginBottom: 20,
          flexWrap: 'wrap',
        }}
      >
        <FilterSelect
          label="Stato"
          value={filtroStato}
          onChange={setFiltroStato}
          options={[
            { value: 'tutti',      label: 'Tutti gli stati' },
            { value: 'in_attesa',  label: 'In Attesa' },
            { value: 'approvata',  label: 'Approvata' },
            { value: 'rifiutata',  label: 'Rifiutata' },
            { value: 'eseguita',   label: 'Eseguita' },
          ]}
        />
        <FilterSelect
          label="Livello Rischio"
          value={filtroRischio}
          onChange={setFiltroRischio}
          options={[
            { value: 'tutti',   label: 'Tutti i rischi' },
            { value: 'basso',   label: 'Basso' },
            { value: 'medio',   label: 'Medio' },
            { value: 'alto',    label: 'Alto' },
            { value: 'critico', label: 'Critico' },
          ]}
        />
        <div style={{ fontSize: 13, color: C.textMuted, paddingBottom: 2 }}>
          {loading ? 'Caricamento...' : `${proposte.length} proposte`}
        </div>
      </div>

      {/* Error state */}
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

      {/* Table */}
      {!loading && !error && (
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr auto',
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
            <span>Titolo</span>
            <span>Agente</span>
            <span>Tipo Azione</span>
            <span>Rischio</span>
            <span>Stato</span>
            <span>Azioni</span>
          </div>

          {/* Rows */}
          {proposte.length === 0 ? (
            <div
              style={{
                padding: '32px 16px',
                color: C.textMuted,
                fontSize: 13,
                textAlign: 'center',
              }}
            >
              Nessuna proposta trovata per i filtri selezionati
            </div>
          ) : (
            proposte.map(p => (
              <div
                key={p.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr auto',
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
                  ((e.currentTarget as HTMLDivElement).style.background =
                    'transparent')
                }
              >
                {/* Titolo */}
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: C.textPrimary,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      marginBottom: 2,
                    }}
                  >
                    {p.titolo}
                  </div>
                  <div style={{ fontSize: 11, color: C.textMuted }}>
                    {formatDate(p.creato_il)}
                  </div>
                </div>

                {/* Agente badge (viola) */}
                <div>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 500,
                      background: `${C.secondary}22`,
                      color: C.secondary,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '100%',
                    }}
                  >
                    {p.ruolo_agente}
                  </span>
                </div>

                {/* Tipo azione */}
                <div
                  style={{
                    fontSize: 13,
                    color: C.textSecondary,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {p.tipo_azione}
                </div>

                {/* Rischio */}
                <div>
                  <RischioBadge livello={p.livello_rischio} />
                </div>

                {/* Stato */}
                <div>
                  <StatoBadge stato={p.stato} />
                </div>

                {/* Azioni */}
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  {p.stato === 'in_attesa' ? (
                    <>
                      <button
                        disabled={actioningId === p.id}
                        onClick={() => void handleApprova(p.id)}
                        style={{
                          background: C.success,
                          color: '#fff',
                          border: 'none',
                          borderRadius: 6,
                          padding: '5px 12px',
                          fontSize: 12,
                          fontWeight: 500,
                          cursor: actioningId === p.id ? 'not-allowed' : 'pointer',
                          opacity: actioningId === p.id ? 0.5 : 1,
                          fontFamily: 'inherit',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        Approva
                      </button>
                      <button
                        disabled={actioningId === p.id}
                        onClick={() => void handleRifiuta(p.id)}
                        style={{
                          background: C.error,
                          color: '#fff',
                          border: 'none',
                          borderRadius: 6,
                          padding: '5px 12px',
                          fontSize: 12,
                          fontWeight: 500,
                          cursor: actioningId === p.id ? 'not-allowed' : 'pointer',
                          opacity: actioningId === p.id ? 0.5 : 1,
                          fontFamily: 'inherit',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        Rifiuta
                      </button>
                    </>
                  ) : (
                    <span style={{ fontSize: 12, color: C.textMuted, minWidth: 80 }}>—</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export const Component = TiroPropostePage;
