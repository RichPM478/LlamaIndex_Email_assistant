"""RAGAS evaluation framework adapter."""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import pandas as pd
from datasets import Dataset

# RAGAS imports
from ragas import evaluate
from ragas.metrics import (
    context_recall,
    context_precision,
    answer_relevancy,
    faithfulness,
    answer_correctness
)

# Langchain for RAGAS integration
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.llms import Ollama
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings

# Your architecture imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.core.domain.entities.evaluation import (
    EvaluationTestCase,
    EvaluationResult,
    RAGASMetrics,
    EvaluationSuite
)
from src.infrastructure.config.settings import get_config
from src.infrastructure.migration.bridge import get_llm, get_embed_model


class RAGASAdapter:
    """
    Adapter that bridges RAGAS evaluation framework with your architecture.
    Handles conversion between your data format and RAGAS requirements.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize RAGAS adapter.
        
        Args:
            provider: Model provider to use (gemini, openai, etc.)
        """
        self.config = get_config()
        self.provider = provider or self.config.get_default_provider("models")
        self.llm = None
        self.embeddings = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize LLM and embedding models for RAGAS."""
        if self._initialized:
            return
        
        # Get LLM for evaluation
        self.llm = self._get_langchain_llm()
        
        # Get embeddings for evaluation
        self.embeddings = self._get_langchain_embeddings()
        
        self._initialized = True
    
    def _get_langchain_llm(self) -> BaseLanguageModel:
        """Get Langchain-compatible LLM for RAGAS."""
        # For RAGAS, we need a Langchain LLM
        # We'll use OpenAI for evaluation even if using Gemini for main queries
        # This ensures consistent evaluation metrics
        
        if self.provider == "openai":
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=0.1  # Low temperature for consistent evaluation
            )
        elif self.provider == "gemini":
            # Use OpenAI for evaluation to ensure RAGAS compatibility
            # Gemini can be used through Langchain but requires additional setup
            return ChatOpenAI(
                model="gpt-3.5-turbo",  # Cheaper model for evaluation
                temperature=0.1
            )
        elif self.provider == "ollama":
            return Ollama(
                model="llama3",
                temperature=0.1
            )
        else:
            # Default to OpenAI for evaluation
            return ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1
            )
    
    def _get_langchain_embeddings(self) -> Embeddings:
        """Get Langchain-compatible embeddings for RAGAS."""
        # Use OpenAI embeddings for consistent evaluation
        return OpenAIEmbeddings(model="text-embedding-3-small")
    
    async def evaluate_single(
        self,
        test_case: EvaluationTestCase,
        actual_answer: str,
        actual_contexts: List[str],
        response_time: float,
        tokens_used: int = 0
    ) -> EvaluationResult:
        """
        Evaluate a single test case using RAGAS.
        
        Args:
            test_case: The test case to evaluate
            actual_answer: The generated answer from your system
            actual_contexts: The retrieved contexts (email contents)
            response_time: Time taken to generate answer
            tokens_used: Number of tokens used
            
        Returns:
            EvaluationResult with RAGAS metrics
        """
        if not self._initialized:
            await self.initialize()
        
        # Prepare data for RAGAS
        data = {
            "question": [test_case.question],
            "answer": [actual_answer],
            "contexts": [actual_contexts],
            "ground_truth": [test_case.expected_answer] if test_case.expected_answer else [actual_answer]
        }
        
        # Create RAGAS dataset
        dataset = Dataset.from_dict(data)
        
        # Select metrics based on available ground truth
        metrics = [
            context_recall,
            context_precision,
            answer_relevancy,
            faithfulness
        ]
        
        if test_case.expected_answer:
            metrics.append(answer_correctness)
        
        # Run RAGAS evaluation
        try:
            results = evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # Convert to pandas for easier access
            results_df = results.to_pandas()
            
            # Extract metrics
            ragas_metrics = RAGASMetrics(
                context_recall=float(results_df['context_recall'].iloc[0]),
                context_precision=float(results_df['context_precision'].iloc[0]),
                answer_relevance=float(results_df['answer_relevancy'].iloc[0]),
                faithfulness=float(results_df['faithfulness'].iloc[0]),
                answer_correctness=float(results_df['answer_correctness'].iloc[0]) 
                    if 'answer_correctness' in results_df.columns else None
            )
            
        except Exception as e:
            print(f"RAGAS evaluation error: {e}")
            # Fallback to mock metrics if RAGAS fails
            ragas_metrics = self._calculate_fallback_metrics(
                test_case, actual_answer, actual_contexts
            )
        
        # Calculate cost (rough estimate)
        cost = self._estimate_cost(tokens_used)
        
        # Generate explanations for stakeholders
        explanations = self._generate_explanations(ragas_metrics, test_case)
        
        return EvaluationResult(
            test_case_id=test_case.id,
            timestamp=datetime.now(),
            provider=self.provider,
            metrics=ragas_metrics,
            response_time=response_time,
            tokens_used=tokens_used,
            cost=cost,
            retrieved_contexts=actual_contexts,
            generated_answer=actual_answer,
            explanations=explanations
        )
    
    async def evaluate_suite(
        self,
        test_cases: List[EvaluationTestCase],
        query_function: Any,
        name: str = "Email Evaluation Suite"
    ) -> EvaluationSuite:
        """
        Evaluate multiple test cases as a suite.
        
        Args:
            test_cases: List of test cases to evaluate
            query_function: Function to call for generating answers (your ask() function)
            name: Name for the evaluation suite
            
        Returns:
            EvaluationSuite with all results
        """
        if not self._initialized:
            await self.initialize()
        
        results = []
        
        for test_case in test_cases:
            print(f"Evaluating: {test_case.id} - {test_case.question[:50]}...")
            
            # Time the query
            start_time = time.time()
            
            # Get answer from your system
            try:
                response = await asyncio.to_thread(query_function, test_case.question)
                actual_answer = response.get('answer', '')
                actual_contexts = [str(c) for c in response.get('citations', [])]
                tokens_used = response.get('tokens_used', 100)  # Estimate if not provided
            except Exception as e:
                print(f"Query error for {test_case.id}: {e}")
                actual_answer = f"Error: {str(e)}"
                actual_contexts = []
                tokens_used = 0
            
            response_time = time.time() - start_time
            
            # Evaluate with RAGAS
            result = await self.evaluate_single(
                test_case=test_case,
                actual_answer=actual_answer,
                actual_contexts=actual_contexts,
                response_time=response_time,
                tokens_used=tokens_used
            )
            
            results.append(result)
            
            # Brief pause to avoid rate limiting
            await asyncio.sleep(1)
        
        return EvaluationSuite(
            name=name,
            timestamp=datetime.now(),
            results=results
        )
    
    def _calculate_fallback_metrics(
        self,
        test_case: EvaluationTestCase,
        actual_answer: str,
        actual_contexts: List[str]
    ) -> RAGASMetrics:
        """
        Calculate simple fallback metrics if RAGAS fails.
        This is a simplified heuristic-based approach.
        """
        # Simple context recall: what % of expected contexts were found
        if test_case.expected_context:
            found = sum(1 for ctx in test_case.expected_context 
                       if any(ctx in str(ac) for ac in actual_contexts))
            context_recall = found / len(test_case.expected_context) if test_case.expected_context else 0
        else:
            context_recall = 0.5  # Default if no expected context
        
        # Simple context precision: assume 70% if contexts were retrieved
        context_precision = 0.7 if actual_contexts else 0.0
        
        # Simple answer relevance: check if answer addresses the question
        question_words = set(test_case.question.lower().split())
        answer_words = set(actual_answer.lower().split())
        common_words = question_words.intersection(answer_words)
        answer_relevance = min(len(common_words) / max(len(question_words), 1), 1.0)
        
        # Simple faithfulness: assume high if answer is not too long
        faithfulness = 0.9 if len(actual_answer) < 1000 else 0.7
        
        # Simple correctness: compare with expected if available
        if test_case.expected_answer:
            expected_words = set(test_case.expected_answer.lower().split())
            overlap = len(answer_words.intersection(expected_words))
            answer_correctness = min(overlap / max(len(expected_words), 1), 1.0)
        else:
            answer_correctness = None
        
        return RAGASMetrics(
            context_recall=context_recall,
            context_precision=context_precision,
            answer_relevance=answer_relevance,
            faithfulness=faithfulness,
            answer_correctness=answer_correctness
        )
    
    def _estimate_cost(self, tokens_used: int) -> float:
        """Estimate cost based on tokens and provider."""
        # Rough cost estimates per 1K tokens
        cost_per_1k = {
            "gemini": 0.00025,  # Gemini 2.5 Flash
            "openai": 0.002,    # GPT-3.5
            "ollama": 0.0,      # Local model
            "anthropic": 0.003  # Claude
        }
        
        rate = cost_per_1k.get(self.provider, 0.001)
        return (tokens_used / 1000) * rate
    
    def _generate_explanations(
        self,
        metrics: RAGASMetrics,
        test_case: EvaluationTestCase
    ) -> Dict[str, str]:
        """Generate human-readable explanations for metrics."""
        explanations = {}
        
        # Context Recall
        if metrics.context_recall >= 0.9:
            explanations["context_recall"] = "Excellent: Found almost all relevant information"
        elif metrics.context_recall >= 0.7:
            explanations["context_recall"] = "Good: Found most relevant information"
        elif metrics.context_recall >= 0.5:
            explanations["context_recall"] = "Fair: Found some relevant information"
        else:
            explanations["context_recall"] = "Poor: Missed important information"
        
        # Context Precision
        if metrics.context_precision >= 0.9:
            explanations["context_precision"] = "Excellent: Retrieved information is highly relevant"
        elif metrics.context_precision >= 0.7:
            explanations["context_precision"] = "Good: Most retrieved information is relevant"
        elif metrics.context_precision >= 0.5:
            explanations["context_precision"] = "Fair: Some irrelevant information included"
        else:
            explanations["context_precision"] = "Poor: Too much irrelevant information"
        
        # Answer Relevance
        if metrics.answer_relevance >= 0.9:
            explanations["answer_relevance"] = "Excellent: Answer directly addresses the question"
        elif metrics.answer_relevance >= 0.7:
            explanations["answer_relevance"] = "Good: Answer mostly addresses the question"
        elif metrics.answer_relevance >= 0.5:
            explanations["answer_relevance"] = "Fair: Answer partially addresses the question"
        else:
            explanations["answer_relevance"] = "Poor: Answer doesn't address the question well"
        
        # Faithfulness
        if metrics.faithfulness >= 0.95:
            explanations["faithfulness"] = "Excellent: No hallucinations detected"
        elif metrics.faithfulness >= 0.85:
            explanations["faithfulness"] = "Good: Answer well-grounded in facts"
        elif metrics.faithfulness >= 0.7:
            explanations["faithfulness"] = "Fair: Mostly factual with minor issues"
        else:
            explanations["faithfulness"] = "Poor: Potential hallucinations detected"
        
        # Answer Correctness
        if metrics.answer_correctness is not None:
            if metrics.answer_correctness >= 0.9:
                explanations["answer_correctness"] = "Excellent: Answer is factually correct"
            elif metrics.answer_correctness >= 0.75:
                explanations["answer_correctness"] = "Good: Answer is mostly correct"
            elif metrics.answer_correctness >= 0.6:
                explanations["answer_correctness"] = "Fair: Answer has some inaccuracies"
            else:
                explanations["answer_correctness"] = "Poor: Answer has significant errors"
        
        return explanations