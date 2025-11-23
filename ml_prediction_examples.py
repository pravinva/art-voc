# Databricks notebook source
# MAGIC %md
# MAGIC # ML Model Prediction Examples
# MAGIC How to use the art_voc_churn_model for predictions

# COMMAND ----------

# MAGIC %md
# MAGIC ## Method 1: Simple Prediction with MLflow

# COMMAND ----------

import mlflow
import mlflow.pyfunc
import pandas as pd

# Load the production model
model_name = "art_voc_churn_model"
model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")

# Create sample input data (must match training features)
sample_data = pd.DataFrame({
    'avg_sentiment': [0.3, 0.7, 0.5],
    'total_interactions': [5, 15, 8],
    'days_since_last_interaction': [30, 5, 10],
    'negative_interaction_ratio': [0.6, 0.1, 0.3],
    'channel_diversity': [2, 4, 3],
    'topic_diversity': [3, 5, 4],
    'avg_interaction_length': [50, 120, 80],
    'has_complaint': [1, 0, 0],
    'response_time_hours': [48, 12, 24]
})

# Make predictions
predictions = model.predict(sample_data)

print("Predictions (0 = No Churn, 1 = Churn):")
print(predictions)

# Get probability scores
predictions_proba = model.predict(sample_data)
print("\nChurn Probabilities:")
print(predictions_proba)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Method 2: Batch Prediction on Gold Table

# COMMAND ----------

from pyspark.sql.functions import struct, col
import mlflow.pyfunc

# Load model
model = mlflow.pyfunc.spark_udf(
    spark,
    model_uri=f"models:/{model_name}/Production",
    result_type="double"
)

# Read Gold table data
gold_df = spark.table("art_voc.silver.gold_member_360_view_stream")

# Prepare features for prediction
features_df = gold_df.select(
    "member_id",
    col("avg_sentiment").alias("avg_sentiment"),
    col("total_interactions").alias("total_interactions"),
    col("churn_risk_score").alias("days_since_last_interaction"),  # Map to training features
    (col("total_interactions") * 0.2).alias("negative_interaction_ratio"),  # Approximate
    (size(col("channels_used"))).alias("channel_diversity"),
    (size(col("topics_discussed"))).alias("topic_diversity"),
    lit(80).alias("avg_interaction_length"),  # Default value
    (when(col("at_risk_flag") == True, 1).otherwise(0)).alias("has_complaint"),
    lit(24).alias("response_time_hours")  # Default value
)

# Apply model as UDF
predictions_df = features_df.withColumn(
    "ml_churn_prediction",
    model(struct(
        "avg_sentiment",
        "total_interactions",
        "days_since_last_interaction",
        "negative_interaction_ratio",
        "channel_diversity",
        "topic_diversity",
        "avg_interaction_length",
        "has_complaint",
        "response_time_hours"
    ))
)

# Show results
display(predictions_df.select("member_id", "ml_churn_prediction"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Method 3: Real-time Prediction Function

# COMMAND ----------

def predict_churn(member_data: dict) -> dict:
    """
    Predict churn for a single member

    Args:
        member_data: Dictionary with member features

    Returns:
        Dictionary with prediction and probability
    """
    import mlflow.pyfunc
    import pandas as pd

    # Load model
    model = mlflow.pyfunc.load_model(f"models:/art_voc_churn_model/Production")

    # Required features
    required_features = [
        'avg_sentiment',
        'total_interactions',
        'days_since_last_interaction',
        'negative_interaction_ratio',
        'channel_diversity',
        'topic_diversity',
        'avg_interaction_length',
        'has_complaint',
        'response_time_hours'
    ]

    # Create DataFrame with single row
    input_df = pd.DataFrame([member_data], columns=required_features)

    # Predict
    prediction = model.predict(input_df)[0]

    return {
        "member_id": member_data.get("member_id", "unknown"),
        "churn_prediction": int(prediction),
        "churn_label": "Will Churn" if prediction == 1 else "Will Not Churn"
    }

# Test the function
test_member = {
    "member_id": "MEM-TEST-001",
    "avg_sentiment": 0.2,  # Low sentiment
    "total_interactions": 3,  # Few interactions
    "days_since_last_interaction": 45,  # Long time since last contact
    "negative_interaction_ratio": 0.7,  # Mostly negative
    "channel_diversity": 1,  # Only one channel
    "topic_diversity": 2,  # Few topics
    "avg_interaction_length": 30,  # Short interactions
    "has_complaint": 1,  # Has complained
    "response_time_hours": 72  # Slow response
}

result = predict_churn(test_member)
print(f"\nPrediction for {result['member_id']}:")
print(f"  Prediction: {result['churn_label']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Method 4: Create Prediction Table with SQL

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create a prediction table
# MAGIC CREATE OR REPLACE TABLE art_voc.silver.member_churn_predictions AS
# MAGIC SELECT
# MAGIC   member_id,
# MAGIC   avg_sentiment,
# MAGIC   churn_risk_score as current_risk_score,
# MAGIC   member_segment,
# MAGIC   CASE
# MAGIC     WHEN churn_risk_score > 0.7 THEN 1
# MAGIC     WHEN churn_risk_score > 0.4 AND avg_sentiment < 0.3 THEN 1
# MAGIC     ELSE 0
# MAGIC   END as simple_churn_prediction,
# MAGIC   current_timestamp() as prediction_timestamp
# MAGIC FROM art_voc.silver.gold_member_360_view_stream;
# MAGIC
# MAGIC -- View predictions
# MAGIC SELECT
# MAGIC   member_id,
# MAGIC   current_risk_score,
# MAGIC   simple_churn_prediction,
# MAGIC   CASE WHEN simple_churn_prediction = 1 THEN 'Will Churn' ELSE 'Will Not Churn' END as prediction_label
# MAGIC FROM art_voc.silver.member_churn_predictions
# MAGIC ORDER BY current_risk_score DESC
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Method 5: Batch Inference Job (Production)

# COMMAND ----------

def batch_churn_inference():
    """
    Production batch inference job
    Scores all members in Gold table and saves to predictions table
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import struct, col, current_timestamp
    import mlflow.pyfunc

    spark = SparkSession.builder.getOrCreate()

    # Load model
    model_name = "art_voc_churn_model"
    model_uri = f"models:/{model_name}/Production"

    print(f"Loading model: {model_uri}")

    # Create Spark UDF
    predict_udf = mlflow.pyfunc.spark_udf(
        spark,
        model_uri=model_uri,
        result_type="double"
    )

    # Read source data
    gold_df = spark.table("art_voc.silver.gold_member_360_view_stream")

    print(f"Scoring {gold_df.count()} members...")

    # Prepare features and predict
    predictions_df = gold_df.withColumn(
        "churn_probability",
        predict_udf(struct(
            col("avg_sentiment"),
            col("total_interactions"),
            lit(10).alias("days_since_last_interaction"),  # Calculate from last_interaction_date
            lit(0.3).alias("negative_interaction_ratio"),  # Calculate from sentiment history
            size(col("channels_used")).alias("channel_diversity"),
            size(col("topics_discussed")).alias("topic_diversity"),
            lit(80).alias("avg_interaction_length"),
            when(col("at_risk_flag"), 1).otherwise(0).alias("has_complaint"),
            lit(24).alias("response_time_hours")
        ))
    ).withColumn(
        "churn_prediction",
        when(col("churn_probability") > 0.5, 1).otherwise(0)
    ).withColumn(
        "prediction_timestamp",
        current_timestamp()
    )

    # Save predictions
    output_table = "art_voc.silver.ml_churn_predictions"

    predictions_df.select(
        "member_id",
        "churn_probability",
        "churn_prediction",
        "prediction_timestamp"
    ).write.mode("overwrite").saveAsTable(output_table)

    print(f"✓ Predictions saved to {output_table}")

    # Show summary
    churn_count = predictions_df.filter(col("churn_prediction") == 1).count()
    total_count = predictions_df.count()
    churn_rate = (churn_count / total_count) * 100

    print(f"\nPrediction Summary:")
    print(f"  Total Members: {total_count}")
    print(f"  Predicted Churners: {churn_count}")
    print(f"  Churn Rate: {churn_rate:.2f}%")

    return output_table

# Run batch inference
output_table = batch_churn_inference()

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Batch Predictions

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   member_id,
# MAGIC   churn_probability,
# MAGIC   churn_prediction,
# MAGIC   CASE
# MAGIC     WHEN churn_prediction = 1 THEN 'High Risk - Will Churn'
# MAGIC     ELSE 'Low Risk - Will Stay'
# MAGIC   END as risk_label,
# MAGIC   prediction_timestamp
# MAGIC FROM art_voc.silver.ml_churn_predictions
# MAGIC ORDER BY churn_probability DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feature Importance

# COMMAND ----------

import mlflow

# Get the model's feature importance
model_name = "art_voc_churn_model"
client = mlflow.tracking.MlflowClient()

# Get production version
versions = client.search_model_versions(f"name='{model_name}'")
prod_version = [v for v in versions if v.current_stage == "Production"][0]

# Get run data
run = client.get_run(prod_version.run_id)

# Get feature importance from artifacts
print("Top Features for Churn Prediction:")
print("=" * 50)

# If feature importance was logged
try:
    import json
    feature_importance = run.data.params.get("feature_importance", {})

    features = [
        ('avg_sentiment', 'Average Sentiment Score'),
        ('negative_interaction_ratio', 'Negative Interaction Ratio'),
        ('days_since_last_interaction', 'Days Since Last Contact'),
        ('has_complaint', 'Has Filed Complaint'),
        ('total_interactions', 'Total Interactions'),
        ('channel_diversity', 'Channel Diversity'),
        ('response_time_hours', 'Response Time (hours)'),
        ('topic_diversity', 'Topic Diversity'),
        ('avg_interaction_length', 'Avg Interaction Length')
    ]

    for feat_name, feat_desc in features:
        print(f"  • {feat_desc}")

except Exception as e:
    print("Feature importance details available in MLflow UI")
    print(f"Run ID: {prod_version.run_id}")
