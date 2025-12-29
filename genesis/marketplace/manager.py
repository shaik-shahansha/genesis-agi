"""
Marketplace Manager - Handle all marketplace operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import desc, and_, or_, func
from sqlalchemy.orm import Session

from genesis.database.base import get_session
from genesis.database.marketplace_models import (
    MarketplaceListing,
    MarketplaceTransaction,
    MarketplaceReview,
    MarketplaceFavorite,
    ItemType,
    TransactionStatus,
)
from genesis.core.essence import EssenceManager, TransactionType


class MarketplaceManager:
    """Manage marketplace operations."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize marketplace manager."""
        self.session = db_session or get_session()

    # ==================== Listing Management ====================

    def create_listing(
        self,
        seller_id: str,
        seller_name: str,
        item_type: ItemType,
        title: str,
        description: str,
        price: float,
        data: Dict[str, Any],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        preview_image: Optional[str] = None,
        screenshots: Optional[List[str]] = None,
    ) -> MarketplaceListing:
        """Create a new marketplace listing."""
        listing = MarketplaceListing(
            seller_id=seller_id,
            seller_name=seller_name,
            item_type=item_type.value,
            title=title,
            description=description,
            price=price,
            data=data,
            category=category,
            tags=tags or [],
            preview_image=preview_image,
            screenshots=screenshots or [],
        )

        self.session.add(listing)
        self.session.commit()

        return listing

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        """Get listing by ID."""
        listing = self.session.query(MarketplaceListing).filter_by(id=listing_id).first()

        if listing and listing.active:
            # Increment view count
            listing.view_count += 1
            self.session.commit()

        return listing

    def update_listing(
        self,
        listing_id: str,
        seller_id: str,  # For authorization
        **updates
    ) -> Optional[MarketplaceListing]:
        """Update listing (seller only)."""
        listing = self.session.query(MarketplaceListing).filter_by(
            id=listing_id,
            seller_id=seller_id
        ).first()

        if not listing:
            return None

        for key, value in updates.items():
            if hasattr(listing, key):
                setattr(listing, key, value)

        listing.updated_at = datetime.utcnow()
        self.session.commit()

        return listing

    def delete_listing(self, listing_id: str, seller_id: str) -> bool:
        """Soft delete listing (set active=0)."""
        listing = self.session.query(MarketplaceListing).filter_by(
            id=listing_id,
            seller_id=seller_id
        ).first()

        if not listing:
            return False

        listing.active = 0
        self.session.commit()

        return True

    # ==================== Search & Browse ====================

    def search_listings(
        self,
        query: Optional[str] = None,
        item_type: Optional[ItemType] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        sort_by: str = "created_at",  # created_at, price, rating, sales_count
        order: str = "desc",  # desc or asc
        limit: int = 20,
        offset: int = 0,
    ) -> List[MarketplaceListing]:
        """Search and filter marketplace listings."""
        q = self.session.query(MarketplaceListing).filter_by(active=1)

        # Text search (title or description)
        if query:
            search_pattern = f"%{query}%"
            q = q.filter(
                or_(
                    MarketplaceListing.title.ilike(search_pattern),
                    MarketplaceListing.description.ilike(search_pattern)
                )
            )

        # Filters
        if item_type:
            q = q.filter_by(item_type=item_type.value)

        if category:
            q = q.filter_by(category=category)

        if tags:
            # Filter listings that have at least one of the tags
            for tag in tags:
                q = q.filter(MarketplaceListing.tags.contains([tag]))

        if min_price is not None:
            q = q.filter(MarketplaceListing.price >= min_price)

        if max_price is not None:
            q = q.filter(MarketplaceListing.price <= max_price)

        if min_rating is not None:
            q = q.filter(MarketplaceListing.rating >= min_rating)

        # Sorting
        sort_column = getattr(MarketplaceListing, sort_by, MarketplaceListing.created_at)
        if order == "desc":
            q = q.order_by(desc(sort_column))
        else:
            q = q.order_by(sort_column)

        # Pagination
        q = q.limit(limit).offset(offset)

        return q.all()

    def get_trending_listings(self, item_type: Optional[ItemType] = None, limit: int = 10) -> List[MarketplaceListing]:
        """Get trending items (by recent sales and high ratings)."""
        q = self.session.query(MarketplaceListing).filter_by(active=1)

        if item_type:
            q = q.filter_by(item_type=item_type.value)

        # Sort by sales count (recent popularity) and rating
        q = q.order_by(
            desc(MarketplaceListing.sales_count),
            desc(MarketplaceListing.rating)
        ).limit(limit)

        return q.all()

    def get_featured_listings(self, limit: int = 10) -> List[MarketplaceListing]:
        """Get featured listings."""
        return self.session.query(MarketplaceListing).filter_by(
            active=1,
            featured=1
        ).order_by(desc(MarketplaceListing.rating)).limit(limit).all()

    def get_seller_listings(self, seller_id: str) -> List[MarketplaceListing]:
        """Get all listings by a seller."""
        return self.session.query(MarketplaceListing).filter_by(
            seller_id=seller_id,
            active=1
        ).order_by(desc(MarketplaceListing.created_at)).all()

    # ==================== Transactions ====================

    def purchase_item(
        self,
        buyer_id: str,
        listing_id: str,
    ) -> Dict[str, Any]:
        """Purchase an item from marketplace."""
        listing = self.get_listing(listing_id)

        if not listing or not listing.active:
            return {"success": False, "error": "Listing not found or inactive"}

        # Can't buy your own listing
        if listing.seller_id == buyer_id:
            return {"success": False, "error": "Cannot purchase your own listing"}

        # Create transaction record
        transaction = MarketplaceTransaction(
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            listing_id=listing_id,
            amount=listing.price,
            status=TransactionStatus.PENDING.value,
        )

        try:
            # Transfer Essence from buyer to seller
            # Note: This requires EssenceManager integration
            # For now, we'll mark as completed
            transaction.status = TransactionStatus.COMPLETED.value
            transaction.completed_at = datetime.utcnow()

            # Update listing stats
            listing.sales_count += 1

            self.session.add(transaction)
            self.session.commit()

            return {
                "success": True,
                "transaction_id": transaction.id,
                "listing": listing,
                "transaction": transaction,
            }

        except Exception as e:
            transaction.status = TransactionStatus.FAILED.value
            transaction.error_message = str(e)
            self.session.commit()

            return {"success": False, "error": str(e)}

    def get_transaction(self, transaction_id: str) -> Optional[MarketplaceTransaction]:
        """Get transaction by ID."""
        return self.session.query(MarketplaceTransaction).filter_by(id=transaction_id).first()

    def get_user_purchases(self, buyer_id: str) -> List[MarketplaceTransaction]:
        """Get all purchases by a buyer."""
        return self.session.query(MarketplaceTransaction).filter_by(
            buyer_id=buyer_id,
            status=TransactionStatus.COMPLETED.value
        ).order_by(desc(MarketplaceTransaction.timestamp)).all()

    def get_seller_sales(self, seller_id: str) -> List[MarketplaceTransaction]:
        """Get all sales by a seller."""
        return self.session.query(MarketplaceTransaction).filter_by(
            seller_id=seller_id,
            status=TransactionStatus.COMPLETED.value
        ).order_by(desc(MarketplaceTransaction.timestamp)).all()

    # ==================== Reviews ====================

    def add_review(
        self,
        transaction_id: str,
        reviewer_id: str,
        reviewer_name: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> Optional[MarketplaceReview]:
        """Add review for a purchased item."""
        # Verify transaction exists and was completed
        transaction = self.get_transaction(transaction_id)

        if not transaction or transaction.status != TransactionStatus.COMPLETED.value:
            return None

        # Verify reviewer is the buyer
        if transaction.buyer_id != reviewer_id:
            return None

        # Check if review already exists
        existing = self.session.query(MarketplaceReview).filter_by(
            transaction_id=transaction_id
        ).first()

        if existing:
            return None  # Can't review twice

        # Create review
        review = MarketplaceReview(
            transaction_id=transaction_id,
            listing_id=transaction.listing_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            rating=rating,
            comment=comment,
        )

        self.session.add(review)

        # Update listing rating
        listing = self.get_listing(transaction.listing_id)
        if listing:
            # Calculate new average rating
            reviews = self.get_listing_reviews(listing.id)
            total_rating = sum(r.rating for r in reviews) + rating
            review_count = len(reviews) + 1

            listing.rating = total_rating / review_count
            listing.review_count = review_count

        self.session.commit()

        return review

    def get_listing_reviews(self, listing_id: str, limit: int = 50) -> List[MarketplaceReview]:
        """Get all reviews for a listing."""
        return self.session.query(MarketplaceReview).filter_by(
            listing_id=listing_id
        ).order_by(desc(MarketplaceReview.timestamp)).limit(limit).all()

    # ==================== Favorites ====================

    def add_favorite(self, user_id: str, listing_id: str) -> bool:
        """Add listing to favorites."""
        # Check if already favorited
        existing = self.session.query(MarketplaceFavorite).filter_by(
            user_id=user_id,
            listing_id=listing_id
        ).first()

        if existing:
            return False

        favorite = MarketplaceFavorite(
            user_id=user_id,
            listing_id=listing_id,
        )

        self.session.add(favorite)
        self.session.commit()

        return True

    def remove_favorite(self, user_id: str, listing_id: str) -> bool:
        """Remove listing from favorites."""
        favorite = self.session.query(MarketplaceFavorite).filter_by(
            user_id=user_id,
            listing_id=listing_id
        ).first()

        if not favorite:
            return False

        self.session.delete(favorite)
        self.session.commit()

        return True

    def get_user_favorites(self, user_id: str) -> List[MarketplaceListing]:
        """Get user's favorite listings."""
        favorites = self.session.query(MarketplaceFavorite).filter_by(
            user_id=user_id
        ).all()

        listing_ids = [f.listing_id for f in favorites]

        return self.session.query(MarketplaceListing).filter(
            MarketplaceListing.id.in_(listing_ids),
            MarketplaceListing.active == 1
        ).all()

    # ==================== Analytics ====================

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get overall marketplace statistics."""
        return {
            "total_listings": self.session.query(MarketplaceListing).filter_by(active=1).count(),
            "total_transactions": self.session.query(MarketplaceTransaction).filter_by(
                status=TransactionStatus.COMPLETED.value
            ).count(),
            "total_reviews": self.session.query(MarketplaceReview).count(),
            "total_sellers": self.session.query(MarketplaceListing.seller_id).distinct().count(),
            "total_essence_volume": self.session.query(
                func.sum(MarketplaceTransaction.amount)
            ).filter_by(status=TransactionStatus.COMPLETED.value).scalar() or 0,
            "listings_by_type": self._get_listings_by_type(),
            "avg_rating": self.session.query(
                func.avg(MarketplaceListing.rating)
            ).filter(MarketplaceListing.active == 1).scalar() or 0,
        }

    def _get_listings_by_type(self) -> Dict[str, int]:
        """Get count of listings by type."""
        results = self.session.query(
            MarketplaceListing.item_type,
            func.count(MarketplaceListing.id)
        ).filter_by(active=1).group_by(MarketplaceListing.item_type).all()

        return {item_type: count for item_type, count in results}
