#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Session management module for MatSimPy CLI
"""

from datetime import datetime
from typing import Dict, Optional


class Session:
    """Session management class for MatSimPy CLI"""

    def __init__(
        self,
        start_time: datetime,
        command_count: int = 0,
        last_accessed: Optional[Dict[str, datetime]] = None,
    ):
        """
        Initialize a new session

        Args:
            start_time: Session start time
            command_count: Number of commands executed
            last_accessed: Dictionary of last accessed times for menu items
        """
        self.start_time = start_time
        self.command_count = command_count
        self.last_accessed = last_accessed or {}

    def increment_command_count(self) -> None:
        """Increment the command counter"""
        self.command_count += 1

    def get_session_duration(self) -> str:
        """Get the duration of the current session"""
        duration = datetime.now() - self.start_time
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)
        return f"{minutes}m {seconds}s"

    def update_last_accessed(self, item_code: str) -> None:
        """
        Update the last accessed time for a menu item

        Args:
            item_code: Code of the menu item
        """
        self.last_accessed[item_code] = datetime.now()

    def get_last_accessed(self, item_code: str) -> Optional[datetime]:
        """
        Get the last accessed time for a menu item

        Args:
            item_code: Code of the menu item

        Returns:
            Last accessed time or None if never accessed
        """
        return self.last_accessed.get(item_code)
