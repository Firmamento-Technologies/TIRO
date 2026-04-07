"""add performance indexes

Revision ID: 002_indici
Revises: 8d11e162a991
Create Date: 2026-04-06

"""
from alembic import op

revision = "002_indici"
down_revision = "8d11e162a991"
branch_labels = None
depends_on = None


def upgrade():
    # pg_trgm extension for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # FK indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_flussi_soggetto_id ON core.flussi (soggetto_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_flussi_ricevuto_il ON core.flussi (ricevuto_il DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_opportunita_soggetto ON commerciale.opportunita (soggetto_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_opportunita_fase ON commerciale.opportunita (fase)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_proposte_stato ON decisionale.proposte (stato)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_proposte_creato_il ON decisionale.proposte (creato_il DESC)")

    # ARRAY GIN indexes for exact matching
    op.execute("CREATE INDEX IF NOT EXISTS idx_soggetti_email ON core.soggetti USING GIN (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_soggetti_telefono ON core.soggetti USING GIN (telefono)")

    # Trigram index for fuzzy name matching
    op.execute("CREATE INDEX IF NOT EXISTS idx_soggetti_nome_trgm ON core.soggetti USING GIN ((nome || ' ' || cognome) gin_trgm_ops)")

    # JSONB indexes for pipeline
    op.execute("CREATE INDEX IF NOT EXISTS idx_flussi_review_llm ON core.flussi USING GIN (dati_grezzi) WHERE ((dati_grezzi->>'richiede_review_llm') = 'true')")

    # HNSW vector indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_flussi_vettore_hnsw ON core.flussi USING hnsw (vettore vector_l2_ops) WITH (m = 16, ef_construction = 64)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_risorse_vettore_hnsw ON core.risorse USING hnsw (vettore vector_l2_ops) WITH (m = 16, ef_construction = 64)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_memoria_vettore_hnsw ON decisionale.memoria USING hnsw (vettore vector_l2_ops) WITH (m = 16, ef_construction = 64)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS core.idx_flussi_soggetto_id")
    op.execute("DROP INDEX IF EXISTS core.idx_flussi_ricevuto_il")
    op.execute("DROP INDEX IF EXISTS core.idx_flussi_review_llm")
    op.execute("DROP INDEX IF EXISTS core.idx_flussi_vettore_hnsw")
    op.execute("DROP INDEX IF EXISTS core.idx_risorse_vettore_hnsw")
    op.execute("DROP INDEX IF EXISTS core.idx_soggetti_email")
    op.execute("DROP INDEX IF EXISTS core.idx_soggetti_telefono")
    op.execute("DROP INDEX IF EXISTS core.idx_soggetti_nome_trgm")
    op.execute("DROP INDEX IF EXISTS commerciale.idx_opportunita_soggetto")
    op.execute("DROP INDEX IF EXISTS commerciale.idx_opportunita_fase")
    op.execute("DROP INDEX IF EXISTS decisionale.idx_proposte_stato")
    op.execute("DROP INDEX IF EXISTS decisionale.idx_proposte_creato_il")
    op.execute("DROP INDEX IF EXISTS decisionale.idx_memoria_vettore_hnsw")
