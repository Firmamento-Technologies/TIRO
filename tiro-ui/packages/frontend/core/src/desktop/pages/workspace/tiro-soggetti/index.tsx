import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { tiroApi } from '../../../../modules/tiro-shared';
import type { Soggetto } from '../../../../modules/tiro-shared/types';

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
  primaryDark: '#0284C7',
  success: '#22C55E',
  error: '#EF4444',
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

const TIPI = ['tutti', 'membro', 'esterno', 'partner', 'istituzione'] as const;
type Tipo = (typeof TIPI)[number];

// ─── Nuovo Soggetto form ──────────────────────────────────────────────────────
interface NuovoSoggettoFormProps {
  onSaved: (s: Soggetto) => void;
  onCancel: () => void;
}

function NuovoSoggettoForm({ onSaved, onCancel }: NuovoSoggettoFormProps) {
  const [form, setForm] = useState({
    nome: '',
    cognome: '',
    tipo: 'esterno',
    email: '',
    telefono: '',
    ruolo: '',
    tag: '',
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.nome.trim() || !form.cognome.trim()) {
      setErr('Nome e cognome sono obbligatori');
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      const payload: Partial<Soggetto> = {
        nome: form.nome.trim(),
        cognome: form.cognome.trim(),
        tipo: form.tipo,
        email: form.email ? [form.email.trim()] : [],
        telefono: form.telefono ? [form.telefono.trim()] : [],
        ruolo: form.ruolo.trim() || null,
        tag: form.tag ? form.tag.split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      const saved = await tiroApi.createSoggetto(payload);
      onSaved(saved);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Errore salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    background: C.bg,
    border: `1px solid ${C.border}`,
    borderRadius: 6,
    color: C.textPrimary,
    fontSize: 13,
    padding: '8px 12px',
    fontFamily: 'inherit',
    width: '100%',
    boxSizing: 'border-box',
    outline: 'none',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    color: C.textMuted,
    fontWeight: 500,
    marginBottom: 4,
    display: 'block',
  };

  return (
    <div
      style={{
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: 8,
        padding: 20,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: C.textPrimary,
          marginBottom: 16,
        }}
      >
        Nuovo Soggetto
      </div>

      {err && (
        <div
          style={{
            background: '#EF444422',
            border: '1px solid #EF4444',
            borderRadius: 6,
            padding: '8px 12px',
            color: C.error,
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          {err}
        </div>
      )}

      <form onSubmit={e => void handleSubmit(e)}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: 12,
            marginBottom: 12,
          }}
        >
          <div>
            <label style={labelStyle}>Nome *</label>
            <input
              style={inputStyle}
              name="nome"
              value={form.nome}
              onChange={handleChange}
              placeholder="Mario"
            />
          </div>
          <div>
            <label style={labelStyle}>Cognome *</label>
            <input
              style={inputStyle}
              name="cognome"
              value={form.cognome}
              onChange={handleChange}
              placeholder="Rossi"
            />
          </div>
          <div>
            <label style={labelStyle}>Tipo</label>
            <select
              style={{ ...inputStyle, cursor: 'pointer' }}
              name="tipo"
              value={form.tipo}
              onChange={handleChange}
            >
              <option value="membro">Membro</option>
              <option value="esterno">Esterno</option>
              <option value="partner">Partner</option>
              <option value="istituzione">Istituzione</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="mario@esempio.it"
            />
          </div>
          <div>
            <label style={labelStyle}>Telefono</label>
            <input
              style={inputStyle}
              name="telefono"
              value={form.telefono}
              onChange={handleChange}
              placeholder="+39 333 123456"
            />
          </div>
          <div>
            <label style={labelStyle}>Ruolo</label>
            <input
              style={inputStyle}
              name="ruolo"
              value={form.ruolo}
              onChange={handleChange}
              placeholder="CEO"
            />
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label style={labelStyle}>Tag (separati da virgola)</label>
            <input
              style={inputStyle}
              name="tag"
              value={form.tag}
              onChange={handleChange}
              placeholder="vip, prospect, ricorrente"
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              background: 'transparent',
              border: `1px solid ${C.border}`,
              borderRadius: 6,
              color: C.textSecondary,
              fontSize: 13,
              padding: '8px 16px',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            Annulla
          </button>
          <button
            type="submit"
            disabled={saving}
            style={{
              background: C.primary,
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 16px',
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.5 : 1,
              fontFamily: 'inherit',
            }}
          >
            {saving ? 'Salvataggio...' : 'Salva'}
          </button>
        </div>
      </form>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function TiroSoggettiPage() {
  const navigate = useNavigate();
  const [soggetti, setSoggetti] = useState<Soggetto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tipoFiltro, setTipoFiltro] = useState<Tipo>('tutti');
  const [showForm, setShowForm] = useState(false);

  const load = async (tipo: Tipo) => {
    setLoading(true);
    setError(null);
    try {
      const filters = tipo !== 'tutti' ? { tipo } : undefined;
      const data = await tiroApi.getSoggetti(filters);
      setSoggetti(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Errore caricamento');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(tipoFiltro);
  }, [tipoFiltro]);

  const handleSaved = (s: Soggetto) => {
    setSoggetti(prev => [s, ...prev]);
    setShowForm(false);
  };

  const filterBtnStyle = (active: boolean): React.CSSProperties => ({
    background: active ? C.primary : 'transparent',
    border: `1px solid ${active ? C.primary : C.border}`,
    borderRadius: 6,
    color: active ? '#fff' : C.textSecondary,
    fontSize: 13,
    fontWeight: active ? 500 : 400,
    padding: '6px 14px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    transition: 'all 300ms',
    textTransform: 'capitalize',
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
            Soggetti
          </h1>
          <p style={{ fontSize: 13, color: C.textMuted, margin: 0 }}>
            {soggetti.length} soggett{soggetti.length === 1 ? 'o' : 'i'}
            {tipoFiltro !== 'tutti' ? ` · ${tipoFiltro}` : ''}
          </p>
        </div>
        <button
          onClick={() => setShowForm(prev => !prev)}
          style={{
            background: C.primary,
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            fontSize: 13,
            fontWeight: 500,
            padding: '8px 16px',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          + Nuovo Soggetto
        </button>
      </div>

      {/* Inline form */}
      {showForm && (
        <NuovoSoggettoForm
          onSaved={handleSaved}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {TIPI.map(t => (
          <button
            key={t}
            style={filterBtnStyle(tipoFiltro === t)}
            onClick={() => setTipoFiltro(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ color: C.textMuted, fontSize: 13 }}>Caricamento...</div>
      ) : error ? (
        <div style={{ color: C.error, fontSize: 13 }}>Errore: {error}</div>
      ) : (
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.borderSubtle}`,
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr
                style={{
                  background: C.surface,
                  borderBottom: `1px solid ${C.borderSubtle}`,
                }}
              >
                {['Nome', 'Tipo', 'Email', 'Telefono', 'Tag', 'Aggiornato'].map(
                  col => (
                    <th
                      key={col}
                      style={{
                        padding: '10px 12px',
                        textAlign: 'left',
                        fontSize: 12,
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
              {soggetti.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    style={{
                      padding: '24px 12px',
                      textAlign: 'center',
                      color: C.textMuted,
                      fontSize: 13,
                    }}
                  >
                    Nessun soggetto trovato
                  </td>
                </tr>
              ) : (
                soggetti.map(s => {
                  const tc = tipoColor(s.tipo);
                  return (
                    <tr
                      key={s.id}
                      style={{
                        borderBottom: `1px solid ${C.borderSubtle}`,
                        cursor: 'pointer',
                        transition: 'background 300ms',
                      }}
                      onClick={() =>
                        navigate(
                          `/workspace/:workspaceId/tiro/soggetti/${s.id}`.replace(
                            ':workspaceId',
                            window.location.pathname.split('/')[2] ?? ''
                          )
                        )
                      }
                      onMouseEnter={e =>
                        ((e.currentTarget as HTMLTableRowElement).style.background =
                          C.surfaceElevated)
                      }
                      onMouseLeave={e =>
                        ((e.currentTarget as HTMLTableRowElement).style.background =
                          'transparent')
                      }
                    >
                      <td style={{ padding: '10px 12px' }}>
                        <span
                          style={{
                            fontWeight: 500,
                            color: C.textPrimary,
                            fontSize: 13,
                          }}
                        >
                          {s.nome} {s.cognome}
                        </span>
                        {s.ruolo && (
                          <div
                            style={{ fontSize: 11, color: C.textMuted, marginTop: 1 }}
                          >
                            {s.ruolo}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
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
                          }}
                        >
                          {s.tipo}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: '10px 12px',
                          fontSize: 13,
                          color: C.textSecondary,
                        }}
                      >
                        {s.email[0] ?? (
                          <span style={{ color: C.textDisabled }}>—</span>
                        )}
                      </td>
                      <td
                        style={{
                          padding: '10px 12px',
                          fontSize: 13,
                          color: C.textSecondary,
                        }}
                      >
                        {s.telefono[0] ?? (
                          <span style={{ color: C.textDisabled }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {s.tag.slice(0, 3).map(t => (
                            <span
                              key={t}
                              style={{
                                padding: '2px 6px',
                                borderRadius: 4,
                                fontSize: 11,
                                background: C.surfaceElevated,
                                color: C.textSecondary,
                              }}
                            >
                              {t}
                            </span>
                          ))}
                          {s.tag.length > 3 && (
                            <span
                              style={{
                                fontSize: 11,
                                color: C.textMuted,
                              }}
                            >
                              +{s.tag.length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td
                        style={{
                          padding: '10px 12px',
                          fontSize: 12,
                          color: C.textMuted,
                        }}
                      >
                        {new Date(s.aggiornato_il).toLocaleDateString('it-IT')}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export const Component = TiroSoggettiPage;
