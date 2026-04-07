import { useState } from 'react';

import { tiroApi } from '../../../../modules/tiro-shared';
import type { Fascicolo } from '../../../../modules/tiro-shared/types';

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
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const formatDate = (ts: string) =>
  new Date(ts).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });

const rischioColor = (v: number | null) => {
  if (v === null) return C.textMuted;
  if (v < 0.3) return C.success;
  if (v < 0.6) return C.warning;
  if (v < 0.8) return '#F97316';
  return C.error;
};

const rischioLabel = (v: number | null) => {
  if (v === null) return 'N/D';
  if (v < 0.3) return 'Basso';
  if (v < 0.6) return 'Medio';
  if (v < 0.8) return 'Alto';
  return 'Critico';
};

// ─── Fascicolo Card ───────────────────────────────────────────────────────────
function FascicoloCard({
  fascicolo,
  onViewSoggetto,
}: {
  fascicolo: Fascicolo;
  onViewSoggetto: (id: number) => void;
}) {
  const rColor = rischioColor(fascicolo.indice_rischio);
  const oColor = C.primary;
  const pct = (v: number | null) =>
    v !== null ? `${Math.round(v * 100)}%` : 'N/D';

  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.borderSubtle}`,
        borderRadius: 10,
        padding: '16px 20px',
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
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>
            Fascicolo #{fascicolo.id}
          </div>
          <div style={{ fontSize: 11, color: C.textMuted, marginTop: 2 }}>
            Generato il {formatDate(fascicolo.generato_il)}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16 }}>
          {/* Indice rischio */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 2 }}>
              Rischio
            </div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 700,
                color: rColor,
              }}
            >
              {pct(fascicolo.indice_rischio)}
            </div>
            <div style={{ fontSize: 10, color: rColor }}>
              {rischioLabel(fascicolo.indice_rischio)}
            </div>
          </div>

          {/* Indice opportunità */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 2 }}>
              Opportunità
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: oColor }}>
              {pct(fascicolo.indice_opportunita)}
            </div>
          </div>
        </div>
      </div>

      {/* Sintesi */}
      {fascicolo.sintesi && (
        <p
          style={{
            fontSize: 13,
            color: C.textSecondary,
            margin: '0 0 12px',
            lineHeight: 1.5,
          }}
        >
          {fascicolo.sintesi}
        </p>
      )}

      {/* Link to soggetto */}
      {fascicolo.soggetto_id !== null && (
        <button
          onClick={() => onViewSoggetto(fascicolo.soggetto_id as number)}
          style={{
            background: 'transparent',
            border: `1px solid ${C.primary}`,
            color: C.primary,
            borderRadius: 6,
            padding: '5px 12px',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'inherit',
            transition: 'background 150ms',
          }}
          onMouseEnter={e =>
            ((e.currentTarget as HTMLButtonElement).style.background = `${C.primary}22`)
          }
          onMouseLeave={e =>
            ((e.currentTarget as HTMLButtonElement).style.background = 'transparent')
          }
        >
          Vai al soggetto #{fascicolo.soggetto_id} →
        </button>
      )}
    </div>
  );
}

// ─── Lookup form ──────────────────────────────────────────────────────────────
function LookupForm({
  onLoad,
}: {
  onLoad: (id: number, fascicolo: Fascicolo) => void;
}) {
  const [soggettoId, setSoggettoId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(soggettoId, 10);
    if (isNaN(id) || id <= 0) {
      setError('Inserisci un ID soggetto valido');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const fascicolo = await tiroApi.getFascicolo(id);
      onLoad(id, fascicolo);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Fascicolo non trovato'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={e => void handleSubmit(e)}
      style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}
    >
      <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 11, color: C.textMuted, fontWeight: 500 }}>
          ID Soggetto
        </span>
        <input
          type="number"
          min={1}
          value={soggettoId}
          onChange={e => setSoggettoId(e.target.value)}
          placeholder="es. 42"
          style={{
            background: C.surfaceElevated,
            border: `1px solid ${C.border}`,
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 13,
            color: C.textPrimary,
            fontFamily: 'inherit',
            outline: 'none',
            width: 140,
          }}
          onFocus={e =>
            ((e.target as HTMLInputElement).style.borderColor = C.primary)
          }
          onBlur={e =>
            ((e.target as HTMLInputElement).style.borderColor = C.border)
          }
        />
      </label>
      <button
        type="submit"
        disabled={loading || !soggettoId}
        style={{
          background: C.primary,
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          padding: '8px 18px',
          fontSize: 13,
          fontWeight: 500,
          cursor: loading || !soggettoId ? 'not-allowed' : 'pointer',
          opacity: loading || !soggettoId ? 0.6 : 1,
          fontFamily: 'inherit',
        }}
      >
        {loading ? 'Caricamento...' : 'Carica Fascicolo'}
      </button>
      {error && (
        <span style={{ fontSize: 13, color: C.error, alignSelf: 'center' }}>
          {error}
        </span>
      )}
    </form>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroFascicoliPage() {
  const [fascicolo, setFascicolo] = useState<Fascicolo | null>(null);

  const handleLoad = (_id: number, f: Fascicolo) => {
    setFascicolo(f);
  };

  const navigateToSoggetto = (id: number) => {
    // Navigate to soggetto dettaglio — use window.location hash routing
    // consistent with AFFiNE's router pattern
    try {
      const url = new URL(window.location.href);
      url.hash = `/workspace/tiro-soggetti/${id}`;
      window.location.href = url.toString();
    } catch {
      // fallback
      window.location.hash = `/workspace/tiro-soggetti/${id}`;
    }
  };

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
          Fascicoli
        </h1>
        <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
          Profili di rischio e opportunità generati automaticamente per ogni soggetto
        </p>
      </div>

      {/* Lookup form */}
      <div
        style={{
          background: C.surface,
          border: `1px solid ${C.borderSubtle}`,
          borderRadius: 8,
          padding: '16px 20px',
          marginBottom: 24,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: C.textSecondary,
            marginBottom: 12,
          }}
        >
          Cerca fascicolo per soggetto
        </div>
        <LookupForm onLoad={handleLoad} />
      </div>

      {/* Result or empty state */}
      {fascicolo ? (
        <FascicoloCard
          fascicolo={fascicolo}
          onViewSoggetto={navigateToSoggetto}
        />
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '60px 16px',
            color: C.textMuted,
            fontSize: 13,
            gap: 8,
            background: C.surface,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 8,
          }}
        >
          <span style={{ fontSize: 40 }}>📂</span>
          <span style={{ fontWeight: 500, color: C.textSecondary, fontSize: 15 }}>
            Seleziona un soggetto per vedere il fascicolo
          </span>
          <span>
            Inserisci l&apos;ID del soggetto nel campo qui sopra oppure accedi alla{' '}
            <button
              onClick={() => {
                window.location.hash = '/workspace/tiro-soggetti';
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: C.primary,
                cursor: 'pointer',
                padding: 0,
                fontSize: 13,
                fontFamily: 'inherit',
                textDecoration: 'underline',
              }}
            >
              lista soggetti
            </button>
          </span>
        </div>
      )}
    </div>
  );
}

export const Component = TiroFascicoliPage;
