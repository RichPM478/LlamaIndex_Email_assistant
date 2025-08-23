"""
Docling Document Processor for Advanced Attachment Extraction

This module provides comprehensive document processing capabilities for email attachments
using Docling's state-of-the-art document extraction technology.

Features:
- Extract text, tables, and images from PDFs, Word, Excel, PowerPoint
- Preserve document structure and formatting
- Handle complex layouts and multi-column documents
- Extract metadata and document properties
- Support for OCR on scanned documents
"""

import os
import io
import tempfile
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
import magic
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ProcessedDocument:
    """Represents a processed document with extracted content and metadata"""
    filename: str
    file_type: str
    content_type: str
    text: str
    tables: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    page_count: int
    word_count: int
    language: str
    extraction_method: str
    processing_time: float
    error: Optional[str] = None
    warnings: List[str] = None

class DoclingProcessor:
    """
    Advanced document processor using Docling for comprehensive content extraction
    """
    
    # Supported document types with their MIME types
    SUPPORTED_TYPES = {
        'application/pdf': ['.pdf'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'application/vnd.ms-excel': ['.xls'],
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
        'application/vnd.ms-powerpoint': ['.ppt'],
        'text/markdown': ['.md'],
        'text/html': ['.html', '.htm'],
        'text/plain': ['.txt'],  # Add plain text support
        'image/png': ['.png'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/tiff': ['.tif', '.tiff']
    }
    
    def __init__(self, 
                 enable_ocr: bool = True,
                 enable_table_extraction: bool = True,
                 enable_image_extraction: bool = False,
                 max_pages: int = 100,
                 language_detection: bool = True):
        """
        Initialize the Docling processor with configuration options
        
        Args:
            enable_ocr: Enable OCR for scanned documents
            enable_table_extraction: Extract tables as structured data
            enable_image_extraction: Extract images from documents
            max_pages: Maximum pages to process per document
            language_detection: Detect document language
        """
        self.enable_ocr = enable_ocr
        self.enable_table_extraction = enable_table_extraction
        self.enable_image_extraction = enable_image_extraction
        self.max_pages = max_pages
        self.language_detection = language_detection
        
        # Initialize Docling converter
        self.converter = DocumentConverter()
        
        # Initialize file type detector
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"Magic library initialization failed: {e}")
            self.magic = None
    
    
    def process_attachment(self, 
                          attachment_data: bytes,
                          filename: str,
                          content_type: Optional[str] = None) -> ProcessedDocument:
        """
        Process a single email attachment using Docling
        
        Args:
            attachment_data: Raw attachment bytes
            filename: Original filename of the attachment
            content_type: MIME type of the attachment
            
        Returns:
            ProcessedDocument with extracted content and metadata
        """
        import time
        start_time = time.time()
        warnings = []
        
        try:
            # Detect file type if not provided
            if not content_type and self.magic:
                try:
                    content_type = self.magic.from_buffer(attachment_data)
                except Exception as e:
                    warnings.append(f"Could not detect file type: {e}")
                    content_type = self._guess_content_type(filename)
            elif not content_type:
                content_type = self._guess_content_type(filename)
            
            # Check if file type is supported
            file_ext = Path(filename).suffix.lower()
            if not self._is_supported(content_type, file_ext):
                return ProcessedDocument(
                    filename=filename,
                    file_type=file_ext,
                    content_type=content_type,
                    text="",
                    tables=[],
                    metadata={},
                    page_count=0,
                    word_count=0,
                    language="unknown",
                    extraction_method="unsupported",
                    processing_time=time.time() - start_time,
                    error=f"Unsupported file type: {content_type}",
                    warnings=warnings
                )
            
            # Process with Docling
            result = self._process_with_docling(attachment_data, filename, content_type)
            
            # Extract content from Docling result
            text = self._extract_text(result)
            tables = self._extract_tables(result)
            metadata = self._extract_metadata(result)
            
            # Detect language if enabled
            language = "unknown"
            if self.language_detection and text:
                language = self._detect_language(text)
            
            # Calculate metrics
            word_count = len(text.split()) if text else 0
            page_count = metadata.get('page_count', 1)
            
            return ProcessedDocument(
                filename=filename,
                file_type=file_ext,
                content_type=content_type,
                text=text,
                tables=tables,
                metadata=metadata,
                page_count=page_count,
                word_count=word_count,
                language=language,
                extraction_method="docling",
                processing_time=time.time() - start_time,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error processing attachment {filename}: {e}")
            return ProcessedDocument(
                filename=filename,
                file_type=Path(filename).suffix.lower(),
                content_type=content_type or "unknown",
                text="",
                tables=[],
                metadata={},
                page_count=0,
                word_count=0,
                language="unknown",
                extraction_method="failed",
                processing_time=time.time() - start_time,
                error=str(e),
                warnings=warnings
            )
    
    def _process_with_docling(self, 
                             data: bytes, 
                             filename: str,
                             content_type: str) -> ConversionResult:
        """Process document with Docling converter"""
        # Create temporary file for Docling processing
        with tempfile.NamedTemporaryFile(
            suffix=Path(filename).suffix,
            delete=False
        ) as tmp_file:
            tmp_file.write(data)
            tmp_path = tmp_file.name
        
        try:
            # Convert document with Docling
            result = self.converter.convert(
                tmp_path,
                max_num_pages=self.max_pages
            )
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    
    def _extract_text(self, result: ConversionResult) -> str:
        """Extract plain text from Docling document"""
        try:
            # Access the document from the result
            if hasattr(result, 'document') and result.document:
                # Try to export as markdown first
                if hasattr(result.document, 'export_to_markdown'):
                    return result.document.export_to_markdown()
                # Fallback to text export
                elif hasattr(result.document, 'export_to_text'):
                    return result.document.export_to_text()
                # Last resort - get text directly
                elif hasattr(result.document, 'text'):
                    return str(result.document.text)
            return ""
        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            return ""
    
    def _extract_tables(self, result: ConversionResult) -> List[Dict[str, Any]]:
        """Extract tables as structured data"""
        tables = []
        
        if not self.enable_table_extraction:
            return tables
        
        try:
            # Extract tables from document
            if hasattr(result.document, 'tables'):
                for table_idx, table in enumerate(result.document.tables):
                    table_data = {
                        'index': table_idx,
                        'headers': [],
                        'rows': [],
                        'caption': None
                    }
                    
                    # Extract table content
                    if hasattr(table, 'to_dict'):
                        table_dict = table.to_dict()
                        table_data['headers'] = table_dict.get('headers', [])
                        table_data['rows'] = table_dict.get('rows', [])
                        table_data['caption'] = table_dict.get('caption')
                    
                    tables.append(table_data)
                
        except Exception as e:
            logger.warning(f"Failed to extract tables: {e}")
        
        return tables
    
    def _extract_metadata(self, result: ConversionResult) -> Dict[str, Any]:
        """Extract document metadata"""
        metadata = {}
        
        try:
            # Get page count from input or pages
            if hasattr(result, 'input') and hasattr(result.input, 'page_count'):
                metadata['page_count'] = result.input.page_count
            elif hasattr(result, 'pages'):
                metadata['page_count'] = len(result.pages)
            else:
                metadata['page_count'] = 1
            
            # Extract document metadata if available
            if hasattr(result.document, 'metadata'):
                meta = result.document.metadata
                if meta:
                    metadata['title'] = getattr(meta, 'title', None)
                    metadata['author'] = getattr(meta, 'author', None)
                    metadata['subject'] = getattr(meta, 'subject', None)
            
            # Add extraction metadata
            metadata['extraction_method'] = 'docling'
            metadata['ocr_used'] = self.enable_ocr
            metadata['tables_extracted'] = self.enable_table_extraction
            metadata['conversion_status'] = str(result.status) if hasattr(result, 'status') else 'unknown'
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        
        return metadata
    
    def _is_supported(self, content_type: str, file_ext: str) -> bool:
        """Check if file type is supported"""
        # Check by MIME type
        if content_type in self.SUPPORTED_TYPES:
            return True
        
        # Check by extension
        for mime, extensions in self.SUPPORTED_TYPES.items():
            if file_ext in extensions:
                return True
        
        return False
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename"""
        ext = Path(filename).suffix.lower()
        
        for mime, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                return mime
        
        return "application/octet-stream"
    
    def _detect_language(self, text: str) -> str:
        """Detect language of text"""
        try:
            import langdetect
            return langdetect.detect(text[:1000])  # Use first 1000 chars
        except Exception:
            return "unknown"
    
    def process_multiple_attachments(self, 
                                    attachments: List[Dict[str, Any]]) -> List[ProcessedDocument]:
        """
        Process multiple attachments in batch
        
        Args:
            attachments: List of attachment dictionaries with 'data', 'filename', 'content_type'
            
        Returns:
            List of ProcessedDocument objects
        """
        results = []
        
        for attachment in attachments:
            result = self.process_attachment(
                attachment_data=attachment.get('data', b''),
                filename=attachment.get('filename', 'unknown'),
                content_type=attachment.get('content_type')
            )
            results.append(result)
        
        return results
    
    def extract_content_for_indexing(self, processed_doc: ProcessedDocument) -> Dict[str, Any]:
        """
        Prepare extracted content for indexing in LlamaIndex
        
        Args:
            processed_doc: ProcessedDocument object
            
        Returns:
            Dictionary ready for indexing
        """
        # Combine text and table content
        full_content = processed_doc.text
        
        # Add table content as structured text
        if processed_doc.tables:
            full_content += "\n\n--- TABLES ---\n"
            for idx, table in enumerate(processed_doc.tables):
                full_content += f"\nTable {idx + 1}:\n"
                if table.get('caption'):
                    full_content += f"Caption: {table['caption']}\n"
                
                # Format table as text
                headers = table.get('headers', [])
                if headers:
                    full_content += " | ".join(headers) + "\n"
                    full_content += "-" * 50 + "\n"
                
                for row in table.get('rows', []):
                    full_content += " | ".join(str(cell) for cell in row) + "\n"
        
        return {
            'content': full_content,
            'filename': processed_doc.filename,
            'file_type': processed_doc.file_type,
            'metadata': {
                **processed_doc.metadata,
                'word_count': processed_doc.word_count,
                'page_count': processed_doc.page_count,
                'language': processed_doc.language,
                'has_tables': len(processed_doc.tables) > 0,
                'table_count': len(processed_doc.tables),
                'extraction_method': processed_doc.extraction_method,
                'processing_time': processed_doc.processing_time
            }
        }

# Create singleton instance
docling_processor = DoclingProcessor()