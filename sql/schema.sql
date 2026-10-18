-- 1. Kateqoriyalar Cədvəli
CREATE TABLE dim_categories (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

-- 2. Kanallar Cədvəli
CREATE TABLE dim_channels (
    channel_id VARCHAR(50) PRIMARY KEY,
    channel_title VARCHAR(255) NOT NULL,
    custom_url VARCHAR(100),
    country VARCHAR(50),
    subscriber_count BIGINT DEFAULT 0,
    total_views BIGINT DEFAULT 0
);

-- 3. Videoların Sabit Məlumatları Cədvəli
CREATE TABLE dim_videos (
    video_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    duration_sec INT,
    is_short BOOLEAN,
    language VARCHAR(20)
);

-- 4. Fakt Cədvəli (Təmiz Ulduz Sxemi - Bütün FK-lar mərkəzdədir)
CREATE TABLE fact_video_performance (
    fact_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES dim_videos(video_id),
    channel_id VARCHAR(50) REFERENCES dim_channels(channel_id),
    category_id INT REFERENCES dim_categories(category_id),
    date_key INT NOT NULL, -- YYYYMMDD formatı (Məs: 20261007)
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    engagement_rate NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Eyni videonun eyni gün üçün təkrar düşməsinin qarşısını almaq üçün constraint
    CONSTRAINT unique_video_daily_snapshot UNIQUE (video_id, date_key)
);