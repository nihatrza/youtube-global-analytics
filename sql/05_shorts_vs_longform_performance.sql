SELECT 
    CASE WHEN v.is_short THEN 'Shorts (<60s)' ELSE 'Long-Form Video' END AS content_format,
    COUNT(DISTINCT f.video_id) AS total_unique_videos,
    SUM(f.views) AS total_views,
    ROUND(AVG(f.views), 0) AS avg_views_per_snapshot,
    ROUND(AVG((f.likes::numeric / NULLIF(f.views, 0)) * 100), 2) AS avg_like_ratio_pct
FROM fact_video_performance f
JOIN dim_videos v ON f.video_id = v.video_id
GROUP BY v.is_short;