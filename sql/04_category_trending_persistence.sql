WITH video_trending_days AS (
    SELECT 
        f.category_id,
        f.video_id,
        COUNT(DISTINCT f.date_key) AS days_in_trending
    FROM fact_video_performance f
    GROUP BY f.category_id, f.video_id
)
SELECT 
    cat.category_name,
    COUNT(vtd.video_id) AS total_videos,
    ROUND(AVG(vtd.days_in_trending), 1) AS avg_days_in_trending,
    MAX(vtd.days_in_trending) AS max_days_in_trending
FROM video_trending_days vtd
JOIN dim_categories cat ON vtd.category_id = cat.category_id
GROUP BY cat.category_name
ORDER BY avg_days_in_trending DESC;