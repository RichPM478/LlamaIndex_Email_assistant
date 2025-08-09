# app/sync/__init__.py
"""
Email Sync Module - Phase 3B
Real-time email synchronization with quality filtering
"""

from .live_sync import LiveEmailSync, get_sync_engine, SyncStatus

__all__ = ['LiveEmailSync', 'get_sync_engine', 'SyncStatus']