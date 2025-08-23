"""Automated evaluation runner for scheduled and continuous testing."""
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.infrastructure.adapters.evaluation.ragas_adapter import RAGASAdapter
from src.infrastructure.adapters.evaluation.email_test_suite import EmailEvaluationTestSuite
from src.core.domain.entities.evaluation import EvaluationSuite, EvaluationResult
from src.infrastructure.config.settings import get_config
from app.qa.query import ask


class AutoEvaluator:
    """
    Automated evaluation system that runs scheduled tests
    and provides continuous monitoring of system performance.
    """
    
    def __init__(self, results_dir: str = "./evaluation_results"):
        """
        Initialize auto evaluator.
        
        Args:
            results_dir: Directory to store evaluation results
        """
        self.config = get_config()
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_suite = EmailEvaluationTestSuite()
        self.evaluation_history: List[EvaluationSuite] = []
        self.running = False
    
    async def run_daily_evaluation(self) -> EvaluationSuite:
        """Run daily comprehensive evaluation."""
        print(f"[{datetime.now()}] Starting daily evaluation...")
        
        # Get default provider
        provider = self.config.get_default_provider("models")
        
        # Initialize adapter
        adapter = RAGASAdapter(provider=provider)
        
        # Run comprehensive test suite
        test_cases = self.test_suite.get_comprehensive_test_suite()
        
        results = await adapter.evaluate_suite(
            test_cases=test_cases,
            query_function=ask,
            name=f"Daily Evaluation - {provider}"
        )
        
        # Save results
        self._save_results(results, "daily")
        
        # Check for performance degradation
        self._check_performance_alerts(results)
        
        # Generate and save report
        self._generate_report(results, "daily")
        
        print(f"[{datetime.now()}] Daily evaluation complete. Overall score: {results.average_metrics.overall_score:.2%}")
        
        return results
    
    async def run_quick_evaluation(self) -> EvaluationSuite:
        """Run quick evaluation (subset of tests)."""
        print(f"[{datetime.now()}] Starting quick evaluation...")
        
        provider = self.config.get_default_provider("models")
        adapter = RAGASAdapter(provider=provider)
        
        # Use quick test suite
        test_cases = self.test_suite.get_quick_test_suite()
        
        results = await adapter.evaluate_suite(
            test_cases=test_cases,
            query_function=ask,
            name=f"Quick Evaluation - {provider}"
        )
        
        # Save results
        self._save_results(results, "quick")
        
        print(f"[{datetime.now()}] Quick evaluation complete. Overall score: {results.average_metrics.overall_score:.2%}")
        
        return results
    
    async def run_model_comparison(self, models: List[str] = None) -> Dict[str, EvaluationSuite]:
        """
        Run evaluation comparing multiple models.
        
        Args:
            models: List of model providers to compare
            
        Returns:
            Dictionary of model -> evaluation results
        """
        if models is None:
            models = ["gemini", "openai"]  # Default comparison
        
        print(f"[{datetime.now()}] Starting model comparison: {models}")
        
        comparison_results = {}
        test_cases = self.test_suite.get_quick_test_suite()  # Use quick suite for comparison
        
        for model in models:
            try:
                print(f"Testing {model}...")
                adapter = RAGASAdapter(provider=model)
                
                results = await adapter.evaluate_suite(
                    test_cases=test_cases,
                    query_function=ask,
                    name=f"Model Comparison - {model}"
                )
                
                comparison_results[model] = results
                
            except Exception as e:
                print(f"Error testing {model}: {e}")
                continue
        
        # Generate comparison report
        self._generate_comparison_report(comparison_results)
        
        # Recommend best model
        best_model = self._recommend_best_model(comparison_results)
        print(f"[{datetime.now()}] Recommended model: {best_model}")
        
        return comparison_results
    
    def schedule_evaluations(self):
        """Schedule automatic evaluations."""
        # Daily comprehensive evaluation at 2 AM
        schedule.every().day.at("02:00").do(
            lambda: asyncio.run(self.run_daily_evaluation())
        )
        
        # Quick evaluation every 6 hours
        schedule.every(6).hours.do(
            lambda: asyncio.run(self.run_quick_evaluation())
        )
        
        # Weekly model comparison on Sundays
        schedule.every().sunday.at("03:00").do(
            lambda: asyncio.run(self.run_model_comparison())
        )
        
        print("Evaluation schedule configured:")
        print("  - Daily comprehensive: 2:00 AM")
        print("  - Quick evaluation: Every 6 hours")
        print("  - Model comparison: Sundays 3:00 AM")
    
    def start_scheduler(self):
        """Start the evaluation scheduler."""
        self.running = True
        print("Starting evaluation scheduler...")
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop_scheduler(self):
        """Stop the evaluation scheduler."""
        self.running = False
        print("Evaluation scheduler stopped.")
    
    def _save_results(self, results: EvaluationSuite, eval_type: str):
        """Save evaluation results to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{eval_type}_evaluation_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert results to dict
        results_dict = {
            "name": results.name,
            "timestamp": results.timestamp.isoformat(),
            "summary": results.get_executive_summary(),
            "results": [r.to_dict() for r in results.results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"Results saved to {filepath}")
        
        # Also save to history
        self.evaluation_history.append(results)
        
        # Keep only last 30 days of history
        cutoff = datetime.now() - timedelta(days=30)
        self.evaluation_history = [
            r for r in self.evaluation_history 
            if r.timestamp > cutoff
        ]
    
    def _check_performance_alerts(self, results: EvaluationSuite):
        """Check for performance degradation and send alerts."""
        avg_metrics = results.average_metrics
        alerts = []
        
        # Check each metric against thresholds
        if avg_metrics.context_recall < 0.7:
            alerts.append(f"⚠️ Low Context Recall: {avg_metrics.context_recall:.2%}")
        
        if avg_metrics.context_precision < 0.7:
            alerts.append(f"⚠️ Low Context Precision: {avg_metrics.context_precision:.2%}")
        
        if avg_metrics.answer_relevance < 0.75:
            alerts.append(f"⚠️ Low Answer Relevance: {avg_metrics.answer_relevance:.2%}")
        
        if avg_metrics.faithfulness < 0.85:
            alerts.append(f"⚠️ Low Faithfulness: {avg_metrics.faithfulness:.2%}")
        
        if results.average_response_time > 5.0:
            alerts.append(f"⚠️ Slow Response Time: {results.average_response_time:.1f}s")
        
        # Send alerts (in production, this would send emails/notifications)
        if alerts:
            print("\n🚨 PERFORMANCE ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
            
            # Log to file
            alert_file = self.results_dir / "alerts.log"
            with open(alert_file, 'a') as f:
                f.write(f"\n[{datetime.now()}] Alerts:\n")
                for alert in alerts:
                    f.write(f"  {alert}\n")
    
    def _generate_report(self, results: EvaluationSuite, report_type: str):
        """Generate evaluation report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.results_dir / f"{report_type}_report_{timestamp}.md"
        
        summary = results.get_executive_summary()
        
        report = f"""# Evaluation Report - {report_type.title()}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary
- **Overall Health**: {summary['overall_health']}
- **Tests Run**: {summary['tests_run']}
- **Average Response Time**: {summary['performance']['average_response_time']}
- **Total Cost**: {summary['performance']['total_cost']}

## Key Metrics
"""
        
        for metric, data in summary['key_metrics'].items():
            report += f"- **{metric}**: {data['score']} ({data['status']})\n"
        
        report += "\n## Recommendations\n"
        for rec in summary['recommendations']:
            report += f"- {rec}\n"
        
        # Add detailed results
        report += "\n## Detailed Results\n"
        for result in results.results[:5]:  # Show first 5
            stakeholder_summary = result.get_stakeholder_summary()
            report += f"\n### Test: {result.test_case_id}\n"
            report += f"- Performance Score: {stakeholder_summary['performance_score']}\n"
            report += f"- Speed: {stakeholder_summary['speed']}\n"
            report += f"- Cost: {stakeholder_summary['cost']}\n"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"Report saved to {report_file}")
    
    def _generate_comparison_report(self, comparison_results: Dict[str, EvaluationSuite]):
        """Generate model comparison report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.results_dir / f"model_comparison_{timestamp}.md"
        
        report = f"""# Model Comparison Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Models Tested
"""
        
        # Create comparison table
        comparison_data = []
        
        for model, results in comparison_results.items():
            avg_metrics = results.average_metrics
            comparison_data.append({
                'Model': model.upper(),
                'Overall Score': f"{avg_metrics.overall_score:.2%}",
                'Context Recall': f"{avg_metrics.context_recall:.2%}",
                'Context Precision': f"{avg_metrics.context_precision:.2%}",
                'Answer Relevance': f"{avg_metrics.answer_relevance:.2%}",
                'Faithfulness': f"{avg_metrics.faithfulness:.2%}",
                'Avg Response Time': f"{results.average_response_time:.1f}s",
                'Total Cost': f"${results.total_cost:.4f}"
            })
        
        # Convert to markdown table
        df = pd.DataFrame(comparison_data)
        report += df.to_markdown(index=False)
        
        # Add recommendation
        best_model = self._recommend_best_model(comparison_results)
        report += f"\n\n## Recommendation\n**Best Model**: {best_model.upper()}\n"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"Comparison report saved to {report_file}")
    
    def _recommend_best_model(self, comparison_results: Dict[str, EvaluationSuite]) -> str:
        """Recommend the best model based on evaluation results."""
        if not comparison_results:
            return "No models tested"
        
        # Score each model (weighted by importance)
        model_scores = {}
        
        for model, results in comparison_results.items():
            avg_metrics = results.average_metrics
            
            # Calculate weighted score
            score = (
                avg_metrics.overall_score * 0.4 +  # Overall performance
                (1 / max(results.average_response_time, 0.1)) * 0.2 +  # Speed (inverted)
                (1 / max(results.total_cost, 0.0001)) * 0.2 +  # Cost (inverted)
                avg_metrics.faithfulness * 0.2  # Trustworthiness
            )
            
            model_scores[model] = score
        
        # Get best model
        best_model = max(model_scores, key=model_scores.get)
        return best_model
    
    def get_historical_trends(self, days: int = 7) -> pd.DataFrame:
        """Get historical evaluation trends."""
        cutoff = datetime.now() - timedelta(days=days)
        
        trend_data = []
        for suite in self.evaluation_history:
            if suite.timestamp > cutoff:
                avg_metrics = suite.average_metrics
                trend_data.append({
                    'Date': suite.timestamp.date(),
                    'Overall Score': avg_metrics.overall_score,
                    'Context Recall': avg_metrics.context_recall,
                    'Context Precision': avg_metrics.context_precision,
                    'Answer Relevance': avg_metrics.answer_relevance,
                    'Faithfulness': avg_metrics.faithfulness,
                    'Avg Response Time': suite.average_response_time,
                    'Total Cost': suite.total_cost
                })
        
        if trend_data:
            return pd.DataFrame(trend_data)
        else:
            return pd.DataFrame()


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run email system evaluation")
    parser.add_argument("--type", choices=["quick", "daily", "comparison"], 
                       default="quick", help="Type of evaluation to run")
    parser.add_argument("--models", nargs="+", default=["gemini"],
                       help="Models to evaluate (for comparison)")
    parser.add_argument("--schedule", action="store_true",
                       help="Start scheduled evaluations")
    
    args = parser.parse_args()
    
    evaluator = AutoEvaluator()
    
    if args.schedule:
        evaluator.schedule_evaluations()
        evaluator.start_scheduler()
    else:
        if args.type == "quick":
            asyncio.run(evaluator.run_quick_evaluation())
        elif args.type == "daily":
            asyncio.run(evaluator.run_daily_evaluation())
        elif args.type == "comparison":
            asyncio.run(evaluator.run_model_comparison(args.models))