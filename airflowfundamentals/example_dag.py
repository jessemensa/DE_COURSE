
from airflow import DAG # this defines the entire workflow 
from airflow.operators.python import PythonOperator # run a python function as a task 
from datetime import datetime, timedelta # for date and time manipulation 


# define a task function 
# simple print statement -> when task is executed, it will print this statement
def hello_airflow():
    print("Hello Airflow from Astro CLI!")

def howare_you():
    print("How are you doing today?") 

# default args dictionary holds paramaters that apply to all tasks within the DAG 
default_args = {
    'owner': 'airflow', # owner of the task 
    'depends_on_past': False, # each task is independent of the previous task
    'start_date': datetime(2025, 4, 20), # date when dag should start executing 
    'retries': 1, # specifies the number of retries if a task fails
    'retry_delay': timedelta(minutes=5), # sets the interval between retries
}

# DAG CONTEXT 
with DAG(
    dag_id = 'simple_astro_dag', # unique identifier for the DAG
    default_args=default_args, # applied to all tasks in the DAG 
    description='A simple DAG using Astro CLI', # what the dag does 
    schedule_interval=timedelta(days=1), # controls how often the DAG is triggered 
    catchup=False, # false means that the DAG will only run for the current date skipping any intervals before the start date 
) as dag:
    # task is created using the PythonOperator 
    hello_task = PythonOperator(
        task_id='hello_task', # gives the task a unique id 
        python_callable=hello_airflow, # tells airflow to execute the hello_airflow function when the task is run
    )

    # another task is created using the PythonOperator 
    howareyou_task = PythonOperator(
        task_id='howareyou_task', # gives the task a unique id 
        python_callable=howare_you, # tells airflow to execute the howare_you function when the task is run
    )
    # set the task dependencies
    # this means that the hello_task must be completed before howareyou_task can start
    hello_task >> howareyou_task 