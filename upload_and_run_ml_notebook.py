#!/usr/bin/env python3
"""Upload fixed ML notebook and run it"""
import configparser
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace as ws
from databricks.sdk.service import jobs
import base64
import time

# Read config
config = configparser.ConfigParser()
config.read(Path.home() / ".databrickscfg")

workspace_url = config['DEFAULT']['host'].rstrip('/')
token = config['DEFAULT']['token']

# Initialize client
w = WorkspaceClient(host=workspace_url, token=token)

current_user = w.current_user.me()
user_name = current_user.user_name
notebook_path = f"/Users/{user_name}/art_voc_ml_training"

print("=" * 70)
print(" UPLOADING AND RUNNING ML TRAINING NOTEBOOK")
print("=" * 70)

# Read the fixed notebook
with open('/Users/pravin.varma/Documents/Demo/art-voc/fixed_ml_notebook.py', 'r') as f:
    notebook_content = f.read()

# Encode content
content_bytes = notebook_content.encode('utf-8')
content_b64 = base64.b64encode(content_bytes).decode('utf-8')

print("\n[1/3] Uploading fixed notebook...")
try:
    # Import (overwrite) the notebook
    w.workspace.import_(
        path=notebook_path,
        format=ws.ImportFormat.SOURCE,
        language=ws.Language.PYTHON,
        content=content_b64,
        overwrite=True
    )
    print(f"  ✓ Notebook uploaded: {notebook_path}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

print("\n[2/3] Finding available cluster...")
try:
    # Get list of clusters
    clusters = list(w.clusters.list())

    # Find a running cluster or the first available cluster
    running_cluster = None
    available_cluster = None

    for cluster in clusters:
        if cluster.state == 'RUNNING':
            running_cluster = cluster
            break
        if cluster.state in ['TERMINATED', 'PENDING']:
            available_cluster = cluster

    cluster_to_use = running_cluster or available_cluster

    if cluster_to_use:
        print(f"  ✓ Using cluster: {cluster_to_use.cluster_name} ({cluster_to_use.cluster_id})")
        cluster_id = cluster_to_use.cluster_id

        # Start cluster if not running
        if cluster_to_use.state != 'RUNNING':
            print(f"  Starting cluster...")
            w.clusters.start(cluster_id=cluster_id)

            # Wait for cluster to start (max 5 minutes)
            max_wait = 300
            elapsed = 0
            while elapsed < max_wait:
                cluster_info = w.clusters.get(cluster_id=cluster_id)
                if cluster_info.state == 'RUNNING':
                    print(f"  ✓ Cluster started")
                    break
                elif cluster_info.state in ['ERROR', 'TERMINATED']:
                    print(f"  ✗ Cluster failed to start: {cluster_info.state}")
                    exit(1)
                time.sleep(10)
                elapsed += 10
                print(f"  Waiting for cluster... ({elapsed}s)")
    else:
        print("  ⚠ No clusters found. Creating a new cluster...")
        # Create a simple cluster
        cluster_spec = {
            'cluster_name': 'art_voc_ml_cluster',
            'spark_version': '13.3.x-scala2.12',
            'node_type_id': 'i3.xlarge',
            'num_workers': 0,  # Single node cluster
            'autotermination_minutes': 30
        }
        cluster_response = w.clusters.create(**cluster_spec)
        cluster_id = cluster_response.cluster_id
        print(f"  ✓ Created cluster: {cluster_id}")
        print(f"  Waiting for cluster to start...")

        # Wait for cluster
        max_wait = 300
        elapsed = 0
        while elapsed < max_wait:
            cluster_info = w.clusters.get(cluster_id=cluster_id)
            if cluster_info.state == 'RUNNING':
                print(f"  ✓ Cluster running")
                break
            time.sleep(10)
            elapsed += 10
            print(f"  Waiting... ({elapsed}s)")

except Exception as e:
    print(f"  ✗ Error with cluster: {e}")
    print(f"\n  Please run the notebook manually in Databricks UI:")
    print(f"  {workspace_url}/#workspace{notebook_path}")
    exit(1)

print("\n[3/3] Creating and running job...")
try:
    # Create a one-time job to run the notebook
    job_spec = jobs.CreateJob(
        name=f"art_voc_ml_training_{int(time.time())}",
        tasks=[
            jobs.Task(
                task_key="ml_training",
                notebook_task=jobs.NotebookTask(
                    notebook_path=notebook_path,
                    source=jobs.Source.WORKSPACE
                ),
                existing_cluster_id=cluster_id,
                timeout_seconds=3600
            )
        ],
        timeout_seconds=3600
    )

    job = w.jobs.create(**job_spec.__dict__)
    print(f"  ✓ Job created: {job.job_id}")

    # Run the job
    run = w.jobs.run_now(job_id=job.job_id)
    print(f"  ✓ Job started: Run ID {run.run_id}")
    print(f"\n  Monitor job:")
    print(f"  {workspace_url}/#job/{job.job_id}/run/{run.run_id}")

    print(f"\n  Waiting for job to complete (this may take 3-5 minutes)...")
    print(f"  The job will:")
    print(f"    1. Install required packages (mlflow, xgboost, scikit-learn)")
    print(f"    2. Generate 5000 training samples")
    print(f"    3. Train XGBoost churn model")
    print(f"    4. Register model in MLflow")
    print(f"    5. Transition model to Production")

    # Monitor job
    max_wait = 600  # 10 minutes
    elapsed = 0
    while elapsed < max_wait:
        run_info = w.jobs.get_run(run_id=run.run_id)
        state = run_info.state.life_cycle_state

        print(f"\r  Status: {state} ({elapsed}s)", end="", flush=True)

        if state in ['TERMINATED', 'SKIPPED']:
            result = run_info.state.result_state
            print(f"\n\n  ✓ Job completed: {result}")

            if result == 'SUCCESS':
                print(f"\n  Model 'art_voc_churn_model' trained and registered!")
                print(f"  Check MLflow experiments in Databricks UI")
            else:
                print(f"\n  ⚠ Job did not succeed. Check logs in Databricks UI")
            break
        elif state in ['INTERNAL_ERROR']:
            print(f"\n\n  ✗ Job failed: {state}")
            break

        time.sleep(10)
        elapsed += 10

    if elapsed >= max_wait:
        print(f"\n\n  ⚠ Timeout reached. Job may still be running.")
        print(f"  Check status: {workspace_url}/#job/{job.job_id}/run/{run.run_id}")

except Exception as e:
    print(f"  ✗ Error running job: {e}")
    print(f"\n  Please run the notebook manually in Databricks UI:")
    print(f"  {workspace_url}/#workspace{notebook_path}")

print("\n" + "=" * 70)
