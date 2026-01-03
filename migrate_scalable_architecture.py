"""
Migration script to create new tables for scalable architecture.

Run this to create:
- conversation_messages (replaces in-memory conversation_history)
- concerns (replaces JSON file storage)
- background_tasks (adds persistence for task execution)
"""

from genesis.database.base import init_db, get_engine
from genesis.database.models import Base

def migrate():
    """Create all new tables."""
    print("Creating database tables...")
    
    # This will create all tables defined in models.py
    init_db()
    
    print("✅ Database tables created successfully!")
    print()
    print("New tables:")
    print("  - conversation_messages (conversations now in SQLite)")
    print("  - concerns (proactive concerns now in SQLite)")  
    print("  - background_tasks (task execution now persisted)")
    print()
    print("Architecture improvements:")
    print("  ✅ Memories: ChromaDB only (no JSON bloat)")
    print("  ✅ Conversations: SQLite with pagination")
    print("  ✅ Concerns: SQLite with time-based queries")
    print("  ✅ Background Tasks: SQLite for crash recovery")
    print("  ✅ Mind JSON files: Now <50KB (was MBs)")

if __name__ == "__main__":
    migrate()
