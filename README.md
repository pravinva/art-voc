# ART Voice of Customer - 2-Agent Demo System

**Production-quality demo builder for Australian Retirement Trust Member Listening platform**

## Overview

This is an automated 2-agent system that builds, tests, and validates a complete Member Listening demo application using Databricks Foundation Model API and Vector Search.

### Key Features

-  **Agent 1 (Software Developer)**: Builds complete demo with real ML
-  **Agent 2 (QA Inspector)**: Validates quality, rejects incomplete work
-  **Databricks Foundation Model API**: Claude & Llama for all ML tasks
-  **Vector Search**: Semantic search on member interactions (NEW!)
-  **Iterative Refinement**: Agents loop until production quality achieved
-  **NO Placeholders**: Everything works, no stubs or TODOs

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   2-AGENT ORCHESTRATOR                       │
│                                                              │
│  ┌────────────────┐                  ┌───────────────────┐  │
│  │  AGENT 1       │                  │  AGENT 2          │  │
│  │  Software Dev  │ ───builds───>    │  QA Inspector     │  │
│  │                │                  │                   │  │
│  │  • Generate    │  <──rejected──   │  • Audit Pipeline │  │
│  │    Data        │      fixes       │  • Test ML Models │  │
│  │  • Build ML    │                  │  • Validate UI    │  │
│  │    Pipeline    │  ──approved──>   │  • Security Check │  │
│  │  • Create      │    (success!)    │  • REJECT/APPROVE │  │
│  │    Dashboard   │                  │                   │  │
│  └────────────────┘                  └───────────────────┘  │
│                                                              │
│  Max 3 iterations. If not approved after 3, fails.          │
└──────────────────────────────────────────────────────────────┘
           ▲                                        ▲
           │                                        │
           └───── Databricks Foundation Model API ──┘
                  • Claude Sonnet 4.5
                  • Llama 3.1 70B
                  • BGE-Large-EN (embeddings)
                  • Vector Search
```

---

## What Gets Built

### 1. Synthetic Data (Bronze Layer)
- **1000 member profiles** - Realistic age, balance, tenure distribution
- **100 call transcripts** - Natural conversations using super terminology
- **200 emails** - Member queries and ART responses
- **500 survey responses** - NPS/CSAT with correlated sentiment
- **1000 portal activity logs** - Page views, downloads, actions

### 2. AI-Enriched Data (Silver Layer)
- **Sentiment analysis** - Using Foundation Model API (Claude)
- **Topic extraction** - Identify complaint types, query categories
- **Vector embeddings** - Generated using BGE-Large-EN for semantic search
- **Data joining** - Member profiles + interactions

### 3. Business Insights (Gold Layer)
- **Churn prediction** - Multi-factor risk scoring with AI reasoning
- **Insurance propensity** - Life event detection, needs analysis
- **Financial advice propensity** - Age/balance based recommendations
- **Vector Search** - Find similar members and interactions for targeted campaigns

### 4. Interactive Dashboard (Next.js)
- **Executive metrics** - NPS, churn risk, satisfaction
- **Member 360 view** - Complete profile with AI insights
- **Semantic search** - Find similar complaints/queries using Vector Search
- **Retention playbook** - At-risk members with intervention strategies

---

## Vector Search Integration (NEW!)

Vector Search is integrated throughout the pipeline:

### Use Cases

1. **Similar Complaint Detection**
   ```python
   # Find members with similar complaints for batch resolution
   similar = fm_client.vector_search_similar_interactions(
       query_text="Unhappy with high fees and low returns",
       interaction_embeddings=all_interactions,
       top_k=10
   )
   # Returns: 10 most similar complaints with similarity scores
   ```

2. **Member Similarity Matching**
   ```python
   # Find members with similar profiles for targeted campaigns
   # Example: All members age 30-35 with new babies -> insurance offer
   similar_members = vector_search.find_similar_members(
       member_profile=target_member,
       top_k=50
   )
   ```

3. **Knowledge Base Search**
   ```python
   # Semantic search through historical interactions
   # "How do I switch my investment options?"
   # Returns: Similar questions + successful resolutions
   relevant_cases = vector_search.search_knowledge_base(
       query="investment switch process",
       filter={"resolved": True},
       top_k=5
   )
   ```

### Vector Search Data Flow

```
Bronze Layer (Raw Text)
    ↓
Silver Layer (Generate Embeddings)
    • Call BGE-Large-EN API: fm_client.generate_embedding(text)
    • Store embeddings in Delta table: text_embedding ARRAY<FLOAT>
    ↓
Gold Layer (Vector Search Index)
    • Create Vector Search endpoint
    • Index: art_analytics.member_listening.interaction_vectors
    • Query: Semantic similarity search
    ↓
Dashboard (UI)
    • "Find similar complaints" button
    • Returns: Top 10 similar interactions
    • Display: Similarity score + member details
```

### Vector Search Validation (QA Agent)

Agent 2 validates Vector Search functionality:

```python
# Test 1: Verify embeddings generated
assert silver_df.filter("text_embedding IS NOT NULL").count() > 900

# Test 2: Verify similarity search works
similar = fm_client.vector_search_similar_interactions(
    query_text="High fees complaint",
    interaction_embeddings=embeddings,
    top_k=5
)
assert len(similar) == 5
assert all(s['similarity_score'] > 0.7 for s in similar)

# Test 3: Verify similar = similar (not random)
# A complaint should match other complaints, not praise
```

---

## Installation

### Prerequisites

1. **Databricks Workspace** with Foundation Model API enabled
2. **Python 3.9+**
3. **Databricks CLI configured**

### Setup

```bash
# 1. Clone repository
cd /Users/pravin.varma/Documents/Demo/art-voc

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure Databricks CLI (if not already done)
databricks configure --token
# Enter your workspace URL and token

# 4. Verify Foundation Model API access
python -c "from databricks_fm_client import DatabricksFMClient; import configparser; from pathlib import Path; config = configparser.ConfigParser(); config.read(Path.home() / '.databrickscfg'); client = DatabricksFMClient(config['DEFAULT']['host'], config['DEFAULT']['token']); print(' Foundation Model API connected')"

# 5. Run the orchestrator
python art_voc_orchestrator.py
```

---

## Usage

### Basic Run

```bash
python art_voc_orchestrator.py
```

This will:
1. Agent 1 generates synthetic data, builds ML pipeline, creates dashboard
2. Agent 2 inspects all components with 50+ checks
3. If approved → Success! Ready to demo
4. If rejected → Agent 1 fixes issues, Agent 2 re-inspects
5. Loops up to 3 iterations

### Output Structure

```
art-voc/
├── output/
│   ├── artifacts/
│   │   ├── iteration_1/
│   │   │   ├── react_app/          # Next.js dashboard
│   │   │   ├── bronze_data.json    # Synthetic data
│   │   │   ├── silver_enriched.json
│   │   │   └── gold_insights.json
│   │   ├── iteration_2/            # If rejected in iter 1
│   │   └── iteration_3/
│   ├── qa_reports/
│   │   ├── qa_report_iteration_1_20250123_143022.md
│   │   ├── qa_report_iteration_1_20250123_143022.json
│   │   └── ...
│   └── data/
│       ├── member_profiles.csv
│       ├── interactions.csv
│       └── embeddings.parquet      # Vector embeddings
```

### Deploy Dashboard

```bash
cd output/artifacts/iteration_1/react_app
npm install
npm run dev
# Open http://localhost:3000
```

---

## Agent Specifications

### Agent 1: Software Developer

**Responsibilities:**
- Generate 1000+ realistic records across 5 data sources
- Call Foundation Model API for ALL ML tasks (no Math.random!)
- Generate vector embeddings for all interactions
- Build complete Bronze → Silver → Gold pipeline
- Create production-ready Next.js dashboard
- Implement Vector Search functionality

**Quality Standards:**
- NO stubs, placeholders, or TODOs
- All ML uses real API calls
- Data must be varied and realistic
- Vector Search must work with actual embeddings

### Agent 2: QA Inspector

**Inspection Categories:**

1. **Data Pipeline**
   -  Bronze: 1000+ records, realistic variation
   -  Silver: Sentiment correlates with content
   -  Gold: Churn scores vary, logical reasoning
   -  Vector embeddings: Generated for all interactions

2. **ML Models**
   -  Sentiment: Complaints = negative, praise = positive
   -  Churn: High-risk has risk factors, low-risk does not
   -  Propensity: Scores align with demographics
   -  Vector Search: Similar complaints cluster together

3. **User Interface**
   -  Dashboard loads in <5 seconds
   -  Member search filters work
   -  Charts display real data
   -  Vector Search UI functional

4. **Security**
   -  No hardcoded credentials
   -  Input validation on all routes
   -  Error handling doesn't expose internals

5. **Performance**
   -  API efficiency (no 100+ calls on page load)
   -  Vector Search queries <500ms

**Rejection Criteria:**
-  Any ML function uses Math.random()
-  Sentiment doesn't correlate with text
-  UI shows placeholder text
-  Vector Search returns random results
-  Credentials exposed in code
-  Dashboard doesn't load

---

## API Endpoints Used

### Foundation Model API

```python
# Claude Sonnet 4.5 (for complex reasoning)
POST /serving-endpoints/databricks-claude-sonnet-4-5/invocations
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "max_tokens": 4000,
  "temperature": 0.7
}

# Llama 3.1 70B (for fast structured outputs)
POST /serving-endpoints/databricks-meta-llama-3-1-70b-instruct/invocations
{
  "messages": [{"role": "user", "content": "Return only JSON: {...}"}],
  "max_tokens": 2000,
  "temperature": 0.1
}

# BGE-Large-EN (for vector embeddings)
POST /serving-endpoints/databricks-bge-large-en/invocations
{
  "input": "Text to embed"
}
# Returns: {"data": [{"embedding": [1024 floats]}]}
```

### Vector Search API

```python
# Create Vector Search Index (in Unity Catalog)
from databricks.vector_search.client import VectorSearchClient

client = VectorSearchClient()
index = client.create_delta_sync_index(
    endpoint_name="art_voc_endpoint",
    index_name="art_analytics.member_listening.interaction_vectors",
    source_table_name="art_analytics.member_listening.silver_interactions_enriched",
    pipeline_type="CONTINUOUS",
    primary_key="interaction_id",
    embedding_source_column="text_embedding"
)

# Query Vector Search
results = index.similarity_search(
    query_text="Complaint about high fees",
    columns=["member_id", "interaction_text", "sentiment_score"],
    num_results=10
)
```

---

## Example QA Report

```markdown
# Quality Inspection Report
**Iteration:** 1
**Date:** 2025-01-23 14:30:22
**Inspector:** Agent 2 (QA Engineer)

---

## Executive Summary
**Overall Status:**  **APPROVED**

**Issue Counts:**
-  Critical Issues: 0
-  Major Issues: 0
-  Minor Issues: 2

---

## Category Results

### Data Pipeline: PASS
- Bronze Layer:  1000 members, 100 transcripts, realistic variation
- Silver Layer:  Sentiment analysis working correctly
- Gold Layer:  Churn predictions logical and varied
- Vector Embeddings:  Generated for all 1100 interactions

### AI/ML Models: PASS
- Sentiment Analysis:  Test cases passed (positive/negative detection)
- Churn Prediction:  High-risk = logical factors, low-risk = no factors
- Propensity Scoring:  Scores align with demographics
- Vector Search:  Similar complaints cluster correctly

### User Interface: PASS
- Dashboard Load:  Loads in 3.2 seconds
- Member Search:  Filters work correctly
- Charts/Visualizations:  Display real data from pipeline
- Vector Search UI:  Semantic search returns relevant results

### Security: PASS
- Credential Management:  Environment variables used
- Input Validation:  All routes validated

---

## Minor Issues

 1. Dashboard could use loading skeleton for better UX
 2. Vector Search results could show similarity scores in UI

---

## Sign-Off

- [x] Data pipeline is complete and functional
- [x] All ML models functional
- [x] UI is polished and working
- [x] Security standards met
- [x] Vector Search working correctly
- [x] Ready for executive demo

**Recommendation:** APPROVE - Demo is production-ready

**Signature:** Agent 2 (QA Inspector)
**Date:** 2025-01-23 14:30:22
```

---

## Troubleshooting

### Foundation Model API not accessible

```bash
# Check your workspace has FM API enabled
curl -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  "$DATABRICKS_HOST/api/2.0/serving-endpoints" | jq .

# Should see: databricks-claude-sonnet-4-5, databricks-meta-llama-3-1-70b-instruct
```

### Vector Search endpoint not found

```bash
# Vector Search requires Databricks Runtime 13.3+
# Check your workspace settings -> Compute -> Runtime version
```

### Agent 1 generates but Agent 2 rejects every time

```bash
# Check the QA report to see specific failures
cat output/qa_reports/qa_report_iteration_1_*.md

# Common issues:
# - API rate limits (add delays between calls)
# - Embedding generation timeout (batch size too large)
# - Dashboard build failures (check Node.js version >= 18)
```

---

## Production Deployment (Databricks)

To deploy this on Databricks workspace:

1. **Upload notebooks**
   ```bash
   databricks workspace import-dir . /Workspace/Users/{email}/art-voc/
   ```

2. **Create Unity Catalog schema**
   ```sql
   CREATE CATALOG IF NOT EXISTS art_analytics;
   CREATE SCHEMA IF NOT EXISTS art_analytics.member_listening;
   ```

3. **Create Databricks Workflow**
   ```yaml
   name: ART VOC 2-Agent Demo Builder
   tasks:
     - task_key: run_orchestrator
       python_wheel_task:
         package_name: "art_voc"
         entry_point: "main"
       new_cluster:
         spark_version: "14.3.x-scala2.12"
         node_type_id: "i3.xlarge"
         num_workers: 2
   ```

4. **Deploy dashboard to Databricks Apps**
   ```bash
   cd output/artifacts/iteration_1/react_app
   databricks apps deploy --source-path . --app-name art-voc-dashboard
   ```

---

## References

- [Databricks Foundation Model API Docs](https://docs.databricks.com/en/machine-learning/foundation-models/index.html)
- [Databricks Vector Search Docs](https://docs.databricks.com/en/generative-ai/vector-search.html)
- [BGE-Large-EN Model Card](https://huggingface.co/BAAI/bge-large-en-v1.5)
- [ART Member Listening Prompts](agent-prompts-file.md)
- [QA Inspection Protocol](qa-inspection-prompts.md)

---

## License

Internal use only - Australian Retirement Trust

---

## Contact

For questions or issues, contact the Databricks Field Engineering team.
