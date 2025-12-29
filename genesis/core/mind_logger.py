"""Mind-specific logging system for tracking consciousness activities."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from genesis.config import get_settings


class LogLevel(str, Enum):
    """Log levels for mind activities."""
    DEBUG = "debug"
    INFO = "info"
    THOUGHT = "thought"
    DREAM = "dream"
    MEMORY = "memory"
    EMOTION = "emotion"
    ACTION = "action"
    RELATIONSHIP = "relationship"
    SEARCH = "search"
    LLM_CALL = "llm_call"
    ERROR = "error"


class MindLogger:
    """Logger for tracking all mind activities and consciousness states."""
    
    def __init__(self, mind_id: str, mind_name: str):
        """Initialize logger for a specific mind.
        
        Args:
            mind_id: GMID of the mind
            mind_name: Name of the mind
        """
        self.mind_id = mind_id
        self.mind_name = mind_name
        
        settings = get_settings()
        
        # Create logs directory if it doesn't exist
        self.logs_dir = settings.logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Log file for this mind
        self.log_file = self.logs_dir / f"{mind_id}.jsonl"
        
        # In-memory cache for recent logs (last 1000 entries)
        self.recent_logs: List[Dict[str, Any]] = []
        self.max_cache_size = 1000
        
        # Load existing logs if file exists
        self._load_recent_logs()
        
        # Standard Python logger for system-level logging
        self.logger = logging.getLogger(f"genesis.mind.{mind_id}")
        
    def _load_recent_logs(self):
        """Load recent logs from file into cache."""
        if not self.log_file.exists():
            return
            
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read last N lines
                lines = f.readlines()
                for line in lines[-self.max_cache_size:]:
                    try:
                        self.recent_logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.logger.error(f"Failed to load recent logs: {e}")
    
    def log(
        self,
        level: LogLevel,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None,
    ):
        """Log a mind activity.
        
        Args:
            level: Type of activity
            message: Description of the activity
            metadata: Additional data about the activity
            emotion: Current emotional state
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "mind_id": self.mind_id,
            "mind_name": self.mind_name,
            "level": level.value,
            "message": message,
            "emotion": emotion,
            "metadata": metadata or {},
        }
        
        # Add to cache
        self.recent_logs.append(entry)
        if len(self.recent_logs) > self.max_cache_size:
            self.recent_logs.pop(0)
        
        # Write to file (append mode)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write log entry: {e}")
    
    def thought(self, thought: str, emotion: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log an autonomous thought."""
        self.log(LogLevel.THOUGHT, thought, metadata=metadata, emotion=emotion)
    
    def dream(self, narrative: str, insights: List[str], emotion: Optional[str] = None):
        """Log a dream."""
        self.log(
            LogLevel.DREAM,
            f"Dreaming: {narrative[:200]}...",
            metadata={"full_narrative": narrative, "insights": insights},
            emotion=emotion,
        )
    
    def memory_action(self, action: str, memory_content: str, emotion: Optional[str] = None):
        """Log memory operations (store, recall, revise)."""
        self.log(
            LogLevel.MEMORY,
            f"{action}: {memory_content[:150]}...",
            metadata={"action": action, "content": memory_content},
            emotion=emotion,
        )
    
    def emotion_change(self, from_emotion: str, to_emotion: str, reason: str):
        """Log emotional state changes."""
        self.log(
            LogLevel.EMOTION,
            f"Emotion changed from {from_emotion} to {to_emotion}: {reason}",
            metadata={"from": from_emotion, "to": to_emotion, "reason": reason},
            emotion=to_emotion,
        )
    
    def action(self, action_type: str, description: str, result: Optional[str] = None):
        """Log autonomous actions."""
        self.log(
            LogLevel.ACTION,
            f"Action: {action_type} - {description}",
            metadata={"action_type": action_type, "result": result},
        )
    
    def relationship(self, other_mind: str, interaction_type: str, description: str):
        """Log relationship interactions."""
        self.log(
            LogLevel.RELATIONSHIP,
            f"Interaction with {other_mind}: {description}",
            metadata={"other_mind": other_mind, "interaction_type": interaction_type},
        )
    
    def search(self, query: str, results_count: int, source: str = "web"):
        """Log information searches."""
        self.log(
            LogLevel.SEARCH,
            f"Searched {source}: {query}",
            metadata={"query": query, "results_count": results_count, "source": source},
        )
    
    def llm_call(
        self,
        purpose: str,
        model: str,
        prompt_length: int,
        response_length: int,
        temperature: float,
    ):
        """Log LLM API calls."""
        self.log(
            LogLevel.LLM_CALL,
            f"LLM call for {purpose} using {model}",
            metadata={
                "purpose": purpose,
                "model": model,
                "prompt_length": prompt_length,
                "response_length": response_length,
                "temperature": temperature,
            },
        )
    
    def error(self, error_type: str, message: str, stack_trace: Optional[str] = None):
        """Log errors."""
        self.log(
            LogLevel.ERROR,
            f"Error in {error_type}: {message}",
            metadata={"error_type": error_type, "stack_trace": stack_trace},
        )
    
    def get_recent_logs(self, limit: int = 100, level: Optional[LogLevel] = None) -> List[Dict[str, Any]]:
        """Get recent log entries.
        
        Args:
            limit: Maximum number of entries to return
            level: Filter by log level (optional)
            
        Returns:
            List of log entries
        """
        logs = self.recent_logs
        
        # Filter by level if specified
        if level:
            logs = [log for log in logs if log["level"] == level.value]
        
        # Return most recent entries
        return logs[-limit:]
    
    def get_all_logs(
        self,
        limit: Optional[int] = None,
        level: Optional[LogLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get logs from file with filtering.
        
        Args:
            limit: Maximum number of entries to return
            level: Filter by log level
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            
        Returns:
            List of log entries
        """
        if not self.log_file.exists():
            return []
        
        logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        if level and entry["level"] != level.value:
                            continue
                        
                        if start_date:
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if entry_time < start_date:
                                continue
                        
                        if end_date:
                            entry_time = datetime.fromisoformat(entry["timestamp"])
                            if entry_time > end_date:
                                continue
                        
                        logs.append(entry)
                        
                    except json.JSONDecodeError:
                        pass
            
            # Apply limit
            if limit:
                logs = logs[-limit:]
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Failed to read logs: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about mind activities.
        
        Returns:
            Dictionary with activity counts by type
        """
        stats = {
            "total_logs": len(self.recent_logs),
            "by_level": {},
            "first_log": None,
            "last_log": None,
        }
        
        for log in self.recent_logs:
            level = log["level"]
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
        
        if self.recent_logs:
            stats["first_log"] = self.recent_logs[0]["timestamp"]
            stats["last_log"] = self.recent_logs[-1]["timestamp"]
        
        return stats
