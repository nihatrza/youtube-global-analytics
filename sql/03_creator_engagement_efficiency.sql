SELECT 
    c.channel_title,
    c.country,
    c.subscriber_count,
    COUNT(DISTINCT f.video_id) AS total_trending_videos,
    ROUND(AVG(f.views), 0) AS avg_views,
    ROUND(AVG((f.likes + f.comments)::numeric / NULLIF(f.views, 0) * 100), 2) AS avg_engagement_rate_pct
FROM fact_video_performance f
JOIN dim_channels c ON f.channel_id = c.channel_id
WHERE c.subscriber_count >= 100000 -- Minimum 100k abunəçisi olanlar
GROUP BY c.channel_id, c.channel_title, c.country, c.subscriber_count
HAVING COUNT(DISTINCT f.video_id) >= 3
ORDER BY avg_engagement_rate_pct DESC
LIMIT 10;