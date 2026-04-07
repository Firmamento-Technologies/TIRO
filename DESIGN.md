# DESIGN.md — TIRO

> This file defines the visual design system for TIRO.
> AI agents MUST follow these constraints when generating UI code.
> Generated with `/design-system create` skill.

---

## 1. Visual Theme & Atmosphere

**Mood:** Centro di comando aziendale intelligente — professionale, preciso, autorevole ma accessibile. Comunica "intelligenza al tuo servizio" senza essere freddo o intimidatorio.

**Design Philosophy:** Dark-first interface con accenti luminosi per guidare l'attenzione. Il layout e denso di informazioni ma mai caotico — ogni dato ha il suo spazio. Le superfici scure riducono l'affaticamento visivo per uso prolungato (dashboard che resta aperta tutto il giorno). L'interfaccia respira attraverso spacing consistente e gerarchia tipografica chiara.

**Visual Metaphors:** Plancia di controllo (non cockpit — niente elementi decorativi). Le azioni degli agenti AI sono visibili ma non invasive — suggeriscono, non comandano. I livelli di rischio usano colore e posizione, mai solo colore (accessibilita).

**Color Temperature:** Cool (blu/ciano dominant)
**Whitespace:** Balanced — denso nelle tabelle e kanban, arioso nelle schede soggetto e fascicoli
**Animation:** Minimal — solo transizioni funzionali (300ms ease), nessuna animazione decorativa

---

## 2. Color Palette

### Primary
- **Primary** — `#0EA5E9` — Azioni principali, link attivi, elementi interattivi, badge CRM
- **Primary Dark** — `#0284C7` — Hover su elementi primary, sidebar attivo
- **Primary Light** — `#38BDF8` — Focus ring, highlight selezione

### Secondary
- **Secondary** — `#8B5CF6` — Elementi agentici (proposte, sessioni, deliberazioni), badge decisionale
- **Secondary Dark** — `#7C3AED` — Hover su elementi agentici
- **Secondary Light** — `#A78BFA` — Background leggero per card agentiche

### Accent
- **Accent** — `#14B8A6` — Indicatori positivi, trend in crescita, scoring alto, opportunita
- **Accent Dark** — `#0D9488` — Hover su accent

### Neutrals (Dark Theme)
- **Background** — `#0F172A` — Sfondo principale pagina (slate-900)
- **Surface** — `#1E293B` — Card, pannelli, sidebar (slate-800)
- **Surface Elevated** — `#334155` — Dropdown, tooltip, modal (slate-700)
- **Border** — `#475569` — Bordi, divisori (slate-600)
- **Border Subtle** — `#334155` — Bordi leggeri, separatori secondari (slate-700)
- **Text Primary** — `#F8FAFC` — Testo principale, headings (slate-50)
- **Text Secondary** — `#CBD5E1` — Testo secondario, label (slate-300)
- **Text Muted** — `#94A3B8` — Placeholder, caption, timestamp (slate-400)
- **Text Disabled** — `#64748B` — Elementi disabilitati (slate-500)

### Semantic
- **Success** — `#22C55E` — Approvato, completato, connessione attiva
- **Warning** — `#F59E0B` — Rischio medio, timeout vicino, attenzione richiesta
- **Error** — `#EF4444` — Rischio critico, errore, rifiutato, connessione persa
- **Info** — `#3B82F6` — Informativo, suggerimento, notifica neutra

### Risk Level Colors (specifici TIRO)
- **Rischio Basso** — `#22C55E` (success) — Auto-approvato, nessuna azione richiesta
- **Rischio Medio** — `#F59E0B` (warning) — Richiede attenzione, timer attivo
- **Rischio Alto** — `#F97316` (orange-500) — Blocca fino ad approvazione
- **Rischio Critico** — `#EF4444` (error) — Blocca, doppia conferma richiesta

---

## 3. Typography

**Font Families:**
- **Headings:** Inter, -apple-system, sans-serif
- **Body:** Inter, -apple-system, sans-serif
- **Mono:** JetBrains Mono, Menlo, monospace

**Size Scale:**

| Token | Size | Usage |
|-------|------|-------|
| xs | 11px | Badge count, timestamp compatto |
| sm | 13px | Label, caption, metadata tabella |
| base | 14px | Body text, celle tabella, input |
| lg | 15px | Lead text, descrizione card |
| xl | 17px | Titolo card, nome soggetto |
| 2xl | 20px | Titolo sezione, nome pagina |
| 3xl | 24px | KPI value, titolo fascicolo |
| 4xl | 32px | KPI hero nel cruscotto |

**Weights:** Regular (400), Medium (500), Semibold (600), Bold (700)
**Body line-height:** 1.5 | **Heading line-height:** 1.25
**Letter spacing heading:** -0.01em | **Letter spacing body:** 0

**Nota:** La size base e 14px (non 16px) perche TIRO e una dashboard densa — 16px spreca spazio nelle tabelle e sidebar. Il body text nelle schede fascicolo usa 15px (lg) per leggibilita dei testi lunghi.

---

## 4. Component Styling

### Buttons

| Variant | Background | Text | Border | Hover | Usage |
|---------|-----------|------|--------|-------|-------|
| Primary | `#0EA5E9` | `#FFFFFF` | none | `#0284C7` | Azioni principali: Salva, Crea, Approva |
| Secondary | transparent | `#CBD5E1` | `1px #475569` | bg `#334155` | Azioni secondarie: Annulla, Filtra |
| Ghost | transparent | `#94A3B8` | none | bg `#1E293B` | Azioni terziarie: link in-text |
| Destructive | `#EF4444` | `#FFFFFF` | none | `#DC2626` | Rifiuta, Elimina |
| Approve | `#22C55E` | `#FFFFFF` | none | `#16A34A` | Approva proposta |

**Border radius:** 6px
**Padding:** 8px 16px (sm), 10px 20px (md), 12px 24px (lg)
**Focus:** ring 2px offset 2px `#38BDF8`
**Disabled:** opacity 0.5, cursor not-allowed

### Cards

- **Background:** `#1E293B` (surface)
- **Border:** `1px solid #334155` (border-subtle)
- **Border radius:** 8px
- **Shadow:** none (le card si distinguono per background, non ombra — tema dark)
- **Padding:** 16px (compatto), 20px (standard), 24px (ampio)
- **Hover:** border `#475569`

### Inputs

- **Background:** `#0F172A` (background)
- **Border:** `1px solid #475569`
- **Border radius:** 6px
- **Text:** `#F8FAFC`
- **Placeholder:** `#64748B`
- **Focus:** border `#0EA5E9`, ring 2px `#0EA5E9/20%`
- **Padding:** 8px 12px

### Navigation (Sidebar)

- **Sidebar background:** `#0F172A`
- **Sidebar width:** 240px (expanded), 48px (collapsed)
- **Item padding:** 8px 12px
- **Item hover:** bg `#1E293B`
- **Item active:** bg `#1E293B`, border-left 2px `#0EA5E9`, text `#F8FAFC`
- **Item inactive text:** `#94A3B8`
- **Section header:** `#64748B`, uppercase, 11px, letter-spacing 0.05em
- **Divider:** `#334155`

### Tables (frequenti in TIRO)

- **Header bg:** `#1E293B`
- **Header text:** `#94A3B8`, 12px, semibold, uppercase
- **Row bg:** transparent
- **Row hover:** `#1E293B`
- **Row border:** `1px solid #1E293B`
- **Cell padding:** 10px 12px
- **Alternating rows:** NO — uso hover per evidenziare

### Badges / Tag

| Variant | Background | Text |
|---------|-----------|------|
| Default | `#334155` | `#CBD5E1` |
| Primary | `#0EA5E9/15%` | `#38BDF8` |
| Success | `#22C55E/15%` | `#22C55E` |
| Warning | `#F59E0B/15%` | `#F59E0B` |
| Error | `#EF4444/15%` | `#EF4444` |
| Purple (agentico) | `#8B5CF6/15%` | `#A78BFA` |

**Border radius badge:** 4px | **Padding:** 2px 8px | **Font size:** 12px, medium

---

## 5. Layout & Spacing

**Spacing Scale:** 4px base

| Token | px | Usage |
|-------|-----|-------|
| 1 | 4 | Gap minimo tra icona e testo |
| 2 | 8 | Padding interno badge, gap tra elementi inline |
| 3 | 12 | Padding celle tabella, gap griglia compatta |
| 4 | 16 | Padding card compatta, gap standard |
| 5 | 20 | Padding card standard |
| 6 | 24 | Padding card ampia, gap tra sezioni |
| 8 | 32 | Separazione tra gruppi di contenuto |
| 10 | 40 | Margin tra sezioni pagina |
| 12 | 48 | Spazio sopra/sotto header pagina |
| 16 | 64 | Separazione tra aree principali |

**Page layout:**
- Sidebar (240px fixed) + Content area (fluid)
- Content max-width: nessuno (dashboard usa tutto lo spazio)
- Content padding: 24px
- Grid: CSS Grid o Flexbox, nessun framework

**Breakpoints (desktop-first):**
| Name | Width | Behavior |
|------|-------|----------|
| xl | >= 1280px | Layout completo, sidebar espansa |
| lg | >= 1024px | Sidebar collassata a icone |
| md | >= 768px | Layout singola colonna |
| sm | < 768px | Mobile — non prioritario per v1 |

---

## 6. Depth & Elevation

TIRO usa **separazione per colore** (non ombra) nel tema dark:

| Level | Surface | Usage |
|-------|---------|-------|
| 0 | `#0F172A` | Background pagina |
| 1 | `#1E293B` | Card, sidebar, pannelli |
| 2 | `#334155` | Dropdown, popover, tooltip |
| 3 | `#475569` | Modal overlay content |

**Modal backdrop:** `#000000/60%`
**Shadow:** usata SOLO per dropdown e modal flottanti: `0 4px 12px #000000/30%`
**Border radius:** 8px (card, modal), 6px (button, input), 4px (badge, tag)

---

## 7. Iconography & Assets

- **Icon set:** Lucide React (coerente, MIT, 1000+ icone)
- **Icon size:** 16px (inline), 20px (navigation), 24px (hero/empty state)
- **Icon color:** segue il testo — `#94A3B8` default, `#F8FAFC` quando attivo
- **Logo:** "TIRO" in Inter Bold 20px con icona bersaglio stilizzata (da definire)
- **Empty states:** Icona 48px `#475569` + testo `#64748B` + CTA primary

---

## 8. Do's and Don'ts

### Do
- Usa il dark theme SEMPRE — non esiste un tema chiaro per TIRO v1
- Comunica i livelli di rischio con colore + icona + testo (mai solo colore)
- Mantieni la gerarchia visiva: azioni primary (ciano), agentiche (viola), rischio (scala warning)
- Usa tabelle per dati strutturati, card per entita singole
- Mostra timestamp relativi ("3 ore fa") con tooltip per timestamp assoluto
- Allinea i numeri a destra nelle tabelle
- Usa il font mono per ID, hash, valori tecnici

### Don't
- NON usare mai il nome "AFFiNE" — il prodotto si chiama TIRO
- NON usare ombre per separare i livelli — usa colori di superficie
- NON aggiungere animazioni decorative — solo transizioni funzionali (300ms)
- NON usare rosso per azioni positive (anche se e "urgente")
- NON mescolare terminologia — usa SOLO: soggetti, flussi, fascicoli, proposte, opportunita, enti
- NON mostrare dati raw JSON all'utente — sempre formattati
- NON usare font size sotto 11px

---

## 9. Agent Prompt Guide

> **Per AI agent che generano UI per TIRO:**
>
> TIRO e una dashboard gestionale dark-theme. Usa sfondo `#0F172A`, superfici `#1E293B`, testo `#F8FAFC`.
> Font: Inter 14px base. Colori azione: ciano `#0EA5E9` (primary), viola `#8B5CF6` (agenti AI), teal `#14B8A6` (positivo).
> Rischio: verde (basso) → giallo (medio) → arancio (alto) → rosso (critico).
> Border radius: 8px card, 6px button/input, 4px badge.
> NO ombre (usa colori superficie per depth). NO animazioni decorative. NO riferimenti ad AFFiNE.
> Terminologia obbligatoria: soggetti, flussi, fascicoli, proposte, opportunita, enti, cruscotto, decisionale.
> Desktop-first, sidebar 240px + content fluid. Tabelle per liste, card per entita.
