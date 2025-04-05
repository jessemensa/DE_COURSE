from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
from datetime import datetime, timedelta
import pandas as pd
import requests
import boto3
import io

# Constants
API_BASE_URL = "http://api.exchangeratesapi.io/v1/"
ACCESS_KEY = "6e45c8ce217f5beca6893ac6968c5c2f"
S3_BUCKET_NAME = "decourse2025"
AWS_CONN_ID = "aws_default"  # Make sure this connection exists in Airflow

# === Helper to get boto3 client with Airflow creds ===
def get_s3_client(conn_id=AWS_CONN_ID):
    conn = BaseHook.get_connection(conn_id)
    return boto3.client(
        's3',
        aws_access_key_id=conn.login,
        aws_secret_access_key=conn.password,
        region_name=conn.extra_dejson.get("region_name", "us-east-1")
    )

# === API data fetching ===
def fetch_exchange_rates(endpoint: str):
    url = f"{API_BASE_URL}{endpoint}?access_key={ACCESS_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def extract_rates(endpoint: str):
    if endpoint == "latest":
        data = fetch_exchange_rates("latest")
    else:
        date_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        data = fetch_exchange_rates(date_str)
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])

# === Merge and Upload ===
def merge_and_upload_to_s3(**kwargs):
    latest_df = extract_rates("latest")
    historic_df = extract_rates("historic")
    merged_df = (pd.concat([latest_df, historic_df], ignore_index=True)
                 .sort_values(by='currency')
                 .drop_duplicates(subset=['currency', 'date'], keep=False))

    print(merged_df.head())

    # Dynamic S3 Key (optional — change to static if you prefer)
    date_str = datetime.now().strftime('%Y-%m-%d')
    s3_key = f"exchange_rates/{date_str}/exchange_rates.csv"

    # Save to S3
    buffer = io.StringIO()
    merged_df.to_csv(buffer, index=False)
    buffer.seek(0)

    s3 = get_s3_client()
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())
    print(f"Uploaded exchange rates to s3://{S3_BUCKET_NAME}/{s3_key}")

# === DAG Definition ===
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
    dag_id="exchange_rates_to_s3",
    default_args=default_args,
    description="Fetch exchange rates and upload to S3",
    schedule_interval='@daily',
    start_date=datetime(2025, 4, 5),
    catchup=False
) as dag:

    process_and_upload = PythonOperator(
        task_id="merge_and_upload_to_s3",
        python_callable=merge_and_upload_to_s3
    )

    process_and_upload
