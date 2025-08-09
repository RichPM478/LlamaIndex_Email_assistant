# app/qa/intelligent_query.py
"""
Intelligent Query Engine with Phase 3C Enhancements

Integrates query intelligence with the existing lazy query engine
for context-aware, intent-driven email search.
"""

from typing import Dict, Any, List, Optional
import time
from app.qa.lazy_query import LazyEmailQueryEngine, QueryStrategy
from app.intelligence.query_intelligence import query_intelligence, QueryIntent

class IntelligentEmailQueryEngine(LazyEmailQueryEngine):
    """
    Enhanced query engine with intelligent query processing.
    Builds on the lazy query engine with Phase 3C intelligence features.
    """
    
    def __init__(self, strategy: QueryStrategy = QueryStrategy.OPTIMIZED, persist_dir: str = "data/index"):
        super().__init__(strategy, persist_dir)
        self.query_intelligence = query_intelligence
        self._debug_mode = False
    
    def set_debug_mode(self, enabled: bool):
        """Enable/disable debug output for query intelligence"""
        self._debug_mode = enabled
    
    def intelligent_query(self, question: str, top_k: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Main intelligent query method with Phase 3C enhancements
        """
        start_time = time.time()
        
        # Step 1: Analyze and enhance the query
        enhancement = self.query_intelligence.analyze_query(question)
        
        if self._debug_mode:
            print("\n" + "="*60)
            print("🧠 QUERY INTELLIGENCE DEBUG")
            print("="*60)
            print(self.query_intelligence.format_enhancement_summary(enhancement))
            print("="*60)
        
        # Step 2: Use enhanced query and parameters
        enhanced_question = enhancement.enhanced_query
        optimal_top_k = enhancement.suggested_top_k
        
        # Override top_k if enhancement suggests better value
        if optimal_top_k > top_k:
            top_k = optimal_top_k
        
        # Step 3: Apply intelligent metadata filtering
        if enhancement.metadata_filters:
            kwargs.update(enhancement.metadata_filters)
        
        # Step 4: Execute enhanced query
        if enhancement.intent == QueryIntent.SEARCH_SENDER:
            result = self._sender_focused_query(enhanced_question, enhancement, top_k, **kwargs)
        elif enhancement.intent == QueryIntent.ASK_SUMMARY:
            result = self._summary_focused_query(enhanced_question, enhancement, top_k, **kwargs)
        elif enhancement.intent == QueryIntent.ASK_ACTION:
            result = self._action_focused_query(enhanced_question, enhancement, top_k, **kwargs)
        elif enhancement.intent == QueryIntent.SEARCH_URGENT:
            result = self._urgency_focused_query(enhanced_question, enhancement, top_k, **kwargs)
        else:
            result = self._general_enhanced_query(enhanced_question, enhancement, top_k, **kwargs)
        
        # Step 5: Enhance the response with intelligence metadata
        result['query_intelligence'] = {
            'original_query': enhancement.original_query,
            'enhanced_query': enhancement.enhanced_query,
            'intent': enhancement.intent.value,
            'confidence': enhancement.confidence,
            'extracted_entities': enhancement.extracted_entities,
            'context': enhancement.context_expansion,
            'processing_time': time.time() - start_time
        }
        
        return result
    
    def _sender_focused_query(self, question: str, enhancement, top_k: int, **kwargs) -> Dict[str, Any]:
        """Enhanced query for sender-focused searches"""
        # Increase search scope for sender filtering
        search_k = min(top_k * 3, 25)
        
        result = self._optimized_query(question, search_k, **kwargs)
        
        # Post-process to prioritize sender matches
        if enhancement.extracted_entities.get('names'):
            target_names = [name.lower() for name in enhancement.extracted_entities['names']]
            
            # Re-rank results by sender relevance
            citations = result.get('citations', [])
            sender_matches = []
            other_matches = []
            
            for citation in citations:
                sender = citation.get('from', '').lower()
                if any(name in sender for name in target_names):
                    sender_matches.append(citation)
                else:
                    other_matches.append(citation)
            
            # Prioritize sender matches
            result['citations'] = sender_matches + other_matches[:top_k - len(sender_matches)]
            result['citations'] = result['citations'][:top_k]
        
        return result
    
    def _summary_focused_query(self, question: str, enhancement, top_k: int, **kwargs) -> Dict[str, Any]:
        """Enhanced query for summary requests"""
        # Get more results for comprehensive summary
        search_k = min(top_k * 2, 20)
        
        result = self._optimized_query(question, search_k, **kwargs)
        
        # Enhance response for better summarization
        if result.get('citations'):
            # Group by sender for better summary structure
            sender_groups = {}
            for citation in result['citations']:
                sender = citation.get('from', 'Unknown')
                if sender not in sender_groups:
                    sender_groups[sender] = []
                sender_groups[sender].append(citation)
            
            result['sender_breakdown'] = {
                sender: len(citations) for sender, citations in sender_groups.items()
            }
        
        return result
    
    def _action_focused_query(self, question: str, enhancement, top_k: int, **kwargs) -> Dict[str, Any]:
        """Enhanced query for action item searches"""
        # Add action-oriented terms
        action_terms = " todo action required respond reply follow up complete finish submit"
        enhanced_question = question + action_terms
        
        result = self._optimized_query(enhanced_question, top_k, **kwargs)
        
        # Post-process to highlight action items
        if result.get('citations'):
            action_keywords = ['please', 'need', 'required', 'asap', 'deadline', 'due', 'complete', 'respond']
            
            for citation in result['citations']:
                snippet = citation.get('snippet', '').lower()
                action_score = sum(1 for keyword in action_keywords if keyword in snippet)
                citation['action_score'] = action_score
            
            # Sort by action relevance
            result['citations'].sort(key=lambda x: x.get('action_score', 0), reverse=True)
        
        return result
    
    def _urgency_focused_query(self, question: str, enhancement, top_k: int, **kwargs) -> Dict[str, Any]:
        """Enhanced query for urgent/important searches"""
        # Add urgency terms
        urgency_terms = " urgent important critical deadline asap emergency priority"
        enhanced_question = question + urgency_terms
        
        result = self._optimized_query(enhanced_question, top_k, **kwargs)
        
        # Post-process to highlight urgency indicators
        if result.get('citations'):
            urgency_keywords = ['urgent', 'asap', 'critical', 'deadline', 'emergency', 'important', 'priority']
            
            for citation in result['citations']:
                snippet = citation.get('snippet', '').lower()
                subject = citation.get('subject', '').lower()
                
                urgency_score = 0
                urgency_score += sum(2 for keyword in urgency_keywords if keyword in subject)  # Subject carries more weight
                urgency_score += sum(1 for keyword in urgency_keywords if keyword in snippet)
                
                citation['urgency_score'] = urgency_score
                
                # Add urgency indicators
                found_indicators = [kw for kw in urgency_keywords if kw in (subject + ' ' + snippet)]
                citation['urgency_indicators'] = found_indicators
            
            # Sort by urgency relevance
            result['citations'].sort(key=lambda x: x.get('urgency_score', 0), reverse=True)
        
        return result
    
    def _general_enhanced_query(self, question: str, enhancement, top_k: int, **kwargs) -> Dict[str, Any]:
        """Enhanced general query with intelligence improvements"""
        result = self._optimized_query(question, top_k, **kwargs)
        
        # Add entity highlighting if available
        if enhancement.extracted_entities:
            entities = enhancement.extracted_entities
            
            # Highlight entities in citations
            if result.get('citations'):
                for citation in result['citations']:
                    highlighted_entities = []
                    
                    snippet = citation.get('snippet', '')
                    subject = citation.get('subject', '')
                    text = snippet + ' ' + subject
                    
                    # Check for entity matches
                    for entity_type, entity_values in entities.items():
                        for value in entity_values:
                            if str(value).lower() in text.lower():
                                highlighted_entities.append({
                                    'type': entity_type,
                                    'value': value
                                })
                    
                    citation['highlighted_entities'] = highlighted_entities
        
        return result

# Convenience function for easy migration from lazy query
def intelligent_ask(question: str, top_k: int = 5, debug: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Drop-in replacement for lazy_optimized_ask with intelligence enhancements
    """
    engine = IntelligentEmailQueryEngine()
    engine.set_debug_mode(debug)
    return engine.intelligent_query(question, top_k, **kwargs)