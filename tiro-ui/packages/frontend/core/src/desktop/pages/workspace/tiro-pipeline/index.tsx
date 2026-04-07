import { useEffect, useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import type { Opportunita } from '../../../../modules/tiro-shared/types';

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

// ─── Pipeline phases ──────────────────────────────────────────────────────────
const FASI = [
  { id: 'contatto', label: 'Contatto', color: C.textMuted },
  { id: 'qualificato', label: 'Qualificato', color: C.primary },
  { id: 'proposta', label: 'Proposta', color: '#8B5CF6' },
  { id: 'trattativa', label: 'Trattativa', color: C.warning },
  { id: 'chiuso_ok', label: 'Chiuso ✓', color: C.success },
  { id: 'chiuso_no', label: 'Chiuso ✗', color: C.error },
] as const;

type FaseId = (typeof FASI)[number]['id'];

// ─── Helpers ──────────────────────────────────────────────────────────────────
const formatEur = (v: number) =>
  new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(v);

const probabilitaColor = (p: number) => {
  if (p >= 75) return C.success;
  if (p >= 40) return C.warning;
  return C.error;
};

// ─── Opportunita Card ─────────────────────────────────────────────────────────
interface OppCardProps {
  opp: Opportunita;
  faseColor: string;
}

function OppCard({ opp, faseColor }: OppCardProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? C.surfaceElevated : C.bg,
        border: `1px solid ${hovered ? C.border : C.borderSubtle}`,
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
        cursor: 'default',
        transition: 'all 300ms',
      }}
    >
      {/* Titolo */}
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: C.textPrimary,
          marginBottom: 4,
          lineHeight: 1.3,
        }}
      >
        {opp.titolo}
      </div>

      {/* Ente (placeholder — ente_id only) */}
      {opp.ente_id != null && (
        <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 6 }}>
          Ente #{opp.ente_id}
        </div>
      )}

      {/* Valore + Probabilità */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: 8,
        }}
      >
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: C.accent,
          }}
        >
          {opp.valore_eur != null
            ? formatEur(opp.valore_eur)
            : <span style={{ color: C.textDisabled, fontWeight: 400 }}>—</span>}
        </span>

        {opp.probabilita != null && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: probabilitaColor(opp.probabilita),
              background: `${probabilitaColor(opp.probabilita)}22`,
              padding: '2px 6px',
              borderRadius: 4,
            }}
          >
            {opp.probabilita}%
          </span>
        )}
      </div>

      {/* Scadenza */}
      {opp.chiusura_prevista && (
        <div style={{ fontSize: 11, color: C.textDisabled, marginTop: 6 }}>
          Chiusura: {new Date(opp.chiusura_prevista).toLocaleDateString('it-IT')}
        </div>
      )}

      {/* Fase accent line */}
      <div
        style={{
          height: 2,
          background: faseColor,
          borderRadius: 1,
          marginTop: 10,
          opacity: 0.6,
        }}
      />
    </div>
  );
}

// ─── Column header ────────────────────────────────────────────────────────────
interface ColHeaderProps {
  label: string;
  count: number;
  total: number;
  color: string;
}

function ColHeader({ label, count, total, color }: ColHeaderProps) {
  return (
    <div
      style={{
        padding: '10px 12px',
        borderBottom: `1px solid ${C.borderSubtle}`,
        borderTop: `3px solid ${color}`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 4,
        }}
      >
        <span
          style={{ fontSize: 13, fontWeight: 600, color: C.textSecondary }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: 12,
            fontWeight: 500,
            color,
            background: `${color}22`,
            padding: '1px 6px',
            borderRadius: 10,
          }}
        >
          {count}
        </span>
      </div>
      {total > 0 && (
        <div style={{ fontSize: 11, color: C.textMuted }}>
          {formatEur(total)}
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroPipelinePage() {
  const [opportunita, setOpportunita] = useState<Opportunita[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await tiroApi.getOpportunita();
        setOpportunita(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Errore caricamento');
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

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

  // Group by fase
  const byFase = new Map<FaseId, Opportunita[]>();
  for (const fase of FASI) {
    byFase.set(fase.id, []);
  }
  for (const o of opportunita) {
    const key = o.fase as FaseId;
    if (byFase.has(key)) {
      byFase.get(key)!.push(o);
    } else {
      // unknown fase — put in contatto
      byFase.get('contatto')!.push(o);
    }
  }

  const totalPipeline = opportunita.reduce(
    (acc, o) => acc + (o.valore_eur ?? 0),
    0
  );

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
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
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
            Pipeline
          </h1>
          <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
            {opportunita.length} opportunit{opportunita.length === 1 ? 'à' : 'à'} ·{' '}
            <span style={{ color: C.accent }}>{formatEur(totalPipeline)}</span> totali
          </p>
        </div>
      </div>

      {/* Kanban board */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: 12,
          flex: 1,
          alignItems: 'start',
          overflowX: 'auto',
          minWidth: 0,
        }}
      >
        {FASI.map(fase => {
          const cards = byFase.get(fase.id) ?? [];
          const colTotal = cards.reduce(
            (acc, o) => acc + (o.valore_eur ?? 0),
            0
          );

          return (
            <div
              key={fase.id}
              style={{
                background: C.surface,
                border: `1px solid ${C.borderSubtle}`,
                borderRadius: 8,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                minWidth: 200,
              }}
            >
              <ColHeader
                label={fase.label}
                count={cards.length}
                total={colTotal}
                color={fase.color}
              />

              <div
                style={{
                  padding: 8,
                  flex: 1,
                  minHeight: 80,
                }}
              >
                {cards.length === 0 ? (
                  <div
                    style={{
                      padding: '16px 8px',
                      textAlign: 'center',
                      fontSize: 12,
                      color: C.textDisabled,
                    }}
                  >
                    Nessuna opportunità
                  </div>
                ) : (
                  cards.map(o => (
                    <OppCard key={o.id} opp={o} faseColor={fase.color} />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const Component = TiroPipelinePage;
