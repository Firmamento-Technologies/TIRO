import { useEffect, useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import type {
  Flusso,
  KpiCruscotto,
  Proposta,
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
  primary: '#0EA5E9',
  primaryDark: '#0284C7',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  secondary: '#8B5CF6',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const formatEur = (value: number) =>
  new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(
    value
  );

const formatRelative = (ts: string) => {
  const diff = Date.now() - new Date(ts).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m fa`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h fa`;
  return new Date(ts).toLocaleDateString('it-IT');
};

const rischioColor = (livello: string) => {
  switch (livello) {
    case 'basso':
      return C.success;
    case 'medio':
      return C.warning;
    case 'alto':
      return '#F97316';
    case 'critico':
      return C.error;
    default:
      return C.textMuted;
  }
};

const canaleIcon = (canale: string) => {
  switch (canale.toLowerCase()) {
    case 'email':
      return '✉';
    case 'whatsapp':
      return '💬';
    case 'telefono':
      return '📞';
    case 'incontro':
      return '🤝';
    default:
      return '📄';
  }
};

// ─── KPI Card ─────────────────────────────────────────────────────────────────
interface KpiCardProps {
  label: string;
  value: string | number;
  icon: string;
  color?: string;
}

function KpiCard({ label, value, icon, color = C.primary }: KpiCardProps) {
  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.borderSubtle}`,
        borderRadius: 8,
        padding: 20,
        flex: 1,
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 20 }}>{icon}</span>
        <span style={{ fontSize: 13, color: C.textMuted, fontWeight: 500 }}>
          {label}
        </span>
      </div>
      <div
        style={{
          fontSize: 32,
          fontWeight: 700,
          color,
          lineHeight: 1.1,
          letterSpacing: '-0.01em',
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ─── Rischio Badge ────────────────────────────────────────────────────────────
function RischioBadge({ livello }: { livello: string }) {
  const color = rischioColor(livello);
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
        textTransform: 'capitalize',
      }}
    >
      {livello}
    </span>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroCruscottoPage() {
  const [kpi, setKpi] = useState<KpiCruscotto | null>(null);
  const [flussi, setFlussi] = useState<Flusso[]>([]);
  const [proposte, setProposte] = useState<Proposta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioningId, setActioningId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiData, flussiData, proposteData] = await Promise.all([
        tiroApi.getKpiCruscotto(),
        tiroApi.getFlussi(),
        tiroApi.getProposte({ stato: 'in_attesa' }),
      ]);
      setKpi(kpiData);
      setFlussi(flussiData.slice(0, 10));
      setProposte(proposteData.slice(0, 10));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Errore caricamento dati');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleApprova = async (id: number) => {
    setActioningId(id);
    try {
      await tiroApi.approvaProposte(id);
      setProposte(prev => prev.filter(p => p.id !== id));
      setKpi(prev =>
        prev
          ? { ...prev, proposte_in_attesa: prev.proposte_in_attesa - 1 }
          : prev
      );
    } catch {
      // ignore
    } finally {
      setActioningId(null);
    }
  };

  const handleRifiuta = async (id: number) => {
    setActioningId(id);
    try {
      await tiroApi.rifiutaProposta(id, 'Rifiutato dal cruscotto');
      setProposte(prev => prev.filter(p => p.id !== id));
      setKpi(prev =>
        prev
          ? { ...prev, proposte_in_attesa: prev.proposte_in_attesa - 1 }
          : prev
      );
    } catch {
      // ignore
    } finally {
      setActioningId(null);
    }
  };

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

  if (error) {
    return (
      <div
        style={{
          padding: 24,
          color: C.error,
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
        }}
      >
        Errore: {error}
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
          Cruscotto
        </h1>
        <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
          Panoramica operativa in tempo reale
        </p>
      </div>

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <KpiCard
          label="Soggetti Attivi"
          value={kpi?.soggetti_attivi ?? 0}
          icon="👥"
          color={C.primary}
        />
        <KpiCard
          label="Opportunità Aperte"
          value={kpi?.opportunita_aperte ?? 0}
          icon="🎯"
          color="#14B8A6"
        />
        <KpiCard
          label="Valore Pipeline"
          value={formatEur(kpi?.valore_pipeline ?? 0)}
          icon="💰"
          color={C.success}
        />
        <KpiCard
          label="Proposte in Attesa"
          value={kpi?.proposte_in_attesa ?? 0}
          icon="⚡"
          color={C.secondary}
        />
      </div>

      {/* Two columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Flussi Recenti */}
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
            }}
          >
            Flussi Recenti
          </div>
          {flussi.length === 0 ? (
            <div
              style={{ padding: 16, color: C.textMuted, fontSize: 13 }}
            >
              Nessun flusso recente
            </div>
          ) : (
            <div>
              {flussi.map(f => (
                <div
                  key={f.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '10px 16px',
                    borderBottom: `1px solid ${C.borderSubtle}`,
                    transition: 'background 300ms',
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
                  <span
                    style={{
                      fontSize: 16,
                      lineHeight: 1,
                      marginTop: 1,
                      flexShrink: 0,
                    }}
                  >
                    {canaleIcon(f.canale)}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        color: C.textSecondary,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {f.oggetto ?? f.contenuto?.slice(0, 60) ?? '(nessun contenuto)'}
                    </div>
                    <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
                      {f.canale} · soggetto #{f.soggetto_id}
                    </div>
                  </div>
                  <span
                    style={{ fontSize: 11, color: C.textMuted, flexShrink: 0 }}
                  >
                    {formatRelative(f.ricevuto_il)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Proposte in Attesa */}
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
            }}
          >
            Proposte in Attesa
          </div>
          {proposte.length === 0 ? (
            <div
              style={{ padding: 16, color: C.textMuted, fontSize: 13 }}
            >
              Nessuna proposta in attesa
            </div>
          ) : (
            <div>
              {proposte.map(p => (
                <div
                  key={p.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 16px',
                    borderBottom: `1px solid ${C.borderSubtle}`,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                      <RischioBadge livello={p.livello_rischio} />
                    </div>
                    <div
                      style={{
                        fontSize: 13,
                        color: C.textSecondary,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {p.titolo}
                    </div>
                    <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
                      {p.ruolo_agente} · {p.tipo_azione}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <button
                      disabled={actioningId === p.id}
                      onClick={() => void handleApprova(p.id)}
                      style={{
                        background: C.success,
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        padding: '6px 12px',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: actioningId === p.id ? 'not-allowed' : 'pointer',
                        opacity: actioningId === p.id ? 0.5 : 1,
                        fontFamily: 'inherit',
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
                        padding: '6px 12px',
                        fontSize: 12,
                        fontWeight: 500,
                        cursor: actioningId === p.id ? 'not-allowed' : 'pointer',
                        opacity: actioningId === p.id ? 0.5 : 1,
                        fontFamily: 'inherit',
                      }}
                    >
                      Rifiuta
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export const Component = TiroCruscottoPage;
