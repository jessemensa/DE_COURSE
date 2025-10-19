"""
Simple ETL Demo: Exchange Rates to Snowflake
============================================

A beginner-friendly Apache Airflow ETL pipeline that demonstrates:
- Data extraction from Exchange Rates API
- Intermediate storage in S3
- Data transformation and cleaning
- Loading into Snowflake data warehouse

Architecture: API → S3 → Transform → S3 → Snowflake
"""

# =============================================================================
# IMPORTS
# =============================================================================

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.models import Variable
from airflow.hooks.base import BaseHook
from datetime import datetime, timedelta
import pandas as pd
import requests
import boto3
import io
import logging

# =============================================================================
# CONFIGURATION CLASS
# =============================================================================

class Config:
    """Configuration settings for the ETL pipeline"""
    
    # API Configuration
    API_BASE_URL = "http://api.exchangeratesapi.io/v1/"
    API_ACCESS_KEY_VAR = "exchangerates_api_key"
    
    # S3 Configuration
    S3_BUCKET = "data-pipeline-project-demo-1"
    AWS_CONNECTION_ID = "aws_default"
    
    # S3 File Paths
    S3_RAW_LATEST = "raw_data/latest_rates.csv"
    S3_RAW_HISTORIC = "raw_data/historic_rates.csv"
    S3_TRANSFORMED = "transformed_data/exchange_rates.csv"
    
    # Snowflake Configuration
    SNOWFLAKE_CONNECTION_ID = "snowflake_conn"
    SNOWFLAKE_TABLE = "EXCHANGE_RATES"
    
    # Data Configuration
    HISTORIC_DAYS_BACK = 2

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_s3_client():
    """
    Create and return a boto3 S3 client using Airflow connection credentials.
    
    Returns:
        boto3.client: Configured S3 client
    """
    try:
        # Get AWS connection from Airflow
        aws_conn = BaseHook.get_connection(Config.AWS_CONNECTION_ID)
        
        # Create S3 client with credentials
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_conn.login,
            aws_secret_access_key=aws_conn.password,
            region_name=aws_conn.extra_dejson.get('region_name', 'us-east-1')
        )
        
        logging.info("✅ S3 client created successfully")
        return s3_client
        
    except Exception as e:
        logging.error(f"❌ Failed to create S3 client: {str(e)}")
        raise

def save_dataframe_to_s3(df, s3_key, bucket_name):
    """
    Save a pandas DataFrame to S3 as a CSV file.
    
    Args:
        df (pandas.DataFrame): DataFrame to save
        s3_key (str): S3 key (file path) for the CSV
        bucket_name (str): S3 bucket name
    """
    try:
        s3_client = get_s3_client()
        
        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=csv_content,
            ContentType='text/csv'
        )
        
        logging.info(f"✅ DataFrame saved to S3: s3://{bucket_name}/{s3_key}")
        
    except Exception as e:
        logging.error(f"❌ Failed to save DataFrame to S3: {str(e)}")
        raise

def read_dataframe_from_s3(s3_key, bucket_name):
    """
    Read a CSV file from S3 and return as pandas DataFrame.
    
    Args:
        s3_key (str): S3 key (file path) for the CSV
        bucket_name (str): S3 bucket name
        
    Returns:
        pandas.DataFrame: DataFrame containing the CSV data
    """
    try:
        s3_client = get_s3_client()
        
        # Get object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        csv_content = response['Body'].read().decode('utf-8')
        
        # Convert to DataFrame
        df = pd.read_csv(io.StringIO(csv_content))
        
        logging.info(f"✅ DataFrame read from S3: s3://{bucket_name}/{s3_key}")
        return df
        
    except Exception as e:
        logging.error(f"❌ Failed to read DataFrame from S3: {str(e)}")
        raise

def fetch_exchange_rates(date_str=None):
    """
    Fetch exchange rates from the Exchange Rates API.
    
    Args:
        date_str (str, optional): Date in YYYY-MM-DD format. If None, fetches latest rates.
        
    Returns:
        dict: API response containing exchange rates data
    """
    try:
        # Get API access key from Airflow Variable
        api_key = Variable.get(Config.API_ACCESS_KEY_VAR)
        
        # Construct API URL
        if date_str:
            url = f"{Config.API_BASE_URL}{date_str}?access_key={api_key}"
            logging.info(f"🔄 Fetching historical exchange rates for {date_str}")
        else:
            url = f"{Config.API_BASE_URL}latest?access_key={api_key}"
            logging.info("🔄 Fetching latest exchange rates")
        
        # Make API request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if not data.get('success', True):
            error_msg = data.get('error', {}).get('info', 'Unknown API error')
            raise Exception(f"API Error: {error_msg}")
        
        logging.info("✅ Exchange rates fetched successfully")
        return data
        
    except Exception as e:
        logging.error(f"❌ Failed to fetch exchange rates: {str(e)}")
        raise

# =============================================================================
# ETL FUNCTIONS
# =============================================================================

def convert_api_response_to_dataframe(api_data, data_type):
    """
    Convert API response to a standardized DataFrame.
    
    Args:
        api_data (dict): API response data
        data_type (str): Type of data ('latest' or 'historic')
        
    Returns:
        pandas.DataFrame: Standardized DataFrame with columns: currency, rate, date, type
    """
    try:
        rates = api_data.get('rates', {})
        date = api_data.get('date', '')
        base_currency = api_data.get('base', 'USD')
        
        # Prepare data for DataFrame
        data = []
        for currency, rate in rates.items():
            data.append({
                'currency': currency,
                'rate': rate,
                'date': date,
                'type': data_type
            })
        
        # Add base currency with rate 1.0
        data.append({
            'currency': base_currency,
            'rate': 1.0,
            'date': date,
            'type': data_type
        })
        
        df = pd.DataFrame(data)
        logging.info(f"✅ Converted {len(df)} records to DataFrame for {data_type} data")
        return df
        
    except Exception as e:
        logging.error(f"❌ Failed to convert API response to DataFrame: {str(e)}")
        raise

def clean_and_transform_data(df):
    """
    Clean and transform the exchange rates DataFrame.
    
    Args:
        df (pandas.DataFrame): Raw exchange rates DataFrame
        
    Returns:
        pandas.DataFrame: Cleaned and transformed DataFrame
    """
    try:
        logging.info("🔄 Starting data cleaning and transformation")
        
        # Create a copy to avoid modifying original
        df_clean = df.copy()
        
        # Convert currency to uppercase
        df_clean['currency'] = df_clean['currency'].str.upper()
        
        # Convert rate to numeric, handling any string values
        df_clean['rate'] = pd.to_numeric(df_clean['rate'], errors='coerce')
        
        # Convert date to datetime
        df_clean['date'] = pd.to_datetime(df_clean['date'])
        
        # Add derived fields
        df_clean['rate_usd'] = 1.0  # Base rate for USD
        df_clean['rate_inverted'] = 1.0 / df_clean['rate']  # Inverted rate
        df_clean['created_at'] = datetime.now()  # Timestamp
        
        # Remove duplicates by currency+date, keeping the last occurrence
        df_clean = df_clean.drop_duplicates(subset=['currency', 'date'], keep='last')
        
        # Sort by currency for consistency
        df_clean = df_clean.sort_values('currency').reset_index(drop=True)
        
        logging.info(f"✅ Data cleaning completed. Final dataset: {len(df_clean)} records")
        return df_clean
        
    except Exception as e:
        logging.error(f"❌ Failed to clean and transform data: {str(e)}")
        raise

def extract_data(**context):
    """
    Extract exchange rates data from API and save to S3.
    
    Args:
        **context: Airflow task context
        
    Returns:
        dict: S3 keys for raw data files
    """
    try:
        logging.info("🔄 Starting data extraction...")
        
        # Fetch latest exchange rates
        latest_data = fetch_exchange_rates()
        latest_df = convert_api_response_to_dataframe(latest_data, 'latest')
        
        # Fetch historical data (2 days back)
        execution_date = context['ds']
        historic_date = (datetime.strptime(execution_date, '%Y-%m-%d') - 
                        timedelta(days=Config.HISTORIC_DAYS_BACK)).strftime('%Y-%m-%d')
        
        historic_data = fetch_exchange_rates(historic_date)
        historic_df = convert_api_response_to_dataframe(historic_data, 'historic')
        
        # Save to S3
        save_dataframe_to_s3(latest_df, Config.S3_RAW_LATEST, Config.S3_BUCKET)
        save_dataframe_to_s3(historic_df, Config.S3_RAW_HISTORIC, Config.S3_BUCKET)
        
        # Prepare return data for XCom
        s3_keys = {
            'latest_s3_key': Config.S3_RAW_LATEST,
            'historic_s3_key': Config.S3_RAW_HISTORIC
        }
        
        logging.info("✅ Extracted data successfully and saved to S3")
        return s3_keys
        
    except Exception as e:
        logging.error(f"❌ Data extraction failed: {str(e)}")
        raise

def transform_data(**context):
    """
    Transform the extracted data by combining and cleaning datasets.
    
    Args:
        **context: Airflow task context
        
    Returns:
        str: S3 key for transformed data
    """
    try:
        logging.info("🔄 Starting data transformation...")
        
        # Get S3 keys from previous task
        s3_keys = context['task_instance'].xcom_pull(task_ids='extract_data')
        
        # Read data from S3
        latest_df = read_dataframe_from_s3(s3_keys['latest_s3_key'], Config.S3_BUCKET)
        historic_df = read_dataframe_from_s3(s3_keys['historic_s3_key'], Config.S3_BUCKET)
        
        logging.info(f"📖 Read {len(latest_df)} latest records and {len(historic_df)} historic records")
        
        # Combine datasets
        combined_df = pd.concat([latest_df, historic_df], ignore_index=True)
        logging.info(f"📊 Combined dataset: {len(combined_df)} total records")
        
        # Clean and transform data
        transformed_df = clean_and_transform_data(combined_df)
        
        # Save transformed data to S3
        save_dataframe_to_s3(transformed_df, Config.S3_TRANSFORMED, Config.S3_BUCKET)
        
        logging.info("✅ Data transformation completed successfully")
        return Config.S3_TRANSFORMED
        
    except Exception as e:
        logging.error(f"❌ Data transformation failed: {str(e)}")
        raise

def load_data(**context):
    """
    Prepare data for loading into Snowflake.
    
    Args:
        **context: Airflow task context
        
    Returns:
        str: S3 key for transformed data
    """
    try:
        logging.info("🔄 Preparing data for Snowflake loading...")
        
        # Get transformed S3 key from previous task
        transformed_s3_key = context['task_instance'].xcom_pull(task_ids='transform_data')
        
        # Verify the file exists in S3
        s3_client = get_s3_client()
        try:
            s3_client.head_object(Bucket=Config.S3_BUCKET, Key=transformed_s3_key)
            logging.info(f"✅ Transformed data verified in S3: s3://{Config.S3_BUCKET}/{transformed_s3_key}")
        except Exception as e:
            logging.error(f"❌ Transformed data not found in S3: {str(e)}")
            raise
        
        logging.info("✅ Data preparation for Snowflake completed")
        return transformed_s3_key
        
    except Exception as e:
        logging.error(f"❌ Data preparation for Snowflake failed: {str(e)}")
        raise

# =============================================================================
# DAG DEFINITION
# =============================================================================

# Default arguments for the DAG
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# Create the DAG
dag = DAG(
    'simple_etl_demo',
    default_args=default_args,
    description='Simple ETL pipeline: API → S3 → Transform → S3 → Snowflake',
    schedule_interval='@daily',
    catchup=False,
    tags=['etl', 'demo', 'beginner', 's3-storage'],
    max_active_runs=1,
)

# =============================================================================
# TASK DEFINITIONS
# =============================================================================

# Task 1: Extract data from API
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    provide_context=True,
    dag=dag,
)

# Task 2: Transform data
transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag,
)

# Task 3: Prepare data for loading
load_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    provide_context=True,
    dag=dag,
)

# Task 4: Recreate Snowflake table
recreate_table_task = SQLExecuteQueryOperator(
    task_id='recreate_snowflake_table',
    conn_id=Config.SNOWFLAKE_CONNECTION_ID,
    sql=f"""
    CREATE OR REPLACE TABLE {Config.SNOWFLAKE_TABLE} (
        currency VARCHAR(3),
        rate DECIMAL(20, 8),
        date DATE,
        type VARCHAR(20),
        rate_usd DECIMAL(20, 8),
        rate_inverted DECIMAL(20, 8),
        created_at TIMESTAMP_NTZ
    );
    """,
    dag=dag,
)

# Task 5: Copy data from S3 to Snowflake
copy_to_snowflake_task = SQLExecuteQueryOperator(
    task_id='copy_to_snowflake',
    conn_id=Config.SNOWFLAKE_CONNECTION_ID,
    sql="""
    COPY INTO {table_name}
    FROM 's3://{bucket_name}/{{{{ ti.xcom_pull(task_ids="load_data") }}}}'
    CREDENTIALS = (AWS_KEY_ID = '{{{{ conn.{aws_conn_id}.login }}}}' 
                   AWS_SECRET_KEY = '{{{{ conn.{aws_conn_id}.password }}}}')
    FILE_FORMAT = (TYPE = 'CSV' 
                   FIELD_DELIMITER = ',' 
                   SKIP_HEADER = 1 
                   FIELD_OPTIONALLY_ENCLOSED_BY = '"')
    ON_ERROR = 'CONTINUE';
    """.format(
        table_name=Config.SNOWFLAKE_TABLE,
        bucket_name=Config.S3_BUCKET,
        aws_conn_id=Config.AWS_CONNECTION_ID
    ),
    dag=dag,
)

# Task 6: Data quality check
quality_check_task = SQLExecuteQueryOperator(
    task_id='data_quality_check',
    conn_id=Config.SNOWFLAKE_CONNECTION_ID,
    sql=f"""
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT currency) as unique_currencies,
        MIN(date) as earliest_date,
        MAX(date) as latest_date,
        COUNT(CASE WHEN rate <= 0 THEN 1 END) as invalid_rates
    FROM {Config.SNOWFLAKE_TABLE}
    WHERE date = CURRENT_DATE();
    """,
    dag=dag,
)

# =============================================================================
# TASK DEPENDENCIES
# =============================================================================

# Define the task flow: extract → transform → load → create_table → copy_to_snowflake → quality_check
extract_task >> transform_task >> load_task >> recreate_table_task >> copy_to_snowflake_task >> quality_check_task
