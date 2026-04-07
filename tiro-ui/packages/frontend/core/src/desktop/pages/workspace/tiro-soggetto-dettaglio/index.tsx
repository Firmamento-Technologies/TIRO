import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { tiroApi } from '../../../../modules/tiro-shared';
import type {
  Flusso,
  Opportunita,
  Soggetto,
} from '../../../../modules/tiro-shared/types';

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
  textDisabled: '#64748B',
  primary: '#0EA5E9',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  accent: '#14B8A6',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const tipoColor = (tipo: string) => {
  switch (tipo) {
    case 'membro':
      return { bg: '#0EA5E922', color: '#38BDF8' };
    case 'esterno':
      return { bg: '#334155', color: '#CBD5E1' };
    case 'partner':
      return { bg: '#14B8A622', color: '#14B8A6' };
    case 'istituzione':
      return { bg: '#8B5CF622', color: '#A78BFA' };
    default:
      return { bg: '#334155', color: '#CBD5E1' };
  }
};

const faseColor = (fase: string) => {
  switch (fase) {
    case 'chiuso_ok':
      return C.success;
    case 'chiuso_no':
      return C.error;
    case 'proposta':
    case 'trattativa':
      return C.warning;
    default:
      return C.primary;
  }
};

const formatEur = (v: number) =>
  new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);

const formatRelative = (ts: string) => {
  const diff = Date.now() - new Date(ts).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m fa`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h fa`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}g fa`;
  return new Date(ts).toLocaleDateString('it-IT');
};

const canaleIcon = (canale: string) => {
  switch (canale.toLowerCase()) {
    case 'email': return '✉';
    case 'whatsapp': return '💬';
    case 'telefono': return '📞';
    case 'incontro': return '🤝';
    default: return '📄';
  }
};

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroSoggettoDettaglioPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [soggetto, setSoggetto] = useState<Soggetto | null>(null);
  const [flussi, setFlussi] = useState<Flusso[]>([]);
  const [opportunita, setOpportunita] = useState<Opportunita[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const numId = parseInt(id, 10);
    if (isNaN(numId)) {
      setError('ID soggetto non valido');
      setLoading(false);
      return;
    }

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [soggettoData, flussiData, oppData] = await Promise.all([
          tiroApi.getSoggetto(numId),
          tiroApi.getFlussi({ soggetto_id: numId }),
          tiroApi.getOpportunita({ soggetto_id: numId }),
        ]);
        setSoggetto(soggettoData);
        setFlussi(flussiData);
        setOpportunita(oppData);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Errore caricamento');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [id]);

  if (loading) {
    return (
      <div
        style={{
          padding: 24,
          color: C.textMuted,
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
        }}
      >
        Caricamento...
      </div>
    );
  }

  if (error || !soggetto) {
    return (
      <div
        style={{
          padding: 24,
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
        }}
      >
        <div style={{ color: C.error, marginBottom: 12 }}>
          {error ?? 'Soggetto non trovato'}
        </div>
        <button
          onClick={() => navigate(-1)}
          style={{
            background: 'transparent',
            border: `1px solid ${C.border}`,
            borderRadius: 6,
            color: C.textSecondary,
            fontSize: 13,
            padding: '6px 12px',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          ← Torna indietro
        </button>
      </div>
    );
  }

  const tc = tipoColor(soggetto.tipo);

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
      {/* Back nav */}
      <button
        onClick={() => navigate(-1)}
        style={{
          background: 'transparent',
          border: 'none',
          color: C.textMuted,
          fontSize: 13,
          cursor: 'pointer',
          padding: 0,
          marginBottom: 16,
          fontFamily: 'inherit',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        ← Soggetti
      </button>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16, alignItems: 'start' }}>
        {/* Left: Profile card */}
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 8,
            padding: 20,
          }}
        >
          {/* Avatar placeholder */}
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: C.surfaceElevated,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 22,
              fontWeight: 700,
              color: C.primary,
              marginBottom: 12,
            }}
          >
            {soggetto.nome[0]?.toUpperCase() ?? '?'}{soggetto.cognome[0]?.toUpperCase() ?? ''}
          </div>

          <div
            style={{
              fontSize: 17,
              fontWeight: 600,
              color: C.textPrimary,
              marginBottom: 4,
            }}
          >
            {soggetto.nome} {soggetto.cognome}
          </div>

          {soggetto.ruolo && (
            <div
              style={{ fontSize: 13, color: C.textMuted, marginBottom: 8 }}
            >
              {soggetto.ruolo}
            </div>
          )}

          <span
            style={{
              display: 'inline-block',
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 500,
              background: tc.bg,
              color: tc.color,
              textTransform: 'capitalize',
              marginBottom: 16,
            }}
          >
            {soggetto.tipo}
          </span>

          <div
            style={{
              borderTop: `1px solid ${C.borderSubtle}`,
              paddingTop: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {/* Email */}
            {soggetto.email.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: 11,
                    color: C.textDisabled,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 2,
                  }}
                >
                  Email
                </div>
                {soggetto.email.map(e => (
                  <div key={e} style={{ fontSize: 13, color: C.textSecondary }}>
                    {e}
                  </div>
                ))}
              </div>
            )}

            {/* Telefono */}
            {soggetto.telefono.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: 11,
                    color: C.textDisabled,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 2,
                  }}
                >
                  Telefono
                </div>
                {soggetto.telefono.map(t => (
                  <div key={t} style={{ fontSize: 13, color: C.textSecondary }}>
                    {t}
                  </div>
                ))}
              </div>
            )}

            {/* Tag */}
            {soggetto.tag.length > 0 && (
              <div>
                <div
                  style={{
                    fontSize: 11,
                    color: C.textDisabled,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 4,
                  }}
                >
                  Tag
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {soggetto.tag.map(t => (
                    <span
                      key={t}
                      style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        background: C.surfaceElevated,
                        color: C.textSecondary,
                      }}
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div
              style={{
                fontSize: 11,
                color: C.textDisabled,
                marginTop: 4,
              }}
            >
              Aggiornato il {new Date(soggetto.aggiornato_il).toLocaleDateString('it-IT')}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Timeline flussi */}
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.borderSubtle}`,
              borderRadius: 8,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '12px 16px',
                borderBottom: `1px solid ${C.borderSubtle}`,
                fontSize: 13,
                fontWeight: 600,
                color: C.textSecondary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>Timeline flussi</span>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 400,
                  color: C.textMuted,
                }}
              >
                {flussi.length} eventi
              </span>
            </div>

            {flussi.length === 0 ? (
              <div style={{ padding: '16px', color: C.textMuted, fontSize: 13 }}>
                Nessun flusso per questo soggetto
              </div>
            ) : (
              <div
                style={{
                  maxHeight: 320,
                  overflowY: 'auto',
                }}
              >
                {flussi.map((f, idx) => (
                  <div
                    key={f.id}
                    style={{
                      display: 'flex',
                      gap: 12,
                      padding: '12px 16px',
                      borderBottom:
                        idx < flussi.length - 1
                          ? `1px solid ${C.borderSubtle}`
                          : 'none',
                    }}
                  >
                    {/* Timeline dot */}
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: '50%',
                          background: C.surfaceElevated,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: 14,
                        }}
                      >
                        {canaleIcon(f.canale)}
                      </div>
                      {idx < flussi.length - 1 && (
                        <div
                          style={{
                            width: 1,
                            flex: 1,
                            background: C.borderSubtle,
                            marginTop: 4,
                            minHeight: 12,
                          }}
                        />
                      )}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          marginBottom: 2,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 12,
                            fontWeight: 500,
                            color: C.primary,
                            textTransform: 'capitalize',
                          }}
                        >
                          {f.canale}
                        </span>
                        <span style={{ fontSize: 11, color: C.textMuted }}>
                          {f.direzione === 'in' ? '← in entrata' : '→ in uscita'}
                        </span>
                        <span
                          style={{
                            fontSize: 11,
                            color: C.textMuted,
                            marginLeft: 'auto',
                          }}
                        >
                          {formatRelative(f.ricevuto_il)}
                        </span>
                      </div>
                      {f.oggetto && (
                        <div
                          style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: C.textSecondary,
                            marginBottom: 2,
                          }}
                        >
                          {f.oggetto}
                        </div>
                      )}
                      {f.contenuto && (
                        <div
                          style={{
                            fontSize: 12,
                            color: C.textMuted,
                            overflow: 'hidden',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                          }}
                        >
                          {f.contenuto}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Opportunità */}
          <div
            style={{
              background: C.surface,
              border: `1px solid ${C.borderSubtle}`,
              borderRadius: 8,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '12px 16px',
                borderBottom: `1px solid ${C.borderSubtle}`,
                fontSize: 13,
                fontWeight: 600,
                color: C.textSecondary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>Opportunità</span>
              <span style={{ fontSize: 12, fontWeight: 400, color: C.textMuted }}>
                {opportunita.length} opportunit{opportunita.length === 1 ? 'à' : 'à'}
              </span>
            </div>

            {opportunita.length === 0 ? (
              <div style={{ padding: '16px', color: C.textMuted, fontSize: 13 }}>
                Nessuna opportunità associata
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.borderSubtle}` }}>
                    {['Titolo', 'Fase', 'Valore', 'Probabilità', 'Chiusura'].map(
                      col => (
                        <th
                          key={col}
                          style={{
                            padding: '8px 12px',
                            textAlign: 'left',
                            fontSize: 11,
                            fontWeight: 600,
                            color: C.textMuted,
                            textTransform: 'uppercase',
                            letterSpacing: '0.04em',
                          }}
                        >
                          {col}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {opportunita.map(o => {
                    const fc = faseColor(o.fase);
                    return (
                      <tr
                        key={o.id}
                        style={{
                          borderBottom: `1px solid ${C.borderSubtle}`,
                          transition: 'background 300ms',
                        }}
                        onMouseEnter={e =>
                          ((e.currentTarget as HTMLTableRowElement).style.background =
                            C.surfaceElevated)
                        }
                        onMouseLeave={e =>
                          ((e.currentTarget as HTMLTableRowElement).style.background =
                            'transparent')
                        }
                      >
                        <td
                          style={{
                            padding: '10px 12px',
                            fontSize: 13,
                            fontWeight: 500,
                            color: C.textPrimary,
                          }}
                        >
                          {o.titolo}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <span
                            style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: 4,
                              fontSize: 11,
                              fontWeight: 500,
                              background: `${fc}22`,
                              color: fc,
                              textTransform: 'capitalize',
                            }}
                          >
                            {o.fase.replace('_', ' ')}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: '10px 12px',
                            fontSize: 13,
                            color: C.accent,
                            textAlign: 'right',
                          }}
                        >
                          {o.valore_eur != null
                            ? formatEur(o.valore_eur)
                            : <span style={{ color: C.textDisabled }}>—</span>}
                        </td>
                        <td
                          style={{
                            padding: '10px 12px',
                            fontSize: 13,
                            color: C.textSecondary,
                            textAlign: 'right',
                          }}
                        >
                          {o.probabilita != null
                            ? `${o.probabilita}%`
                            : <span style={{ color: C.textDisabled }}>—</span>}
                        </td>
                        <td
                          style={{
                            padding: '10px 12px',
                            fontSize: 12,
                            color: C.textMuted,
                          }}
                        >
                          {o.chiusura_prevista
                            ? new Date(o.chiusura_prevista).toLocaleDateString('it-IT')
                            : <span style={{ color: C.textDisabled }}>—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export const Component = TiroSoggettoDettaglioPage;
