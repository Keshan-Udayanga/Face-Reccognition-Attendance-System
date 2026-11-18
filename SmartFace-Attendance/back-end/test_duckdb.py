
import duckdb

# Read all CSV files inside attendance folder
result = duckdb.sql("""
    SELECT *
    FROM read_csv_auto('attendance/*.csv')
""").df()

# Display CSV data
print(result)
