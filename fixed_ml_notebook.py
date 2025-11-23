# Databricks notebook source
# MAGIC %md
# MAGIC # Real Churn Prediction Model Training
# MAGIC Using XGBoost with MLflow tracking

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Required Packages

# COMMAND ----------

# MAGIC %pip install mlflow xgboost scikit-learn pandas numpy --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import mlflow.xgboost
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import pandas as pd
import numpy as np
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Realistic Training Data

# COMMAND ----------

# Set seed for reproducibility
np.random.seed(42)

# Generate 5000 members with realistic patterns
n_samples = 5000

# Create realistic features
data = {
    'member_id': [f'MEM-{10000 + i}' for i in range(n_samples)],
    'avg_sentiment': np.random.beta(5, 2, n_samples),
    'total_interactions': np.random.poisson(8, n_samples) + 1,
    'days_since_last_interaction': np.random.exponential(15, n_samples),
    'negative_interaction_ratio': np.random.beta(2, 8, n_samples),
    'channel_diversity': np.random.randint(1, 5, n_samples),
    'topic_diversity': np.random.randint(1, 6, n_samples),
    'avg_interaction_length': np.random.gamma(3, 20, n_samples),
    'has_complaint': np.random.binomial(1, 0.15, n_samples),
    'response_time_hours': np.random.exponential(24, n_samples),
}

df = pd.DataFrame(data)

# Generate churn labels based on realistic patterns
churn_logit = (
    -2.0
    - 3.0 * df['avg_sentiment']
    + 2.0 * df['negative_interaction_ratio']
    + 0.01 * df['days_since_last_interaction']
    - 0.1 * df['total_interactions']
    - 0.2 * df['channel_diversity']
    + 1.5 * df['has_complaint']
    + 0.01 * df['response_time_hours']
    + np.random.normal(0, 0.5, n_samples)
)

churn_prob = 1 / (1 + np.exp(-churn_logit))
df['churned'] = (churn_prob > np.random.random(n_samples)).astype(int)

print(f"Generated {n_samples} training samples")
print(f"Churn rate: {df['churned'].mean():.2%} ({df['churned'].sum()} churned)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare Features and Split Data

# COMMAND ----------

feature_columns = [
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

X = df[feature_columns]
y = df['churned']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set: {len(X_train)} samples ({y_train.mean():.2%} churn)")
print(f"Test set: {len(X_test)} samples ({y_test.mean():.2%} churn)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Train XGBoost Model with MLflow

# COMMAND ----------

# Enable MLflow autologging
mlflow.xgboost.autolog(log_input_examples=True, log_model_signatures=True)

with mlflow.start_run(run_name="churn_xgboost_production") as run:
    # Model parameters
    params = {
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 100,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'random_state': 42
    }

    # Train model
    model = XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Calculate metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred),
        'recall': recall_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred),
        'roc_auc': roc_auc_score(y_test, y_pred_proba)
    }

    # Log custom metrics
    for metric_name, metric_value in metrics.items():
        mlflow.log_metric(f"test_{metric_name}", metric_value)

    # Log feature importance
    feature_importance = dict(zip(feature_columns, model.feature_importances_))
    mlflow.log_dict(feature_importance, "feature_importance.json")

    # Register model
    model_name = "art_voc_churn_model"
    model_uri = f"runs:/{run.info.run_id}/model"

    mlflow.register_model(model_uri, model_name)

    print("\n" + "="*70)
    print(" MODEL TRAINING COMPLETE")
    print("="*70)
    print(f"Run ID: {run.info.run_id}")
    print(f"Model: {model_name}")
    print("\nTest Metrics:")
    for metric_name, metric_value in metrics.items():
        print(f"  • {metric_name}: {metric_value:.4f}")

    print("\nTop 5 Important Features:")
    sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    for feat, importance in sorted_importance[:5]:
        print(f"  • {feat}: {importance:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transition Model to Production

# COMMAND ----------

from mlflow.tracking import MlflowClient

client = MlflowClient()
model_name = "art_voc_churn_model"

# Get latest version
latest_versions = client.get_latest_versions(model_name, stages=["None"])
if latest_versions:
    latest_version = latest_versions[0].version

    # Transition to Production
    client.transition_model_version_stage(
        name=model_name,
        version=latest_version,
        stage="Production"
    )

    print(f"✓ Model '{model_name}' version {latest_version} → Production")
    print(f"\nModel URI for inference: models:/{model_name}/Production")
else:
    print("⚠ No model versions found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Model Loading

# COMMAND ----------

# Load the production model
import mlflow.pyfunc

loaded_model = mlflow.pyfunc.load_model(f"models:/{model_name}/Production")

# Test prediction
test_input = X_test.head(5)
test_predictions = loaded_model.predict(test_input)

print("✓ Model loaded successfully from registry")
print("\nSample Predictions:")
print(test_predictions)
