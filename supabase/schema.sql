-- =============================================================
-- Solo Hedge Fund Agent - Supabase Schema
-- Created: 2026-03-13
-- =============================================================
-- Run this SQL in the Supabase Dashboard > SQL Editor
-- =============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================
-- 1. holdings - 포트폴리오 보유 종목
-- =============================================================
CREATE TABLE IF NOT EXISTS holdings (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker      TEXT NOT NULL,
    name        TEXT NOT NULL,
    quantity    NUMERIC NOT NULL DEFAULT 0,
    avg_price   NUMERIC NOT NULL DEFAULT 0,
    currency    TEXT NOT NULL DEFAULT 'USD' CHECK (currency IN ('KRW', 'USD')),
    sector      TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id);
-- Prevent duplicate tickers per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_holdings_user_ticker ON holdings(user_id, ticker);

-- =============================================================
-- 2. signals - 매크로 시그널 스냅샷
-- =============================================================
CREATE TABLE IF NOT EXISTS signals (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indicator   TEXT NOT NULL,
    value       NUMERIC,
    change_1d   NUMERIC,
    change_1w   NUMERIC,
    change_1m   NUMERIC,
    level       TEXT NOT NULL DEFAULT 'calm' CHECK (level IN ('danger', 'caution', 'calm', 'bullish', 'bearish', 'info')),
    message     TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_signals_captured_at ON signals(captured_at DESC);
-- Index for indicator lookups
CREATE INDEX IF NOT EXISTS idx_signals_indicator ON signals(indicator);

-- =============================================================
-- 3. chat_history - AI 채팅 기록
-- =============================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for user chat history, ordered by time
CREATE INDEX IF NOT EXISTS idx_chat_history_user_created ON chat_history(user_id, created_at DESC);

-- =============================================================
-- 4. digest_insights - PDF 인사이트 분석 결과
-- =============================================================
CREATE TABLE IF NOT EXISTS digest_insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename            TEXT NOT NULL UNIQUE,
    summary             TEXT,
    usefulness          INTEGER CHECK (usefulness BETWEEN 1 AND 10),
    themes              TEXT[] DEFAULT '{}',
    key_tickers         TEXT[] DEFAULT '{}',
    action_suggestion   TEXT,
    source_type         TEXT,
    credibility         INTEGER CHECK (credibility BETWEEN 1 AND 10),
    macro_view          TEXT,
    portfolio_relevance TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for usefulness-based queries
CREATE INDEX IF NOT EXISTS idx_digest_insights_usefulness ON digest_insights(usefulness DESC);
-- Full-text search on summary
CREATE INDEX IF NOT EXISTS idx_digest_insights_summary_fts
    ON digest_insights USING gin(to_tsvector('simple', coalesce(summary, '')));

-- =============================================================
-- 5. Row Level Security (RLS) Policies
-- =============================================================

-- ---- holdings: 사용자 본인 데이터만 CRUD ----
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;

CREATE POLICY holdings_select ON holdings
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY holdings_insert ON holdings
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY holdings_update ON holdings
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY holdings_delete ON holdings
    FOR DELETE USING (auth.uid() = user_id);

-- ---- chat_history: 사용자 본인 데이터만 CRUD ----
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY chat_history_select ON chat_history
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY chat_history_insert ON chat_history
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY chat_history_update ON chat_history
    FOR UPDATE USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY chat_history_delete ON chat_history
    FOR DELETE USING (auth.uid() = user_id);

-- ---- signals: 모든 인증 사용자 읽기 가능, service_role만 쓰기 ----
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY signals_select ON signals
    FOR SELECT USING (auth.role() = 'authenticated');

-- INSERT/UPDATE/DELETE는 service_role key를 통해서만 가능 (RLS bypass)
-- 별도 정책 없이 service_role은 자동으로 RLS를 우회합니다.

-- ---- digest_insights: 모든 인증 사용자 읽기 가능, service_role만 쓰기 ----
ALTER TABLE digest_insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY digest_insights_select ON digest_insights
    FOR SELECT USING (auth.role() = 'authenticated');

-- INSERT/UPDATE/DELETE는 service_role key를 통해서만 가능 (RLS bypass)

-- =============================================================
-- 6. Helper: updated_at 자동 갱신 트리거
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_holdings_updated_at
    BEFORE UPDATE ON holdings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- Done. 4 tables, RLS policies, indexes, and triggers created.
-- =============================================================
