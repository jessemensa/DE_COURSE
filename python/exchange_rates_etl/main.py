import pandas as pd # For data manipulation
import requests # For making HTTP requests to the exchange rates API 
import sqlite3  # For interacting with SQLite database 
from datetime import datetime, timedelta # For working with dates and time periods 
import os # For interacting with the operating system 

# Constants
DB_PATH = "db/foo.db" 
API_BASE_URL = "http://api.exchangeratesapi.io/v1/"
ACCESS_KEY = "901ca420ca881948f44c28505e16bccf"

# Database connection
# Function to establish and return a database connection 
def get_db_connection():
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # return a connection to the SQLite database at DB_PATH 
    return sqlite3.connect(DB_PATH)

# def get_db_connection():
#     return sqlite3.connect(DB_PATH)

# Function that fetch exchange rate data from the API 
def fetch_exchange_rates(endpoint: str):
    # construct the full URL using the base URL, endpoint and access key 
    url = f"{API_BASE_URL}{endpoint}?access_key={ACCESS_KEY}"
    # send an http get request to the constructed URL 
    response = requests.get(url)
    response.raise_for_status()  # Raise error for bad response
    # return the json decoded response (python dictionary) 
    return response.json()

# Function to extract the latest exchange rates and return as a DataFrame.
def extract_latest_rates():
    # Fetch the JSON data from the latest endpoint 
    data = fetch_exchange_rates("latest")
    # Convert the 'rates' dictionary into a DataFrame with columns 'currency' and 'rate'
    # and add the corresponding date as a new column.
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])

# Function to extract historic exchange rates for a specific date and return as a DataFrame.
def extract_historic_rates():
    # Calculate the date for 2 days ago in 'YYYY-MM-DD' format
    date_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    # Fetch JSON data from the API for the historic date 
    data = fetch_exchange_rates(date_str)
    # Convert the rates dictionary into a DataFrame and add the date. 
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])

# Function to merge the latest and historic DataFrames.
def merge_rates(latest_df, historic_df):
    return (pd.concat([latest_df, historic_df], ignore_index=True) # Concatenate the two DataFrames 
            .sort_values(by='currency') # sort the data by the currency column 
            .drop_duplicates(subset=['currency', 'date'], keep=False)) # remove duplicates based on 'currency' and 'date'


# Function to save the DataFrame to an SQLite database table 
def save_to_db(df, conn):
    # write the DataFrame to a table named 'exchange_rates' and replace it if it exists 
    df.to_sql('exchange_rates', conn, if_exists='replace', index=False)


# Function to perform a conversion using the exchange rate from the database 
def perform_conversion(conn):
    query = """
        SELECT 100 * rate 
        FROM exchange_rates 
        WHERE currency = 'GBP' 
        AND date = (SELECT MAX(date) FROM exchange_rates WHERE currency = 'GBP')
    """
    # execute the SQL query to fetch one result 
    result = conn.execute(query).fetchone()
    # if a result is returned, print the conversion output 
    if result:
        print(f"100 EUR was worth {result[0]:.2f} GBP 2 days ago.")

# Main function to orchestrate the ETL process 
def main():
    # Get a connection to the database 
    conn = get_db_connection()
    try:
        # extract the latest and historic exchange rates 
        latest_df = extract_latest_rates()
        historic_df = extract_historic_rates()
        # merge the two dataframes 
        exchange_rates = merge_rates(latest_df, historic_df)
        # save the merged data to the database 
        save_to_db(exchange_rates, conn)
        # perform a conversion calculation based on the GBP rate 
        perform_conversion(conn)
    finally:
        # ensure that the database connection is closed 
        conn.close()

if __name__ == "__main__":
    main()
