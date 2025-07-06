"""
Response formatters for progressive delivery.
Provides consistent formatting for response data.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from django.utils import timezone


class ProgressiveResponseFormatter:
    """
    Formatter for progressive delivery responses.

    Provides consistent formatting for response data.
    """

    @staticmethod
    def format_response(
        results: List[Dict[str, Any]],
        cursor: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
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
            "timestamp": timezone.now().isoformat(),
        }

        if meta:
            response_data["meta"] = meta

        return response_data

    @staticmethod
    def format_error_response(
        error_message: str, error_code: str = "error"
    ) -> Dict[str, Any]:
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
                "timestamp": timezone.now().isoformat(),
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

    @staticmethod
    def format_streaming_response(
        results: List[Dict[str, Any]],
        chunk_info: Dict[str, Any],
        cursor: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format a streaming progressive response.

        Args:
            results: List of result dictionaries
            chunk_info: Information about the current chunk
            cursor: Optional cursor for next request
            meta: Optional metadata dictionary

        Returns:
            Formatted streaming response dictionary
        """
        response_data = {
            "results": results,
            "cursor": cursor,
            "chunk_info": chunk_info,
            "timestamp": timezone.now().isoformat(),
        }

        if meta:
            response_data["meta"] = meta

        return response_data


class MetaInfoBuilder:
    """
    Builder for metadata information in progressive responses.
    """

    def __init__(self):
        self.meta_info = {}

    def add_total_count(self, count: int) -> "MetaInfoBuilder":
        """Add total count to metadata."""
        self.meta_info["total_count"] = count
        return self

    def add_page_info(self, current_page: int, total_pages: int) -> "MetaInfoBuilder":
        """Add pagination info to metadata."""
        self.meta_info["pagination"] = {
            "current_page": current_page,
            "total_pages": total_pages,
        }
        return self

    def add_chunk_info(
        self, chunk_index: int, chunk_size: int, total_chunks: int
    ) -> "MetaInfoBuilder":
        """Add chunk information to metadata."""
        self.meta_info["chunk_info"] = {
            "chunk_index": chunk_index,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
        }
        return self

    def add_timing_info(
        self, start_time: datetime, end_time: datetime
    ) -> "MetaInfoBuilder":
        """Add timing info to metadata."""
        duration = (end_time - start_time).total_seconds()
        self.meta_info["timing"] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
        }
        return self

    def add_performance_info(
        self, query_count: int = None, cache_hits: int = None
    ) -> "MetaInfoBuilder":
        """Add performance info to metadata."""
        perf_info = {}
        if query_count is not None:
            perf_info["query_count"] = query_count
        if cache_hits is not None:
            perf_info["cache_hits"] = cache_hits

        if perf_info:
            self.meta_info["performance"] = perf_info

        return self

    def add_user_info(
        self, user_id: int = None, user_type: str = None
    ) -> "MetaInfoBuilder":
        """Add user info to metadata."""
        user_info = {}
        if user_id is not None:
            user_info["user_id"] = user_id
        if user_type is not None:
            user_info["user_type"] = user_type

        if user_info:
            self.meta_info["user"] = user_info

        return self

    def add_custom_info(self, key: str, value: Any) -> "MetaInfoBuilder":
        """Add custom info to metadata."""
        self.meta_info[key] = value
        return self

    def build(self) -> Dict[str, Any]:
        """Build the metadata dictionary."""
        return self.meta_info.copy()


class ChunkInfoBuilder:
    """
    Builder for chunk information in progressive responses.
    """

    def __init__(self):
        self.chunk_info = {}

    def set_current_chunk(
        self, chunk_index: int, chunk_size: int
    ) -> "ChunkInfoBuilder":
        """Set current chunk information."""
        self.chunk_info["current_chunk"] = chunk_index
        self.chunk_info["chunk_size"] = chunk_size
        return self

    def set_total_info(self, total_items: int, total_chunks: int) -> "ChunkInfoBuilder":
        """Set total information."""
        self.chunk_info["total_items"] = total_items
        self.chunk_info["total_chunks"] = total_chunks
        return self

    def set_progress(
        self, items_loaded: int, items_remaining: int
    ) -> "ChunkInfoBuilder":
        """Set progress information."""
        self.chunk_info["items_loaded"] = items_loaded
        self.chunk_info["items_remaining"] = items_remaining
        if items_loaded + items_remaining > 0:
            self.chunk_info["progress_percent"] = (
                items_loaded / (items_loaded + items_remaining)
            ) * 100
        return self

    def set_has_more(self, has_more: bool) -> "ChunkInfoBuilder":
        """Set whether there are more chunks."""
        self.chunk_info["has_more"] = has_more
        return self

    def build(self) -> Dict[str, Any]:
        """Build the chunk info dictionary."""
        return self.chunk_info.copy()


class ResponseBuilder:
    """
    Comprehensive response builder for progressive delivery.
    """

    def __init__(self):
        self.results = []
        self.cursor = None
        self.meta = None
        self.chunk_info = None
        self.error_info = None
        self.formatter = ProgressiveResponseFormatter()

    def add_result(self, part_name: str, part_data: Any) -> "ResponseBuilder":
        """Add a result part."""
        self.results.append({part_name: part_data})
        return self

    def add_results(self, results: List[Dict[str, Any]]) -> "ResponseBuilder":
        """Add multiple results."""
        self.results.extend(results)
        return self

    def set_cursor(self, cursor: str) -> "ResponseBuilder":
        """Set the cursor for next request."""
        self.cursor = cursor
        return self

    def set_meta(self, meta: Dict[str, Any]) -> "ResponseBuilder":
        """Set metadata."""
        self.meta = meta
        return self

    def set_chunk_info(self, chunk_info: Dict[str, Any]) -> "ResponseBuilder":
        """Set chunk information."""
        self.chunk_info = chunk_info
        return self

    def set_error(
        self, error_message: str, error_code: str = "error"
    ) -> "ResponseBuilder":
        """Set error information."""
        self.error_info = {
            "message": error_message,
            "code": error_code,
            "timestamp": timezone.now().isoformat(),
        }
        return self

    def build(self) -> Dict[str, Any]:
        """Build the final response."""
        if self.error_info:
            return {"error": self.error_info}

        response_data = {
            "results": self.results,
            "cursor": self.cursor,
            "timestamp": timezone.now().isoformat(),
        }

        if self.meta:
            response_data["meta"] = self.meta

        if self.chunk_info:
            response_data["chunk_info"] = self.chunk_info

        return response_data

    def build_streaming(self) -> Dict[str, Any]:
        """Build a streaming response."""
        if self.error_info:
            return {"error": self.error_info}

        return self.formatter.format_streaming_response(
            self.results, self.chunk_info or {}, self.cursor, self.meta
        )


# Utility functions for quick formatting
def format_success_response(
    results: List[Dict[str, Any]], cursor: str = None, **meta_kwargs
) -> Dict[str, Any]:
    """
    Quick function to format a successful response.

    Args:
        results: List of result dictionaries
        cursor: Optional cursor for next request
        **meta_kwargs: Additional metadata

    Returns:
        Formatted response dictionary
    """
    meta = meta_kwargs if meta_kwargs else None
    return ProgressiveResponseFormatter.format_response(results, cursor, meta)


def format_error_response(
    error_message: str, error_code: str = "error"
) -> Dict[str, Any]:
    """
    Quick function to format an error response.

    Args:
        error_message: Error message
        error_code: Error code

    Returns:
        Formatted error response dictionary
    """
    return ProgressiveResponseFormatter.format_error_response(error_message, error_code)


def build_meta_info(**kwargs) -> Dict[str, Any]:
    """
    Quick function to build metadata.

    Args:
        **kwargs: Metadata key-value pairs

    Returns:
        Metadata dictionary
    """
    builder = MetaInfoBuilder()
    for key, value in kwargs.items():
        builder.add_custom_info(key, value)
    return builder.build()


def build_chunk_info(
    chunk_index: int, chunk_size: int, total_items: int, has_more: bool
) -> Dict[str, Any]:
    """
    Quick function to build chunk information.

    Args:
        chunk_index: Current chunk index
        chunk_size: Size of current chunk
        total_items: Total number of items
        has_more: Whether there are more chunks

    Returns:
        Chunk info dictionary
    """
    total_chunks = (total_items + chunk_size - 1) // chunk_size  # Ceiling division

    return (
        ChunkInfoBuilder()
        .set_current_chunk(chunk_index, chunk_size)
        .set_total_info(total_items, total_chunks)
        .set_has_more(has_more)
        .build()
    )
