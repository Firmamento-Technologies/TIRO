import { clearToken, getToken, setToken } from './auth-store';
import type {
  Fascicolo,
  Flusso,
  KpiCruscotto,
  Opportunita,
  Proposta,
  RegolaRischio,
  Soggetto,
  TokenResponse,
} from './types';

const DEFAULT_BASE_URL =
  (typeof process !== 'undefined' && process.env['TIRO_API_URL']) ||
  'http://localhost:8000';

export class TiroApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = DEFAULT_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  // ─── Internal helpers ─────────────────────────────────────────────────────

  private buildHeaders(extra?: Record<string, string>): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...extra,
    };
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      method,
      headers: this.buildHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      throw new Error(`TIRO API ${method} ${path} → ${response.status}: ${text}`);
    }

    return response.json() as Promise<T>;
  }

  private buildQuery(filters?: Record<string, unknown>): string {
    if (!filters || Object.keys(filters).length === 0) return '';
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
    const qs = params.toString();
    return qs ? `?${qs}` : '';
  }

  // ─── Auth ──────────────────────────────────────────────────────────────────

  async login(email: string, password: string): Promise<TokenResponse> {
    // tiro-core uses OAuth2 password flow (form-encoded)
    const response = await fetch(`${this.baseUrl}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => response.statusText);
      throw new Error(`Login fallito (${response.status}): ${text}`);
    }

    const data = (await response.json()) as TokenResponse;
    setToken(data.access_token);
    return data;
  }

  logout(): void {
    clearToken();
  }

  // ─── Soggetti ──────────────────────────────────────────────────────────────

  getSoggetti(filters?: Record<string, unknown>): Promise<Soggetto[]> {
    return this.request<Soggetto[]>('GET', `/soggetti${this.buildQuery(filters)}`);
  }

  getSoggetto(id: number): Promise<Soggetto> {
    return this.request<Soggetto>('GET', `/soggetti/${id}`);
  }

  createSoggetto(data: Partial<Soggetto>): Promise<Soggetto> {
    return this.request<Soggetto>('POST', '/soggetti', data);
  }

  updateSoggetto(id: number, data: Partial<Soggetto>): Promise<Soggetto> {
    return this.request<Soggetto>('PUT', `/soggetti/${id}`, data);
  }

  // ─── Flussi ────────────────────────────────────────────────────────────────

  getFlussi(filters?: Record<string, unknown>): Promise<Flusso[]> {
    return this.request<Flusso[]>('GET', `/flussi${this.buildQuery(filters)}`);
  }

  // ─── Opportunità ───────────────────────────────────────────────────────────

  getOpportunita(filters?: Record<string, unknown>): Promise<Opportunita[]> {
    return this.request<Opportunita[]>('GET', `/opportunita${this.buildQuery(filters)}`);
  }

  createOpportunita(data: Partial<Opportunita>): Promise<Opportunita> {
    return this.request<Opportunita>('POST', '/opportunita', data);
  }

  // ─── Fascicoli ─────────────────────────────────────────────────────────────

  getFascicolo(id: number): Promise<Fascicolo> {
    return this.request<Fascicolo>('GET', `/fascicoli/${id}`);
  }

  // ─── Proposte ──────────────────────────────────────────────────────────────

  getProposte(filters?: Record<string, unknown>): Promise<Proposta[]> {
    return this.request<Proposta[]>('GET', `/proposte${this.buildQuery(filters)}`);
  }

  approvaProposte(id: number): Promise<Proposta> {
    return this.request<Proposta>('POST', `/proposte/${id}/approva`);
  }

  rifiutaProposta(id: number, motivo: string): Promise<Proposta> {
    return this.request<Proposta>('POST', `/proposte/${id}/rifiuta`, { motivo });
  }

  // ─── Ricerca ───────────────────────────────────────────────────────────────

  ricerca(
    vettore: number[],
    tabella: string
  ): Promise<Array<Record<string, unknown>>> {
    return this.request<Array<Record<string, unknown>>>('POST', '/ricerca', {
      vettore,
      tabella,
    });
  }

  // ─── Regole ────────────────────────────────────────────────────────────────

  getRegole(): Promise<RegolaRischio[]> {
    return this.request<RegolaRischio[]>('GET', '/regole');
  }

  // ─── KPI Cruscotto ─────────────────────────────────────────────────────────

  async getKpiCruscotto(): Promise<KpiCruscotto> {
    const [soggetti, opportunita, proposte] = await Promise.all([
      this.getSoggetti(),
      this.getOpportunita(),
      this.getProposte({ stato: 'in_attesa' }),
    ]);

    const valore_pipeline = opportunita.reduce(
      (acc, o) => acc + (o.valore_eur ?? 0),
      0
    );

    return {
      soggetti_attivi: soggetti.length,
      opportunita_aperte: opportunita.length,
      valore_pipeline,
      proposte_in_attesa: proposte.length,
    };
  }
}

/** Singleton condiviso nell'app */
export const tiroApi = new TiroApiClient();
