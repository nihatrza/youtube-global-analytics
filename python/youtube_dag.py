from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:
    from airflow.operators.python import PythonOperator

from youtube_etl import run_pipeline

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2026, 10, 1),
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="daily_youtube_quota_max_etl",
    default_args=default_args,
    description="Daily YouTube trending ETL until quota is exhausted",
    schedule="30 8 * * *",  # 08:30 UTC = Baku 12:30, YouTube kvota sıfırlanmasından sonra
    catchup=False,
    max_active_runs=1,
) as dag:
    PythonOperator(
        task_id="execute_max_quota_youtube_etl",
        python_callable=run_pipeline,
        execution_timeout=timedelta(hours=2),
    )
