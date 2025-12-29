"""
Initialize marketplace database tables.
"""

from genesis.database.base import Base, get_engine
from genesis.database.marketplace_models import (
    MarketplaceListing,
    MarketplaceTransaction,
    MarketplaceReview,
    MarketplaceFavorite,
)


def init_marketplace_tables():
    """Create all marketplace tables."""
    print("Creating marketplace database tables...")

    engine = get_engine()

    # Create all tables
    Base.metadata.create_all(
        engine,
        tables=[
            MarketplaceListing.__table__,
            MarketplaceTransaction.__table__,
            MarketplaceReview.__table__,
            MarketplaceFavorite.__table__,
        ]
    )

    print("✅ Marketplace tables created successfully!")


if __name__ == "__main__":
    init_marketplace_tables()
