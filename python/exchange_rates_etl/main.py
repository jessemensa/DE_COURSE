import pandas as pd
import requests
import sqlite3
from datetime import datetime, timedelta

# Constants
DB_PATH = "db/foo.db"
API_BASE_URL = "http://api.exchangeratesapi.io/v1/"
ACCESS_KEY = "6e45c8ce217f5beca6893ac6968c5c2f"

# Database connection
def get_db_connection():
    return sqlite3.connect(DB_PATH)

def fetch_exchange_rates(endpoint: str):
    url = f"{API_BASE_URL}{endpoint}?access_key={ACCESS_KEY}"
    response = requests.get(url)
    response.raise_for_status()  # Raise error for bad response
    return response.json()

def extract_latest_rates():
    data = fetch_exchange_rates("latest")
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])

def extract_historic_rates():
    date_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    data = fetch_exchange_rates(date_str)
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])

def merge_rates(latest_df, historic_df):
    return (pd.concat([latest_df, historic_df], ignore_index=True)
            .sort_values(by='currency')
            .drop_duplicates(subset=['currency', 'date'], keep=False))

def save_to_db(df, conn):
    df.to_sql('exchange_rates', conn, if_exists='replace', index=False)

def perform_conversion(conn):
    query = """
        SELECT 100 * rate 
        FROM exchange_rates 
        WHERE currency = 'GBP' 
        AND date = (SELECT MAX(date) FROM exchange_rates WHERE currency = 'GBP')
    """
    result = conn.execute(query).fetchone()
    if result:
        print(f"100 EUR was worth {result[0]:.2f} GBP 2 days ago.")

def main():
    conn = get_db_connection()
    try:
        latest_df = extract_latest_rates()
        historic_df = extract_historic_rates()
        exchange_rates = merge_rates(latest_df, historic_df)
        save_to_db(exchange_rates, conn)
        perform_conversion(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
