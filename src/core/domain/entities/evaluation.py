"""Domain entities for evaluation system."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class TestCategory(Enum):
    """Categories of test cases."""
    SEARCH = "search"
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    URGENT = "urgent"
    COMPLEX = "complex"


class TestDifficulty(Enum):
    """Difficulty levels for test cases."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MetricStatus(Enum):
    """Status indicators for metrics."""
    EXCELLENT = "excellent"  # >= 90%
    GOOD = "good"           # >= 75%
    FAIR = "fair"           # >= 60%
    POOR = "poor"           # < 60%


@dataclass
class EvaluationTestCase:
    """Single test case for evaluation."""
    id: str
    question: str
    expected_context: List[str]  # Expected email IDs or document IDs to retrieve
    expected_answer: Optional[str] = None  # Ground truth answer
    category: TestCategory = TestCategory.SEARCH
    difficulty: TestDifficulty = TestDifficulty.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "question": self.question,
            "expected_context": self.expected_context,
            "expected_answer": self.expected_answer,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "metadata": self.metadata
        }


@dataclass
class RAGASMetrics:
    """RAGAS evaluation metrics."""
    context_recall: float  # How well system finds relevant information
    context_precision: float  # How relevant the retrieved information is
    answer_relevance: float  # How well answer addresses the question
    faithfulness: float  # How grounded the answer is in context
    answer_correctness: Optional[float] = None  # Factual correctness (if ground truth available)
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall score."""
        scores = [
            self.context_recall * 0.2,
            self.context_precision * 0.2,
            self.answer_relevance * 0.25,
            self.faithfulness * 0.25
        ]
        if self.answer_correctness is not None:
            scores.append(self.answer_correctness * 0.1)
        return sum(scores) / (0.9 if self.answer_correctness is None else 1.0)
    
    def get_status(self, metric_value: float) -> MetricStatus:
        """Get status indicator for a metric value."""
        if metric_value >= 0.9:
            return MetricStatus.EXCELLENT
        elif metric_value >= 0.75:
            return MetricStatus.GOOD
        elif metric_value >= 0.6:
            return MetricStatus.FAIR
        else:
            return MetricStatus.POOR


@dataclass
class EvaluationResult:
    """Complete evaluation result for a test case."""
    test_case_id: str
    timestamp: datetime
    provider: str  # Model provider used (gemini, openai, etc.)
    
    # RAGAS Metrics
    metrics: RAGASMetrics
    
    # Performance metrics
    response_time: float  # Seconds
    tokens_used: int
    cost: float  # Estimated cost in USD
    
    # Actual results
    retrieved_contexts: List[str]
    generated_answer: str
    
    # Detailed explanations for stakeholders
    explanations: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_case_id": self.test_case_id,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "metrics": {
                "context_recall": self.metrics.context_recall,
                "context_precision": self.metrics.context_precision,
                "answer_relevance": self.metrics.answer_relevance,
                "faithfulness": self.metrics.faithfulness,
                "answer_correctness": self.metrics.answer_correctness,
                "overall_score": self.metrics.overall_score
            },
            "performance": {
                "response_time": self.response_time,
                "tokens_used": self.tokens_used,
                "cost": self.cost
            },
            "retrieved_contexts": self.retrieved_contexts,
            "generated_answer": self.generated_answer,
            "explanations": self.explanations
        }
    
    def get_stakeholder_summary(self) -> Dict[str, Any]:
        """Get simplified summary for non-technical stakeholders."""
        return {
            "test_performed": self.test_case_id,
            "ai_model": self.provider.upper(),
            "performance_score": f"{self.metrics.overall_score * 100:.1f}%",
            "finding_information": {
                "score": f"{self.metrics.context_recall * 100:.0f}%",
                "status": self.metrics.get_status(self.metrics.context_recall).value,
                "meaning": "How well the AI finds relevant emails"
            },
            "accuracy": {
                "score": f"{self.metrics.context_precision * 100:.0f}%",
                "status": self.metrics.get_status(self.metrics.context_precision).value,
                "meaning": "How relevant the found information is"
            },
            "helpfulness": {
                "score": f"{self.metrics.answer_relevance * 100:.0f}%",
                "status": self.metrics.get_status(self.metrics.answer_relevance).value,
                "meaning": "How well the answer addresses your question"
            },
            "trustworthiness": {
                "score": f"{self.metrics.faithfulness * 100:.0f}%",
                "status": self.metrics.get_status(self.metrics.faithfulness).value,
                "meaning": "Answer based on facts, no hallucinations"
            },
            "speed": f"{self.response_time:.1f} seconds",
            "cost": f"${self.cost:.4f}"
        }


@dataclass
class EvaluationSuite:
    """Collection of evaluation results."""
    name: str
    timestamp: datetime
    results: List[EvaluationResult]
    
    @property
    def average_metrics(self) -> RAGASMetrics:
        """Calculate average metrics across all results."""
        if not self.results:
            return RAGASMetrics(0, 0, 0, 0, 0)
        
        avg_recall = sum(r.metrics.context_recall for r in self.results) / len(self.results)
        avg_precision = sum(r.metrics.context_precision for r in self.results) / len(self.results)
        avg_relevance = sum(r.metrics.answer_relevance for r in self.results) / len(self.results)
        avg_faithfulness = sum(r.metrics.faithfulness for r in self.results) / len(self.results)
        
        correctness_results = [r.metrics.answer_correctness for r in self.results 
                              if r.metrics.answer_correctness is not None]
        avg_correctness = sum(correctness_results) / len(correctness_results) if correctness_results else None
        
        return RAGASMetrics(
            context_recall=avg_recall,
            context_precision=avg_precision,
            answer_relevance=avg_relevance,
            faithfulness=avg_faithfulness,
            answer_correctness=avg_correctness
        )
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost of evaluation suite."""
        return sum(r.cost for r in self.results)
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if not self.results:
            return 0
        return sum(r.response_time for r in self.results) / len(self.results)
    
    def get_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary for stakeholders."""
        avg_metrics = self.average_metrics
        
        return {
            "evaluation_name": self.name,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "tests_run": len(self.results),
            "overall_health": f"{avg_metrics.overall_score * 100:.1f}%",
            "key_metrics": {
                "Finding Information": {
                    "score": f"{avg_metrics.context_recall * 100:.0f}%",
                    "status": avg_metrics.get_status(avg_metrics.context_recall).value.upper()
                },
                "Accuracy": {
                    "score": f"{avg_metrics.context_precision * 100:.0f}%",
                    "status": avg_metrics.get_status(avg_metrics.context_precision).value.upper()
                },
                "Helpfulness": {
                    "score": f"{avg_metrics.answer_relevance * 100:.0f}%",
                    "status": avg_metrics.get_status(avg_metrics.answer_relevance).value.upper()
                },
                "Trustworthiness": {
                    "score": f"{avg_metrics.faithfulness * 100:.0f}%",
                    "status": avg_metrics.get_status(avg_metrics.faithfulness).value.upper()
                }
            },
            "performance": {
                "average_response_time": f"{self.average_response_time:.1f} seconds",
                "total_cost": f"${self.total_cost:.2f}"
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []
        avg_metrics = self.average_metrics
        
        if avg_metrics.context_recall < 0.7:
            recommendations.append("Consider improving search indexing for better information retrieval")
        
        if avg_metrics.context_precision < 0.7:
            recommendations.append("Fine-tune retrieval to reduce irrelevant results")
        
        if avg_metrics.answer_relevance < 0.75:
            recommendations.append("Adjust prompt engineering to improve answer relevance")
        
        if avg_metrics.faithfulness < 0.85:
            recommendations.append("Strengthen grounding mechanisms to prevent hallucinations")
        
        if self.average_response_time > 5:
            recommendations.append("Optimize query processing for faster responses")
        
        if not recommendations:
            recommendations.append("System performing well - maintain current configuration")
        
        return recommendations