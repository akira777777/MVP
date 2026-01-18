-- Migration: Create businesses table for lead generation
-- This table stores business information collected from Google Maps

CREATE TABLE IF NOT EXISTS businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT DEFAULT 'Prague',
    district TEXT, -- Prague 1-10, etc.
    postal_code TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    phone TEXT,
    website TEXT,
    category TEXT NOT NULL,
    subcategory TEXT,
    google_place_id TEXT UNIQUE, -- Для дедупликации
    rating DECIMAL(3, 2),
    review_count INTEGER,
    opening_hours JSONB, -- Структурированные часы работы
    verified BOOLEAN DEFAULT FALSE, -- Ручная верификация
    data_source TEXT NOT NULL, -- 'api', 'mcp', 'scraper'
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB -- Дополнительные данные
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_businesses_category ON businesses(category);
CREATE INDEX IF NOT EXISTS idx_businesses_district ON businesses(district);
CREATE INDEX IF NOT EXISTS idx_businesses_google_place_id ON businesses(google_place_id);
CREATE INDEX IF NOT EXISTS idx_businesses_data_source ON businesses(data_source);
CREATE INDEX IF NOT EXISTS idx_businesses_collected_at ON businesses(collected_at);

-- Для геопоиска (требует расширение PostGIS или можно использовать простой индекс)
-- CREATE INDEX idx_businesses_location ON businesses USING GIST(
--     ll_to_earth(latitude, longitude)
-- );

-- RLS политики (если нужны)
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Public read access" ON businesses
    FOR SELECT USING (true);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_businesses_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_businesses_updated_at_trigger
    BEFORE UPDATE ON businesses
    FOR EACH ROW
    EXECUTE FUNCTION update_businesses_updated_at();
