WITH daily_views AS (
    SELECT 
        f.video_id,
        v.title,
        f.date_key AS date,
        f.views,
        LAG(f.views) OVER (PARTITION BY f.video_id ORDER BY f.date_key) AS prev_day_views
    FROM fact_video_performance f
    JOIN dim_videos v ON f.video_id = v.video_id
)
SELECT 
    title,
    date,
    views AS current_views,
    prev_day_views,
    (views - prev_day_views) AS daily_view_gain
FROM daily_views
WHERE prev_day_views IS NOT NULL
ORDER BY daily_view_gain DESC
LIMIT 10;