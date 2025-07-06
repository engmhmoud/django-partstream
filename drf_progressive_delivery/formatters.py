"""
Response formatters for progressive delivery.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class ProgressiveResponseFormatter:
    """
    Formatter for progressive delivery responses.
    
    Provides consistent formatting for response data.
    """
    
    @staticmethod
    def format_response(
        results: List[Dict[str, Any]], 
        cursor: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a progressive delivery response.
        
        Args:
            results: List of result dictionaries
            cursor: Optional cursor for next request
            meta: Optional metadata dictionary
            
        Returns:
            Formatted response dictionary
        """
        response_data = {
            "results": results,
            "cursor": cursor,
            "timestamp": datetime.now().isoformat(),
        }
        
        if meta:
            response_data["meta"] = meta
        
        return response_data
    
    @staticmethod
    def format_error_response(error_message: str, error_code: str = "error") -> Dict[str, Any]:
        """
        Format an error response.
        
        Args:
            error_message: Error message
            error_code: Error code
            
        Returns:
            Formatted error response dictionary
        """
        return {
            "error": {
                "message": error_message,
                "code": error_code,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    @staticmethod
    def format_part(part_name: str, part_data: Any) -> Dict[str, Any]:
        """
        Format a single response part.
        
        Args:
            part_name: Name of the part
            part_data: Data for the part
            
        Returns:
            Formatted part dictionary
        """
        return {part_name: part_data}


class MetaInfoBuilder:
    """
    Builder for metadata information in progressive responses.
    """
    
    def __init__(self):
        self.meta_info = {}
    
    def add_total_count(self, count: int) -> 'MetaInfoBuilder':
        """Add total count to metadata."""
        self.meta_info['total_count'] = count
        return self
    
    def add_page_info(self, current_page: int, total_pages: int) -> 'MetaInfoBuilder':
        """Add pagination info to metadata."""
        self.meta_info['pagination'] = {
            'current_page': current_page,
            'total_pages': total_pages
        }
        return self
    
    def add_timing_info(self, start_time: datetime, end_time: datetime) -> 'MetaInfoBuilder':
        """Add timing info to metadata."""
        duration = (end_time - start_time).total_seconds()
        self.meta_info['timing'] = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration
        }
        return self
    
    def add_custom_info(self, key: str, value: Any) -> 'MetaInfoBuilder':
        """Add custom info to metadata."""
        self.meta_info[key] = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the metadata dictionary."""
        return self.meta_info.copy() 