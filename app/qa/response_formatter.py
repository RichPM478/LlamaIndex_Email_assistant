# app/qa/response_formatter.py
"""
Enhanced response formatting for ChatGPT/Claude-like summaries
"""

from typing import Dict, Any, List
import re


class ResponseFormatter:
    """Format query responses into structured, readable summaries"""
    
    @staticmethod
    def format_response(raw_response: str, citations: List[Dict[str, Any]], query: str) -> str:
        """
        Format raw response into a structured summary
        
        Args:
            raw_response: Raw text response from query engine
            citations: List of source citations
            query: Original user query
            
        Returns:
            Formatted markdown response
        """
        # Detect query type and format accordingly
        if any(word in query.lower() for word in ['summarize', 'summary', 'latest', 'recent', 'news']):
            return ResponseFormatter._format_summary_response(raw_response, citations)
        elif any(word in query.lower() for word in ['list', 'what are', 'show me']):
            return ResponseFormatter._format_list_response(raw_response, citations)
        elif any(word in query.lower() for word in ['explain', 'how', 'why', 'what is']):
            return ResponseFormatter._format_explanation_response(raw_response, citations)
        else:
            return ResponseFormatter._format_general_response(raw_response, citations)
    
    @staticmethod
    def _format_summary_response(text: str, citations: List[Dict[str, Any]]) -> str:
        """Format as a news/summary style response"""
        
        # Try to extract key points from the text
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        
        # Group related content
        ai_topics = []
        business_topics = []
        tech_topics = []
        other_topics = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in ['ai', 'artificial intelligence', 'machine learning', 'llm', 'gpt', 'generative']):
                ai_topics.append(sentence)
            elif any(word in sentence_lower for word in ['business', 'company', 'enterprise', 'startup']):
                business_topics.append(sentence)
            elif any(word in sentence_lower for word in ['software', 'programming', 'development', 'technology']):
                tech_topics.append(sentence)
            else:
                other_topics.append(sentence)
        
        # Build formatted response
        formatted = "## 📊 AI News Summary\n\n"
        
        if ai_topics:
            formatted += "### 🤖 AI Developments\n"
            for topic in ai_topics[:3]:  # Limit to top 3
                formatted += f"• {topic}\n"
            formatted += "\n"
        
        if business_topics:
            formatted += "### 💼 Business & Industry\n"
            for topic in business_topics[:3]:
                formatted += f"• {topic}\n"
            formatted += "\n"
        
        if tech_topics:
            formatted += "### 💻 Technology Updates\n"
            for topic in tech_topics[:3]:
                formatted += f"• {topic}\n"
            formatted += "\n"
        
        if other_topics and len(other_topics) > 0:
            formatted += "### 📌 Additional Highlights\n"
            for topic in other_topics[:2]:
                formatted += f"• {topic}\n"
            formatted += "\n"
        
        # Add source information if available
        if citations:
            formatted += "---\n"
            formatted += f"*Based on {len(citations)} relevant emails"
            
            # Get date range if available
            dates = [c.get('date') for c in citations if c.get('date')]
            if dates:
                formatted += f" from the past week*"
            else:
                formatted += "*"
        
        return formatted
    
    @staticmethod
    def _format_list_response(text: str, citations: List[Dict[str, Any]]) -> str:
        """Format as a structured list"""
        
        # Extract potential list items
        lines = text.split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if line and not line.endswith(':'):
                # Clean up line
                line = line.lstrip('•-*123456789. ')
                if line:
                    items.append(line)
        
        formatted = "## 📋 Results\n\n"
        
        if items:
            for i, item in enumerate(items[:10], 1):  # Limit to 10 items
                formatted += f"{i}. {item}\n"
        else:
            # Fallback to original text
            formatted += text
        
        if citations:
            formatted += f"\n---\n*Found in {len(citations)} emails*"
        
        return formatted
    
    @staticmethod
    def _format_explanation_response(text: str, citations: List[Dict[str, Any]]) -> str:
        """Format as an explanation with clear structure"""
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        formatted = "## 💡 Explanation\n\n"
        
        if paragraphs:
            # First paragraph as overview
            formatted += f"**Overview:** {paragraphs[0]}\n\n"
            
            # Remaining as details
            if len(paragraphs) > 1:
                formatted += "**Details:**\n"
                for para in paragraphs[1:4]:  # Limit to 3 additional paragraphs
                    formatted += f"\n{para}\n"
        else:
            formatted += text
        
        if citations:
            formatted += f"\n---\n*Source: {len(citations)} relevant emails*"
        
        return formatted
    
    @staticmethod
    def _format_general_response(text: str, citations: List[Dict[str, Any]]) -> str:
        """Format as a general structured response"""
        
        # Clean up the text
        text = text.strip()
        
        # If text is very short, just return it
        if len(text) < 100:
            return text
        
        # Split into sentences for better formatting
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        
        formatted = ""
        
        # Group sentences into paragraphs (3-4 sentences each)
        current_para = []
        for sentence in sentences:
            current_para.append(sentence)
            if len(current_para) >= 3:
                formatted += ' '.join(current_para) + "\n\n"
                current_para = []
        
        # Add remaining sentences
        if current_para:
            formatted += ' '.join(current_para)
        
        if citations:
            formatted += f"\n\n---\n*Based on {len(citations)} sources*"
        
        return formatted
    
    @staticmethod
    def format_citations(citations: List[Dict[str, Any]]) -> str:
        """Format citations as a clean reference list"""
        
        if not citations:
            return ""
        
        formatted = "\n\n### 📚 Sources\n"
        
        for i, cite in enumerate(citations[:5], 1):  # Show top 5 sources
            from_name = cite.get('from', 'Unknown Sender')
            subject = cite.get('subject', 'No Subject')
            date = cite.get('date', '')
            
            # Clean up sender name
            if '@' in from_name:
                from_name = from_name.split('<')[0].strip()
            
            # Truncate long subjects
            if len(subject) > 60:
                subject = subject[:57] + "..."
            
            formatted += f"\n{i}. **{from_name}**"
            if date:
                formatted += f" ({date})"
            formatted += f"\n   _{subject}_\n"
        
        return formatted