#!/usr/bin/env python3
"""
ART Voice of Customer - 2-Agent System Orchestrator
Sequential quality assurance workflow with iterative refinement
"""
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Import agent implementations
from art_voc_agent_1_software import SoftwareDevAgent
from art_voc_agent_2_qa import QAInspectorAgent
from databricks_fm_client import DatabricksFMClient


class TwoAgentOrchestrator:
    """
    Main orchestrator for the 2-agent system
    Manages iterative build -> inspect -> fix loop
    """

    def __init__(self, workspace_url: str, token: str, max_iterations: int = 3):
        self.workspace_url = workspace_url
        self.token = token
        self.max_iterations = max_iterations

        # Initialize Databricks FM client
        self.fm_client = DatabricksFMClient(workspace_url, token)

        # Initialize both agents
        self.agent1 = SoftwareDevAgent(self.fm_client)
        self.agent2 = QAInspectorAgent(self.fm_client)

        # Create output directories
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        (self.output_dir / "artifacts").mkdir(exist_ok=True)
        (self.output_dir / "qa_reports").mkdir(exist_ok=True)
        (self.output_dir / "data").mkdir(exist_ok=True)

        print("=" * 70)
        print(" ART VOC 2-AGENT SYSTEM")
        print("=" * 70)
        print(f"Workspace: {workspace_url}")
        print(f"Max Iterations: {max_iterations}")
        print(f"Output Directory: {self.output_dir.absolute()}")
        print("=" * 70)

    def run(self) -> Dict[str, Any]:
        """
        Execute the 2-agent system with iterative refinement

        Returns:
            Final result with status, report, and artifacts
        """
        agent1_context = {
            'issues_to_fix': [],
            'iteration': 0
        }

        for iteration in range(self.max_iterations):
            print(f"\n{'=' * 70}")
            print(f" ITERATION {iteration + 1} of {self.max_iterations}")
            print(f"{'=' * 70}\n")

            agent1_context['iteration'] = iteration + 1

            # ============================================================
            # STEP 1: Agent 1 (Software Developer) builds implementation
            # ============================================================
            print(" AGENT 1 (Software Developer): Building implementation...\n")

            agent1_result = self.agent1.build_implementation(agent1_context)

            print(f"\n Agent 1 Completed:")
            print(f"   - Data Generation: {agent1_result['data_generation_status']}")
            print(f"   - Pipeline Status: {agent1_result['pipeline_status']}")
            print(f"   - Dashboard Status: {agent1_result['dashboard_status']}")
            print(f"   - Artifacts: {len(agent1_result['artifacts'])} files")

            # Save Agent 1 artifacts
            self._save_artifacts(agent1_result['artifacts'], iteration)

            time.sleep(2)  # Brief pause between agents

            # ============================================================
            # STEP 2: Agent 2 (QA Inspector) validates implementation
            # ============================================================
            print(f"\n AGENT 2 (QA Inspector): Running inspections...\n")

            agent2_result = self.agent2.inspect_implementation(agent1_result)

            print(f"\n QA Report Generated:")
            print(f"   - Overall Status: {agent2_result['overall_status']}")
            print(f"   - Data Pipeline: {agent2_result['categories']['data_pipeline']}")
            print(f"   - ML Models: {agent2_result['categories']['ml_models']}")
            print(f"   - User Interface: {agent2_result['categories']['ui']}")
            print(f"   - Security: {agent2_result['categories']['security']}")
            print(f"   - Critical Issues: {len(agent2_result['critical_issues'])}")
            print(f"   - Major Issues: {len(agent2_result['major_issues'])}")

            # Save QA report
            report_path = self._save_qa_report(agent2_result, iteration)
            print(f"\n    Report saved: {report_path}")

            # ============================================================
            # STEP 3: Decision - Approved or Needs Revision?
            # ============================================================
            if agent2_result['overall_status'] == 'APPROVED':
                print(f"\n{'=' * 70}")
                print(" SUCCESS: DEMO APPROVED FOR PRODUCTION")
                print(f"{'=' * 70}")
                print(f"\n Demo is production-ready after {iteration + 1} iteration(s)")
                print(f"\n Final Statistics:")
                print(f"   - Total Iterations: {iteration + 1}")
                print(f"   - Data Records: {agent1_result.get('data_stats', {}).get('total_records', 'N/A')}")
                print(f"   - ML Predictions: {agent1_result.get('data_stats', {}).get('predictions', 'N/A')}")
                print(f"   - Dashboard Pages: {agent1_result.get('dashboard_pages', 0)}")
                print(f"\n Deliverables:")
                print(f"   - Final Report: {report_path}")
                print(f"   - React App: {self.output_dir / 'artifacts' / 'react_app'}")
                print(f"   - Data Files: {self.output_dir / 'data'}")

                return {
                    'status': 'SUCCESS',
                    'iterations': iteration + 1,
                    'report_path': str(report_path),
                    'artifacts': agent1_result['artifacts'],
                    'qa_result': agent2_result,
                    'dashboard_url': agent1_result.get('dashboard_url')
                }

            else:
                # REJECTED - prepare for next iteration
                print(f"\n{'=' * 70}")
                print(f" REJECTED: Found {len(agent2_result['all_issues'])} issue(s)")
                print(f"{'=' * 70}")

                print(f"\n Critical Issues ({len(agent2_result['critical_issues'])}):")
                for issue in agent2_result['critical_issues'][:5]:  # Show first 5
                    print(f"   - {issue['category']}: {issue['description'][:80]}")

                if len(agent2_result['major_issues']) > 0:
                    print(f"\n Major Issues ({len(agent2_result['major_issues'])}):")
                    for issue in agent2_result['major_issues'][:3]:  # Show first 3
                        print(f"   - {issue['category']}: {issue['description'][:80]}")

                # Pass issues back to Agent 1 for next iteration
                agent1_context['issues_to_fix'] = agent2_result['all_issues']

                if iteration < self.max_iterations - 1:
                    print(f"\n Proceeding to iteration {iteration + 2}...")
                    time.sleep(3)
                else:
                    print(f"\n  Reached maximum iterations")

        # Max iterations reached without approval
        print(f"\n{'=' * 70}")
        print("  FAILED: Could not achieve production quality")
        print(f"{'=' * 70}")
        print(f"\nReached {self.max_iterations} iterations without approval")
        print(f"Last QA Report: {report_path}")

        return {
            'status': 'FAILED',
            'iterations': self.max_iterations,
            'last_report': str(report_path),
            'last_issues': agent2_result['all_issues']
        }

    def _save_artifacts(self, artifacts: List[Dict], iteration: int):
        """Save Agent 1's generated artifacts"""
        iteration_dir = self.output_dir / "artifacts" / f"iteration_{iteration + 1}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        for artifact in artifacts:
            file_path = iteration_dir / artifact['filename']

            if artifact['type'] == 'code':
                file_path.write_text(artifact['content'])
            elif artifact['type'] == 'json':
                file_path.write_text(json.dumps(artifact['content'], indent=2))
            elif artifact['type'] == 'binary':
                file_path.write_bytes(artifact['content'])

    def _save_qa_report(self, qa_result: Dict, iteration: int) -> Path:
        """Save Agent 2's QA report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"qa_report_iteration_{iteration + 1}_{timestamp}.md"
        report_path = self.output_dir / "qa_reports" / report_filename

        # Generate markdown report
        report_content = self._generate_markdown_report(qa_result, iteration + 1)
        report_path.write_text(report_content)

        # Also save JSON version
        json_path = report_path.with_suffix('.json')
        json_path.write_text(json.dumps(qa_result, indent=2))

        return report_path

    def _generate_markdown_report(self, qa_result: Dict, iteration: int) -> str:
        """Generate markdown QA report from results"""
        status_emoji = "" if qa_result['overall_status'] == 'APPROVED' else ""

        report = f"""# Quality Inspection Report
**Iteration:** {iteration}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Inspector:** Agent 2 (QA Engineer)

---

## Executive Summary
**Overall Status:** {status_emoji} **{qa_result['overall_status']}**

**Issue Counts:**
-  Critical Issues: {len(qa_result['critical_issues'])}
-  Major Issues: {len(qa_result['major_issues'])}
-  Minor Issues: {len(qa_result['minor_issues'])}

---

## Category Results

### Data Pipeline: {qa_result['categories']['data_pipeline']}
- Bronze Layer: {'' if qa_result['details']['data_pipeline'].get('bronze') == 'PASS' else ''}
- Silver Layer: {'' if qa_result['details']['data_pipeline'].get('silver') == 'PASS' else ''}
- Gold Layer: {'' if qa_result['details']['data_pipeline'].get('gold') == 'PASS' else ''}

### AI/ML Models: {qa_result['categories']['ml_models']}
- Sentiment Analysis: {'' if qa_result['details']['ml_models'].get('sentiment') == 'PASS' else ''}
- Churn Prediction: {'' if qa_result['details']['ml_models'].get('churn') == 'PASS' else ''}
- Propensity Scoring: {'' if qa_result['details']['ml_models'].get('propensity') == 'PASS' else ''}

### User Interface: {qa_result['categories']['ui']}
- Dashboard Load: {'' if qa_result['details']['ui'].get('load') == 'PASS' else ''}
- Member Search: {'' if qa_result['details']['ui'].get('search') == 'PASS' else ''}
- Charts/Visualizations: {'' if qa_result['details']['ui'].get('charts') == 'PASS' else ''}

### Security: {qa_result['categories']['security']}
- Credential Management: {'' if qa_result['details']['security'].get('credentials') == 'PASS' else ''}
- Input Validation: {'' if qa_result['details']['security'].get('validation') == 'PASS' else ''}

---

## Issues Found

"""

        # Add critical issues
        if qa_result['critical_issues']:
            report += "###  Critical Issues (Must Fix Before Demo)\n\n"
            for i, issue in enumerate(qa_result['critical_issues'], 1):
                report += f"{i}. **{issue['category']}**: {issue['description']}\n"
                if 'fix' in issue:
                    report += f"   - **Fix:** {issue['fix']}\n"
                report += "\n"

        # Add major issues
        if qa_result['major_issues']:
            report += "###  Major Issues (Should Fix)\n\n"
            for i, issue in enumerate(qa_result['major_issues'], 1):
                report += f"{i}. **{issue['category']}**: {issue['description']}\n"
                if 'fix' in issue:
                    report += f"   - **Fix:** {issue['fix']}\n"
                report += "\n"

        # Add minor issues
        if qa_result['minor_issues']:
            report += "###  Minor Issues (Nice to Have)\n\n"
            for i, issue in enumerate(qa_result['minor_issues'], 1):
                report += f"{i}. {issue['description']}\n"

        # Add sign-off
        report += f"""
---

## Sign-Off

- [{'x' if qa_result['categories']['data_pipeline'] == 'PASS' else ' '}] Data pipeline is complete and functional
- [{'x' if qa_result['categories']['ml_models'] == 'PASS' else ' '}] All ML models functional
- [{'x' if qa_result['categories']['ui'] == 'PASS' else ' '}] UI is polished and working
- [{'x' if qa_result['categories']['security'] == 'PASS' else ' '}] Security standards met
- [{'x' if qa_result['overall_status'] == 'APPROVED' else ' '}] Ready for executive demo

**Recommendation:** {'APPROVE - Demo is production-ready' if qa_result['overall_status'] == 'APPROVED' else 'REJECT - Must fix critical issues'}

**Signature:** Agent 2 (QA Inspector)
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    """Main entry point"""
    # Read Databricks config
    import configparser
    config_path = Path.home() / ".databrickscfg"

    if not config_path.exists():
        print(" Error: ~/.databrickscfg not found")
        print("   Please run: databricks configure --token")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_path)

    workspace_url = config['DEFAULT']['host'].rstrip('/')
    token = config['DEFAULT']['token']

    # Create and run orchestrator
    orchestrator = TwoAgentOrchestrator(
        workspace_url=workspace_url,
        token=token,
        max_iterations=3
    )

    try:
        result = orchestrator.run()

        if result['status'] == 'SUCCESS':
            print(f"\n Demo generation successful!")
            print(f"\nNext steps:")
            print(f"1. Review QA report: {result['report_path']}")
            print(f"2. Deploy dashboard: cd output/artifacts/react_app && npm install && npm run dev")
            print(f"3. Present to ART executives!")
            sys.exit(0)
        else:
            print(f"\n  Demo generation failed after {result['iterations']} iterations")
            print(f"Review last report: {result['last_report']}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
