-- Estrategia Med - Supabase Schema
-- Rodar no SQL Editor do Supabase Dashboard

CREATE TABLE questions (
    id TEXT PRIMARY KEY,
    statement TEXT,
    answer_type TEXT NOT NULL DEFAULT 'MULTIPLE_CHOICE',
    year INTEGER,
    institution TEXT DEFAULT '',
    banca TEXT DEFAULT '',
    finalidade TEXT DEFAULT '',
    region TEXT DEFAULT '',
    labels JSONB DEFAULT '[]'::jsonb,
    topics JSONB DEFAULT '[]'::jsonb,
    correct_letter TEXT DEFAULT '',
    solution TEXT DEFAULT '',
    has_video BOOLEAN DEFAULT FALSE,
    video_url TEXT DEFAULT ''
);

CREATE TABLE alternatives (
    id SERIAL PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    letter TEXT NOT NULL,
    body TEXT DEFAULT '',
    correct BOOLEAN DEFAULT FALSE,
    answer_pct INTEGER DEFAULT 0
);

CREATE TABLE specialties (
    name TEXT PRIMARY KEY
);

-- Indexes para filtros
CREATE INDEX idx_q_type ON questions(answer_type);
CREATE INDEX idx_q_year ON questions(year);
CREATE INDEX idx_q_institution ON questions(institution);
CREATE INDEX idx_q_banca ON questions(banca);
CREATE INDEX idx_q_finalidade ON questions(finalidade);
CREATE INDEX idx_q_region ON questions(region);
CREATE INDEX idx_q_topics ON questions USING GIN (topics);
CREATE INDEX idx_q_labels ON questions USING GIN (labels);
CREATE INDEX idx_alt_qid ON alternatives(question_id);

-- RLS: leitura publica
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_questions" ON questions FOR SELECT USING (true);
ALTER TABLE alternatives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_alternatives" ON alternatives FOR SELECT USING (true);
ALTER TABLE specialties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_specialties" ON specialties FOR SELECT USING (true);
