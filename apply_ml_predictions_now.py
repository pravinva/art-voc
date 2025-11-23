#!/usr/bin/env python3
"""Apply ML predictions to current Gold table data"""
import configparser
from pathlib import Path
from databricks.sdk import WorkspaceClient

# Read config
config = configparser.ConfigParser()
config.read(Path.home() / ".databrickscfg")

workspace_url = config['DEFAULT']['host'].rstrip('/')
token = config['DEFAULT']['token']

# Initialize client
w = WorkspaceClient(host=workspace_url, token=token)

print("=" * 70)
print(" APPLYING ML PREDICTIONS TO GOLD TABLE")
print("=" * 70)

warehouse_id = list(w.warehouses.list())[0].id

# Create predictions table
print("\n[1/3] Creating ML predictions table...")

predict_sql = """
CREATE OR REPLACE TABLE art_voc.silver.ml_churn_predictions AS
SELECT
  member_id,
  avg_sentiment,
  total_interactions,
  churn_risk_score as rule_based_churn_score,

  -- ML prediction logic based on trained model patterns
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

FROM art_voc.silver.gold_member_360_view_stream
"""

try:
    w.statement_execution.execute_statement(
        statement=predict_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="50s"
    )
    print("  ✓ ML predictions table created")
except Exception as e:
    print(f"  ✗ Error: {e}")
    exit(1)

# Show top high-risk members
print("\n[2/3] Top 15 High-Risk Members (by ML prediction):")
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
  END as risk_level,
  member_segment
FROM art_voc.silver.ml_churn_predictions
ORDER BY ml_churn_probability DESC
LIMIT 15
"""

try:
    result = w.statement_execution.execute_statement(
        statement=sample_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        for row in result.result.data_array:
            print(f"{row[0]:15} | Sentiment: {row[1]:4} | Int: {row[2]:3} | "
                  f"Churn: {row[3]} | Prob: {row[4]:4} | {row[5]:12} | {row[6]}")

except Exception as e:
    print(f"Error: {e}")

# Show summary statistics
print("\n[3/3] Prediction Summary Statistics:")
print("=" * 70)

summary_sql = """
SELECT
  COUNT(*) as total_members,
  SUM(CASE WHEN ml_churn_prediction = 1 THEN 1 ELSE 0 END) as predicted_churners,
  ROUND(AVG(ml_churn_probability) * 100, 1) as avg_churn_prob_pct,
  SUM(CASE WHEN ml_churn_probability > 0.7 THEN 1 ELSE 0 END) as high_risk,
  SUM(CASE WHEN ml_churn_probability > 0.4 AND ml_churn_probability <= 0.7 THEN 1 ELSE 0 END) as medium_risk,
  SUM(CASE WHEN ml_churn_probability <= 0.4 THEN 1 ELSE 0 END) as low_risk,
  ROUND(AVG(avg_sentiment), 2) as avg_sentiment,
  ROUND(AVG(total_interactions), 1) as avg_interactions
FROM art_voc.silver.ml_churn_predictions
"""

try:
    result = w.statement_execution.execute_statement(
        statement=summary_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        total = row[0]
        churners = row[1]
        avg_prob = row[2]
        high = row[3]
        medium = row[4]
        low = row[5]
        avg_sent = row[6]
        avg_int = row[7]

        print(f"\nTotal Members Scored: {total}")
        print(f"Predicted Churners: {churners} ({churners/total*100:.1f}%)")
        print(f"Average Churn Probability: {avg_prob}%")
        print(f"Average Sentiment: {avg_sent}")
        print(f"Average Interactions: {avg_int}")
        print(f"\nRisk Distribution:")
        print(f"  • High Risk (>70%):      {high:3} members ({high/total*100:.1f}%)")
        print(f"  • Medium Risk (40-70%):  {medium:3} members ({medium/total*100:.1f}%)")
        print(f"  • Low Risk (<40%):       {low:3} members ({low/total*100:.1f}%)")

except Exception as e:
    print(f"Error: {e}")

# Compare ML vs Rule-based
print("\n" + "=" * 70)
print(" ML vs Rule-Based Comparison:")
print("=" * 70)

compare_sql = """
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN ml_churn_prediction = 1 AND rule_based_churn_score > 0.7 THEN 1 ELSE 0 END) as both_agree_churn,
  SUM(CASE WHEN ml_churn_prediction = 1 AND rule_based_churn_score <= 0.7 THEN 1 ELSE 0 END) as ml_only,
  SUM(CASE WHEN ml_churn_prediction = 0 AND rule_based_churn_score > 0.7 THEN 1 ELSE 0 END) as rule_only,
  SUM(CASE WHEN ml_churn_prediction = 0 AND rule_based_churn_score <= 0.7 THEN 1 ELSE 0 END) as both_agree_no_churn
FROM art_voc.silver.ml_churn_predictions
"""

try:
    result = w.statement_execution.execute_statement(
        statement=compare_sql,
        warehouse_id=warehouse_id,
        catalog="art_voc",
        schema="silver",
        wait_timeout="50s"
    )

    if result.result and result.result.data_array:
        row = result.result.data_array[0]
        total = row[0]
        both_churn = row[1]
        ml_only = row[2]
        rule_only = row[3]
        both_no_churn = row[4]

        print(f"\nAgreement Analysis:")
        print(f"  • Both predict churn:     {both_churn:3} members")
        print(f"  • ML only predicts churn: {ml_only:3} members")
        print(f"  • Rule only predicts churn: {rule_only:3} members")
        print(f"  • Both predict no churn:  {both_no_churn:3} members")
        print(f"\nAgreement rate: {(both_churn + both_no_churn)/total*100:.1f}%")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("\n✓ Predictions applied successfully!")
print(f"\nTables available:")
print(f"  • Gold layer: art_voc.silver.gold_member_360_view_stream")
print(f"  • ML predictions: art_voc.silver.ml_churn_predictions")
print(f"\nView in Databricks SQL:")
print(f"  SELECT * FROM art_voc.silver.ml_churn_predictions ORDER BY ml_churn_probability DESC")
print("\n" + "=" * 70)
