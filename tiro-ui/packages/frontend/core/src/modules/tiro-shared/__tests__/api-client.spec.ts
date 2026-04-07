import {
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
  type MockedFunction,
} from 'vitest';

import { TiroApiClient } from '../api-client';
import type { KpiCruscotto, Opportunita, Proposta, Soggetto } from '../types';

// ─── localStorage mock ────────────────────────────────────────────────────────

function createLocalStorageMock() {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
}

// ─── Fetch mock helpers ───────────────────────────────────────────────────────

function mockFetch(data: unknown, status = 200, ok = true): MockedFunction<typeof fetch> {
  const mock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(status === 200 ? '' : String(data)),
    statusText: ok ? 'OK' : 'Error',
  } as unknown as Response);
  vi.stubGlobal('fetch', mock);
  return mock;
}

function mockFetchError(message: string): MockedFunction<typeof fetch> {
  const mock = vi.fn().mockRejectedValue(new Error(message));
  vi.stubGlobal('fetch', mock);
  return mock;
}

const BASE_URL = 'http://localhost:8000';

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TiroApiClient', () => {
  let client: TiroApiClient;
  let lsMock: ReturnType<typeof createLocalStorageMock>;

  beforeEach(() => {
    client = new TiroApiClient(BASE_URL);
    lsMock = createLocalStorageMock();
    vi.stubGlobal('localStorage', lsMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  // ─── login ────────────────────────────────────────────────────────────────

  describe('login', () => {
    test('calls /auth/token with form-encoded body', async () => {
      const tokenData = { access_token: 'abc123', tipo: 'bearer' };
      const fetchMock = mockFetch(tokenData);

      await client.login('user@example.com', 'password123');

      expect(fetchMock).toHaveBeenCalledOnce();
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/auth/token`);
      expect(options.method).toBe('POST');
      const headers = options.headers as Record<string, string>;
      expect(headers['Content-Type']).toBe('application/x-www-form-urlencoded');
      const body = options.body as URLSearchParams;
      expect(body.get('username')).toBe('user@example.com');
      expect(body.get('password')).toBe('password123');
    });

    test('stores token in localStorage on success', async () => {
      mockFetch({ access_token: 'stored-token', tipo: 'bearer' });
      await client.login('user@example.com', 'pass');
      expect(lsMock.setItem).toHaveBeenCalledWith('tiro_jwt', 'stored-token');
    });

    test('returns TokenResponse on success', async () => {
      const tokenData = { access_token: 'tok', tipo: 'bearer' };
      mockFetch(tokenData);
      const result = await client.login('u', 'p');
      expect(result).toEqual(tokenData);
    });

    test('throws on non-OK response', async () => {
      mockFetch('Unauthorized', 401, false);
      await expect(client.login('u', 'wrong')).rejects.toThrow(/401/);
    });
  });

  // ─── logout ───────────────────────────────────────────────────────────────

  describe('logout', () => {
    test('clears token from localStorage', () => {
      client.logout();
      expect(lsMock.removeItem).toHaveBeenCalledWith('tiro_jwt');
    });
  });

  // ─── getSoggetti ──────────────────────────────────────────────────────────

  describe('getSoggetti', () => {
    test('sends GET request to /soggetti', async () => {
      const fetchMock = mockFetch([]);
      await client.getSoggetti();
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/soggetti`);
      expect(options.method).toBe('GET');
    });

    test('sends Authorization header when token is set', async () => {
      lsMock.getItem.mockReturnValue('my-jwt');
      const fetchMock = mockFetch([]);
      await client.getSoggetti();
      const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer my-jwt');
    });

    test('does not send Authorization header when no token', async () => {
      const fetchMock = mockFetch([]);
      await client.getSoggetti();
      const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['Authorization']).toBeUndefined();
    });

    test('passes tipo filter as query param', async () => {
      const fetchMock = mockFetch([]);
      await client.getSoggetti({ tipo: 'persona' });
      const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/soggetti?tipo=persona`);
    });

    test('omits undefined/null filter values', async () => {
      const fetchMock = mockFetch([]);
      await client.getSoggetti({ tipo: undefined, stato: null });
      const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/soggetti`);
    });

    test('returns parsed array', async () => {
      const soggetti: Partial<Soggetto>[] = [{ id: 1, nome: 'Mario' }];
      mockFetch(soggetti);
      const result = await client.getSoggetti();
      expect(result).toEqual(soggetti);
    });
  });

  // ─── createSoggetto ───────────────────────────────────────────────────────

  describe('createSoggetto', () => {
    test('sends POST to /soggetti with JSON body', async () => {
      const newSoggetto = { nome: 'Luigi', cognome: 'Verdi', tipo: 'persona' };
      const fetchMock = mockFetch({ id: 2, ...newSoggetto });
      await client.createSoggetto(newSoggetto);
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/soggetti`);
      expect(options.method).toBe('POST');
      expect(JSON.parse(options.body as string)).toEqual(newSoggetto);
    });

    test('sets Content-Type to application/json', async () => {
      const fetchMock = mockFetch({ id: 3 });
      await client.createSoggetto({ nome: 'Test' });
      const [, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['Content-Type']).toBe('application/json');
    });
  });

  // ─── approvaProposte ──────────────────────────────────────────────────────

  describe('approvaProposte', () => {
    test('sends POST to /proposte/:id/approva', async () => {
      const proposta: Partial<Proposta> = { id: 5, stato: 'approvata' };
      const fetchMock = mockFetch(proposta);
      await client.approvaProposte(5);
      const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe(`${BASE_URL}/proposte/5/approva`);
      expect(options.method).toBe('POST');
    });
  });

  // ─── getKpiCruscotto ──────────────────────────────────────────────────────

  describe('getKpiCruscotto', () => {
    test('aggregates multiple API calls', async () => {
      const soggetti: Partial<Soggetto>[] = [{ id: 1 }, { id: 2 }];
      const opportunita: Partial<Opportunita>[] = [
        { id: 10, valore_eur: 1000 },
        { id: 11, valore_eur: 2500 },
      ];
      const proposte: Partial<Proposta>[] = [{ id: 20 }, { id: 21 }, { id: 22 }];

      const fetchMock = vi
        .fn()
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(soggetti) })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(opportunita) })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(proposte) });
      vi.stubGlobal('fetch', fetchMock);

      const kpi: KpiCruscotto = await client.getKpiCruscotto();

      expect(kpi.soggetti_attivi).toBe(2);
      expect(kpi.opportunita_aperte).toBe(2);
      expect(kpi.valore_pipeline).toBe(3500);
      expect(kpi.proposte_in_attesa).toBe(3);
    });

    test('handles opportunita with null valore_eur', async () => {
      const opportunita: Partial<Opportunita>[] = [
        { id: 1, valore_eur: null },
        { id: 2, valore_eur: 500 },
      ];

      const fetchMock = vi
        .fn()
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(opportunita),
        })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });
      vi.stubGlobal('fetch', fetchMock);

      const kpi = await client.getKpiCruscotto();
      expect(kpi.valore_pipeline).toBe(500);
    });
  });

  // ─── Network errors ───────────────────────────────────────────────────────

  describe('request error handling', () => {
    test('throws on network error', async () => {
      mockFetchError('Network failure');
      await expect(client.getSoggetti()).rejects.toThrow('Network failure');
    });

    test('throws descriptive error on non-OK response', async () => {
      mockFetch('Not found', 404, false);
      await expect(client.getSoggetto(999)).rejects.toThrow(
        /TIRO API GET \/soggetti\/999 → 404/
      );
    });

    test('throws descriptive error on 500', async () => {
      mockFetch('Internal Server Error', 500, false);
      await expect(client.getRegole()).rejects.toThrow(/500/);
    });
  });
});
