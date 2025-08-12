"""
Smart Email Chunking Strategy
Preserves logical boundaries and conversation context
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import tiktoken


@dataclass
class EmailChunk:
    """Represents a logical chunk of email content"""
    text: str
    chunk_type: str  # 'greeting', 'body', 'signature', 'quote', 'paragraph'
    chunk_index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "chunk_type": self.chunk_type,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "token_count": self.token_count,
            "metadata": self.metadata
        }


class SmartEmailChunker:
    """
    Intelligent email chunking that preserves context and logical boundaries
    """
    
    def __init__(self, 
                 min_chunk_size: int = 50,  # Reduced for better granularity
                 max_chunk_size: int = 384,  # Optimized for 512 token embeddings
                 overlap_size: int = 30,  # Reduced overlap for efficiency
                 preserve_paragraphs: bool = True,
                 preserve_sentences: bool = True):  # New: sentence boundary awareness
        """
        Initialize smart chunker
        
        Args:
            min_chunk_size: Minimum tokens per chunk
            max_chunk_size: Maximum tokens per chunk  
            overlap_size: Token overlap between chunks
            preserve_paragraphs: Try to keep paragraphs together
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.preserve_paragraphs = preserve_paragraphs
        self.preserve_sentences = preserve_sentences
        
        # Initialize tokenizer (using cl100k_base for GPT-3.5/4)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            # Fallback to approximate token counting
            self.tokenizer = None
    
    def chunk_email(self, 
                   email_content: Dict[str, str],
                   metadata: Dict[str, Any]) -> List[EmailChunk]:
        """
        Chunk email content intelligently
        
        Args:
            email_content: Dict with keys like 'main_content', 'greeting', 'signature', etc.
            metadata: Email metadata to attach to chunks
            
        Returns:
            List of EmailChunk objects
        """
        chunks = []
        
        # 1. Handle greeting as separate chunk if significant
        if email_content.get('greeting') and len(email_content['greeting']) > 20:
            chunks.append(self._create_chunk(
                email_content['greeting'],
                'greeting',
                0,
                metadata
            ))
        
        # 2. Chunk main content
        main_content = email_content.get('main_content', '')
        if main_content:
            content_chunks = self._chunk_main_content(main_content, metadata)
            chunks.extend(content_chunks)
        
        # 3. Handle signature as separate chunk if significant
        if email_content.get('signature') and len(email_content['signature']) > 30:
            chunks.append(self._create_chunk(
                email_content['signature'],
                'signature',
                len(chunks),
                metadata
            ))
        
        # 4. Handle quoted text separately (if not too long)
        quoted_text = email_content.get('quoted_text', '')
        if quoted_text and len(quoted_text) < 2000:
            # Chunk quoted text with sentence awareness
            quote_chunks = self._chunk_text(
                quoted_text,
                max_size=self.max_chunk_size // 2,
                chunk_type='quote',
                preserve_sentences=self.preserve_sentences
            )
            for chunk_text in quote_chunks:
                chunks.append(self._create_chunk(
                    chunk_text,
                    'quote',
                    len(chunks),
                    metadata
                ))
        
        # Update total chunks count
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks
        
        # If no chunks were created, create at least one
        if not chunks and email_content.get('cleaned_full_text'):
            chunks.append(self._create_chunk(
                email_content['cleaned_full_text'][:self.max_chunk_size * 4],  # Approximate
                'body',
                0,
                metadata
            ))
            chunks[0].total_chunks = 1
        
        return chunks
    
    def _chunk_main_content(self, 
                           content: str,
                           metadata: Dict[str, Any]) -> List[EmailChunk]:
        """Chunk main email content preserving paragraph boundaries"""
        chunks = []
        
        if self.preserve_paragraphs:
            # Split by paragraphs
            paragraphs = self._split_into_paragraphs(content)
            
            current_chunk = []
            current_tokens = 0
            
            for para in paragraphs:
                para_tokens = self._count_tokens(para)
                
                # If single paragraph is too large, split it
                if para_tokens > self.max_chunk_size:
                    # Save current chunk if any
                    if current_chunk:
                        chunk_text = '\n\n'.join(current_chunk)
                        chunks.append(self._create_chunk(
                            chunk_text,
                            'paragraph',
                            len(chunks),
                            metadata
                        ))
                        current_chunk = []
                        current_tokens = 0
                    
                    # Split large paragraph
                    para_chunks = self._chunk_text(para, self.max_chunk_size)
                    for pc in para_chunks:
                        chunks.append(self._create_chunk(
                            pc,
                            'body',
                            len(chunks),
                            metadata
                        ))
                
                # If adding this paragraph would exceed limit, start new chunk
                elif current_tokens + para_tokens > self.max_chunk_size:
                    # Save current chunk
                    if current_chunk:
                        chunk_text = '\n\n'.join(current_chunk)
                        chunks.append(self._create_chunk(
                            chunk_text,
                            'paragraph',
                            len(chunks),
                            metadata
                        ))
                    
                    # Start new chunk with overlap
                    if self.overlap_size > 0 and current_chunk:
                        # Include last paragraph as overlap
                        current_chunk = [current_chunk[-1], para]
                        current_tokens = self._count_tokens('\n\n'.join(current_chunk))
                    else:
                        current_chunk = [para]
                        current_tokens = para_tokens
                
                else:
                    # Add to current chunk
                    current_chunk.append(para)
                    current_tokens += para_tokens
            
            # Don't forget last chunk
            if current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text,
                    'paragraph',
                    len(chunks),
                    metadata
                ))
        
        else:
            # Simple chunking without paragraph preservation
            text_chunks = self._chunk_text(content, self.max_chunk_size)
            for chunk_text in text_chunks:
                chunks.append(self._create_chunk(
                    chunk_text,
                    'body',
                    len(chunks),
                    metadata
                ))
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Clean and filter
        clean_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Minimum paragraph length
                clean_paragraphs.append(para)
        
        # If no paragraphs found, split by sentences
        if not clean_paragraphs:
            sentences = self._split_into_sentences(text)
            # Group sentences into pseudo-paragraphs
            current_para = []
            for sent in sentences:
                current_para.append(sent)
                if len(' '.join(current_para)) > 200:  # Approximate paragraph size
                    clean_paragraphs.append(' '.join(current_para))
                    current_para = []
            if current_para:
                clean_paragraphs.append(' '.join(current_para))
        
        return clean_paragraphs
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be improved with NLTK if available)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _chunk_text(self, 
                   text: str,
                   max_size: int,
                   chunk_type: str = 'body',
                   preserve_sentences: bool = True) -> List[str]:
        """
        Simple text chunking by token count
        """
        if not text:
            return []
        
        tokens = self._count_tokens(text)
        
        if tokens <= max_size:
            return [text]
        
        # Split with sentence awareness if enabled
        if preserve_sentences and self.preserve_sentences:
            sentences = self._split_into_sentences(text)
            chunks = []
            current_chunk = []
            current_tokens = 0
            
            for sent in sentences:
                sent_tokens = self._count_tokens(sent)
                
                # If single sentence is too large, split by words
                if sent_tokens > max_size:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_tokens = 0
                    
                    # Split large sentence
                    words = sent.split()
                    word_chunk = []
                    word_tokens = 0
                    
                    for word in words:
                        wt = self._count_tokens(word)
                        if word_tokens + wt > max_size:
                            if word_chunk:
                                chunks.append(' '.join(word_chunk))
                            word_chunk = [word]
                            word_tokens = wt
                        else:
                            word_chunk.append(word)
                            word_tokens += wt
                    
                    if word_chunk:
                        chunks.append(' '.join(word_chunk))
                
                elif current_tokens + sent_tokens > max_size:
                    # Save current chunk
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    
                    # Start new chunk with overlap
                    if self.overlap_size > 0 and current_chunk:
                        # Use last sentence as overlap
                        current_chunk = [current_chunk[-1], sent] if len(current_chunk) > 0 else [sent]
                        current_tokens = self._count_tokens(' '.join(current_chunk))
                    else:
                        current_chunk = [sent]
                        current_tokens = sent_tokens
                else:
                    current_chunk.append(sent)
                    current_tokens += sent_tokens
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
        
        else:
            # Original word-based splitting
            chunks = []
            words = text.split()
            current_chunk = []
            current_tokens = 0
            
            for word in words:
                word_tokens = self._count_tokens(word)
                
                if current_tokens + word_tokens > max_size:
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    
                    # Start new chunk with overlap
                    if self.overlap_size > 0 and len(current_chunk) > 10:
                        # Include last few words as overlap
                        overlap_words = current_chunk[-10:]
                        current_chunk = overlap_words + [word]
                        current_tokens = self._count_tokens(' '.join(current_chunk))
                    else:
                        current_chunk = [word]
                        current_tokens = word_tokens
                else:
                    current_chunk.append(word)
                    current_tokens += word_tokens
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _create_chunk(self,
                     text: str,
                     chunk_type: str,
                     index: int,
                     metadata: Dict[str, Any]) -> EmailChunk:
        """Create an EmailChunk object"""
        return EmailChunk(
            text=text,
            chunk_type=chunk_type,
            chunk_index=index,
            total_chunks=0,  # Will be updated later
            token_count=self._count_tokens(text),
            metadata=metadata.copy()
        )
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Approximate: 1 token ≈ 4 characters
            return len(text) // 4
    
    def create_searchable_chunks(self,
                                email_doc: Any,
                                include_metadata_context: bool = True) -> List[Dict[str, Any]]:
        """
        Create chunks optimized for search with optional metadata context
        
        Args:
            email_doc: EmailDocument object
            include_metadata_context: Whether to prepend metadata to chunks
            
        Returns:
            List of chunk dictionaries ready for indexing
        """
        # Extract content sections
        content_dict = {
            'greeting': email_doc.content.greeting,
            'main_content': email_doc.content.main_content,
            'signature': email_doc.content.signature,
            'quoted_text': email_doc.content.quoted_text,
            'cleaned_full_text': email_doc.content.cleaned_full_text
        }
        
        # Create metadata dict
        metadata = email_doc.metadata.to_dict()
        metadata['quality_score'] = email_doc.quality_score
        metadata['marketing_score'] = email_doc.marketing_score
        metadata['importance_score'] = email_doc.importance_score
        
        # Chunk the email
        chunks = self.chunk_email(content_dict, metadata)
        
        # Convert to searchable format
        searchable_chunks = []
        
        for chunk in chunks:
            # Optionally prepend metadata context for better search
            if include_metadata_context and chunk.chunk_type in ['body', 'paragraph']:
                context = f"From: {metadata.get('from_address', {}).get('name', 'Unknown')}\n"
                context += f"Subject: {metadata.get('subject', 'No Subject')}\n"
                context += f"Date: {metadata.get('date', 'Unknown')}\n\n"
                chunk_text = context + chunk.text
            else:
                chunk_text = chunk.text
            
            searchable_chunk = {
                'text': chunk_text,
                'chunk_type': chunk.chunk_type,
                'chunk_index': chunk.chunk_index,
                'total_chunks': chunk.total_chunks,
                'token_count': chunk.token_count,
                'metadata': chunk.metadata
            }
            
            searchable_chunks.append(searchable_chunk)
        
        return searchable_chunks