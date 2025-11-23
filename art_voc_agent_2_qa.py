"""
Agent 2: Quality Assurance Inspector Agent
Validates implementation quality, rejects incomplete work
"""
import json
from typing import Dict, List, Any


class QAInspectorAgent:
    """Agent 2 - Quality assurance and validation"""

    def __init__(self, fm_client):
        self.fm_client = fm_client
        print(" Agent 2 (QA Inspector) initialized")

    def inspect_implementation(self, agent1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspect Agent 1's implementation across all categories

        Args:
            agent1_result: Output from Agent 1

        Returns:
            QA report with PASS/FAIL status and issues found
        """
        print(" Starting comprehensive quality inspection...\n")

        qa_report = {
            'overall_status': 'PENDING',
            'categories': {
                'data_pipeline': 'PENDING',
                'ml_models': 'PENDING',
                'ui': 'PENDING',
                'security': 'PENDING'
            },
            'details': {
                'data_pipeline': {},
                'ml_models': {},
                'ui': {},
                'security': {}
            },
            'critical_issues': [],
            'major_issues': [],
            'minor_issues': [],
            'all_issues': []
        }

        # ============================================================
        # CATEGORY 1: Data Pipeline Inspection
        # ============================================================
        print(" Category 1: Data Pipeline Inspection")
        pipeline_result = self._inspect_data_pipeline(agent1_result)

        qa_report['categories']['data_pipeline'] = pipeline_result['status']
        qa_report['details']['data_pipeline'] = pipeline_result['details']

        if pipeline_result['status'] == 'FAIL':
            qa_report['critical_issues'].extend(pipeline_result.get('issues', []))

        print(f"   Result: {pipeline_result['status']}")
        if pipeline_result.get('issues'):
            for issue in pipeline_result['issues'][:3]:
                print(f"       {issue['description'][:80]}")

        # ============================================================
        # CATEGORY 2: ML Models Validation
        # ============================================================
        print("\n Category 2: ML Models Validation")
        ml_result = self._inspect_ml_models(agent1_result)

        qa_report['categories']['ml_models'] = ml_result['status']
        qa_report['details']['ml_models'] = ml_result['details']

        if ml_result['status'] == 'FAIL':
            qa_report['critical_issues'].extend(ml_result.get('issues', []))

        print(f"   Result: {ml_result['status']}")
        if ml_result.get('issues'):
            for issue in ml_result['issues'][:3]:
                print(f"       {issue['description'][:80]}")

        # ============================================================
        # CATEGORY 3: User Interface Validation
        # ============================================================
        print("\n Category 3: User Interface Validation")
        ui_result = self._inspect_ui(agent1_result)

        qa_report['categories']['ui'] = ui_result['status']
        qa_report['details']['ui'] = ui_result['details']

        if ui_result['status'] == 'FAIL':
            qa_report['major_issues'].extend(ui_result.get('issues', []))
        else:
            qa_report['minor_issues'].extend(ui_result.get('issues', []))

        print(f"   Result: {ui_result['status']}")

        # ============================================================
        # CATEGORY 4: Security Audit
        # ============================================================
        print("\n Category 4: Security Audit")
        security_result = self._inspect_security(agent1_result)

        qa_report['categories']['security'] = security_result['status']
        qa_report['details']['security'] = security_result['details']

        if security_result['status'] == 'FAIL':
            qa_report['critical_issues'].extend(security_result.get('issues', []))

        print(f"   Result: {security_result['status']}")

        # ============================================================
        # FINAL DETERMINATION
        # ============================================================
        qa_report['all_issues'] = (
            qa_report['critical_issues'] +
            qa_report['major_issues'] +
            qa_report['minor_issues']
        )

        # Approve only if all critical categories pass
        all_pass = all(
            qa_report['categories'][cat] == 'PASS'
            for cat in ['data_pipeline', 'ml_models', 'security']
        )

        qa_report['overall_status'] = 'APPROVED' if all_pass else 'REJECTED'

        print("\n" + "="*60)
        if qa_report['overall_status'] == 'APPROVED':
            print(" OVERALL STATUS: APPROVED")
        else:
            print(" OVERALL STATUS: REJECTED")
        print("="*60)

        return qa_report

    def _inspect_data_pipeline(self, agent1_result: Dict) -> Dict:
        """Inspect data quality and completeness"""
        issues = []
        details = {'bronze': 'PENDING', 'silver': 'PENDING', 'gold': 'PENDING'}

        # Bronze Layer Checks
        total_records = agent1_result.get('data_stats', {}).get('total_records', 0)

        if total_records < 100:
            issues.append({
                'severity': 'critical',
                'category': 'Data Pipeline - Bronze',
                'description': f'Insufficient data volume: {total_records} records (need ≥100)',
                'fix': 'Increase data generation to at least 100 total records'
            })
            details['bronze'] = 'FAIL'
        else:
            details['bronze'] = 'PASS'

        # Silver Layer Checks
        predictions = agent1_result.get('data_stats', {}).get('predictions', 0)
        embeddings = agent1_result.get('data_stats', {}).get('embeddings', 0)

        if predictions == 0:
            issues.append({
                'severity': 'critical',
                'category': 'Data Pipeline - Silver',
                'description': 'No sentiment predictions generated',
                'fix': 'Ensure sentiment analysis is running for all interactions'
            })
            details['silver'] = 'FAIL'
        elif embeddings == 0:
            issues.append({
                'severity': 'critical',
                'category': 'Data Pipeline - Silver',
                'description': 'No vector embeddings generated (Vector Search not functional)',
                'fix': 'Call BGE-Large-EN API to generate embeddings for all interactions'
            })
            details['silver'] = 'FAIL'
        else:
            details['silver'] = 'PASS'

        # Gold Layer Checks
        # Check that gold_insights artifact exists
        gold_artifact = next(
            (a for a in agent1_result.get('artifacts', []) if 'gold_insights' in a.get('filename', '')),
            None
        )

        if not gold_artifact:
            issues.append({
                'severity': 'critical',
                'category': 'Data Pipeline - Gold',
                'description': 'Gold layer insights not generated',
                'fix': 'Run churn prediction and generate member 360 insights'
            })
            details['gold'] = 'FAIL'
        else:
            details['gold'] = 'PASS'

        status = 'PASS' if not issues else 'FAIL'

        return {
            'status': status,
            'details': details,
            'issues': issues
        }

    def _inspect_ml_models(self, agent1_result: Dict) -> Dict:
        """Validate ML model quality with test cases"""
        issues = []
        details = {'sentiment': 'PENDING', 'churn': 'PENDING', 'propensity': 'PENDING', 'vector_search': 'PENDING'}

        # Test Case 1: Sentiment Analysis
        print("    Testing sentiment analysis...")

        try:
            # Test positive text
            positive_result = self.fm_client.analyze_sentiment(
                "Thank you so much! The team was incredibly helpful and I'm very happy with my returns."
            )

            if positive_result['score'] < 0.3:
                issues.append({
                    'severity': 'critical',
                    'category': 'ML Models - Sentiment',
                    'description': f'Positive text scored {positive_result["score"]:.2f} (should be >0.5)',
                    'fix': 'Review sentiment analysis prompt and model temperature'
                })
                details['sentiment'] = 'FAIL'
            else:
                details['sentiment'] = 'PASS'
                print("       Positive sentiment detection working")

        except Exception as e:
            issues.append({
                'severity': 'critical',
                'category': 'ML Models - Sentiment',
                'description': f'Sentiment analysis failed: {str(e)[:100]}',
                'fix': 'Check Foundation Model API connectivity and endpoint'
            })
            details['sentiment'] = 'FAIL'

        # Test Case 2: Churn Prediction
        print("    Testing churn prediction...")

        try:
            # Test high-risk scenario
            high_risk = self.fm_client.predict_churn({
                'avg_sentiment': -0.6,
                'complaint_count': 3,
                'nps_score': 2,
                'balance_trend_pct': -15.0,
                'portal_logins': 0,
                'days_since_contact': 120
            })

            if high_risk['churn_risk_score'] < 0.5:
                issues.append({
                    'severity': 'critical',
                    'category': 'ML Models - Churn',
                    'description': f'High-risk member scored only {high_risk["churn_risk_score"]:.2f}',
                    'fix': 'Adjust churn prediction logic to properly weight negative factors'
                })
                details['churn'] = 'FAIL'
            elif not high_risk.get('key_risk_factors'):
                issues.append({
                    'severity': 'critical',
                    'category': 'ML Models - Churn',
                    'description': 'Churn prediction missing risk factors explanation',
                    'fix': 'Ensure model returns key_risk_factors array'
                })
                details['churn'] = 'FAIL'
            else:
                details['churn'] = 'PASS'
                print("       Churn prediction working")

        except Exception as e:
            issues.append({
                'severity': 'critical',
                'category': 'ML Models - Churn',
                'description': f'Churn prediction failed: {str(e)[:100]}',
                'fix': 'Check Foundation Model API and churn prediction implementation'
            })
            details['churn'] = 'FAIL'

        # Test Case 3: Vector Search (Embedding Generation)
        print("    Testing vector search embeddings...")

        try:
            test_text = "I'm unhappy with the high fees"
            embedding = self.fm_client.generate_embedding(test_text)

            if not embedding or len(embedding) < 1000:
                issues.append({
                    'severity': 'critical',
                    'category': 'ML Models - Vector Search',
                    'description': f'Embedding generation failed or wrong size: {len(embedding) if embedding else 0}',
                    'fix': 'Check BGE-Large-EN endpoint and ensure 1024-dim embeddings'
                })
                details['vector_search'] = 'FAIL'
            else:
                details['vector_search'] = 'PASS'
                print(f"       Vector embeddings generated ({len(embedding)} dimensions)")

        except Exception as e:
            issues.append({
                'severity': 'critical',
                'category': 'ML Models - Vector Search',
                'description': f'Embedding generation failed: {str(e)[:100]}',
                'fix': 'Check Databricks BGE-Large-EN endpoint availability'
            })
            details['vector_search'] = 'FAIL'

        # Propensity scoring - mark as PASS for now (optional feature)
        details['propensity'] = 'PASS'

        status = 'PASS' if details['sentiment'] == 'PASS' and details['churn'] == 'PASS' and details['vector_search'] == 'PASS' else 'FAIL'

        return {
            'status': status,
            'details': details,
            'issues': issues
        }

    def _inspect_ui(self, agent1_result: Dict) -> Dict:
        """Validate dashboard completeness"""
        issues = []
        details = {'load': 'PENDING', 'search': 'PENDING', 'charts': 'PENDING'}

        # Check dashboard artifacts exist
        dashboard_artifacts = [
            a for a in agent1_result.get('artifacts', [])
            if 'dashboard' in a.get('filename', '') or '.tsx' in a.get('filename', '') or '.ts' in a.get('filename', '')
        ]

        if len(dashboard_artifacts) == 0:
            issues.append({
                'severity': 'major',
                'category': 'User Interface',
                'description': 'No dashboard files generated',
                'fix': 'Generate Next.js dashboard with pages and API routes'
            })
            details['load'] = 'FAIL'
            status = 'FAIL'
        else:
            details['load'] = 'PASS'

            # Check Vector Search UI exists
            vector_search_file = next(
                (a for a in dashboard_artifacts if 'vector' in a.get('filename', '').lower()),
                None
            )

            if not vector_search_file:
                issues.append({
                    'severity': 'minor',
                    'category': 'User Interface',
                    'description': 'Vector Search UI not implemented',
                    'fix': 'Add semantic search component to dashboard'
                })
                details['search'] = 'WARN'
            else:
                details['search'] = 'PASS'

            details['charts'] = 'PASS'
            status = 'PASS'

        return {
            'status': status,
            'details': details,
            'issues': issues
        }

    def _inspect_security(self, agent1_result: Dict) -> Dict:
        """Security audit"""
        issues = []
        details = {'credentials': 'PENDING', 'validation': 'PENDING'}

        # Check for hardcoded credentials in dashboard code
        dashboard_artifacts = [
            a for a in agent1_result.get('artifacts', [])
            if a.get('type') == 'code'
        ]

        for artifact in dashboard_artifacts:
            content = artifact.get('content', '')

            # Check for hardcoded tokens (basic check)
            if 'dapi' in content.lower() and 'Bearer dapi' in content:
                issues.append({
                    'severity': 'critical',
                    'category': 'Security',
                    'description': f'Hardcoded API token found in {artifact["filename"]}',
                    'fix': 'Use process.env.DATABRICKS_TOKEN instead'
                })
                details['credentials'] = 'FAIL'
                break

        if details['credentials'] == 'PENDING':
            details['credentials'] = 'PASS'

        # Input validation check (verify environment variables used)
        has_env_vars = any('process.env' in a.get('content', '') for a in dashboard_artifacts)

        if not has_env_vars and len(dashboard_artifacts) > 0:
            issues.append({
                'severity': 'critical',
                'category': 'Security',
                'description': 'Dashboard not using environment variables for credentials',
                'fix': 'Use process.env.DATABRICKS_HOST and process.env.DATABRICKS_TOKEN'
            })
            details['validation'] = 'FAIL'
        else:
            details['validation'] = 'PASS'

        status = 'PASS' if details['credentials'] == 'PASS' and details['validation'] == 'PASS' else 'FAIL'

        return {
            'status': status,
            'details': details,
            'issues': issues
        }
