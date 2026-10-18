SELECT 
    v.title,
    c.channel_title,
    v.published_at::date AS publish_date,
    MIN(TO_DATE(f.date_key::text, 'YYYYMMDD')) AS first_trending_date,
    (MIN(TO_DATE(f.date_key::text, 'YYYYMMDD')) - v.published_at::date) AS days_to_trend,
    MAX(f.views) AS peak_views
FROM fact_video_performance f
JOIN dim_videos v ON f.video_id = v.video_id
JOIN dim_channels c ON f.channel_id = c.channel_id
GROUP BY v.video_id, v.title, c.channel_title, v.published_at
HAVING (MIN(TO_DATE(f.date_key::text, 'YYYYMMDD')) - v.published_at::date) <= 2
ORDER BY peak_views DESC
LIMIT 10;