# Importing Relevant Pyrhon libraries
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine

engine = create_engine('sqlite:///db/foo.db', echo=False)


def latest_extraction():
    # "latest" endpoint - request the most recent exchange rate data
    latest_response = requests.get("http://api.exchangeratesapi.io/v1/latest?access_key=6e45c8ce217f5beca6893ac6968c5c2f")  # noqa: E501
    latest_data = latest_response.text
    latest_parsed = json.loads(latest_data)
    latest_data_dict = latest_response.json()['rates']
    latest_data_items = latest_data_dict.items()
    latest_data_list = list(latest_data_items)
    latest_df = pd.DataFrame(latest_data_list, columns=['currency', 'rate'])
    latest_df["date"] = latest_parsed["date"]

    return latest_df


def historic_extraction():
    # "Historic - 2DAYS AGO" endpoint - request the exchange rate data from 2 days ago  # noqa: E501

    # Calculate date for 2 days ago
    N = 2
    date_N_days_ago = datetime.now() - timedelta(days=N)
    date_N_days_ago = date_N_days_ago.strftime('%Y-%m-%d')

    historic_response = requests.get("http://api.exchangeratesapi.io/v1/{}?access_key=6e45c8ce217f5beca6893ac6968c5c2f".format(date_N_days_ago))  # noqa: E501
    historic_data = historic_response.text
    historic_parsed = json.loads(historic_data)
    historic_data_dict = historic_response.json()['rates']
    historic_data_items = historic_data_dict.items()
    historic_data_list = list(historic_data_items)
    historic_df = pd.DataFrame(historic_data_list, columns=['currency', 'rate'])  # noqa: E501
    historic_df["date"] = historic_parsed["date"]

    return historic_df


def merge_latest_and_historic(latest_df, historic_df):

    df1 = latest_df
    df2 = historic_df

    frames = [df1, df2]
    result = pd.concat(frames, ignore_index=True)
    exhange_rates = result.sort_values(by='currency', ascending=True, ignore_index=True)  # noqa: E501
    # Drop duplicate records from dataframe if any
    exhange_rates = exhange_rates.drop_duplicates(keep=False)

    return exhange_rates


def create_sqlite_database(exhange_rates):

    exhange_rates = exhange_rates
    exhange_rates.to_sql('exhange_rates', con=engine, if_exists='replace')


def convertion():
    # converts EUR to GBP based on exchange rate 2days ago
    conv = engine.execute("SELECT 100*rate FROM exhange_rates WHERE currency = 'GBP' AND date = '2021-06-26'").fetchall()  # noqa: E501
    print(" 100 EUR --- > GBP : 2 DAYS AGO WAS :")
    print("Conversion : ", conv)


def main():
    # Main function that combines all functions previously defined with return values  # noqa: E501
    latest_df = latest_extraction()
    historic_df = historic_extraction()
    exhange_rates = merge_latest_and_historic(latest_df, historic_df)
    create_sqlite_database(exhange_rates)
    convertion()


main()
