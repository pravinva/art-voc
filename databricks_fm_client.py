"""
Databricks Foundation Model API Client
Handles all Foundation Model and Vector Search interactions
"""
import requests
import json
from typing import Dict, List, Any, Optional


class DatabricksFMClient:
    """Client for Databricks Foundation Model API and Vector Search"""

    def __init__(self, workspace_url: str, token: str):
        self.workspace_url = workspace_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Foundation Model endpoints - use exact URLs
        self.claude_endpoint = "https://e2-demo-field-eng.cloud.databricks.com/serving-endpoints/databricks-claude-sonnet-4-5/invocations"

        # Embedding endpoint for Vector Search
        self.embedding_endpoint = f"{workspace_url}/serving-endpoints/databricks-bge-large-en/invocations"

    def call_claude(self, system_prompt: str, user_message: str,
                   max_tokens: int = 4000, temperature: float = 0.7) -> str:
        """
        Call Claude Sonnet 4.5 via Foundation Model API

        Args:
            system_prompt: System instructions
            user_message: User query
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (0-1)

        Returns:
            Model response text
        """
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = requests.post(
            self.claude_endpoint,
            headers=self.headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")

        result = response.json()

        # Handle different response formats
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        elif 'content' in result and len(result['content']) > 0:
            return result['content'][0]['text']
        else:
            raise Exception(f"Unexpected response format: {result}")

    def call_llama(self, prompt: str, max_tokens: int = 2000,
                  temperature: float = 0.1) -> str:
        """
        Call Llama 3.1 70B via Foundation Model API
        (Used for faster, structured outputs like JSON)

        Args:
            prompt: Complete prompt
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Model response text
        """
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        response = requests.post(
            self.llama_endpoint,
            headers=self.headers,
            json=payload,
            timeout=90
        )

        if response.status_code != 200:
            raise Exception(f"Llama API error: {response.status_code} - {response.text}")

        result = response.json()

        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"Unexpected response format: {result}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding using BGE-Large-EN model

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1024 dimensions for BGE-Large-EN)
        """
        payload = {
            "input": text
        }

        response = requests.post(
            self.embedding_endpoint,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Embedding API error: {response.status_code} - {response.text}")

        result = response.json()

        # Handle different response formats
        if 'data' in result and len(result['data']) > 0:
            return result['data'][0]['embedding']
        elif 'embeddings' in result and len(result['embeddings']) > 0:
            return result['embeddings'][0]
        else:
            raise Exception(f"Unexpected embedding response format: {result}")

    def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Databricks embedding endpoint supports batch
        payload = {
            "input": texts
        }

        response = requests.post(
            self.embedding_endpoint,
            headers=self.headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Batch embedding API error: {response.status_code} - {response.text}")

        result = response.json()

        if 'data' in result:
            return [item['embedding'] for item in result['data']]
        elif 'embeddings' in result:
            return result['embeddings']
        else:
            raise Exception(f"Unexpected batch embedding response format: {result}")

    # ============================================================
    # ML Functions using Foundation Models
    # ============================================================

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of member interaction

        Returns:
            {
                "score": float (-1.0 to 1.0),
                "label": str ("positive"|"neutral"|"negative"),
                "confidence": float (0.0 to 1.0)
            }
        """
        prompt = f"""Analyze the sentiment of this Australian superannuation member interaction.

Text: "{text}"

Return ONLY valid JSON (no markdown, no explanation):
{{
  "score": <float from -1.0 to 1.0>,
  "label": "positive|neutral|negative",
  "confidence": <float from 0.0 to 1.0>
}}"""

        # Use Claude instead of Llama
        response = self.call_claude("You are a sentiment analysis assistant. Return only JSON.", prompt, max_tokens=200, temperature=0.1)

        # Extract JSON from response
        try:
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join([l for l in lines if not l.startswith('```')])
                response = response.replace('json', '').strip()

            return json.loads(response)
        except json.JSONDecodeError as e:
            # Fallback if parsing fails
            print(f"Warning: Could not parse sentiment JSON: {response[:100]}")
            return {
                "score": 0.0,
                "label": "neutral",
                "confidence": 0.5
            }

    def predict_churn(self, member_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict churn risk using Foundation Model

        Args:
            member_features: Dict with avg_sentiment, complaint_count, nps_score, etc.

        Returns:
            {
                "churn_risk_score": float (0.0-1.0),
                "risk_level": str ("low"|"medium"|"high"),
                "key_risk_factors": List[str],
                "recommended_actions": List[str]
            }
        """
        prompt = f"""You are a churn prediction model for Australian superannuation funds.

Member Features:
- Average Sentiment: {member_features.get('avg_sentiment', 0):.2f} (-1=very negative, +1=very positive)
- Complaint Count: {member_features.get('complaint_count', 0)}
- NPS Score: {member_features.get('nps_score', 5)} (0-10)
- Balance Trend: {member_features.get('balance_trend_pct', 0):.1f}% (last 6 months)
- Portal Engagement: {member_features.get('portal_logins', 0)} logins/month
- Days Since Last Contact: {member_features.get('days_since_contact', 0)}

Predict churn risk and return ONLY valid JSON (no markdown):
{{
  "churn_risk_score": <0.0-1.0>,
  "risk_level": "low|medium|high",
  "key_risk_factors": ["factor 1", "factor 2", ...],
  "recommended_actions": ["action 1", "action 2", ...]
}}"""

        # Use Claude instead of Llama
        response = self.call_claude("You are a churn prediction assistant for superannuation funds. Return only JSON.", prompt, max_tokens=500, temperature=0.2)

        try:
            # Clean response
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join([l for l in lines if not l.startswith('```')])
                response = response.replace('json', '').strip()

            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse churn JSON: {response[:100]}")
            return {
                "churn_risk_score": 0.5,
                "risk_level": "medium",
                "key_risk_factors": ["Analysis incomplete"],
                "recommended_actions": ["Review manually"]
            }

    def predict_upsell_propensity(self, member_profile: Dict[str, Any],
                                  product: str) -> Dict[str, Any]:
        """
        Predict upsell propensity for insurance or financial advice

        Args:
            member_profile: Member data
            product: "insurance" or "financial_advice"

        Returns:
            {
                "propensity_score": float (0.0-1.0),
                "likelihood": str ("low"|"medium"|"high"),
                "reasoning": List[str],
                "recommended_offer": str
            }
        """
        prompt = f"""You are a propensity scoring model for Australian superannuation funds.

Member Profile:
- Age: {member_profile.get('age', 'unknown')}
- Balance: ${member_profile.get('balance', 0):,}
- Insurance Coverage: {member_profile.get('insurance_cover', False)}
- Recent Queries: {member_profile.get('recent_queries', [])}
- Life Events: {member_profile.get('life_events', [])}

Product: {product}

Predict propensity and return ONLY valid JSON:
{{
  "propensity_score": <0.0-1.0>,
  "likelihood": "low|medium|high",
  "reasoning": ["reason 1", "reason 2", ...],
  "recommended_offer": "specific offer text"
}}"""

        # Use Claude instead of Llama
        response = self.call_claude("You are a propensity scoring assistant. Return only JSON.", prompt, max_tokens=400, temperature=0.2)

        try:
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join([l for l in lines if not l.startswith('```')])
                response = response.replace('json', '').strip()

            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse propensity JSON: {response[:100]}")
            return {
                "propensity_score": 0.3,
                "likelihood": "medium",
                "reasoning": ["Analysis incomplete"],
                "recommended_offer": "Contact for more information"
            }

    def vector_search_similar_interactions(self, query_text: str,
                                          interaction_embeddings: List[Dict],
                                          top_k: int = 5) -> List[Dict]:
        """
        Find similar member interactions using vector similarity

        Args:
            query_text: The interaction to find similar matches for
            interaction_embeddings: List of dicts with 'text', 'embedding', 'metadata'
            top_k: Number of similar interactions to return

        Returns:
            List of similar interactions with similarity scores
        """
        # Generate embedding for query
        query_embedding = self.generate_embedding(query_text)

        # Calculate cosine similarity
        similarities = []
        for item in interaction_embeddings:
            similarity = self._cosine_similarity(query_embedding, item['embedding'])
            similarities.append({
                'text': item['text'],
                'metadata': item.get('metadata', {}),
                'similarity_score': similarity
            })

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarities[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
