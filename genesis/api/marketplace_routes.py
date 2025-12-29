"""
Marketplace API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from genesis.marketplace.manager import MarketplaceManager
from genesis.marketplace.installer import ItemInstaller
from genesis.database.marketplace_models import ItemType
from genesis.api.auth import get_current_user


router = APIRouter()


# ==================== Request/Response Models ====================

class CreateListingRequest(BaseModel):
    """Request to create marketplace listing."""
    item_type: ItemType
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    price: float = Field(..., gt=0)
    data: dict  # Item-specific configuration
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    preview_image: Optional[str] = None
    screenshots: Optional[List[str]] = []


class UpdateListingRequest(BaseModel):
    """Request to update marketplace listing."""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    data: Optional[dict] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    active: Optional[int] = None


class PurchaseRequest(BaseModel):
    """Request to purchase item."""
    listing_id: str
    target_mind_id: Optional[str] = None  # For skills, memory packs, etc.


class ReviewRequest(BaseModel):
    """Request to add review."""
    transaction_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


# ==================== Endpoints ====================

@router.post("/listings")
async def create_listing(
    request: CreateListingRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new marketplace listing."""
    manager = MarketplaceManager()

    listing = manager.create_listing(
        seller_id=current_user["user_id"],
        seller_name=current_user.get("username", "Unknown"),
        item_type=request.item_type,
        title=request.title,
        description=request.description,
        price=request.price,
        data=request.data,
        category=request.category,
        tags=request.tags,
        preview_image=request.preview_image,
        screenshots=request.screenshots,
    )

    return {
        "success": True,
        "listing_id": listing.id,
        "listing": {
            "id": listing.id,
            "title": listing.title,
            "item_type": listing.item_type,
            "price": listing.price,
            "created_at": listing.created_at.isoformat(),
        }
    }


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    """Get listing details."""
    manager = MarketplaceManager()
    listing = manager.get_listing(listing_id)

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "id": listing.id,
        "seller_id": listing.seller_id,
        "seller_name": listing.seller_name,
        "item_type": listing.item_type,
        "title": listing.title,
        "description": listing.description,
        "price": listing.price,
        "category": listing.category,
        "tags": listing.tags,
        "rating": listing.rating,
        "review_count": listing.review_count,
        "sales_count": listing.sales_count,
        "view_count": listing.view_count,
        "data": listing.data,
        "preview_image": listing.preview_image,
        "screenshots": listing.screenshots,
        "created_at": listing.created_at.isoformat(),
        "updated_at": listing.updated_at.isoformat(),
    }


@router.put("/listings/{listing_id}")
async def update_listing(
    listing_id: str,
    request: UpdateListingRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update marketplace listing."""
    manager = MarketplaceManager()

    # Only allow updates by the seller
    updates = request.dict(exclude_none=True)
    listing = manager.update_listing(
        listing_id=listing_id,
        seller_id=current_user["user_id"],
        **updates
    )

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or unauthorized")

    return {
        "success": True,
        "listing_id": listing.id,
    }


@router.delete("/listings/{listing_id}")
async def delete_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete marketplace listing."""
    manager = MarketplaceManager()

    success = manager.delete_listing(
        listing_id=listing_id,
        seller_id=current_user["user_id"],
    )

    if not success:
        raise HTTPException(status_code=404, detail="Listing not found or unauthorized")

    return {"success": True}


@router.get("/listings")
async def search_listings(
    query: Optional[str] = Query(None),
    item_type: Optional[ItemType] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),  # Comma-separated
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """Search and browse marketplace listings."""
    manager = MarketplaceManager()

    # Parse tags
    tag_list = tags.split(",") if tags else None

    listings = manager.search_listings(
        query=query,
        item_type=item_type,
        category=category,
        tags=tag_list,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    return {
        "listings": [
            {
                "id": l.id,
                "title": l.title,
                "item_type": l.item_type,
                "price": l.price,
                "rating": l.rating,
                "review_count": l.review_count,
                "sales_count": l.sales_count,
                "preview_image": l.preview_image,
                "seller_name": l.seller_name,
                "category": l.category,
                "tags": l.tags,
            }
            for l in listings
        ],
        "count": len(listings),
        "offset": offset,
        "limit": limit,
    }


@router.get("/trending")
async def get_trending(
    item_type: Optional[ItemType] = Query(None),
    limit: int = Query(10, le=50),
):
    """Get trending marketplace items."""
    manager = MarketplaceManager()
    listings = manager.get_trending_listings(item_type=item_type, limit=limit)

    return {
        "trending": [
            {
                "id": l.id,
                "title": l.title,
                "item_type": l.item_type,
                "price": l.price,
                "rating": l.rating,
                "sales_count": l.sales_count,
                "preview_image": l.preview_image,
            }
            for l in listings
        ]
    }


@router.get("/featured")
async def get_featured(limit: int = Query(10, le=50)):
    """Get featured marketplace items."""
    manager = MarketplaceManager()
    listings = manager.get_featured_listings(limit=limit)

    return {
        "featured": [
            {
                "id": l.id,
                "title": l.title,
                "item_type": l.item_type,
                "price": l.price,
                "rating": l.rating,
                "preview_image": l.preview_image,
            }
            for l in listings
        ]
    }


@router.post("/purchase")
async def purchase_item(
    request: PurchaseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Purchase an item from marketplace."""
    manager = MarketplaceManager()

    # Process purchase
    result = manager.purchase_item(
        buyer_id=current_user["user_id"],
        listing_id=request.listing_id,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Install purchased item
    listing = result["listing"]

    # Add target_mind_id to item data if provided
    item_data = listing.data.copy()
    if request.target_mind_id:
        item_data["target_mind_id"] = request.target_mind_id

    install_result = ItemInstaller.install_item(
        buyer_id=current_user["user_id"],
        item_type=ItemType(listing.item_type),
        item_data=item_data,
    )

    return {
        "success": True,
        "transaction_id": result["transaction_id"],
        "installation": install_result,
    }


@router.get("/my-purchases")
async def get_my_purchases(current_user: dict = Depends(get_current_user)):
    """Get current user's purchase history."""
    manager = MarketplaceManager()
    transactions = manager.get_user_purchases(current_user["user_id"])

    return {
        "purchases": [
            {
                "id": t.id,
                "listing_id": t.listing_id,
                "amount": t.amount,
                "status": t.status,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in transactions
        ]
    }


@router.get("/my-listings")
async def get_my_listings(current_user: dict = Depends(get_current_user)):
    """Get current user's marketplace listings."""
    manager = MarketplaceManager()
    listings = manager.get_seller_listings(current_user["user_id"])

    return {
        "listings": [
            {
                "id": l.id,
                "title": l.title,
                "item_type": l.item_type,
                "price": l.price,
                "rating": l.rating,
                "sales_count": l.sales_count,
                "active": l.active,
                "created_at": l.created_at.isoformat(),
            }
            for l in listings
        ]
    }


@router.get("/my-sales")
async def get_my_sales(current_user: dict = Depends(get_current_user)):
    """Get current user's sales history."""
    manager = MarketplaceManager()
    transactions = manager.get_seller_sales(current_user["user_id"])

    return {
        "sales": [
            {
                "id": t.id,
                "listing_id": t.listing_id,
                "buyer_id": t.buyer_id,
                "amount": t.amount,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in transactions
        ],
        "total_revenue": sum(t.amount for t in transactions),
    }


@router.post("/reviews")
async def add_review(
    request: ReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add review for purchased item."""
    manager = MarketplaceManager()

    review = manager.add_review(
        transaction_id=request.transaction_id,
        reviewer_id=current_user["user_id"],
        reviewer_name=current_user.get("username", "Anonymous"),
        rating=request.rating,
        comment=request.comment,
    )

    if not review:
        raise HTTPException(
            status_code=400,
            detail="Cannot review this transaction (not found, not completed, or already reviewed)"
        )

    return {
        "success": True,
        "review_id": review.id,
    }


@router.get("/listings/{listing_id}/reviews")
async def get_listing_reviews(listing_id: str, limit: int = Query(50, le=100)):
    """Get reviews for a listing."""
    manager = MarketplaceManager()
    reviews = manager.get_listing_reviews(listing_id, limit=limit)

    return {
        "reviews": [
            {
                "id": r.id,
                "reviewer_name": r.reviewer_name,
                "rating": r.rating,
                "comment": r.comment,
                "helpful_count": r.helpful_count,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in reviews
        ]
    }


@router.post("/favorites/{listing_id}")
async def add_favorite(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Add listing to favorites."""
    manager = MarketplaceManager()
    success = manager.add_favorite(current_user["user_id"], listing_id)

    return {"success": success}


@router.delete("/favorites/{listing_id}")
async def remove_favorite(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove listing from favorites."""
    manager = MarketplaceManager()
    success = manager.remove_favorite(current_user["user_id"], listing_id)

    return {"success": success}


@router.get("/favorites")
async def get_favorites(current_user: dict = Depends(get_current_user)):
    """Get user's favorite listings."""
    manager = MarketplaceManager()
    listings = manager.get_user_favorites(current_user["user_id"])

    return {
        "favorites": [
            {
                "id": l.id,
                "title": l.title,
                "item_type": l.item_type,
                "price": l.price,
                "rating": l.rating,
                "preview_image": l.preview_image,
            }
            for l in listings
        ]
    }


@router.get("/stats")
async def get_marketplace_stats():
    """Get marketplace statistics."""
    manager = MarketplaceManager()
    stats = manager.get_marketplace_stats()

    return stats
