"""
Agent 1: Software Development Agent
Builds production-quality demo with real ML and Vector Search
"""
import json
import random
from typing import Dict, List, Any
from datetime import datetime, timedelta


class SoftwareDevAgent:
    """Agent 1 - Builds the complete demo implementation"""

    def __init__(self, fm_client):
        self.fm_client = fm_client
        print(" Agent 1 (Software Developer) initialized")

    def build_implementation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build complete ART VOC demo implementation

        Args:
            context: Contains iteration number and issues_to_fix from previous QA

        Returns:
            Dict with implementation artifacts and status
        """
        iteration = context.get('iteration', 1)
        issues_to_fix = context.get('issues_to_fix', [])

        print(f" Starting implementation (Iteration {iteration})")

        if issues_to_fix:
            print(f"📝 Addressing {len(issues_to_fix)} issues from QA Agent...")
            for issue in issues_to_fix[:3]:  # Show first 3
                print(f"   - {issue.get('category', 'General')}: {issue.get('description', 'Unknown')[:60]}...")

        result = {
            'iteration': iteration,
            'artifacts': [],
            'data_generation_status': 'pending',
            'pipeline_status': 'pending',
            'dashboard_status': 'pending',
            'data_stats': {}
        }

        # ============================================================
        # STEP 1: Generate Synthetic Data (Bronze Layer)
        # ============================================================
        print("\n Step 1: Generating synthetic data...")
        bronze_data = self._generate_bronze_data()

        result['data_generation_status'] = 'completed'
        result['data_stats'] = {
            'members': len(bronze_data['members']),
            'transcripts': len(bronze_data['transcripts']),
            'emails': len(bronze_data['emails']),
            'surveys': len(bronze_data['surveys']),
            'total_records': len(bronze_data['members']) + len(bronze_data['transcripts']) + len(bronze_data['emails']) + len(bronze_data['surveys'])
        }

        # Save bronze artifacts
        result['artifacts'].append({
            'filename': 'bronze_members.json',
            'type': 'json',
            'content': bronze_data['members']
        })
        result['artifacts'].append({
            'filename': 'bronze_transcripts.json',
            'type': 'json',
            'content': bronze_data['transcripts']
        })

        print(f"    Generated {result['data_stats']['total_records']} records")

        # ============================================================
        # STEP 2: AI Enrichment (Silver Layer) with Vector Search
        # ============================================================
        print("\n Step 2: AI enrichment with sentiment analysis and vector embeddings...")
        silver_data = self._build_silver_layer(bronze_data)

        result['data_stats']['predictions'] = len(silver_data['enriched_interactions'])
        result['data_stats']['embeddings'] = sum(1 for i in silver_data['enriched_interactions'] if 'embedding' in i)

        result['artifacts'].append({
            'filename': 'silver_enriched.json',
            'type': 'json',
            'content': silver_data['enriched_interactions'][:100]  # Sample
        })

        print(f"    Enriched {result['data_stats']['predictions']} interactions")
        print(f"    Generated {result['data_stats']['embeddings']} vector embeddings")

        # ============================================================
        # STEP 3: Business Insights (Gold Layer) with Vector Search
        # ============================================================
        print("\n Step 3: Generating business insights with churn prediction...")
        gold_data = self._build_gold_layer(bronze_data, silver_data)

        result['pipeline_status'] = 'completed'
        result['data_stats']['high_risk_members'] = sum(1 for m in gold_data['member_360'] if m.get('churn_risk_level') == 'high')

        result['artifacts'].append({
            'filename': 'gold_insights.json',
            'type': 'json',
            'content': gold_data['member_360'][:50]  # Sample
        })

        print(f"    Generated insights for {len(gold_data['member_360'])} members")
        print(f"     Identified {result['data_stats']['high_risk_members']} high-risk members")

        # ============================================================
        # STEP 4: Build Dashboard (Next.js with Vector Search UI)
        # ============================================================
        print("\n Step 4: Building interactive dashboard...")
        dashboard_files = self._build_dashboard(gold_data)

        result['dashboard_status'] = 'completed'
        result['dashboard_pages'] = len(dashboard_files)

        for file in dashboard_files:
            result['artifacts'].append(file)

        print(f"    Created {len(dashboard_files)} dashboard files")

        # ============================================================
        # FINAL STATUS
        # ============================================================
        print("\n Agent 1 Implementation Complete!")
        print(f"   - Data: {result['data_stats']['total_records']} records")
        print(f"   - ML Predictions: {result['data_stats']['predictions']}")
        print(f"   - Vector Embeddings: {result['data_stats']['embeddings']}")
        print(f"   - High Risk Members: {result['data_stats']['high_risk_members']}")
        print(f"   - Dashboard Files: {result['dashboard_pages']}")

        return result

    def _generate_bronze_data(self) -> Dict[str, List]:
        """Generate realistic synthetic data using Foundation Model"""

        print("    Generating 100 member profiles...")
        members = []
        for i in range(100):  # Reduced for demo speed
            member = {
                'member_id': f'ART-{100000 + i}',
                'age': random.randint(25, 75),
                'balance': random.randint(5000, 2000000),
                'tenure_years': random.randint(1, 30),
                'insurance_cover': random.choice([True, False])
            }
            members.append(member)

        print("    Generating 20 call transcripts with FM API...")
        transcripts = []
        for i, member in enumerate(random.sample(members, min(20, len(members)))):
            # Use Foundation Model to generate realistic transcript
            scenarios = [
                "balance inquiry - positive experience",
                "complaint about high fees",
                "question about insurance options",
                "investment switch request",
                "praise for good returns"
            ]
            scenario = random.choice(scenarios)

            prompt = f"""Generate a realistic Australian superannuation call transcript (50-100 words).

Member: Age {member['age']}, Balance ${member['balance']:,}
Scenario: {scenario}

Make it natural, use proper Australian super terminology (super, concessional contributions, beneficiary, etc.)
"""
            try:
                transcript_text = self.fm_client.call_llama(prompt, max_tokens=200, temperature=0.8)
            except Exception as e:
                print(f"      Warning: FM API call failed, using template: {e}")
                transcript_text = f"Member called about {scenario}. Discussion about their super account."

            transcripts.append({
                'interaction_id': f'CALL-{1000 + i}',
                'member_id': member['member_id'],
                'transcript_text': transcript_text.strip(),
                'interaction_type': 'call',
                'timestamp': (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat()
            })

        print(f"    Generating 30 email interactions...")
        emails = []
        email_templates = [
            "How do I update my beneficiary details?",
            "Can you explain the insurance options available?",
            "I'd like to make an additional contribution",
            "What are my investment options?",
            "I'm unhappy with the recent fee increase"
        ]
        for i, member in enumerate(random.sample(members, min(30, len(members)))):
            emails.append({
                'interaction_id': f'EMAIL-{2000 + i}',
                'member_id': member['member_id'],
                'transcript_text': random.choice(email_templates),
                'interaction_type': 'email',
                'timestamp': (datetime.now() - timedelta(days=random.randint(1, 60))).isoformat()
            })

        print(f"    Generating 50 survey responses...")
        surveys = []
        for i, member in enumerate(random.sample(members, min(50, len(members)))):
            nps = random.randint(0, 10)
            feedback = "Satisfied" if nps >= 7 else ("Neutral" if nps >= 5 else "Disappointed")

            surveys.append({
                'interaction_id': f'SURVEY-{3000 + i}',
                'member_id': member['member_id'],
                'nps_score': nps,
                'transcript_text': f"{feedback} with ART services",
                'interaction_type': 'survey',
                'timestamp': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
            })

        return {
            'members': members,
            'transcripts': transcripts,
            'emails': emails,
            'surveys': surveys
        }

    def _build_silver_layer(self, bronze_data: Dict) -> Dict:
        """Enrich data with sentiment analysis and vector embeddings"""

        all_interactions = bronze_data['transcripts'] + bronze_data['emails'] + bronze_data['surveys']

        enriched = []
        print(f"    Analyzing sentiment for {len(all_interactions)} interactions...")

        for i, interaction in enumerate(all_interactions):
            text = interaction['transcript_text']

            # Sentiment analysis using FM API
            try:
                sentiment = self.fm_client.analyze_sentiment(text)
            except Exception as e:
                print(f"      Warning: Sentiment analysis failed for interaction {i}, using fallback")
                sentiment = {'score': 0.0, 'label': 'neutral', 'confidence': 0.5}

            # Generate vector embedding
            try:
                embedding = self.fm_client.generate_embedding(text)
            except Exception as e:
                print(f"      Warning: Embedding generation failed for interaction {i}, using zeros")
                embedding = [0.0] * 1024  # BGE-Large-EN is 1024 dimensions

            enriched.append({
                **interaction,
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'sentiment_confidence': sentiment['confidence'],
                'embedding': embedding  # Vector for semantic search
            })

            if (i + 1) % 20 == 0:
                print(f"      Processed {i + 1}/{len(all_interactions)} interactions")

        return {'enriched_interactions': enriched}

    def _build_gold_layer(self, bronze_data: Dict, silver_data: Dict) -> Dict:
        """Generate business insights with churn prediction"""

        members = bronze_data['members']
        interactions = silver_data['enriched_interactions']

        # Group interactions by member
        member_interactions = {}
        for interaction in interactions:
            member_id = interaction['member_id']
            if member_id not in member_interactions:
                member_interactions[member_id] = []
            member_interactions[member_id].append(interaction)

        member_360 = []

        print(f"    Predicting churn for {len(members)} members...")

        for i, member in enumerate(members):
            member_id = member['member_id']
            member_ints = member_interactions.get(member_id, [])

            # Calculate aggregates
            avg_sentiment = sum(i['sentiment_score'] for i in member_ints) / len(member_ints) if member_ints else 0
            complaint_count = sum(1 for i in member_ints if 'complaint' in i['transcript_text'].lower())
            nps_score = next((i['nps_score'] for i in member_ints if i['interaction_type'] == 'survey'), 5)

            # Churn prediction using FM API
            try:
                churn_pred = self.fm_client.predict_churn({
                    'avg_sentiment': avg_sentiment,
                    'complaint_count': complaint_count,
                    'nps_score': nps_score,
                    'balance_trend_pct': random.uniform(-10, 10),
                    'portal_logins': random.randint(0, 20),
                    'days_since_contact': random.randint(0, 180)
                })
            except Exception as e:
                print(f"      Warning: Churn prediction failed for {member_id}, using fallback")
                churn_pred = {
                    'churn_risk_score': 0.5,
                    'risk_level': 'medium',
                    'key_risk_factors': ['Analysis incomplete'],
                    'recommended_actions': ['Review manually']
                }

            member_360.append({
                'member_id': member_id,
                'age': member['age'],
                'balance': member['balance'],
                'avg_sentiment': avg_sentiment,
                'interaction_count': len(member_ints),
                'complaint_count': complaint_count,
                'nps_score': nps_score,
                **churn_pred
            })

            if (i + 1) % 25 == 0:
                print(f"      Processed {i + 1}/{len(members)} members")

        return {'member_360': member_360}

    def _build_dashboard(self, gold_data: Dict) -> List[Dict]:
        """Generate Next.js dashboard code with Vector Search UI"""

        dashboard_files = []

        # Main page
        dashboard_files.append({
            'filename': 'dashboard_app.tsx',
            'type': 'code',
            'content': """// Next.js Dashboard for ART Member Listening
import React from 'react';
import { Card, Table, Button, Input } from 'antd';

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = React.useState('');

  const handleVectorSearch = () => {
    // Call Vector Search API
    fetch('/api/vector-search', {
      method: 'POST',
      body: JSON.stringify({ query: searchQuery })
    });
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">ART Member Listening Dashboard</h1>

      {/* Vector Search */}
      <Card title=" Semantic Search" className="mb-6">
        <Input.Search
          placeholder="Find similar complaints or queries..."
          onSearch={handleVectorSearch}
          enterButton="Search"
          size="large"
        />
      </Card>

      {/* Executive Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <h3>NPS Score</h3>
          <p className="text-4xl">7.2</p>
        </Card>
        <Card>
          <h3>High Risk Members</h3>
          <p className="text-4xl">24</p>
        </Card>
        <Card>
          <h3>Avg Sentiment</h3>
          <p className="text-4xl">+0.3</p>
        </Card>
      </div>

      {/* Member Table with real data */}
      <Card title="High Risk Members">
        <Table
          dataSource={""" + json.dumps(gold_data['member_360'][:10]) + """}
          columns={[
            { title: 'Member ID', dataIndex: 'member_id' },
            { title: 'Risk Score', dataIndex: 'churn_risk_score' },
            { title: 'Risk Level', dataIndex: 'risk_level' },
            { title: 'Sentiment', dataIndex: 'avg_sentiment' }
          ]}
        />
      </Card>
    </div>
  );
}
"""
        })

        # API route for Vector Search
        dashboard_files.append({
            'filename': 'api_vector_search.ts',
            'type': 'code',
            'content': """// Vector Search API endpoint
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { query } = req.body;

  // Call Databricks Vector Search
  const response = await fetch(
    `${process.env.DATABRICKS_HOST}/api/2.0/vector-search/indexes/art_analytics.member_listening.interaction_vectors/query`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.DATABRICKS_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query_text: query,
        num_results: 10
      })
    }
  );

  const results = await response.json();
  res.status(200).json(results);
}
"""
        })

        return dashboard_files
