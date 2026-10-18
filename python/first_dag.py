from datetime import datetime

from airflow.sdk import DAG
from airflow.providers.standard.operators.python import PythonOperator


def hello_airflow():
    print("Salam, Airflow!")
    print("Bu mənim ilk DAG-imdir.")


with DAG(
    dag_id="first_dag",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["learning"],
) as dag:

    hello_task = PythonOperator(
        task_id="hello_task",
        python_callable=hello_airflow,
    )
