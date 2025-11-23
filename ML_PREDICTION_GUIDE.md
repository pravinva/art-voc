# ML Model Prediction Guide

## Quick Start - 3 Simple Ways to Predict

### Method 1: Load Model and Predict (Simplest)

```python
import mlflow.pyfunc
import pandas as pd

# Load the model
model = mlflow.pyfunc.load_model("models:/art_voc_churn_model/Production")

# Create input data
data = pd.DataFrame({
    'avg_sentiment': [0.3],
    'total_interactions': [5],
    'days_since_last_interaction': [30],
    'negative_interaction_ratio': [0.6],
    'channel_diversity': [2],
    'topic_diversity': [3],
    'avg_interaction_length': [50],
    'has_complaint': [1],
    'response_time_hours': [48]
})

# Predict
prediction = model.predict(data)
print(f"Churn prediction: {prediction[0]}")  # 0 = No Churn, 1 = Churn
```

### Method 2: Batch Score Gold Table

```python
from pyspark.sql.functions import struct, col
import mlflow.pyfunc

# Create Spark UDF
model_udf = mlflow.pyfunc.spark_udf(
    spark,
    model_uri="models:/art_voc_churn_model/Production",
    result_type="double"
)

# Read Gold table
df = spark.table("art_voc.silver.gold_member_360_view_stream")

# Score all members
predictions_df = df.withColumn(
    "ml_churn_score",
    model_udf(struct(
        col("avg_sentiment"),
        col("total_interactions"),
        # ... other features
    ))
)

# Save results
predictions_df.write.mode("overwrite").saveAsTable("art_voc.silver.churn_predictions")
```

### Method 3: SQL Query (No Code)

```sql
-- Create predictions using rule-based logic
CREATE OR REPLACE TABLE art_voc.silver.churn_predictions AS
SELECT
  member_id,
  CASE
    WHEN churn_risk_score > 0.7 THEN 'High Risk'
    WHEN churn_risk_score > 0.4 THEN 'Medium Risk'
    ELSE 'Low Risk'
  END as churn_risk_category,
  churn_risk_score,
  avg_sentiment,
  member_segment
FROM art_voc.silver.gold_member_360_view_stream;
```

---

## Required Features (9 Total)

Your input data MUST have these columns in this order:

| Feature | Type | Description | Example |
|---------|------|-------------|---------|
| `avg_sentiment` | float | Average sentiment (0-1) | 0.3 |
| `total_interactions` | int | Number of interactions | 5 |
| `days_since_last_interaction` | float | Days since last contact | 30 |
| `negative_interaction_ratio` | float | % negative interactions | 0.6 |
| `channel_diversity` | int | Number of channels used | 2 |
| `topic_diversity` | int | Number of topics discussed | 3 |
| `avg_interaction_length` | float | Average text length | 50 |
| `has_complaint` | int | 1 if complained, 0 if not | 1 |
| `response_time_hours` | float | Avg response time (hours) | 48 |

---

## Example Input/Output

### Input DataFrame:
```python
{
    'avg_sentiment': 0.3,              # Low sentiment
    'total_interactions': 5,            # Few interactions
    'days_since_last_interaction': 30,  # Long gap
    'negative_interaction_ratio': 0.6,  # Mostly negative
    'channel_diversity': 2,             # Only 2 channels
    'topic_diversity': 3,               # 3 topics
    'avg_interaction_length': 50,       # Short messages
    'has_complaint': 1,                 # Filed complaint
    'response_time_hours': 48           # Slow response
}
```

### Output:
```
Prediction: 1 (Will Churn)
Probability: 0.85 (85% chance)
```

---

## Production Batch Inference

### Option A: Databricks Notebook

Upload `/Users/pravin.varma/Documents/Demo/art-voc/ml_prediction_examples.py` to Databricks and run "Method 5: Batch Inference Job"

### Option B: Scheduled Job

1. Go to Databricks Workflows
2. Create new Job
3. Add notebook: `ml_prediction_examples`
4. Select task: Run batch_churn_inference()
5. Schedule: Daily at 11pm (Sunday for weekly)

### Option C: DLT Pipeline Integration

Add this to your DLT pipeline notebook:

```python
@dlt.table(name="ml_churn_predictions")
def ml_churn_predictions():
    import mlflow.pyfunc
    from pyspark.sql.functions import struct

    model_udf = mlflow.pyfunc.spark_udf(
        spark,
        model_uri="models:/art_voc_churn_model/Production",
        result_type="double"
    )

    gold_df = dlt.read("gold_member_360_view_stream")

    return gold_df.withColumn(
        "ml_churn_probability",
        model_udf(struct(...features...))
    )
```

---

## Mapping Gold Table to Model Features

If you're scoring from the Gold table, here's how to map:

```python
from pyspark.sql.functions import *

features_df = gold_df.select(
    col("member_id"),

    # Feature 1: avg_sentiment - DIRECT MAPPING
    col("avg_sentiment"),

    # Feature 2: total_interactions - DIRECT MAPPING
    col("total_interactions"),

    # Feature 3: days_since_last_interaction - CALCULATE FROM DATE
    datediff(current_date(), col("last_interaction_date")).alias("days_since_last_interaction"),

    # Feature 4: negative_interaction_ratio - NEEDS CALCULATION
    # For demo, approximate from sentiment
    when(col("avg_sentiment") < 0.3, 0.7)
        .when(col("avg_sentiment") < 0.5, 0.3)
        .otherwise(0.1).alias("negative_interaction_ratio"),

    # Feature 5: channel_diversity - SIZE OF ARRAY
    size(col("channels_used")).alias("channel_diversity"),

    # Feature 6: topic_diversity - SIZE OF ARRAY
    size(col("topics_discussed")).alias("topic_diversity"),

    # Feature 7: avg_interaction_length - USE DEFAULT OR CALCULATE
    lit(80).alias("avg_interaction_length"),

    # Feature 8: has_complaint - FROM AT_RISK_FLAG
    when(col("at_risk_flag") == True, 1).otherwise(0).alias("has_complaint"),

    # Feature 9: response_time_hours - USE DEFAULT
    lit(24).alias("response_time_hours")
)
```

---

## Testing the Model

### Test 1: High Risk Member
```python
high_risk = pd.DataFrame([{
    'avg_sentiment': 0.1,              # Very negative
    'total_interactions': 2,            # Very few
    'days_since_last_interaction': 60,  # 2 months gap
    'negative_interaction_ratio': 0.9,  # 90% negative
    'channel_diversity': 1,             # Only one channel
    'topic_diversity': 1,               # Only one topic
    'avg_interaction_length': 20,       # Very short
    'has_complaint': 1,                 # Yes
    'response_time_hours': 96           # 4 days response
}])

prediction = model.predict(high_risk)
print(f"High risk prediction: {prediction[0]}")  # Expected: 1 (Churn)
```

### Test 2: Low Risk Member
```python
low_risk = pd.DataFrame([{
    'avg_sentiment': 0.8,              # Very positive
    'total_interactions': 20,           # Many interactions
    'days_since_last_interaction': 3,   # Recent contact
    'negative_interaction_ratio': 0.1,  # Only 10% negative
    'channel_diversity': 4,             # Uses all channels
    'topic_diversity': 5,               # Diverse topics
    'avg_interaction_length': 150,      # Long engaged messages
    'has_complaint': 0,                 # No complaints
    'response_time_hours': 6            # Fast response
}])

prediction = model.predict(low_risk)
print(f"Low risk prediction: {prediction[0]}")  # Expected: 0 (No Churn)
```

---

## Troubleshooting

### Error: "Model not found"
```python
# Check model exists
from mlflow.tracking import MlflowClient
client = MlflowClient()
models = client.search_registered_models()
print([m.name for m in models])
```

### Error: "Feature mismatch"
```python
# Check expected features
import mlflow
model_info = mlflow.models.get_model_info("models:/art_voc_churn_model/Production")
print(model_info.signature)
```

### Error: "Wrong number of features"
Make sure you have exactly 9 features in the correct order!

---

## Integration with Power BI

1. Save predictions to table: `art_voc.silver.churn_predictions`
2. In Power BI Desktop:
   - Get Data → Databricks
   - Select table: `art_voc.silver.churn_predictions`
3. Create dashboard with:
   - Churn rate gauge
   - High-risk member list
   - Sentiment vs Churn scatter plot

---

## Model URI Formats

- **Production**: `models:/art_voc_churn_model/Production`
- **Staging**: `models:/art_voc_churn_model/Staging`
- **Specific Version**: `models:/art_voc_churn_model/1`
- **By Run ID**: `runs:/<run_id>/model`

---

## Next Steps

1. **Test predictions**: Run Method 1 in a notebook
2. **Batch score**: Run Method 5 to score all Gold table members
3. **Schedule job**: Set up weekly batch inference
4. **Monitor model**: Track prediction distribution and accuracy
5. **Retrain**: When model performance degrades

---

## Files Available

- `ml_prediction_examples.py` - Full notebook with 5 methods
- `ML_PREDICTION_GUIDE.md` - This guide
- `FINAL_STATUS_SUMMARY.md` - Complete project status
