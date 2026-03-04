import duckdb

# 1. Connect and run your query
# Replace 'table_name' with your actual table
con = duckdb.connect("wc2026_general.duckdb")
df = con.execute(
    """
SELECT
    champion,
    runner_up,
    third_place,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT sim_id) FROM matches WHERE match_number = 104), 2) AS probability
FROM (
    SELECT 
        sim_id,
        -- Winner of the Final
        MAX(CASE WHEN match_number = 104 THEN winner END) AS champion,
        
        -- Loser of the Final (Nested CASE to keep it strictly in match 104)
        MAX(CASE 
            WHEN match_number = 104 THEN 
                CASE WHEN winner = home_team THEN away_team ELSE home_team END 
            END) AS runner_up,
            
        -- Winner of the 3rd Place Playoff
        MAX(CASE WHEN match_number = 103 THEN winner END) AS third_place
    FROM matches
    WHERE match_number IN (103, 104)
    GROUP BY sim_id
)
GROUP BY champion, runner_up, third_place
ORDER BY count DESC
LIMIT 10;
"""
).fetchdf()

print(df)
