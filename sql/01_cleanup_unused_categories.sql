DELETE FROM dim_categories 
WHERE category_id NOT IN (
    SELECT DISTINCT category_id 
    FROM fact_video_performance
);
