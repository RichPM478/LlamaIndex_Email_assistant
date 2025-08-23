"""Email-specific test suite for RAGAS evaluation."""
from typing import List, Dict, Any
import json
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.core.domain.entities.evaluation import (
    EvaluationTestCase,
    TestCategory,
    TestDifficulty
)


class EmailEvaluationTestSuite:
    """
    Comprehensive test suite for email intelligence system evaluation.
    Contains realistic test cases for different email query scenarios.
    """
    
    def __init__(self):
        """Initialize test suite with predefined test cases."""
        self.test_cases = self._create_test_cases()
    
    def _create_test_cases(self) -> List[EvaluationTestCase]:
        """Create comprehensive test cases for email system."""
        test_cases = []
        
        # Search Accuracy Tests
        test_cases.extend(self._create_search_tests())
        
        # Summary Quality Tests
        test_cases.extend(self._create_summary_tests())
        
        # Urgent Detection Tests
        test_cases.extend(self._create_urgent_tests())
        
        # Analysis Tests
        test_cases.extend(self._create_analysis_tests())
        
        # Complex Query Tests
        test_cases.extend(self._create_complex_tests())
        
        return test_cases
    
    def _create_search_tests(self) -> List[EvaluationTestCase]:
        """Create search accuracy test cases."""
        return [
            EvaluationTestCase(
                id="search_001",
                question="Find all emails about the Q4 budget meeting",
                expected_context=["budget_q4_invite", "budget_q4_agenda", "budget_q4_followup"],
                expected_answer="Found 3 emails about the Q4 budget meeting including the invitation, agenda, and follow-up notes.",
                category=TestCategory.SEARCH,
                difficulty=TestDifficulty.EASY,
                metadata={"topic": "budget", "timeframe": "Q4"}
            ),
            EvaluationTestCase(
                id="search_002",
                question="Show me emails from John Smith in the last week",
                expected_context=["john_project_update", "john_meeting_request"],
                expected_answer="John Smith sent 2 emails in the last week: a project update and a meeting request.",
                category=TestCategory.SEARCH,
                difficulty=TestDifficulty.EASY,
                metadata={"sender": "John Smith", "timeframe": "last_week"}
            ),
            EvaluationTestCase(
                id="search_003",
                question="Find emails with attachments about the marketing campaign",
                expected_context=["marketing_presentation", "marketing_budget_xlsx", "campaign_images"],
                expected_answer="3 emails with attachments related to marketing campaign: presentation slides, budget spreadsheet, and campaign images.",
                category=TestCategory.SEARCH,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"has_attachments": True, "topic": "marketing"}
            ),
            EvaluationTestCase(
                id="search_004",
                question="What emails mention both Project Alpha and deadline",
                expected_context=["alpha_timeline", "alpha_delay_notice", "alpha_milestone"],
                expected_answer="3 emails mention Project Alpha and deadlines, including timeline updates and delay notifications.",
                category=TestCategory.SEARCH,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"keywords": ["Project Alpha", "deadline"]}
            ),
            EvaluationTestCase(
                id="search_005",
                question="Find all unread emails from external clients",
                expected_context=["client_inquiry_unread", "client_complaint_unread"],
                expected_answer="2 unread emails from external clients requiring attention.",
                category=TestCategory.SEARCH,
                difficulty=TestDifficulty.HARD,
                metadata={"status": "unread", "sender_type": "external"}
            )
        ]
    
    def _create_summary_tests(self) -> List[EvaluationTestCase]:
        """Create summary quality test cases."""
        return [
            EvaluationTestCase(
                id="summary_001",
                question="Summarize today's emails",
                expected_context=["today_meeting", "today_report", "today_question"],
                expected_answer="Today you received 3 emails: a meeting invitation for tomorrow, a status report from the dev team, and a question about project timeline.",
                category=TestCategory.SUMMARY,
                difficulty=TestDifficulty.EASY,
                metadata={"timeframe": "today"}
            ),
            EvaluationTestCase(
                id="summary_002",
                question="What are the key points from the product team's emails this week?",
                expected_context=["product_launch", "product_bugs", "product_metrics"],
                expected_answer="Product team updates: 1) Launch delayed by 2 weeks, 2) 3 critical bugs fixed, 3) User engagement up 15%.",
                category=TestCategory.SUMMARY,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"team": "product", "timeframe": "this_week"}
            ),
            EvaluationTestCase(
                id="summary_003",
                question="Summarize all emails about the customer complaint from ABC Corp",
                expected_context=["abc_initial_complaint", "abc_investigation", "abc_resolution"],
                expected_answer="ABC Corp complaint timeline: Initial issue with billing error ($5000), investigation found system glitch, resolved with refund and 10% discount.",
                category=TestCategory.SUMMARY,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"client": "ABC Corp", "issue": "complaint"}
            ),
            EvaluationTestCase(
                id="summary_004",
                question="Give me a summary of action items from yesterday's emails",
                expected_context=["action_review_doc", "action_approve_budget", "action_schedule_meeting"],
                expected_answer="3 action items from yesterday: 1) Review design document by Friday, 2) Approve Q1 budget, 3) Schedule team retrospective.",
                category=TestCategory.SUMMARY,
                difficulty=TestDifficulty.HARD,
                metadata={"type": "action_items", "timeframe": "yesterday"}
            )
        ]
    
    def _create_urgent_tests(self) -> List[EvaluationTestCase]:
        """Create urgent detection test cases."""
        return [
            EvaluationTestCase(
                id="urgent_001",
                question="What emails need immediate attention?",
                expected_context=["server_down", "client_escalation", "deadline_today"],
                expected_answer="3 urgent emails: Server outage affecting production, client escalation from CEO, and proposal deadline today at 5 PM.",
                category=TestCategory.URGENT,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"priority": "urgent"}
            ),
            EvaluationTestCase(
                id="urgent_002",
                question="Are there any emails marked as high priority that I haven't responded to?",
                expected_context=["high_priority_unanswered_1", "high_priority_unanswered_2"],
                expected_answer="2 high priority emails awaiting response: Budget approval request from CFO and security incident report from IT.",
                category=TestCategory.URGENT,
                difficulty=TestDifficulty.HARD,
                metadata={"priority": "high", "status": "unanswered"}
            ),
            EvaluationTestCase(
                id="urgent_003",
                question="Show me emails with deadlines in the next 24 hours",
                expected_context=["deadline_tomorrow_report", "deadline_tomorrow_presentation"],
                expected_answer="2 deadlines within 24 hours: Quarterly report due tomorrow 9 AM, Board presentation slides due tomorrow 2 PM.",
                category=TestCategory.URGENT,
                difficulty=TestDifficulty.MEDIUM,
                metadata={"deadline": "24_hours"}
            )
        ]
    
    def _create_analysis_tests(self) -> List[EvaluationTestCase]:
        """Create analysis test cases."""
        return [
            EvaluationTestCase(
                id="analysis_001",
                question="Who do I email most frequently about technical issues?",
                expected_context=["tech_sarah_threads", "tech_mike_threads", "tech_team_threads"],
                expected_answer="You most frequently email Sarah Chen (15 threads) about technical issues, followed by Mike Johnson (8 threads).",
                category=TestCategory.ANALYSIS,
                difficulty=TestDifficulty.HARD,
                metadata={"analysis_type": "frequency", "topic": "technical"}
            ),
            EvaluationTestCase(
                id="analysis_002",
                question="What's the sentiment of client emails this month?",
                expected_context=["client_positive_feedback", "client_neutral_inquiry", "client_negative_complaint"],
                expected_answer="Client sentiment this month: 60% positive (satisfaction with service), 30% neutral (general inquiries), 10% negative (delivery delays).",
                category=TestCategory.ANALYSIS,
                difficulty=TestDifficulty.HARD,
                metadata={"analysis_type": "sentiment", "timeframe": "this_month"}
            ),
            EvaluationTestCase(
                id="analysis_003",
                question="What topics are trending in my emails this week?",
                expected_context=["trend_budget", "trend_hiring", "trend_product_launch"],
                expected_answer="Top 3 trending topics this week: 1) Budget planning (12 emails), 2) New hiring (8 emails), 3) Product launch (7 emails).",
                category=TestCategory.ANALYSIS,
                difficulty=TestDifficulty.HARD,
                metadata={"analysis_type": "trends", "timeframe": "this_week"}
            )
        ]
    
    def _create_complex_tests(self) -> List[EvaluationTestCase]:
        """Create complex multi-part query test cases."""
        return [
            EvaluationTestCase(
                id="complex_001",
                question="Find all emails about Project Phoenix, summarize the current status, and identify any blockers mentioned",
                expected_context=["phoenix_kickoff", "phoenix_update_1", "phoenix_blocker_resources", "phoenix_blocker_technical"],
                expected_answer="Project Phoenix: Started 3 weeks ago, currently in development phase. Two blockers: 1) Need 2 more developers, 2) API integration issues with third-party service.",
                category=TestCategory.COMPLEX,
                difficulty=TestDifficulty.HARD,
                metadata={"project": "Phoenix", "query_parts": ["find", "summarize", "identify"]}
            ),
            EvaluationTestCase(
                id="complex_002",
                question="Compare the feedback from our top 3 clients and identify common concerns",
                expected_context=["client1_feedback", "client2_feedback", "client3_feedback"],
                expected_answer="Top 3 clients feedback comparison: Common concerns include 1) Response time for support tickets (all 3 clients), 2) Need for better documentation (2 clients), 3) Request for monthly review calls (2 clients).",
                category=TestCategory.COMPLEX,
                difficulty=TestDifficulty.HARD,
                metadata={"analysis_type": "comparison", "clients": ["client1", "client2", "client3"]}
            ),
            EvaluationTestCase(
                id="complex_003",
                question="What meetings do I have scheduled based on email invites, and which ones conflict?",
                expected_context=["meeting_monday_10am", "meeting_monday_10am_conflict", "meeting_tuesday_2pm"],
                expected_answer="3 meetings scheduled: Monday 10 AM - Budget Review and Product Demo (CONFLICT), Tuesday 2 PM - Team Standup. Recommend rescheduling one Monday meeting.",
                category=TestCategory.COMPLEX,
                difficulty=TestDifficulty.HARD,
                metadata={"type": "scheduling", "conflict_detection": True}
            )
        ]
    
    def get_test_cases_by_category(self, category: TestCategory) -> List[EvaluationTestCase]:
        """Get test cases filtered by category."""
        return [tc for tc in self.test_cases if tc.category == category]
    
    def get_test_cases_by_difficulty(self, difficulty: TestDifficulty) -> List[EvaluationTestCase]:
        """Get test cases filtered by difficulty."""
        return [tc for tc in self.test_cases if tc.difficulty == difficulty]
    
    def get_quick_test_suite(self) -> List[EvaluationTestCase]:
        """Get a quick subset of tests for rapid evaluation."""
        # Return 1 easy, 2 medium, 1 hard test
        quick_suite = []
        quick_suite.extend(self.get_test_cases_by_difficulty(TestDifficulty.EASY)[:1])
        quick_suite.extend(self.get_test_cases_by_difficulty(TestDifficulty.MEDIUM)[:2])
        quick_suite.extend(self.get_test_cases_by_difficulty(TestDifficulty.HARD)[:1])
        return quick_suite
    
    def get_comprehensive_test_suite(self) -> List[EvaluationTestCase]:
        """Get all test cases for comprehensive evaluation."""
        return self.test_cases
    
    def export_test_cases(self, filepath: str):
        """Export test cases to JSON file."""
        data = [tc.to_dict() for tc in self.test_cases]
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Exported {len(data)} test cases to {filepath}")
    
    def import_test_cases(self, filepath: str) -> List[EvaluationTestCase]:
        """Import test cases from JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Test case file not found: {filepath}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        test_cases = []
        for item in data:
            # Convert string enums back to enum types
            item['category'] = TestCategory(item['category'])
            item['difficulty'] = TestDifficulty(item['difficulty'])
            test_cases.append(EvaluationTestCase(**item))
        
        self.test_cases = test_cases
        print(f"Imported {len(test_cases)} test cases from {filepath}")
        return test_cases