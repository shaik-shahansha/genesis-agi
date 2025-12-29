"""
Database models for Genesis Marketplace.

Enables buying/selling of Minds, Environments, Skills, and Memory Packs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid

from genesis.database.base import Base


class ItemType(str, Enum):
    """Types of items that can be sold in marketplace."""
    MIND = "mind"
    ENVIRONMENT = "environment"
    SKILL = "skill"
    MEMORY_PACK = "memory_pack"
    PERSONALITY_TRAIT = "personality_trait"
    TOOL = "tool"


class TransactionStatus(str, Enum):
    """Status of marketplace transactions."""
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"


class MarketplaceListing(Base):
    """Marketplace listing for sellable items."""

    __tablename__ = "marketplace_listings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String, nullable=False, index=True)  # Mind GMID or user ID
    seller_name = Column(String, nullable=False)

    # Item details
    item_type = Column(String, nullable=False, index=True)  # ItemType enum
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=True, index=True)
    tags = Column(JSON, default=list)  # List[str]

    # Pricing
    price = Column(Float, nullable=False)  # In GEN

    # Popularity & reviews
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    sales_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # Item configuration (varies by type)
    data = Column(JSON, nullable=False)  # Mind config, environment config, etc.

    # Media
    preview_image = Column(String, nullable=True)
    screenshots = Column(JSON, default=list)  # List[str] of image URLs

    # Status
    active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    featured = Column(Integer, default=0)  # 1 = featured, 0 = normal

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_item_type_active', 'item_type', 'active'),
        Index('idx_category_active', 'category', 'active'),
        Index('idx_featured', 'featured', 'active'),
        Index('idx_sales', 'sales_count'),
        Index('idx_rating', 'rating'),
    )


class MarketplaceTransaction(Base):
    """Record of marketplace purchases."""

    __tablename__ = "marketplace_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Parties
    buyer_id = Column(String, nullable=False, index=True)
    seller_id = Column(String, nullable=False, index=True)

    # Transaction details
    listing_id = Column(String, ForeignKey('marketplace_listings.id'), nullable=False)
    amount = Column(Float, nullable=False)  # In GEN
    status = Column(String, nullable=False, default=TransactionStatus.PENDING.value)

    # Additional data
    extra_metadata = Column(JSON, default=dict)  # Custom fields
    error_message = Column(Text, nullable=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_buyer_status', 'buyer_id', 'status'),
        Index('idx_seller_status', 'seller_id', 'status'),
    )


class MarketplaceReview(Base):
    """Reviews for marketplace items."""

    __tablename__ = "marketplace_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Review details
    transaction_id = Column(String, ForeignKey('marketplace_transactions.id'), nullable=False, unique=True)
    listing_id = Column(String, ForeignKey('marketplace_listings.id'), nullable=False, index=True)
    reviewer_id = Column(String, nullable=False, index=True)
    reviewer_name = Column(String, nullable=False)

    # Rating & feedback
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)

    # Helpful votes
    helpful_count = Column(Integer, default=0)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_listing_rating', 'listing_id', 'rating'),
    )


class MarketplaceFavorite(Base):
    """User favorites/wishlist."""

    __tablename__ = "marketplace_favorites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    listing_id = Column(String, ForeignKey('marketplace_listings.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_user_listing', 'user_id', 'listing_id', unique=True),
    )
