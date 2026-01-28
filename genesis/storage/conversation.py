"""
Conversation management with SQLite for scalability.

Replaces in-memory conversation_history list with database storage
for better scalability and querying capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from genesis.database.base import get_session
from genesis.database.models import ConversationMessage


class ConversationManager:
    """
    Manages conversation history in SQLite for scalability.
    
    Replaces:
        mind.conversation_history = []  # In-memory list (bloats JSON)
    
    With:
        mind.conversation = ConversationManager(mind_id)  # SQLite-backed
    
    Features:
    - Efficient pagination (get last N messages)
    - Time-based queries (messages from last week)
    - User filtering (conversation with specific user)
    - Environment filtering (messages in specific environment)
    - Automatic retention policies (delete old messages)
    """
    
    def __init__(self, mind_gmid: str):
        """
        Initialize conversation manager for a Mind.
        
        Args:
            mind_gmid: Genesis Mind ID
        """
        self.mind_gmid = mind_gmid
    
    def add_message(
        self,
        role: str,
        content: str,
        user_email: Optional[str] = None,
        environment_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> ConversationMessage:
        """
        Add a message to conversation history.
        
        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            user_email: Email of user (if user message)
            environment_id: Environment where message was sent
            metadata: Additional metadata
            timestamp: Message timestamp (default: now)
            
        Returns:
            Created message record
        """
        try:
            with get_session() as session:
                message = ConversationMessage(
                    mind_gmid=self.mind_gmid,
                    user_email=user_email,
                    environment_id=environment_id,
                    role=role,
                    content=content,
                    timestamp=timestamp or datetime.now(),
                    extra_data=metadata or {}
                )
                session.add(message)
                session.commit()
                session.refresh(message)
                return message
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
    
    def get_recent_messages(
        self,
        limit: int = 50,
        user_email: Optional[str] = None,
        environment_id: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages.
        
        Args:
            limit: Maximum number of messages to return
            user_email: Filter by specific user
            environment_id: Filter by environment
            role: Filter by role ('user', 'assistant', 'system')
            
        Returns:
            List of message dictionaries (newest first)
        """
        with get_session() as session:
            query = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            )
            
            # Apply filters
            # For user_email: Only include messages FROM that specific user
            # This ensures users only see their own conversation history
            if user_email:
                query = query.filter(ConversationMessage.user_email == user_email)
            if environment_id:
                query = query.filter(ConversationMessage.environment_id == environment_id)
            if role:
                query = query.filter(ConversationMessage.role == role)
            
            # Order by timestamp descending and limit
            messages = query.order_by(
                ConversationMessage.timestamp.desc()
            ).limit(limit).all()
            
            # Convert to dict (reverse to chronological order)
            return [self._message_to_dict(msg) for msg in reversed(messages)]

    def get_messages_before(
        self,
        before_id: int,
        limit: int = 50,
        user_email: Optional[str] = None,
        environment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages before a specific message id (cursor-based pagination).

        Args:
            before_id: Message id to page before (exclusive)
            limit: Maximum number of messages to return
            user_email: Filter by specific user
            environment_id: Filter by environment

        Returns:
            List of message dictionaries (chronological order)
        """
        with get_session() as session:
            before_msg = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.id == before_id
            ).first()

            if not before_msg:
                return []

            before_ts = before_msg.timestamp

            # Build query for messages strictly earlier than the cursor
            from sqlalchemy import and_, or_

            query = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                or_(
                    ConversationMessage.timestamp < before_ts,
                    and_(
                        ConversationMessage.timestamp == before_ts,
                        ConversationMessage.id < before_id
                    )
                )
            )

            # Apply filters
            if user_email:
                query = query.filter(ConversationMessage.user_email == user_email)
            if environment_id:
                query = query.filter(ConversationMessage.environment_id == environment_id)

            # Order by newest first (descending), then reverse to chronological
            messages = query.order_by(
                ConversationMessage.timestamp.desc(),
                ConversationMessage.id.desc()
            ).limit(limit).all()

            return [self._message_to_dict(msg) for msg in reversed(messages)]
    
    def get_messages_since(
        self,
        since: datetime,
        user_email: Optional[str] = None,
        environment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages since a specific time.
        
        Args:
            since: Get messages after this timestamp
            user_email: Filter by specific user
            environment_id: Filter by environment
            
        Returns:
            List of message dictionaries (chronological order)
        """
        with get_session() as session:
            query = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.timestamp >= since
            )
            
            # Apply filters
            if user_email:
                query = query.filter(ConversationMessage.user_email == user_email)
            if environment_id:
                query = query.filter(ConversationMessage.environment_id == environment_id)
            
            # Order chronologically
            messages = query.order_by(ConversationMessage.timestamp.asc()).all()
            
            return [self._message_to_dict(msg) for msg in messages]
    
    def get_conversation_context(
        self,
        max_messages: int = 10,
        user_email: Optional[str] = None,
        environment_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation context for LLM.
        
        This is used in Mind.think() to provide conversation history.
        
        Args:
            max_messages: Maximum messages to include
            user_email: Filter by specific user conversation
            environment_id: Filter by environment
            
        Returns:
            List of message dicts in format: [{"role": "user", "content": "..."}]
        """
        return self.get_recent_messages(
            limit=max_messages,
            user_email=user_email,
            environment_id=environment_id
        )
    
    def delete_old_messages(
        self,
        older_than_days: int = 90,
        keep_minimum: int = 100
    ) -> int:
        """
        Delete old messages for retention policy.
        
        Args:
            older_than_days: Delete messages older than this many days
            keep_minimum: Always keep at least this many recent messages
            
        Returns:
            Number of messages deleted
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        
        with get_session() as session:
            # Count total messages
            total = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            ).count()
            
            # Don't delete if we'd go below minimum
            if total <= keep_minimum:
                return 0
            
            # Get IDs of messages to keep (most recent)
            keep_ids = [
                msg.id for msg in session.query(ConversationMessage.id).filter(
                    ConversationMessage.mind_gmid == self.mind_gmid
                ).order_by(
                    ConversationMessage.timestamp.desc()
                ).limit(keep_minimum).all()
            ]
            
            # Delete old messages not in keep list
            deleted = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.timestamp < cutoff_date,
                ~ConversationMessage.id.in_(keep_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get conversation statistics.
        
        Returns:
            Dictionary with stats (total messages, by role, by user, etc.)
        """
        with get_session() as session:
            total = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            ).count()
            
            # Count by role
            user_msgs = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.role == 'user'
            ).count()
            
            assistant_msgs = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.role == 'assistant'
            ).count()
            
            system_msgs = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid,
                ConversationMessage.role == 'system'
            ).count()
            
            # Get oldest and newest
            oldest = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            ).order_by(ConversationMessage.timestamp.asc()).first()
            
            newest = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            ).order_by(ConversationMessage.timestamp.desc()).first()
            
            return {
                "total_messages": total,
                "user_messages": user_msgs,
                "assistant_messages": assistant_msgs,
                "system_messages": system_msgs,
                "oldest_message": oldest.timestamp.isoformat() if oldest else None,
                "newest_message": newest.timestamp.isoformat() if newest else None
            }
    
    def get_conversation_threads(self, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of conversation threads (unique user+environment combinations).
        
        Args:
            user_email: Filter by specific user
            
        Returns:
            List of conversation threads with metadata (last message, count, etc.)
        """
        from sqlalchemy import func, desc
        
        with get_session() as session:
            # Query for distinct user_email + environment_id combinations
            query = session.query(
                ConversationMessage.user_email,
                ConversationMessage.environment_id,
                func.max(ConversationMessage.timestamp).label('last_message_time'),
                func.count(ConversationMessage.id).label('message_count')
            ).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            )
            
            if user_email:
                query = query.filter(ConversationMessage.user_email == user_email)
            
            threads = query.group_by(
                ConversationMessage.user_email,
                ConversationMessage.environment_id
            ).order_by(desc('last_message_time')).all()
            
            # Get last message preview for each thread
            result = []
            for thread in threads:
                # Get the actual last message
                last_msg = session.query(ConversationMessage).filter(
                    ConversationMessage.mind_gmid == self.mind_gmid,
                    ConversationMessage.user_email == thread.user_email,
                    ConversationMessage.environment_id == thread.environment_id
                ).order_by(ConversationMessage.timestamp.desc()).first()
                
                result.append({
                    "user_email": thread.user_email,
                    "environment_id": thread.environment_id,
                    "last_message_time": thread.last_message_time.isoformat() if thread.last_message_time else None,
                    "message_count": thread.message_count,
                    "last_message_preview": last_msg.content[:100] if last_msg else None,
                    "last_message_role": last_msg.role if last_msg else None
                })
            
            return result
    
    def clear_all(self) -> int:
        """
        Clear all conversation history (use with caution).
        
        Returns:
            Number of messages deleted
        """
        with get_session() as session:
            deleted = session.query(ConversationMessage).filter(
                ConversationMessage.mind_gmid == self.mind_gmid
            ).delete()
            session.commit()
            return deleted
    
    def _message_to_dict(self, msg: ConversationMessage) -> Dict[str, Any]:
        """Convert database message to dictionary."""
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "user_email": msg.user_email,
            "environment_id": msg.environment_id,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "metadata": msg.extra_data
        }
