
# Import Airflow modules for creating DAGs and using operators 
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.hooks.base import BaseHook

# Import standard libraries for date/time manipulation, data handling, HTTP requests, AWS S3 client, and in-memory IO
from datetime import datetime, timedelta
import pandas as pd
import requests
import boto3
import io

# === Constants ===
# Base URL for exchange rate API and personal access key 
API_BASE_URL = "http://api.exchangeratesapi.io/v1/"
ACCESS_KEY = "6e45c8ce217f5beca6893ac6968c5c2f" 
# S3 bucket name to which files will be uploaded 
S3_BUCKET_NAME = "decourse2025"
# AWS connection ID configured in Airflow for AES access 
AWS_CONN_ID = "aws_default"
# Snowflake connection ID configured in Airflow for SQL tasks 
SQL_CONN_ID = "snowflake_conn"


# === Helper to get boto3 client ===
def get_s3_client(conn_id=AWS_CONN_ID):
    # Retrieve connection details for AWS from Airflow 
    conn = BaseHook.get_connection(conn_id)
    # Return a boto3 S3 client configured with AWS credentials and region 
    return boto3.client(
        's3',
        aws_access_key_id=conn.login,
        aws_secret_access_key=conn.password,
        region_name=conn.extra_dejson.get("region_name", "us-east-1")
    )


# === Data extraction ===
def fetch_exchange_rates(endpoint: str):
    # Construct the full API URL with the endpoint and access key as query parameter 
    url = f"{API_BASE_URL}{endpoint}?access_key={ACCESS_KEY}"
    # Make a GET request to the API
    response = requests.get(url)
    # Raise an error if the request results in an unsucessful status code 
    response.raise_for_status()
    # Return a parsed JSON response as a Python dictionary 
    return response.json()


def extract_rates(endpoint: str):
    # If the endpoint is "latest", fetch the latest exchange rates 
    if endpoint == "latest":
        data = fetch_exchange_rates("latest")
    else:
    # If not, assume historic data is needed (2 days ago)
        date_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        data = fetch_exchange_rates(date_str)
    # Convert the 'rates' dictionary into a pandas DataFrame with 'currency' and 'rate' columns.
    # Also, add a 'date' column using the date from the JSON data.
    return pd.DataFrame(data['rates'].items(), columns=['currency', 'rate']).assign(date=data['date'])


# === Upload to S3 ===
def merge_and_upload_to_s3(**kwargs):
    # Extract the latest exchange rates DataFrame
    latest_df = extract_rates("latest")
    # Extract historic exchange rates DataFrame (from 2 days ago)
    historic_df = extract_rates("historic")
    # Merge the two DataFrames, sort by 'currency', and remove duplicates based on 'currency' and 'date'
    merged_df = (pd.concat([latest_df, historic_df], ignore_index=True)
                 .sort_values(by='currency')
                 .drop_duplicates(subset=['currency', 'date'], keep=False))
    # Create an in-memory text stream and write the DataFrame as CSV into it
    buffer = io.StringIO()
    merged_df.to_csv(buffer, index=False)
    buffer.seek(0) # Rewind the buffer so data can be read from the beginning

    # Get the S3 client using the helper function
    s3 = get_s3_client()
    # Create a timestamp to include in the S3 key for uniqueness
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Build the S3 key (path) for the CSV file
    s3_key = f"exchange_rates/exchange_rates_{timestamp}.csv"
    # Upload the CSV file content from the buffer to the specified S3 bucket
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=buffer.getvalue())

    # Push the key to XCom
    kwargs['ti'].xcom_push(key='s3_key', value=s3_key)
    # Print a confirmation message including the S3 location of the uploaded file
    print(f"Uploaded exchange rates to s3://{S3_BUCKET_NAME}/{s3_key}")


# === DAG definition ===
# Set default arguments for the DAG, such as owner and retry settings.
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2)
}

# Define the DAG using a context manager that takes the DAG configuration
with DAG(
        dag_id="exchange_rates_to_snowflake",
        default_args=default_args,
        description="Fetch exchange rates, upload to S3, and copy to Snowflake using SQLExecuteQueryOperator",
        schedule_interval='@daily',
        start_date=datetime(2025, 4, 5),
        catchup=False,
        tags=["exchange", "s3", "snowflake"]
) as dag:
    # Define a PythonOperator that calls merge_and_upload_to_s3 to extract, merge, and upload data to S3
    upload_to_s3 = PythonOperator(
        task_id="merge_and_upload_to_s3",
        python_callable=merge_and_upload_to_s3,
        provide_context=True # Allows the function to access context variables like ti (task instance)
    )
    # Define an SQLExecuteQueryOperator that will copy the uploaded CSV file from S3 into a Snowflake table.
    # This task pulls the S3 key (file path) from XCom.
    copy_to_snowflake = SQLExecuteQueryOperator(
        task_id="copy_s3_to_snowflake",
        conn_id=SQL_CONN_ID,
        sql="""
            COPY INTO EXCHANGE_RATES
            FROM 's3://{{ params.bucket }}/{{ ti.xcom_pull(task_ids="merge_and_upload_to_s3", key="s3_key") }}'
            CREDENTIALS=(
                AWS_KEY_ID='{{ conn.aws_default.login }}'
                AWS_SECRET_KEY='{{ conn.aws_default.password }}'
            )
            FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='"')
            ON_ERROR='CONTINUE';
        """,
        params={"bucket": S3_BUCKET_NAME}
    )
    # Set the task dependency so that the S3 upload happens before copying data to Snowflake.
    upload_to_s3 >> copy_to_snowflake
