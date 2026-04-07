import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import {
  clearToken,
  getToken,
  getUser,
  isAuthenticated,
  setToken,
} from '../auth-store';

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

// ─── JWT helpers ─────────────────────────────────────────────────────────────

function makeJwtPayload(payload: Record<string, unknown>): string {
  // Use Buffer for base64url in Node.js
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    .toString('base64url');
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${header}.${body}.fakesignature`;
}

function futureExp(): number {
  return Math.floor(Date.now() / 1000) + 3600;
}

function pastExp(): number {
  return Math.floor(Date.now() / 1000) - 1;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('auth-store', () => {
  let lsMock: ReturnType<typeof createLocalStorageMock>;

  beforeEach(() => {
    lsMock = createLocalStorageMock();
    vi.stubGlobal('localStorage', lsMock);
    // Node doesn't have atob/btoa by default in older versions; polyfill if needed
    if (typeof globalThis.atob === 'undefined') {
      vi.stubGlobal('atob', (str: string) =>
        Buffer.from(str, 'base64').toString('binary')
      );
    }
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe('setToken / getToken', () => {
    test('setToken stores token in localStorage', () => {
      setToken('my-token');
      expect(lsMock.setItem).toHaveBeenCalledWith('tiro_jwt', 'my-token');
    });

    test('getToken retrieves stored token', () => {
      lsMock.getItem.mockReturnValue('my-token');
      expect(getToken()).toBe('my-token');
    });

    test('getToken returns null when no token stored', () => {
      expect(getToken()).toBeNull();
    });
  });

  describe('clearToken', () => {
    test('clearToken removes token from localStorage', () => {
      clearToken();
      expect(lsMock.removeItem).toHaveBeenCalledWith('tiro_jwt');
    });

    test('clearToken is idempotent when no token present', () => {
      expect(() => clearToken()).not.toThrow();
    });
  });

  describe('isAuthenticated', () => {
    test('returns false when no token stored', () => {
      expect(isAuthenticated()).toBe(false);
    });

    test('returns false when token has invalid format (too few parts)', () => {
      lsMock.getItem.mockReturnValue('notavalidjwt');
      expect(isAuthenticated()).toBe(false);
    });

    test('returns false when token is expired and clears it', () => {
      const token = makeJwtPayload({ sub: 'user1', exp: pastExp() });
      lsMock.getItem.mockReturnValue(token);
      expect(isAuthenticated()).toBe(false);
      // expired token should be auto-cleared
      expect(lsMock.removeItem).toHaveBeenCalledWith('tiro_jwt');
    });

    test('returns true when token is valid and not expired', () => {
      const token = makeJwtPayload({ sub: 'user1', exp: futureExp() });
      lsMock.getItem.mockReturnValue(token);
      expect(isAuthenticated()).toBe(true);
    });

    test('returns true when token has no exp claim', () => {
      const token = makeJwtPayload({ sub: 'user1' });
      lsMock.getItem.mockReturnValue(token);
      expect(isAuthenticated()).toBe(true);
    });
  });

  describe('getUser', () => {
    test('returns null when no token stored', () => {
      expect(getUser()).toBeNull();
    });

    test('extracts user payload from valid JWT', () => {
      const payload = { sub: 'user42', email: 'test@example.com', exp: futureExp() };
      const token = makeJwtPayload(payload);
      lsMock.getItem.mockReturnValue(token);
      const user = getUser();
      expect(user).not.toBeNull();
      expect(user?.['sub']).toBe('user42');
      expect(user?.['email']).toBe('test@example.com');
    });

    test('returns null for malformed token', () => {
      lsMock.getItem.mockReturnValue('malformed');
      expect(getUser()).toBeNull();
    });
  });
});
