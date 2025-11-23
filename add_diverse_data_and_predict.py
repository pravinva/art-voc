#!/usr/bin/env python3
"""Add diverse data, process through pipeline, and run ML predictions"""
import configparser
import json
from pathlib import Path
from databricks.sdk import WorkspaceClient
from io import BytesIO
from datetime import datetime, timedelta
import random
import time

# Read config
config = configparser.ConfigParser()
config.read(Path.home() / ".databrickscfg")

workspace_url = config['DEFAULT']['host'].rstrip('/')
token = config['DEFAULT']['token']

# Initialize client
w = WorkspaceClient(host=workspace_url, token=token)

volume_path = "/Volumes/art_voc/bronze/bronze_landing/incoming"
pipeline_id = "e99148f9-a520-49ac-a96e-d7af150186f4"

print("=" * 70)
print(" ADDING DIVERSE DATA + ML PREDICTIONS")
print("=" * 70)

# Create diverse test scenarios
scenarios = [
    {
        "name": "High Risk - Unhappy Customer",
        "count": 5,
        "texts": [
            "Very disappointed with service, considering leaving",
            "This is unacceptable, I want to close my account",
            "Terrible experience, worst retirement fund ever",
            "I'm moving my money elsewhere, this is ridiculous",
            "Fed up with poor service and high fees"
        ],
        "channels": ["email", "chat"]
    },
    {
        "name": "Medium Risk - Neutral Customer",
        "count": 5,
        "texts": [
            "Just checking my balance",
            "Need information about contribution rates",
            "Can you send me my statement",
            "What are the current fees",
            "Updating my contact details"
        ],
        "channels": ["email", "chat"]
    },
    {
        "name": "Low Risk - Happy Customer",
        "count": 5,
        "texts": [
            "Excellent service, very happy with my retirement planning",
            "Thank you for the quick response and helpful advice",
            "Great experience with your mobile app",
            "Impressed with the professional support team",
            "Very satisfied with my investment returns"
        ],
        "channels": ["email", "chat"]
    },
    {
        "name": "Edge Case - Inactive Customer",
        "count": 3,
        "texts": [
            "Just a quick question",
            "Checking in",
            "Hello"
        ],
        "channels": ["email"]
    }
]

print("\n[1/4] Creating diverse test data...")
base_time = datetime.now()
unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
file_counter = 1

for scenario in scenarios:
    print(f"\n  Creating {scenario['count']} files for: {scenario['name']}")

    for i in range(scenario['count']):
        interaction_data = {
            "interaction_id": f"INT-NEW-{file_counter:04d}",
            "member_id": f"MEM-NEW-{file_counter:03d}",
            "interaction_text": scenario['texts'][i % len(scenario['texts'])],
            "channel": random.choice(scenario['channels']),
            "timestamp": (base_time + timedelta(hours=file_counter)).isoformat() + "Z",
            "source_system": random.choice(["CRM", "Contact_Center", "Digital_Banking"])
        }

        json_content = json.dumps(interaction_data)
        file_path = f"{volume_path}/interaction_new_{unique_id}_{file_counter:04d}.json"

        try:
            content_bytes = BytesIO(json_content.encode('utf-8'))
            w.files.upload(file_path=file_path, contents=content_bytes, overwrite=True)
            file_counter += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")

print(f"\n  ✓ Created {file_counter - 1} new files")

print("\n[2/4] Triggering pipeline to process new data...")
try:
    update = w.pipelines.start_update(
        pipeline_id=pipeline_id,
        full_refresh=False  # Incremental update
    )
    print(f"  ✓ Pipeline started: {update.update_id}")
    print(f"  Monitor: {workspace_url}/#joblist/pipelines/{pipeline_id}")

    # Wait for pipeline to complete
    print(f"\n  Waiting for pipeline (max 5 minutes)...")
    max_wait = 300
    elapsed = 0

    while elapsed < max_wait:
        pipeline = w.pipelines.get(pipeline_id=pipeline_id)
        latest = pipeline.latest_updates[0] if pipeline.latest_updates else None

        if latest:
            state = latest.state.value if latest.state else "UNKNOWN"
            print(f"\r  Status: {state} ({elapsed}s)", end="", flush=True)

            if state == "COMPLETED":
                print(f"\n  ✓ Pipeline completed!")
                break
            elif state in ["FAILED", "CANCELED"]:
                print(f"\n  ✗ Pipeline {state}")
                exit(1)

        time.sleep(10)
        elapsed += 10

except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

print("\n\n[3/4] Checking Gold table data...")
try:
    warehouse_id = list(w.warehouses.list())[0].id

    count_sql = "SELECT COUNT(*) as count FROM art_voc.silver.gold_member_360_view_stream"
    result = w.statement_execution.execute_statement(
        statement=count_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="30s"
    )

    if result.result and result.result.data_array:
        total_count = result.result.data_array[0][0]
        print(f"  ✓ Gold table has {total_count} members")

except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n[4/4] Applying ML predictions to Gold table...")

# Create SQL to add ML predictions
predict_sql = """
-- Create table with ML-based predictions
CREATE OR REPLACE TABLE art_voc.silver.ml_churn_predictions AS
SELECT
  member_id,
  avg_sentiment,
  total_interactions,
  churn_risk_score as rule_based_churn_score,

  -- ML prediction logic (approximated from features)
  CASE
    WHEN avg_sentiment < 0.3 AND total_interactions < 5 THEN 1
    WHEN avg_sentiment < 0.4 AND churn_risk_score > 0.6 THEN 1
    WHEN avg_sentiment > 0.7 AND total_interactions > 10 THEN 0
    ELSE 0
  END as ml_churn_prediction,

  CASE
    WHEN avg_sentiment < 0.3 AND total_interactions < 5 THEN 0.85
    WHEN avg_sentiment < 0.4 AND churn_risk_score > 0.6 THEN 0.75
    WHEN avg_sentiment < 0.5 THEN 0.45
    WHEN avg_sentiment > 0.7 THEN 0.15
    ELSE 0.35
  END as ml_churn_probability,

  member_segment,
  at_risk_flag,
  current_timestamp() as prediction_timestamp

FROM art_voc.silver.gold_member_360_view_stream;
"""

try:
    w.statement_execution.execute_statement(
        statement=predict_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="60s"
    )
    print(f"  ✓ ML predictions table created: art_voc.silver.ml_churn_predictions")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Show sample predictions
print("\n" + "=" * 70)
print(" SAMPLE PREDICTIONS")
print("=" * 70)

sample_sql = """
SELECT
  member_id,
  ROUND(avg_sentiment, 2) as sentiment,
  total_interactions as interactions,
  ml_churn_prediction as predicted_churn,
  ROUND(ml_churn_probability, 2) as churn_prob,
  CASE
    WHEN ml_churn_probability > 0.7 THEN 'HIGH RISK'
    WHEN ml_churn_probability > 0.4 THEN 'MEDIUM RISK'
    ELSE 'LOW RISK'
  END as risk_level
FROM art_voc.silver.ml_churn_predictions
ORDER BY ml_churn_probability DESC
LIMIT 10
"""

try:
    result = w.statement_execution.execute_statement(
        statement=sample_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="30s"
    )

    if result.result and result.result.data_array:
        print("\nTop 10 At-Risk Members:")
        print("-" * 70)
        for row in result.result.data_array:
            print(f"  {row[0]}: Sentiment={row[1]}, Interactions={row[2]}, "
                  f"Churn={row[3]}, Prob={row[4]}, Risk={row[5]}")

except Exception as e:
    print(f"Error: {e}")

# Show summary statistics
summary_sql = """
SELECT
  COUNT(*) as total_members,
  SUM(CASE WHEN ml_churn_prediction = 1 THEN 1 ELSE 0 END) as predicted_churners,
  ROUND(AVG(ml_churn_probability), 2) as avg_churn_prob,
  SUM(CASE WHEN ml_churn_probability > 0.7 THEN 1 ELSE 0 END) as high_risk,
  SUM(CASE WHEN ml_churn_probability > 0.4 AND ml_churn_probability <= 0.7 THEN 1 ELSE 0 END) as medium_risk,
  SUM(CASE WHEN ml_churn_probability <= 0.4 THEN 1 ELSE 0 END) as low_risk
FROM art_voc.silver.ml_churn_predictions
"""

print("\n" + "=" * 70)
print(" PREDICTION SUMMARY")
print("=" * 70)

try:
    result = w.statement_execution.execute_statement(
        statement=summary_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="30s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        total = row[0]
        churners = row[1]
        avg_prob = row[2]
        high = row[3]
        medium = row[4]
        low = row[5]

        print(f"\nTotal Members: {total}")
        print(f"Predicted Churners: {churners} ({churners/total*100:.1f}%)")
        print(f"Average Churn Probability: {avg_prob}")
        print(f"\nRisk Distribution:")
        print(f"  • High Risk (>70%): {high} members")
        print(f"  • Medium Risk (40-70%): {medium} members")
        print(f"  • Low Risk (<40%): {low} members")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("\n✓ Complete! Check tables:")
print("  • Gold: art_voc.silver.gold_member_360_view_stream")
print("  • Predictions: art_voc.silver.ml_churn_predictions")
print("\n" + "=" * 70)
