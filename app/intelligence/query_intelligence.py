# app/intelligence/query_intelligence.py
"""
Phase 3C: Enhanced Query Intelligence System

Features:
- Intelligent query understanding and enhancement
- Context-aware query expansion
- Intent recognition and categorization
- Semantic query processing
- Smart metadata filtering
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json

class QueryIntent(Enum):
    """Different types of user query intents"""
    SEARCH_SENDER = "search_sender"          # "emails from John"
    SEARCH_TOPIC = "search_topic"            # "meeting emails"
    SEARCH_TIMEFRAME = "search_timeframe"    # "last week's emails"
    SEARCH_URGENT = "search_urgent"          # "important emails"
    SEARCH_CATEGORY = "search_category"      # "payment emails"
    SEARCH_CONTENT = "search_content"        # "project updates"
    SEARCH_ATTACHMENTS = "search_attachments" # "emails with files"
    SEARCH_UNREAD = "search_unread"          # "new emails"
    ASK_SUMMARY = "ask_summary"              # "summarize recent emails"
    ASK_ACTION = "ask_action"                # "what do I need to do"
    ASK_STATUS = "ask_status"                # "any updates on project"
    GENERAL = "general"                      # Fallback

@dataclass
class QueryEnhancement:
    """Enhanced query with extracted intelligence"""
    original_query: str
    enhanced_query: str
    intent: QueryIntent
    confidence: float
    extracted_entities: Dict[str, Any]
    metadata_filters: Dict[str, Any]
    suggested_top_k: int
    context_expansion: str

class QueryIntelligenceEngine:
    """
    Advanced query understanding and enhancement system.
    Transforms user queries into semantically rich, context-aware searches.
    """
    
    def __init__(self):
        # Intent recognition patterns
        self.intent_patterns = {
            QueryIntent.SEARCH_SENDER: [
                r'\b(?:from|by|sent by|emails? from|messages? from)\s+([^,\.\?]+)',
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:sent|emailed|wrote)',
                r'\b(?:who is|what did|has)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'@(\w+)',  # @username mentions
            ],
            QueryIntent.SEARCH_TIMEFRAME: [
                r'\b(?:in the\s+)?(?:last|past|previous)\s+(\d+\s+\w+)',
                r'\b(?:this|today|yesterday|tomorrow)',
                r'\b(?:last|this|next)\s+(?:week|month|year)',
                r'\b(?:since|after|before)\s+([^\s,\.\?]+)',
                r'\b(\d{1,2}\/\d{1,2}|\w+\s+\d{1,2})',  # Dates
            ],
            QueryIntent.SEARCH_URGENT: [
                r'\b(?:urgent|important|critical|priority|deadline)',
                r'\b(?:need(?:s)?\s+(?:immediate|quick|fast))',
                r'\b(?:asap|emergency|critical)',
            ],
            QueryIntent.SEARCH_CATEGORY: [
                r'\b(?:payment|invoice|bill|money|financial)',
                r'\b(?:meeting|appointment|calendar|schedule)',
                r'\b(?:task|todo|action|homework|assignment)',
                r'\b(?:notification|alert|update|news)',
            ],
            QueryIntent.SEARCH_TOPIC: [
                r'\b(?:about|regarding|concerning|related to)\s+([^,\.\?]+)',
                r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*)\s+(?:project|update|report)',
            ],
            QueryIntent.ASK_SUMMARY: [
                r'\b(?:summarize|summary|overview|what\'s new)',
                r'\b(?:catch me up|fill me in|brief me)',
                r'\b(?:recent|latest|new)\s+(?:emails|messages|updates)',
            ],
            QueryIntent.ASK_ACTION: [
                r'\b(?:what do I need|action required|to do|tasks?)',
                r'\b(?:pending|outstanding|waiting|due)',
                r'\b(?:follow up|respond to|reply)',
            ],
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'names': re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'),
            'companies': re.compile(r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*(?:\s+(?:Ltd|Inc|Corp|Company|School|University))?)\b'),
            'dates': re.compile(r'\b(\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|\w+\s+\d{1,2}(?:,?\s+\d{4})?)\b'),
            'amounts': re.compile(r'[£$€¥]?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'),
            'times': re.compile(r'\b(?:1[0-2]|0?[1-9]):[0-5][0-9]\s?(?:AM|PM|am|pm)\b'),
            'emails': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }
        
        # Context enhancement rules
        self.context_rules = {
            'school': ['homework', 'assignment', 'class', 'teacher', 'education', 'study'],
            'work': ['project', 'deadline', 'meeting', 'colleague', 'boss', 'client'],
            'finance': ['payment', 'invoice', 'bill', 'bank', 'money', 'cost'],
            'health': ['appointment', 'doctor', 'medical', 'health', 'clinic'],
            'travel': ['flight', 'hotel', 'trip', 'vacation', 'booking'],
            'shopping': ['order', 'delivery', 'purchase', 'buy', 'sale'],
        }
        
        # Timeframe mappings
        self.timeframe_mapping = {
            'today': 'last 1 days',
            'yesterday': '2 days ago',
            'this week': 'last 7 days',
            'last week': '7 to 14 days ago',
            'this month': 'last 30 days',
            'last month': '30 to 60 days ago',
        }
    
    def analyze_query(self, query: str) -> QueryEnhancement:
        """
        Main entry point: Analyze and enhance a user query
        """
        if not query or not query.strip():
            return self._create_fallback_enhancement(query)
        
        query = query.strip()
        
        # Step 1: Detect query intent
        intent, confidence = self._detect_intent(query)
        
        # Step 2: Extract entities and context
        entities = self._extract_entities(query)
        
        # Step 3: Build metadata filters
        metadata_filters = self._build_metadata_filters(query, entities, intent)
        
        # Step 4: Enhance the query text
        enhanced_query = self._enhance_query_text(query, intent, entities)
        
        # Step 5: Expand with context
        context_expansion = self._expand_context(query, intent, entities)
        
        # Step 6: Suggest optimal retrieval parameters
        suggested_top_k = self._suggest_top_k(intent, entities)
        
        return QueryEnhancement(
            original_query=query,
            enhanced_query=enhanced_query,
            intent=intent,
            confidence=confidence,
            extracted_entities=entities,
            metadata_filters=metadata_filters,
            suggested_top_k=suggested_top_k,
            context_expansion=context_expansion
        )
    
    def _detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Detect the primary intent of the query"""
        query_lower = query.lower()
        best_intent = QueryIntent.GENERAL
        max_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            confidence = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    matches += 1
                    confidence += 0.3  # Base confidence per match
            
            # Boost confidence based on number of matches
            if matches > 0:
                confidence = min(0.9, confidence * matches)
                
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_intent = intent
        
        return best_intent, max_confidence
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract named entities and structured data from query"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(query)
            if matches:
                entities[entity_type] = matches
        
        # Clean up name entities (remove common words)
        if 'names' in entities:
            filtered_names = []
            common_words = {'from', 'to', 'about', 'what', 'when', 'where', 'how', 'the', 'and', 'or'}
            for name in entities['names']:
                if name.lower() not in common_words and len(name) > 2:
                    filtered_names.append(name)
            entities['names'] = filtered_names[:3]  # Limit to top 3
        
        return entities
    
    def _build_metadata_filters(self, query: str, entities: Dict, intent: QueryIntent) -> Dict[str, Any]:
        """Build metadata filters for more targeted search"""
        filters = {}
        
        # Sender filtering
        if intent == QueryIntent.SEARCH_SENDER and 'names' in entities:
            # Use the first name found as primary sender filter
            if entities['names']:
                filters['from_contains'] = entities['names'][0].lower()
        
        # Date range filtering
        if intent == QueryIntent.SEARCH_TIMEFRAME:
            date_filter = self._parse_timeframe(query)
            if date_filter:
                filters.update(date_filter)
        
        # Category filtering
        if intent == QueryIntent.SEARCH_CATEGORY:
            category = self._detect_category(query)
            if category:
                filters['category'] = category
        
        # Urgency filtering
        if intent == QueryIntent.SEARCH_URGENT:
            filters['min_importance'] = 4  # High importance and above
        
        return filters
    
    def _enhance_query_text(self, query: str, intent: QueryIntent, entities: Dict) -> str:
        """Enhance the query text with better search terms"""
        enhanced = query
        
        # Add synonyms and related terms based on intent
        if intent == QueryIntent.SEARCH_CATEGORY:
            enhanced = self._add_category_synonyms(enhanced)
        
        elif intent == QueryIntent.SEARCH_URGENT:
            enhanced += " urgent important critical priority deadline"
        
        elif intent == QueryIntent.ASK_ACTION:
            enhanced += " action required todo task pending response needed"
        
        elif intent == QueryIntent.ASK_SUMMARY:
            enhanced += " update status progress report summary"
        
        # Add context from entities
        if 'names' in entities and entities['names']:
            # Don't repeat names already in query
            for name in entities['names']:
                if name.lower() not in enhanced.lower():
                    enhanced += f" {name}"
        
        return enhanced.strip()
    
    def _expand_context(self, query: str, intent: QueryIntent, entities: Dict) -> str:
        """Expand query with contextual understanding"""
        context_parts = []
        
        # Add context based on detected topics
        query_lower = query.lower()
        for context, keywords in self.context_rules.items():
            if any(keyword in query_lower for keyword in keywords):
                context_parts.append(f"Context: {context}-related communication")
                break
        
        # Add intent-based context
        if intent == QueryIntent.SEARCH_SENDER:
            context_parts.append("Focus: Communications from specific person/organization")
        elif intent == QueryIntent.ASK_ACTION:
            context_parts.append("Focus: Actionable items and tasks requiring response")
        elif intent == QueryIntent.SEARCH_URGENT:
            context_parts.append("Focus: High-priority and time-sensitive communications")
        
        return " | ".join(context_parts)
    
    def _suggest_top_k(self, intent: QueryIntent, entities: Dict) -> int:
        """Suggest optimal number of results based on query type"""
        base_k = 5
        
        if intent == QueryIntent.ASK_SUMMARY:
            return 10  # More results for comprehensive summary
        elif intent == QueryIntent.SEARCH_SENDER:
            return 8   # More results when looking for specific person
        elif intent == QueryIntent.SEARCH_URGENT:
            return 6   # Slightly more for urgent items
        elif intent == QueryIntent.ASK_ACTION:
            return 7   # More for actionable items
        
        return base_k
    
    def _add_category_synonyms(self, query: str) -> str:
        """Add category-specific synonyms to improve search"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['payment', 'invoice', 'bill']):
            query += " money financial cost charge fee payment invoice bill due amount"
        elif any(word in query_lower for word in ['meeting', 'appointment']):
            query += " meeting conference call schedule calendar appointment invite"
        elif any(word in query_lower for word in ['task', 'homework', 'assignment']):
            query += " task todo action homework assignment complete finish submit"
        elif any(word in query_lower for word in ['urgent', 'important']):
            query += " urgent important critical priority deadline asap emergency"
        
        return query
    
    def _parse_timeframe(self, query: str) -> Optional[Dict[str, Any]]:
        """Parse timeframe expressions into date filters"""
        query_lower = query.lower()
        now = datetime.now()
        
        # Check for common timeframes
        for phrase, mapping in self.timeframe_mapping.items():
            if phrase in query_lower:
                if 'last' in mapping:
                    days = int(re.search(r'(\d+)', mapping).group(1))
                    start_date = now - timedelta(days=days)
                    return {
                        'date_after': start_date.strftime('%Y-%m-%d'),
                        'timeframe_description': phrase
                    }
        
        # Parse "last X days/weeks/months"
        match = re.search(r'(?:last|past)\s+(\d+)\s+(day|week|month)s?', query_lower)
        if match:
            number, unit = match.groups()
            number = int(number)
            
            if unit == 'day':
                start_date = now - timedelta(days=number)
            elif unit == 'week':
                start_date = now - timedelta(weeks=number)
            elif unit == 'month':
                start_date = now - timedelta(days=number * 30)  # Approximate
            
            return {
                'date_after': start_date.strftime('%Y-%m-%d'),
                'timeframe_description': f"last {number} {unit}{'s' if number > 1 else ''}"
            }
        
        return None
    
    def _detect_category(self, query: str) -> Optional[str]:
        """Detect email category from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['payment', 'invoice', 'bill', 'money']):
            return 'financial'
        elif any(word in query_lower for word in ['meeting', 'appointment', 'calendar']):
            return 'meeting'  
        elif any(word in query_lower for word in ['task', 'homework', 'assignment']):
            return 'task'
        elif any(word in query_lower for word in ['urgent', 'important', 'critical']):
            return 'urgent'
        
        return None
    
    def _create_fallback_enhancement(self, query: str) -> QueryEnhancement:
        """Create a basic enhancement for unclear queries"""
        return QueryEnhancement(
            original_query=query or "",
            enhanced_query=query or "recent emails",
            intent=QueryIntent.GENERAL,
            confidence=0.1,
            extracted_entities={},
            metadata_filters={},
            suggested_top_k=5,
            context_expansion="General email search"
        )
    
    def format_enhancement_summary(self, enhancement: QueryEnhancement) -> str:
        """Format enhancement details for debugging/display"""
        lines = [
            f"📝 Original: {enhancement.original_query}",
            f"🧠 Enhanced: {enhancement.enhanced_query}",
            f"🎯 Intent: {enhancement.intent.value} ({enhancement.confidence:.1%} confidence)",
            f"📊 Suggested results: {enhancement.suggested_top_k}",
        ]
        
        if enhancement.extracted_entities:
            entities_str = []
            for entity_type, values in enhancement.extracted_entities.items():
                if values:
                    entities_str.append(f"{entity_type}: {', '.join(map(str, values))}")
            if entities_str:
                lines.append(f"🔍 Entities: {' | '.join(entities_str)}")
        
        if enhancement.metadata_filters:
            filters_str = []
            for key, value in enhancement.metadata_filters.items():
                filters_str.append(f"{key}={value}")
            lines.append(f"🎛️ Filters: {', '.join(filters_str)}")
        
        if enhancement.context_expansion:
            lines.append(f"🌐 Context: {enhancement.context_expansion}")
        
        return "\n".join(lines)

# Global instance
query_intelligence = QueryIntelligenceEngine()