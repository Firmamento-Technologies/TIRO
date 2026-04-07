export interface Soggetto {
  id: number;
  tipo: string;
  nome: string;
  cognome: string;
  email: string[];
  telefono: string[];
  organizzazione_id: number | null;
  ruolo: string | null;
  tag: string[];
  profilo: Record<string, unknown>;
  creato_il: string;
  aggiornato_il: string;
}

export interface Flusso {
  id: number;
  soggetto_id: number;
  canale: string;
  direzione: string;
  oggetto: string | null;
  contenuto: string | null;
  dati_grezzi: Record<string, unknown>;
  ricevuto_il: string;
  elaborato_il: string | null;
}

export interface Opportunita {
  id: number;
  ente_id: number | null;
  soggetto_id: number | null;
  titolo: string;
  fase: string;
  valore_eur: number | null;
  probabilita: number | null;
  chiusura_prevista: string | null;
  dettagli: Record<string, unknown>;
}

export interface Fascicolo {
  id: number;
  soggetto_id: number | null;
  ente_id: number | null;
  sintesi: string | null;
  indice_rischio: number | null;
  indice_opportunita: number | null;
  generato_il: string;
  sezioni: Record<string, unknown>;
}

export interface Proposta {
  id: number;
  ruolo_agente: string;
  tipo_azione: string;
  titolo: string;
  descrizione: string | null;
  destinatario: Record<string, unknown>;
  livello_rischio: string;
  stato: string;
  approvato_da: string | null;
  canale_approvazione: string | null;
  creato_il: string;
  deciso_il: string | null;
  eseguito_il: string | null;
}

export interface RegolaRischio {
  id: number;
  pattern_azione: string;
  livello_rischio: string;
  descrizione: string | null;
  approvazione_automatica: boolean;
}

export interface TokenResponse {
  access_token: string;
  tipo: string;
}

export interface KpiCruscotto {
  soggetti_attivi: number;
  opportunita_aperte: number;
  valore_pipeline: number;
  proposte_in_attesa: number;
}
