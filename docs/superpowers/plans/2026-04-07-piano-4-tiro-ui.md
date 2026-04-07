# Piano 4: TIRO UI (AFFiNE Fork)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Creare il frontend TIRO come fork di AFFiNE, completamente rebrandizzato, con 4 moduli nativi (Cruscotto, CRM, Ricerca, Decisionale) e un pannello Sistema. Ogni modulo si connette all'API REST tiro-core su `http://localhost:8000`.

**Architecture:** Fork AFFiNE monorepo. Moduli custom registrati nel DI framework `@toeverything/infra`. Ogni modulo e una route con pagine React che comunicano con tiro-core via fetch. Styling via vanilla-extract (`.css.ts`). WebSocket per notifiche real-time proposte.

**Tech Stack:** Node.js 22, TypeScript 5, React 19, React Router v6, vanilla-extract, `@toeverything/infra` DI, `@blocksuite/icons/rc`, Lucide React.

**Spec di riferimento:** `docs/superpowers/specs/2026-04-06-tiro-architettura-design.md` (Sezione 5), `DESIGN.md`

**Design System:** Dark theme obbligatorio. Sfondo `#0F172A`, superfici `#1E293B`, testo `#F8FAFC`. Colori: ciano `#0EA5E9` (primary), viola `#8B5CF6` (agenti), teal `#14B8A6` (positivo). Font: Inter 14px base.

---

## API Reference (tiro-core)

Le pagine UI consumano queste API. Tutte richiedono header `Authorization: Bearer <token>` (tranne `/api/auth/login`).

| Endpoint | Metodo | Parametri | Response |
|---|---|---|---|
| `/api/auth/login` | POST | `{email, password}` | `{access_token, tipo}` |
| `/api/soggetti` | GET | `?tipo=` | `SoggettoResponse[]` |
| `/api/soggetti` | POST | `SoggettoCrea` body | `SoggettoResponse` |
| `/api/soggetti/{id}` | GET | — | `SoggettoResponse` |
| `/api/soggetti/{id}` | PATCH | `SoggettoAggiorna` body | `SoggettoResponse` |
| `/api/flussi` | GET | `?soggetto_id=&canale=` | `FlussoResponse[]` |
| `/api/opportunita` | GET | `?fase=` | `OpportunitaResponse[]` |
| `/api/opportunita` | POST | `OpportunitaCrea` body | `OpportunitaResponse` |
| `/api/fascicoli/{id}` | GET | — | `FascicoloResponse` |
| `/api/proposte/` | GET | `?stato=&livello=&limit=` | `PropostaResponse[]` |
| `/api/proposte/{id}` | GET | — | `PropostaResponse` |
| `/api/proposte/{id}/approva` | PATCH | `{canale: "pannello"}` | `PropostaResponse` |
| `/api/proposte/{id}/rifiuta` | PATCH | — | `PropostaResponse` |
| `/api/ricerca` | POST | `{vettore, limite, tabella}` | `RisultatoRicerca[]` |
| `/api/sistema/regole` | GET | — | `RegolaRischioResponse[]` |
| `/ws/eventi` | WS | — | Stream notifiche JSON |

### Data Shapes (TypeScript types)

```typescript
// --- Auth ---
interface LoginRequest { email: string; password: string; }
interface TokenResponse { access_token: string; tipo: string; }

// --- Core ---
interface Soggetto {
  id: number; tipo: string; // membro|esterno|partner|istituzione
  nome: string; cognome: string;
  email: string[]; telefono: string[];
  organizzazione_id: number | null; ruolo: string | null;
  tag: string[]; profilo: Record<string, unknown>;
  creato_il: string; aggiornato_il: string;
}

interface Flusso {
  id: number; soggetto_id: number;
  canale: string; // messaggio|posta|voce|documento
  direzione: string; // entrata|uscita
  oggetto: string | null; contenuto: string | null;
  dati_grezzi: Record<string, unknown>;
  ricevuto_il: string; elaborato_il: string | null;
}

// --- Commerciale ---
interface Opportunita {
  id: number; ente_id: number | null; soggetto_id: number | null;
  titolo: string;
  fase: string; // contatto|qualificato|proposta|trattativa|chiuso_ok|chiuso_no
  valore_eur: number | null; probabilita: number | null;
  chiusura_prevista: string | null; dettagli: Record<string, unknown>;
}

interface Fascicolo {
  id: number; soggetto_id: number | null; ente_id: number | null;
  sintesi: string | null;
  indice_rischio: number | null; indice_opportunita: number | null;
  generato_il: string; sezioni: Record<string, unknown>;
}

// --- Decisionale ---
interface Proposta {
  id: number; ruolo_agente: string; tipo_azione: string;
  titolo: string; descrizione: string | null;
  destinatario: Record<string, unknown>;
  livello_rischio: string; // basso|medio|alto|critico
  stato: string; // in_attesa|approvata|rifiutata|automatica|eseguita
  approvato_da: string | null; canale_approvazione: string | null;
  creato_il: string; deciso_il: string | null; eseguito_il: string | null;
}

interface Sessione {
  id: number; ciclo: number; partecipanti: string[];
  consenso: Record<string, unknown>; conflitti: Record<string, unknown>;
  creato_il: string;
}

// --- Sistema ---
interface RegolaRischio {
  id: number; pattern_azione: string; livello_rischio: string;
  descrizione: string | null; approvazione_automatica: boolean;
}
```

---

## Struttura File

```
TIRO/
  tiro-ui/                              # AFFiNE fork root
    package.json                        # Rebrandizzato "tiro-ui"
    .env.local                          # TIRO_API_URL=http://localhost:8000
    packages/
      frontend/
        core/src/
          modules/
            tiro-api/                   # HTTP client + auth + types condivisi
              index.ts                  # configureApiModule(framework)
              services/
                api-client.ts           # fetch wrapper con JWT
                auth-store.ts           # Token storage + login/logout
              types.ts                  # TypeScript interfaces (vedi sopra)
            tiro-cruscotto/             # Dashboard homepage
              index.ts
              views/
                cruscotto-page.tsx
                cruscotto-page.css.ts
              components/
                kpi-card.tsx
                kpi-card.css.ts
                flussi-recenti.tsx
                flussi-recenti.css.ts
                proposte-widget.tsx
                proposte-widget.css.ts
            tiro-crm/                   # CRM module
              index.ts
              views/
                soggetti-lista.tsx
                soggetti-lista.css.ts
                soggetto-scheda.tsx
                soggetto-scheda.css.ts
                pipeline-kanban.tsx
                pipeline-kanban.css.ts
              components/
                soggetto-card.tsx
                soggetto-card.css.ts
                soggetto-form.tsx
                soggetto-form.css.ts
                kanban-colonna.tsx
                kanban-colonna.css.ts
                opportunita-card.tsx
                opportunita-card.css.ts
            tiro-ricerca/               # Research module
              index.ts
              views/
                ricerca-page.tsx
                ricerca-page.css.ts
              components/
                barra-ricerca.tsx
                risultato-card.tsx
                risultato-card.css.ts
            tiro-decisionale/           # Agent control module
              index.ts
              views/
                proposte-lista.tsx
                proposte-lista.css.ts
                sessioni-lista.tsx
                sessioni-lista.css.ts
              components/
                proposta-card.tsx
                proposta-card.css.ts
                rischio-badge.tsx
                rischio-badge.css.ts
            tiro-sistema/               # Admin module
              index.ts
              views/
                regole-lista.tsx
                regole-lista.css.ts
          components/
            root-app-sidebar/
              index.tsx                 # MODIFIED: aggiunge voci sidebar TIRO
        apps/
          desktop/
            src/
              workbench-router.ts       # MODIFIED: aggiunge routes TIRO
              pages/workspace/
                tiro-cruscotto/index.tsx
                tiro-crm/index.tsx
                tiro-crm/soggetto.tsx
                tiro-crm/pipeline.tsx
                tiro-ricerca/index.tsx
                tiro-decisionale/index.tsx
                tiro-decisionale/sessioni.tsx
                tiro-sistema/index.tsx
```

---

## Task 1: Fork AFFiNE + Setup Ambiente + Rebrand Minimo

**Files:**
- Create: `tiro-ui/` (cloned from AFFiNE)
- Create: `tiro-ui/.env.local`
- Modify: `tiro-ui/package.json` (name, branding)
- Modify: various manifest/i18n files

**Obiettivo:** Fork funzionante che compila e si avvia, con nome "TIRO" nei punti visibili.

- [ ] **Step 1: Clone AFFiNE nella directory tiro-ui**

```bash
cd /root/TIRO
git clone --depth 1 https://github.com/toeverything/AFFiNE.git tiro-ui
cd tiro-ui
rm -rf .git
```

- [ ] **Step 2: Configurare ambiente Node**

```bash
cd /root/TIRO/tiro-ui
# AFFiNE usa Yarn con corepack
corepack enable
yarn install
```

- [ ] **Step 3: Creare `.env.local`**

```env
# tiro-ui/.env.local
TIRO_API_URL=http://localhost:8000
```

- [ ] **Step 4: Rebrand package.json**

Nel root `package.json`, cambiare:
- `"name"` → `"tiro-ui"`
- `"productName"` → `"TIRO"`
- `"description"` → `"TIRO — Piattaforma gestionale aziendale unificata"`

- [ ] **Step 5: Rebrand titolo app**

Cercare tutti i file che contengono la stringa "AFFiNE" visibile all'utente:
```bash
grep -r "AFFiNE" --include="*.json" --include="*.ts" --include="*.tsx" -l | head -40
```

File prioritari da modificare:
- `packages/frontend/core/src/components/root-app-sidebar/index.tsx` — logo e nome sidebar
- Tutti i file i18n in `packages/frontend/i18n/src/resources/` — sostituire "AFFiNE" con "TIRO"
- `manifest.json` / `index.html` — titolo browser tab

- [ ] **Step 6: Rimuovere feature non necessarie**

Commentare o rimuovere import/voci sidebar per:
- AI assistant (tutto cio che referenzia `copilot` o `ai`)
- Cloud sync / AFFiNE Cloud
- Marketplace / template gallery

NON cancellare i file — solo rimuovere le voci dalla navigazione e dal routing per v1.

- [ ] **Step 7: Verificare compilazione**

```bash
cd /root/TIRO/tiro-ui
yarn build
# oppure
yarn dev
```

Il goal e ottenere un'app che si avvia senza errori. Funzionalita editor blocchi nativa di AFFiNE deve restare operativa.

**Criteri di completamento:**
- App compila senza errori
- Browser mostra "TIRO" nel titolo/sidebar
- Nessun riferimento visibile a "AFFiNE"
- Editor blocchi AFFiNE funziona ancora

---

## Task 2: Modulo API Client + Auth

**Files:**
- Create: `packages/frontend/core/src/modules/tiro-api/index.ts`
- Create: `packages/frontend/core/src/modules/tiro-api/services/api-client.ts`
- Create: `packages/frontend/core/src/modules/tiro-api/services/auth-store.ts`
- Create: `packages/frontend/core/src/modules/tiro-api/types.ts`
- Modify: `packages/frontend/core/src/modules/index.ts` — registrare modulo

**Obiettivo:** Client HTTP centralizzato con gestione JWT. Tutti i moduli TIRO usano questo come unico punto di comunicazione con tiro-core.

- [ ] **Step 1: Creare types.ts con tutte le interfacce TypeScript**

File: `packages/frontend/core/src/modules/tiro-api/types.ts`

Copiare tutte le interfacce dalla sezione "Data Shapes" sopra. Aggiungere anche:

```typescript
export type TipoSoggetto = 'membro' | 'esterno' | 'partner' | 'istituzione';
export type Canale = 'messaggio' | 'posta' | 'voce' | 'documento';
export type FaseOpportunita = 'contatto' | 'qualificato' | 'proposta' | 'trattativa' | 'chiuso_ok' | 'chiuso_no';
export type LivelloRischio = 'basso' | 'medio' | 'alto' | 'critico';
export type StatoProposta = 'in_attesa' | 'approvata' | 'rifiutata' | 'automatica' | 'eseguita';
export type RuoloUtente = 'titolare' | 'responsabile' | 'coordinatore' | 'operativo' | 'osservatore';
```

- [ ] **Step 2: Creare auth-store.ts**

File: `packages/frontend/core/src/modules/tiro-api/services/auth-store.ts`

```typescript
const TOKEN_KEY = 'tiro_token';

export class AuthStore {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem(TOKEN_KEY);
  }

  getToken(): string | null {
    return this.token;
  }

  setToken(token: string): void {
    this.token = token;
    localStorage.setItem(TOKEN_KEY, token);
  }

  clearToken(): void {
    this.token = null;
    localStorage.removeItem(TOKEN_KEY);
  }

  isAuthenticated(): boolean {
    return this.token !== null;
  }
}
```

- [ ] **Step 3: Creare api-client.ts**

File: `packages/frontend/core/src/modules/tiro-api/services/api-client.ts`

```typescript
import { AuthStore } from './auth-store';

const BASE_URL = process.env.TIRO_API_URL ?? 'http://localhost:8000';

export class TiroApiClient {
  constructor(private readonly auth: AuthStore) {}

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) ?? {}),
    };

    const token = this.auth.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}/api${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.auth.clearToken();
      throw new Error('Non autenticato');
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? `Errore ${response.status}`);
    }

    return response.json() as Promise<T>;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  // --- Auth ---
  async login(email: string, password: string): Promise<void> {
    const res = await this.post<{ access_token: string }>('/auth/login', {
      email,
      password,
    });
    this.auth.setToken(res.access_token);
  }

  logout(): void {
    this.auth.clearToken();
  }
}
```

- [ ] **Step 4: Creare index.ts con DI registration**

File: `packages/frontend/core/src/modules/tiro-api/index.ts`

```typescript
import type { Framework } from '@toeverything/infra';
import { AuthStore } from './services/auth-store';
import { TiroApiClient } from './services/api-client';

export { AuthStore, TiroApiClient };
export * from './types';

// DI tokens — adattare al pattern esatto di @toeverything/infra
// Se il framework usa createIdentifier:
// export const AuthStoreIdentifier = createIdentifier<AuthStore>('AuthStore');
// export const TiroApiClientIdentifier = createIdentifier<TiroApiClient>('TiroApiClient');

export function configureTiroApiModule(framework: Framework): void {
  // Registrare come singleton nel DI container.
  // Pattern esatto dipende dalla versione di @toeverything/infra.
  // Verificare come gli altri moduli registrano i servizi e seguire lo stesso pattern.
  // Esempio indicativo:
  // framework.register(AuthStoreIdentifier, AuthStore);
  // framework.register(TiroApiClientIdentifier, TiroApiClient, [AuthStoreIdentifier]);
}
```

**Nota:** Il pattern DI esatto va verificato ispezionando come moduli esistenti (es. `workbench`, `theme`) si registrano in `packages/frontend/core/src/modules/index.ts`. Adattare `configureTiroApiModule` di conseguenza.

- [ ] **Step 5: Registrare il modulo in modules/index.ts**

In `packages/frontend/core/src/modules/index.ts`, aggiungere:

```typescript
import { configureTiroApiModule } from './tiro-api';

// Dentro configureCommonModules(framework):
configureTiroApiModule(framework);
```

- [ ] **Step 6: Creare hook React per accesso al client**

File: `packages/frontend/core/src/modules/tiro-api/hooks.ts`

```typescript
import { useMemo } from 'react';
import { AuthStore } from './services/auth-store';
import { TiroApiClient } from './services/api-client';

// Singleton — in v1 semplifichiamo con un singleton diretto.
// In futuro migrare al DI framework.
let _auth: AuthStore | null = null;
let _client: TiroApiClient | null = null;

function getAuth(): AuthStore {
  if (!_auth) _auth = new AuthStore();
  return _auth;
}

function getClient(): TiroApiClient {
  if (!_client) _client = new TiroApiClient(getAuth());
  return _client;
}

export function useTiroApi(): TiroApiClient {
  return useMemo(() => getClient(), []);
}

export function useAuth(): AuthStore {
  return useMemo(() => getAuth(), []);
}
```

**Criteri di completamento:**
- `TiroApiClient` puo fare GET/POST/PATCH con JWT
- `AuthStore` salva/legge token da localStorage
- Modulo registrato nel DI framework
- Hook `useTiroApi()` e `useAuth()` disponibili per i componenti

---

## Task 3: Routing + Sidebar + Login Page

**Files:**
- Modify: `packages/frontend/apps/desktop/src/workbench-router.ts`
- Modify: `packages/frontend/core/src/components/root-app-sidebar/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/workspace/tiro-cruscotto/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/workspace/tiro-crm/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/workspace/tiro-ricerca/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/workspace/tiro-decisionale/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/workspace/tiro-sistema/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/tiro-login/index.tsx`
- Create: `packages/frontend/apps/desktop/src/pages/tiro-login/login.css.ts`

**Obiettivo:** Navigazione funzionante — sidebar con tutte le voci TIRO, routing a pagine placeholder, login page.

- [ ] **Step 1: Creare page placeholder per ogni modulo**

Ogni pagina segue il pattern AFFiNE con `ViewHeader`/`ViewBody`:

```tsx
// packages/frontend/apps/desktop/src/pages/workspace/tiro-cruscotto/index.tsx
import { ViewBody, ViewHeader, ViewTitle } from '@affine/core/modules/workbench';

export function TiroCruscottoPage() {
  return (
    <>
      <ViewHeader>
        <ViewTitle title="Cruscotto" />
      </ViewHeader>
      <ViewBody>
        <div style={{ padding: 24, color: '#F8FAFC' }}>
          Cruscotto — placeholder
        </div>
      </ViewBody>
    </>
  );
}
export const Component = TiroCruscottoPage;
```

Ripetere per:
- `tiro-crm/index.tsx` — title "Soggetti"
- `tiro-ricerca/index.tsx` — title "Ricerca"
- `tiro-decisionale/index.tsx` — title "Proposte"
- `tiro-sistema/index.tsx` — title "Sistema"

- [ ] **Step 2: Registrare routes in workbench-router.ts**

Trovare il file `workbench-router.ts` (verificare path esatto con `find`) e aggiungere le routes:

```typescript
// Dentro la definizione delle routes:
{
  path: '/tiro-cruscotto',
  lazy: () => import('./pages/workspace/tiro-cruscotto/index'),
},
{
  path: '/tiro-crm',
  lazy: () => import('./pages/workspace/tiro-crm/index'),
},
{
  path: '/tiro-crm/:soggettoId',
  lazy: () => import('./pages/workspace/tiro-crm/soggetto'),
},
{
  path: '/tiro-crm/pipeline',
  lazy: () => import('./pages/workspace/tiro-crm/pipeline'),
},
{
  path: '/tiro-ricerca',
  lazy: () => import('./pages/workspace/tiro-ricerca/index'),
},
{
  path: '/tiro-decisionale',
  lazy: () => import('./pages/workspace/tiro-decisionale/index'),
},
{
  path: '/tiro-decisionale/sessioni',
  lazy: () => import('./pages/workspace/tiro-decisionale/sessioni'),
},
{
  path: '/tiro-sistema',
  lazy: () => import('./pages/workspace/tiro-sistema/index'),
},
```

- [ ] **Step 3: Aggiungere voci sidebar**

In `packages/frontend/core/src/components/root-app-sidebar/index.tsx`:

Importare icone Lucide:
```typescript
import { LayoutDashboard, Users, Search, Brain, Settings } from 'lucide-react';
```

Aggiungere voci nel JSX della sidebar, PRIMA delle voci AFFiNE native:

```tsx
{/* === TIRO === */}
<div style={{ padding: '8px 12px', color: '#64748B', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
  TIRO
</div>
<MenuLinkItem
  icon={<LayoutDashboard size={20} />}
  active={pathname === '/tiro-cruscotto'}
  to="/tiro-cruscotto"
>
  <span>Cruscotto</span>
</MenuLinkItem>
<MenuLinkItem
  icon={<Users size={20} />}
  active={pathname.startsWith('/tiro-crm')}
  to="/tiro-crm"
>
  <span>Soggetti</span>
</MenuLinkItem>
<MenuLinkItem
  icon={<Search size={20} />}
  active={pathname === '/tiro-ricerca'}
  to="/tiro-ricerca"
>
  <span>Ricerca</span>
</MenuLinkItem>
<MenuLinkItem
  icon={<Brain size={20} />}
  active={pathname.startsWith('/tiro-decisionale')}
  to="/tiro-decisionale"
>
  <span>Decisionale</span>
</MenuLinkItem>
<MenuLinkItem
  icon={<Settings size={20} />}
  active={pathname === '/tiro-sistema'}
  to="/tiro-sistema"
>
  <span>Sistema</span>
</MenuLinkItem>
```

**Nota:** `MenuLinkItem` e il componente sidebar di AFFiNE. Verificare il nome esatto e l'API props ispezionando il file sidebar esistente. Se AFFiNE usa un componente diverso (es. `AppSidebarMenuLinkItem`), adattare.

- [ ] **Step 4: Creare Login Page**

File: `packages/frontend/apps/desktop/src/pages/tiro-login/login.css.ts`

```typescript
import { style } from '@vanilla-extract/css';

export const loginContainer = style({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100vh',
  backgroundColor: '#0F172A',
});

export const loginCard = style({
  backgroundColor: '#1E293B',
  border: '1px solid #334155',
  borderRadius: 8,
  padding: 32,
  width: 400,
});

export const loginTitle = style({
  color: '#F8FAFC',
  fontSize: 24,
  fontWeight: 700,
  marginBottom: 24,
  textAlign: 'center',
});

export const loginInput = style({
  width: '100%',
  backgroundColor: '#0F172A',
  border: '1px solid #475569',
  borderRadius: 6,
  color: '#F8FAFC',
  padding: '8px 12px',
  fontSize: 14,
  marginBottom: 16,
  outline: 'none',
  ':focus': {
    borderColor: '#0EA5E9',
  },
});

export const loginButton = style({
  width: '100%',
  backgroundColor: '#0EA5E9',
  color: '#FFFFFF',
  border: 'none',
  borderRadius: 6,
  padding: '10px 20px',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  ':hover': {
    backgroundColor: '#0284C7',
  },
  ':disabled': {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
});

export const loginError = style({
  color: '#EF4444',
  fontSize: 13,
  marginBottom: 16,
  textAlign: 'center',
});
```

File: `packages/frontend/apps/desktop/src/pages/tiro-login/index.tsx`

```tsx
import { useState, useCallback, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTiroApi } from '@affine/core/modules/tiro-api/hooks';
import * as styles from './login.css';

export function TiroLoginPage() {
  const api = useTiroApi();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login(email, password);
      navigate('/tiro-cruscotto');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore di login');
    } finally {
      setLoading(false);
    }
  }, [api, email, password, navigate]);

  return (
    <div className={styles.loginContainer}>
      <form className={styles.loginCard} onSubmit={handleSubmit}>
        <h1 className={styles.loginTitle}>TIRO</h1>
        {error && <div className={styles.loginError}>{error}</div>}
        <input
          className={styles.loginInput}
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
        <input
          className={styles.loginInput}
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
        <button
          className={styles.loginButton}
          type="submit"
          disabled={loading}
        >
          {loading ? 'Accesso...' : 'Accedi'}
        </button>
      </form>
    </div>
  );
}
export const Component = TiroLoginPage;
```

- [ ] **Step 5: Aggiungere route login e redirect**

In `workbench-router.ts`:
```typescript
{ path: '/tiro-login', lazy: () => import('./pages/tiro-login/index') }
```

Aggiungere guard: se `AuthStore.isAuthenticated()` e `false`, redirect a `/tiro-login`.

- [ ] **Step 6: Verificare navigazione**

```bash
cd /root/TIRO/tiro-ui && yarn dev
```

Verificare:
- Login page appare a `/tiro-login`
- Dopo login, redirect a `/tiro-cruscotto`
- Sidebar mostra le 5 voci TIRO
- Click su ogni voce naviga alla pagina placeholder corretta
- Nessun riferimento visibile a "AFFiNE"

**Criteri di completamento:**
- Routing funzionante con 8 pagine (5 moduli + 2 sub-page + login)
- Sidebar con icone Lucide e voci TIRO
- Login page con form email/password
- Redirect automatico se non autenticato

---

## Task 4: Cruscotto (Dashboard Homepage)

**Files:**
- Modify: `pages/workspace/tiro-cruscotto/index.tsx` — sostituire placeholder
- Create: `modules/tiro-cruscotto/index.ts`
- Create: `modules/tiro-cruscotto/views/cruscotto-page.tsx`
- Create: `modules/tiro-cruscotto/views/cruscotto-page.css.ts`
- Create: `modules/tiro-cruscotto/components/kpi-card.tsx`
- Create: `modules/tiro-cruscotto/components/kpi-card.css.ts`
- Create: `modules/tiro-cruscotto/components/flussi-recenti.tsx`
- Create: `modules/tiro-cruscotto/components/flussi-recenti.css.ts`
- Create: `modules/tiro-cruscotto/components/proposte-widget.tsx`
- Create: `modules/tiro-cruscotto/components/proposte-widget.css.ts`

**Obiettivo:** Dashboard con KPI cards, timeline flussi recenti, widget proposte in attesa.

- [ ] **Step 1: Creare vanilla-extract theme tokens**

File: `modules/tiro-cruscotto/views/cruscotto-page.css.ts`

```typescript
import { style } from '@vanilla-extract/css';

export const pageContainer = style({
  padding: 24,
  backgroundColor: '#0F172A',
  minHeight: '100%',
});

export const pageTitle = style({
  color: '#F8FAFC',
  fontSize: 20,
  fontWeight: 600,
  marginBottom: 24,
});

export const kpiGrid = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(4, 1fr)',
  gap: 16,
  marginBottom: 32,
});

export const contentGrid = style({
  display: 'grid',
  gridTemplateColumns: '2fr 1fr',
  gap: 24,
});
```

- [ ] **Step 2: KPI Card component**

File: `modules/tiro-cruscotto/components/kpi-card.css.ts`

```typescript
import { style } from '@vanilla-extract/css';

export const card = style({
  backgroundColor: '#1E293B',
  border: '1px solid #334155',
  borderRadius: 8,
  padding: 20,
});

export const label = style({
  color: '#94A3B8',
  fontSize: 13,
  fontWeight: 500,
  marginBottom: 8,
});

export const value = style({
  color: '#F8FAFC',
  fontSize: 32,
  fontWeight: 700,
  lineHeight: 1.25,
});

export const subtext = style({
  color: '#CBD5E1',
  fontSize: 13,
  marginTop: 4,
});
```

File: `modules/tiro-cruscotto/components/kpi-card.tsx`

```tsx
import * as styles from './kpi-card.css';

interface KpiCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  color?: string; // accent color for value
}

export function KpiCard({ label, value, subtext, color }: KpiCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value} style={color ? { color } : undefined}>
        {value}
      </div>
      {subtext && <div className={styles.subtext}>{subtext}</div>}
    </div>
  );
}
```

- [ ] **Step 3: Flussi Recenti component**

File: `modules/tiro-cruscotto/components/flussi-recenti.tsx`

Lista verticale dei 20 flussi piu recenti. Ogni riga mostra:
- Icona canale (Mail, MessageSquare, Mic, FileText da Lucide)
- Direzione (freccia entrata/uscita)
- Oggetto o troncamento contenuto (max 80 char)
- Timestamp relativo ("3 ore fa")
- Badge canale colorato

Chiama `api.get<Flusso[]>('/flussi')` al mount.

- [ ] **Step 4: Proposte Widget component**

File: `modules/tiro-cruscotto/components/proposte-widget.tsx`

Widget che mostra le proposte `in_attesa`, con bottoni Approva/Rifiuta inline:
- Chiama `api.get<Proposta[]>('/proposte/?stato=in_attesa&limit=10')`
- Ogni proposta mostra: titolo, ruolo_agente (badge viola), livello_rischio (badge colore)
- Bottoni: Approva (verde `#22C55E`) e Rifiuta (rosso `#EF4444`)
- Click Approva chiama `api.patch('/proposte/{id}/approva')`
- Click Rifiuta chiama `api.patch('/proposte/{id}/rifiuta')`
- Dopo azione, ricarica lista

- [ ] **Step 5: Assemblare CruscottoPage**

File: `modules/tiro-cruscotto/views/cruscotto-page.tsx`

```tsx
import { useEffect, useState } from 'react';
import { useTiroApi } from '../../tiro-api/hooks';
import type { Soggetto, Opportunita, Proposta } from '../../tiro-api/types';
import { KpiCard } from '../components/kpi-card';
import { FlussiRecenti } from '../components/flussi-recenti';
import { ProposteWidget } from '../components/proposte-widget';
import * as styles from './cruscotto-page.css';

export function CruscottoPage() {
  const api = useTiroApi();
  const [soggetti, setSoggetti] = useState<Soggetto[]>([]);
  const [opportunita, setOpportunita] = useState<Opportunita[]>([]);
  const [proposteInAttesa, setProposteInAttesa] = useState<Proposta[]>([]);

  useEffect(() => {
    Promise.all([
      api.get<Soggetto[]>('/soggetti'),
      api.get<Opportunita[]>('/opportunita'),
      api.get<Proposta[]>('/proposte/?stato=in_attesa'),
    ]).then(([s, o, p]) => {
      setSoggetti(s);
      setOpportunita(o);
      setProposteInAttesa(p);
    });
  }, [api]);

  const valPipeline = opportunita
    .filter(o => !o.fase.startsWith('chiuso'))
    .reduce((sum, o) => sum + (o.valore_eur ?? 0), 0);

  return (
    <div className={styles.pageContainer}>
      <h1 className={styles.pageTitle}>Cruscotto</h1>
      <div className={styles.kpiGrid}>
        <KpiCard label="Soggetti attivi" value={soggetti.length} />
        <KpiCard
          label="Opportunita aperte"
          value={opportunita.filter(o => !o.fase.startsWith('chiuso')).length}
          color="#14B8A6"
        />
        <KpiCard
          label="Valore pipeline"
          value={`€${valPipeline.toLocaleString('it-IT')}`}
          color="#0EA5E9"
        />
        <KpiCard
          label="Proposte in attesa"
          value={proposteInAttesa.length}
          color={proposteInAttesa.length > 0 ? '#F59E0B' : '#22C55E'}
        />
      </div>
      <div className={styles.contentGrid}>
        <FlussiRecenti />
        <ProposteWidget />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Collegare alla route**

Modificare `pages/workspace/tiro-cruscotto/index.tsx` per re-esportare:

```tsx
import { ViewBody, ViewHeader, ViewTitle } from '@affine/core/modules/workbench';
import { CruscottoPage } from '@affine/core/modules/tiro-cruscotto/views/cruscotto-page';

export function TiroCruscottoPage() {
  return (
    <>
      <ViewHeader><ViewTitle title="Cruscotto" /></ViewHeader>
      <ViewBody><CruscottoPage /></ViewBody>
    </>
  );
}
export const Component = TiroCruscottoPage;
```

**Criteri di completamento:**
- 4 KPI cards mostrano dati reali da API
- Timeline flussi recenti con icone canale e timestamp relativi
- Widget proposte con bottoni Approva/Rifiuta funzionanti
- Stile conforme a DESIGN.md (dark theme, colori, spacing)

---

## Task 5: CRM — Lista Soggetti + Scheda Soggetto

**Files:**
- Create: `modules/tiro-crm/index.ts`
- Create: `modules/tiro-crm/views/soggetti-lista.tsx`
- Create: `modules/tiro-crm/views/soggetti-lista.css.ts`
- Create: `modules/tiro-crm/views/soggetto-scheda.tsx`
- Create: `modules/tiro-crm/views/soggetto-scheda.css.ts`
- Create: `modules/tiro-crm/components/soggetto-card.tsx`
- Create: `modules/tiro-crm/components/soggetto-form.tsx`
- Create: `modules/tiro-crm/components/soggetto-form.css.ts`
- Modify: `pages/workspace/tiro-crm/index.tsx`
- Create: `pages/workspace/tiro-crm/soggetto.tsx`

**Obiettivo:** Pagina lista soggetti con filtri + pagina dettaglio soggetto con timeline flussi.

- [ ] **Step 1: Lista Soggetti con tabella e filtri**

`modules/tiro-crm/views/soggetti-lista.tsx`:

- Tabella con colonne: Nome, Cognome, Tipo, Email, Ruolo, Tag, Creato il
- Filtro dropdown per `tipo` (membro, esterno, partner, istituzione)
- Barra ricerca locale (filter client-side per nome/cognome)
- Click su riga naviga a `/tiro-crm/{id}`
- Bottone "Nuovo Soggetto" apre modale/drawer con form creazione
- Stile tabella da DESIGN.md: header bg `#1E293B`, header text `#94A3B8` uppercase 12px

API call: `api.get<Soggetto[]>('/soggetti')`, con filtro `?tipo=` se selezionato.

- [ ] **Step 2: Form Creazione Soggetto**

`modules/tiro-crm/components/soggetto-form.tsx`:

Modale o pannello laterale con campi:
- Tipo (select: membro/esterno/partner/istituzione)
- Nome (input text, required)
- Cognome (input text, required)
- Email (input, pulsante "+" per aggiungere multipli)
- Telefono (input, pulsante "+" per aggiungere multipli)
- Ruolo (input text, optional)
- Tag (input con chips, comma-separated)

Submit chiama `api.post('/soggetti', data)`. Successo chiude modale e ricarica lista.

Styling input/button da DESIGN.md.

- [ ] **Step 3: Scheda Soggetto (dettaglio)**

`modules/tiro-crm/views/soggetto-scheda.tsx`:

Layout a due colonne:
- **Colonna sinistra (2/3):** Timeline flussi del soggetto
- **Colonna destra (1/3):** Profilo e info

Profilo card (colonna destra):
- Nome cognome (xl, 17px)
- Tipo badge (stile badge da DESIGN.md)
- Email (lista, cliccabili)
- Telefono (lista)
- Ruolo
- Tag come chips
- Bottone "Modifica" apre form precompilato
- Data creazione/aggiornamento in formato relativo

Timeline flussi (colonna sinistra):
- Chiama `api.get<Flusso[]>('/flussi?soggetto_id={id}')`
- Lista verticale cronologica con linea laterale
- Ogni flusso: icona canale, direzione, oggetto, troncamento contenuto, timestamp
- Badge canale colorato (messaggio=primary, posta=info, voce=accent, documento=default)

- [ ] **Step 4: Collegare alle routes**

`pages/workspace/tiro-crm/index.tsx` → importa `SoggettiLista`
`pages/workspace/tiro-crm/soggetto.tsx` → importa `SoggettoScheda`, legge `:soggettoId` da params

```tsx
// pages/workspace/tiro-crm/soggetto.tsx
import { useParams } from 'react-router-dom';
import { ViewBody, ViewHeader, ViewTitle } from '@affine/core/modules/workbench';
import { SoggettoScheda } from '@affine/core/modules/tiro-crm/views/soggetto-scheda';

export function SoggettoPage() {
  const { soggettoId } = useParams<{ soggettoId: string }>();
  return (
    <>
      <ViewHeader><ViewTitle title="Soggetto" /></ViewHeader>
      <ViewBody>
        <SoggettoScheda soggettoId={Number(soggettoId)} />
      </ViewBody>
    </>
  );
}
export const Component = SoggettoPage;
```

**Criteri di completamento:**
- Tabella soggetti con filtro per tipo e ricerca locale
- Click su riga apre scheda dettaglio
- Scheda mostra profilo + timeline flussi
- Form creazione soggetto funzionante
- Tutti gli stili conformi a DESIGN.md

---

## Task 6: CRM — Pipeline Kanban

**Files:**
- Create: `modules/tiro-crm/views/pipeline-kanban.tsx`
- Create: `modules/tiro-crm/views/pipeline-kanban.css.ts`
- Create: `modules/tiro-crm/components/kanban-colonna.tsx`
- Create: `modules/tiro-crm/components/kanban-colonna.css.ts`
- Create: `modules/tiro-crm/components/opportunita-card.tsx`
- Create: `modules/tiro-crm/components/opportunita-card.css.ts`
- Modify: `pages/workspace/tiro-crm/pipeline.tsx`
- Modify sidebar: aggiungere sub-link "Pipeline" sotto "Soggetti"

**Obiettivo:** Kanban board delle opportunita con drag-and-drop tra fasi.

- [ ] **Step 1: Layout Kanban a colonne orizzontali**

`modules/tiro-crm/views/pipeline-kanban.css.ts`:

```typescript
import { style } from '@vanilla-extract/css';

export const kanbanContainer = style({
  display: 'flex',
  gap: 16,
  padding: 24,
  overflowX: 'auto',
  height: '100%',
  backgroundColor: '#0F172A',
});

export const columnContainer = style({
  minWidth: 280,
  maxWidth: 320,
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
});

export const columnHeader = style({
  padding: '8px 12px',
  marginBottom: 12,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
});

export const columnTitle = style({
  color: '#94A3B8',
  fontSize: 12,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
});

export const columnCount = style({
  backgroundColor: '#334155',
  color: '#CBD5E1',
  borderRadius: 4,
  padding: '2px 8px',
  fontSize: 12,
});

export const columnCards = style({
  flex: 1,
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
});
```

- [ ] **Step 2: Opportunita Card**

`modules/tiro-crm/components/opportunita-card.tsx`:

Card con:
- Titolo (xl, 17px)
- Valore EUR (formattato `€12.500`, colore accent `#14B8A6`)
- Probabilita (badge percentuale)
- Data chiusura prevista (se presente)
- Soggetto collegato (nome, se disponibile)

Stile card da DESIGN.md: bg `#1E293B`, border `#334155`, radius 8px, padding 16px.

- [ ] **Step 3: Pipeline Kanban View**

`modules/tiro-crm/views/pipeline-kanban.tsx`:

6 colonne fisse corrispondenti alle fasi:
1. Contatto
2. Qualificato
3. Proposta
4. Trattativa
5. Chiuso OK (colore success)
6. Chiuso No (colore error, opacita ridotta)

Carica tutte le opportunita con `api.get<Opportunita[]>('/opportunita')` e raggruppa per `fase`.

Header ogni colonna: nome fase + count + valore totale EUR della colonna.

- [ ] **Step 4: Drag-and-Drop**

Per v1, implementare drag-and-drop semplice con HTML5 Drag API nativa:
- `draggable="true"` sulle card
- `onDragStart`: salva `opportunita.id` in `dataTransfer`
- `onDragOver` + `onDrop` sulle colonne: legge id, chiama API per aggiornare fase

**Nota:** L'API `PATCH /api/opportunita/{id}` non esiste ancora in tiro-core. Aggiungere l'endpoint:

```python
# tiro_core/api/opportunita.py — aggiungere
@router.patch("/{opportunita_id}", response_model=OpportunitaResponse)
async def aggiorna_opportunita(
    opportunita_id: int,
    dati: OpportunitaAggiorna,  # nuovo schema con fase opzionale
    db: AsyncSession = Depends(get_db),
    utente: Utente = Depends(get_utente_corrente),
):
    # ... stessa logica di aggiorna_soggetto
```

Se l'endpoint non e disponibile al momento del frontend, usare un `console.warn` e aggiornare lo stato solo localmente.

- [ ] **Step 5: Collegare alla route e sidebar**

Route gia registrata in Task 3: `/tiro-crm/pipeline`.

Aggiungere sub-navigazione nel modulo CRM: tabs "Soggetti" | "Pipeline" in alto nella pagina.

**Criteri di completamento:**
- Kanban con 6 colonne per fase opportunita
- Card mostrano titolo, valore, probabilita
- Drag-and-drop funzionante (almeno visivamente, anche senza API PATCH)
- Totale valore per colonna nel header

---

## Task 7: Modulo Decisionale — Proposte + WebSocket

**Files:**
- Create: `modules/tiro-decisionale/index.ts`
- Create: `modules/tiro-decisionale/views/proposte-lista.tsx`
- Create: `modules/tiro-decisionale/views/proposte-lista.css.ts`
- Create: `modules/tiro-decisionale/views/sessioni-lista.tsx`
- Create: `modules/tiro-decisionale/views/sessioni-lista.css.ts`
- Create: `modules/tiro-decisionale/components/proposta-card.tsx`
- Create: `modules/tiro-decisionale/components/proposta-card.css.ts`
- Create: `modules/tiro-decisionale/components/rischio-badge.tsx`
- Create: `modules/tiro-decisionale/components/rischio-badge.css.ts`
- Create: `modules/tiro-api/services/ws-client.ts`
- Modify: `pages/workspace/tiro-decisionale/index.tsx`
- Create: `pages/workspace/tiro-decisionale/sessioni.tsx`

**Obiettivo:** Coda proposte filtrabile con approve/reject real-time via WebSocket. Vista sessioni read-only.

- [ ] **Step 1: WebSocket Client**

File: `modules/tiro-api/services/ws-client.ts`

```typescript
type EventHandler = (data: unknown) => void;

export class TiroWsClient {
  private ws: WebSocket | null = null;
  private handlers: Set<EventHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly url: string;

  constructor(baseUrl: string = 'ws://localhost:8000') {
    this.url = `${baseUrl}/ws/eventi`;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.forEach(h => h(data));
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }
}
```

Aggiungere hook:

```typescript
// modules/tiro-api/hooks.ts — aggiungere
import { TiroWsClient } from './services/ws-client';

let _ws: TiroWsClient | null = null;

export function useTiroWs(): TiroWsClient {
  if (!_ws) {
    _ws = new TiroWsClient();
    _ws.connect();
  }
  return _ws;
}
```

- [ ] **Step 2: Rischio Badge component**

File: `modules/tiro-decisionale/components/rischio-badge.tsx`

Badge che mostra livello rischio con colore + icona + testo (accessibilita DESIGN.md):
- basso: `#22C55E` + ShieldCheck
- medio: `#F59E0B` + AlertTriangle
- alto: `#F97316` + AlertOctagon
- critico: `#EF4444` + ShieldAlert

```tsx
import { ShieldCheck, AlertTriangle, AlertOctagon, ShieldAlert } from 'lucide-react';
import type { LivelloRischio } from '../../tiro-api/types';

const CONFIG: Record<LivelloRischio, { color: string; bg: string; Icon: typeof ShieldCheck }> = {
  basso:   { color: '#22C55E', bg: 'rgba(34,197,94,0.15)',  Icon: ShieldCheck },
  medio:   { color: '#F59E0B', bg: 'rgba(245,158,11,0.15)', Icon: AlertTriangle },
  alto:    { color: '#F97316', bg: 'rgba(249,115,22,0.15)', Icon: AlertOctagon },
  critico: { color: '#EF4444', bg: 'rgba(239,68,68,0.15)',  Icon: ShieldAlert },
};

export function RischioBadge({ livello }: { livello: LivelloRischio }) {
  const { color, bg, Icon } = CONFIG[livello];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      backgroundColor: bg, color, borderRadius: 4,
      padding: '2px 8px', fontSize: 12, fontWeight: 500,
    }}>
      <Icon size={14} />
      {livello}
    </span>
  );
}
```

- [ ] **Step 3: Proposta Card component**

File: `modules/tiro-decisionale/components/proposta-card.tsx`

Card per singola proposta:
- Titolo (bold, 15px)
- Descrizione (troncata 2 righe, colore text-secondary)
- Badge `ruolo_agente` in viola (`#8B5CF6/15%` bg, `#A78BFA` text)
- Badge `tipo_azione` in default
- `RischioBadge` per `livello_rischio`
- Stato badge (in_attesa=warning, approvata=success, rifiutata=error)
- Timestamp `creato_il` relativo
- Se `stato === 'in_attesa'`: bottoni Approva (verde) e Rifiuta (rosso)

- [ ] **Step 4: ProposteLista view**

File: `modules/tiro-decisionale/views/proposte-lista.tsx`

- Filtri in alto: stato (dropdown), livello_rischio (dropdown), limit (select 20/50/100)
- Lista card proposte
- Chiama `api.get<Proposta[]>('/proposte/?stato=X&livello=Y&limit=Z')`
- Bottone Approva/Rifiuta su ogni card chiama PATCH e ricarica
- WebSocket: ascolta eventi `nuova_proposta` e aggiunge card in tempo reale
  ```typescript
  const ws = useTiroWs();
  useEffect(() => {
    const unsub = ws.subscribe((data: any) => {
      if (data.tipo === 'nuova_proposta') {
        // Ricarica lista
        loadProposte();
      }
    });
    return unsub;
  }, [ws]);
  ```

- [ ] **Step 5: SessioniLista view (read-only)**

File: `modules/tiro-decisionale/views/sessioni-lista.tsx`

**Nota:** L'API `/api/sessioni` non esiste ancora in tiro-core. Per v1:
- Mostrare pagina placeholder "Sessioni — disponibile in una versione futura"
- Oppure, se si aggiunge l'endpoint, mostrare tabella con: ciclo, partecipanti (come chips), data, link per espandere consenso/conflitti in JSON formattato

- [ ] **Step 6: Collegare alle routes**

- `pages/workspace/tiro-decisionale/index.tsx` → `ProposteLista`
- `pages/workspace/tiro-decisionale/sessioni.tsx` → `SessioniLista`
- Tabs in alto: "Proposte" | "Sessioni"

**Criteri di completamento:**
- Lista proposte filtrabile per stato e livello rischio
- Badge rischio accessibili (colore + icona + testo)
- Bottoni Approva/Rifiuta funzionanti con API reale
- WebSocket connesso per aggiornamenti real-time
- Badge agente in viola da DESIGN.md

---

## Task 8: Modulo Ricerca

**Files:**
- Create: `modules/tiro-ricerca/index.ts`
- Create: `modules/tiro-ricerca/views/ricerca-page.tsx`
- Create: `modules/tiro-ricerca/views/ricerca-page.css.ts`
- Create: `modules/tiro-ricerca/components/barra-ricerca.tsx`
- Create: `modules/tiro-ricerca/components/barra-ricerca.css.ts`
- Create: `modules/tiro-ricerca/components/risultato-card.tsx`
- Create: `modules/tiro-ricerca/components/risultato-card.css.ts`
- Modify: `pages/workspace/tiro-ricerca/index.tsx`

**Obiettivo:** Pagina ricerca full-text nei flussi e risorse. La ricerca semantica (vettoriale) richiede embedding lato server, quindi per v1 implementare solo ricerca testuale client-side + layout pronto per semantica.

- [ ] **Step 1: Barra Ricerca component**

`modules/tiro-ricerca/components/barra-ricerca.tsx`:

Input grande stile search con icona Search da Lucide:
- Background `#0F172A`, border `#475569`, focus border `#0EA5E9`
- Placeholder "Cerca in flussi e risorse..."
- Bottone "Cerca" primary
- Toggle: "Flussi" | "Risorse" (seleziona tabella per ricerca semantica)

- [ ] **Step 2: Risultato Card component**

`modules/tiro-ricerca/components/risultato-card.tsx`:

Card per ogni risultato:
- Contenuto (troncato, con highlight della query se ricerca testuale)
- ID in font mono
- Score/distanza (se ricerca semantica)
- Badge tabella (Flusso / Risorsa)

- [ ] **Step 3: Ricerca Page**

`modules/tiro-ricerca/views/ricerca-page.tsx`:

Per v1, implementare due modalita:

**Modalita 1 — Ricerca locale (default):**
- Carica tutti i flussi con `api.get<Flusso[]>('/flussi')`
- Filtra client-side per `contenuto` o `oggetto` che contiene la query
- Mostra risultati come lista di `RisultatoCard`

**Modalita 2 — Ricerca semantica (futura):**
- La ricerca semantica richiede che il frontend invii un vettore embedding
- Per ora, mostrare un banner: "Ricerca semantica: richiede configurazione embedding"
- Layout pronto: quando disponibile, chiamera `api.post('/ricerca', { vettore, limite, tabella })`

- [ ] **Step 4: Collegare alla route**

`pages/workspace/tiro-ricerca/index.tsx` → `RicercaPage`

**Criteri di completamento:**
- Barra ricerca con input e filtri
- Risultati mostrano contenuto flusso con highlight query
- Stile conforme DESIGN.md
- Layout predisposto per ricerca semantica futura

---

## Task 9: Modulo Sistema (Admin)

**Files:**
- Create: `modules/tiro-sistema/index.ts`
- Create: `modules/tiro-sistema/views/regole-lista.tsx`
- Create: `modules/tiro-sistema/views/regole-lista.css.ts`
- Modify: `pages/workspace/tiro-sistema/index.tsx`

**Obiettivo:** Pannello admin con lista regole rischio. Gestione utenti e configurazione sono placeholder per v1 (l'API non e completa).

- [ ] **Step 1: Regole Rischio — Tabella**

`modules/tiro-sistema/views/regole-lista.tsx`:

Tabella delle regole rischio con colonne:
- Pattern azione
- Livello rischio (con `RischioBadge`)
- Descrizione
- Approvazione automatica (Si/No con icona Check/X)

Chiama `api.get<RegolaRischio[]>('/sistema/regole')`.

Stile tabella DESIGN.md: header bg `#1E293B`, text `#94A3B8`, uppercase, 12px.

**Nota di accesso:** Questo endpoint richiede ruolo `titolare` o `responsabile`. Se l'utente non ha il permesso, l'API ritorna 403. Gestire mostrando: "Accesso riservato al titolare e responsabili."

- [ ] **Step 2: Sezioni Placeholder**

Nella pagina Sistema, mostrare tabs:
- **Regole** (funzionante — Step 1)
- **Utenti** — placeholder "Gestione utenti — prossimamente"
- **Configurazione** — placeholder "Configurazione runtime — prossimamente"
- **Registro** — placeholder "Audit trail — prossimamente"

Ogni placeholder usa empty state da DESIGN.md: icona 48px `#475569` + testo `#64748B` + nessun CTA.

- [ ] **Step 3: Collegare alla route**

`pages/workspace/tiro-sistema/index.tsx` → `SistemaPage` con tabs.

**Criteri di completamento:**
- Tabella regole rischio con badge livello
- Gestione errore 403 per ruoli non autorizzati
- Placeholder per sezioni future
- Stile conforme DESIGN.md

---

## Task 10: Docker, Test Build, Integrazione Finale

**Files:**
- Create: `tiro-ui/Dockerfile`
- Modify: `docker-compose.yml` — aggiungere servizio tiro-ui
- Create: `tiro-ui/.env.example`

**Obiettivo:** Container Docker funzionante per tiro-ui, integrato nel Docker Compose di TIRO.

- [ ] **Step 1: Dockerfile per tiro-ui**

```dockerfile
# tiro-ui/Dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY . .
RUN corepack enable && yarn install --immutable
RUN yarn build

FROM node:22-alpine AS runner
WORKDIR /app
# Copiare solo l'output di build (verificare la directory di output di AFFiNE)
# Tipicamente e packages/frontend/apps/desktop/dist o simile
COPY --from=builder /app/packages/frontend/apps/desktop/dist ./dist
# Per servire i file statici, usare un server leggero
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

**Nota:** La struttura di build di AFFiNE e complessa (Electron + web). Per il deploy web:
- Verificare come AFFiNE produce la web build (non Electron)
- Potrebbe essere in `packages/frontend/apps/web/` invece di `desktop/`
- Adattare il Dockerfile di conseguenza

- [ ] **Step 2: Aggiungere servizio in docker-compose.yml**

```yaml
# docker-compose.yml — aggiungere
services:
  tiro-ui:
    build:
      context: ./tiro-ui
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - TIRO_API_URL=http://tiro-core:8000
    depends_on:
      - tiro-core
    networks:
      - tiro-network
    restart: unless-stopped
```

- [ ] **Step 3: Creare .env.example per tiro-ui**

```env
# tiro-ui/.env.example
TIRO_API_URL=http://localhost:8000
```

- [ ] **Step 4: Configurare CORS su tiro-core**

In `tiro-core/tiro_core/main.py`, verificare che CORS permetta `http://localhost:3000`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://tiro-ui:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 5: Smoke Test integrazione**

```bash
docker compose up --build
# Verificare:
# 1. http://localhost:3000 mostra login TIRO
# 2. Login funziona con credenziali del DB
# 3. Cruscotto mostra KPI da tiro-core
# 4. Soggetti carica lista da API
# 5. Proposte carica e permette approve/reject
# 6. WebSocket si connette
```

- [ ] **Step 6: Aggiungere script di dev locale**

Nel root `package.json` o in un `Makefile`:

```bash
# Dev: avvia tiro-core + tiro-ui in parallelo
# Terminal 1:
cd tiro-core && uvicorn tiro_core.main:app --reload --port 8000
# Terminal 2:
cd tiro-ui && yarn dev
```

**Criteri di completamento:**
- `docker compose up --build` avvia tiro-ui sulla porta 3000
- CORS configurato per permettere richieste da tiro-ui a tiro-core
- Login → Cruscotto → Soggetti → Proposte funziona end-to-end
- Nessun errore CORS o connessione nel browser console

---

## Ordine di Esecuzione Consigliato

| Ordine | Task | Dipende da | Stima |
|--------|------|------------|-------|
| 1 | Task 1: Fork + Rebrand | — | 4-6h |
| 2 | Task 2: API Client + Auth | Task 1 | 2-3h |
| 3 | Task 3: Routing + Sidebar + Login | Task 1, 2 | 3-4h |
| 4 | Task 4: Cruscotto | Task 2, 3 | 3-4h |
| 5 | Task 5: CRM Lista + Scheda | Task 2, 3 | 4-5h |
| 6 | Task 6: CRM Pipeline Kanban | Task 5 | 3-4h |
| 7 | Task 7: Decisionale + WebSocket | Task 2, 3 | 4-5h |
| 8 | Task 8: Ricerca | Task 2, 3 | 2-3h |
| 9 | Task 9: Sistema Admin | Task 2, 3 | 2-3h |
| 10 | Task 10: Docker + Integrazione | Task 1-9 | 3-4h |

**Totale stimato:** 30-41 ore di lavoro agentico.

**Rischi principali:**
1. **Build AFFiNE complessa** — il monorepo usa yarn workspaces con molte dipendenze. La prima build potrebbe fallire per versioni Node/Yarn. Prevedere troubleshooting.
2. **DI Framework** — il pattern esatto di `@toeverything/infra` potrebbe differire da quanto documentato. Ispezionare moduli esistenti come reference.
3. **Web vs Electron** — AFFiNE e primariamente Electron. La web build potrebbe richiedere configurazione aggiuntiva.
4. **PATCH opportunita** — l'API backend non ha ancora l'endpoint per aggiornare la fase. Task 6 potrebbe richiedere un piccolo PR su tiro-core.

---

## Convenzioni Codice

- **File naming:** kebab-case per tutti i file (es. `kpi-card.tsx`, `kpi-card.css.ts`)
- **Component naming:** PascalCase (es. `KpiCard`, `ProposteWidget`)
- **CSS:** vanilla-extract (`.css.ts`), NO Tailwind, NO CSS-in-JS runtime
- **State management:** React state + hooks per v1. Nessun Redux/Zustand/Jotai.
- **Error handling:** try/catch su ogni API call, mostrare messaggio utente-friendly
- **No mutation:** creare nuovi array/oggetti per aggiornamenti di stato
- **Terminology:** SOLO soggetti, flussi, fascicoli, proposte, opportunita, enti, cruscotto
- **Accessibility:** rischio sempre comunicato con colore + icona + testo
