'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';

interface Listing {
  id: string;
  title: string;
  item_type: string;
  price: number;
  rating: number;
  review_count: number;
  sales_count: number;
  preview_image?: string;
  seller_name: string;
  category: string;
  tags: string[];
}

export default function MarketplacePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [trending, setTrending] = useState<Listing[]>([]);
  const [featured, setFeatured] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    query: '',
    item_type: '',
    category: '',
    sort_by: 'created_at',
    order: 'desc',
  });

  useEffect(() => {
    loadMarketplace();
  }, [filter]);

  const loadMarketplace = async () => {
    setLoading(true);
    try {
      const [listingsData, trendingData, featuredData] = await Promise.all([
        api.getMarketplaceListings({ ...filter, limit: 20 }),
        api.getTrending(undefined, 6),
        api.getFeatured(6),
      ]);

      setListings(listingsData.listings || []);
      setTrending(trendingData.trending || []);
      setFeatured(featuredData.featured || []);
    } catch (error) {
      console.error('Failed to load marketplace:', error);
    } finally {
      setLoading(false);
    }
  };

  const itemTypeIcon = (type: string) => {
    switch (type) {
      case 'mind': return '🧠';
      case 'environment': return '🌍';
      case 'skill': return '🎯';
      case 'memory_pack': return '📚';
      case 'personality_trait': return '✨';
      case 'tool': return '🔧';
      default: return '📦';
    }
  };

  const ListingCard = ({ listing }: { listing: Listing }) => (
    <Link href={`/marketplace/${listing.id}`}>
      <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-4 hover:border-purple-500/60 transition cursor-pointer h-full flex flex-col">
        {/* Preview Image */}
        <div className="w-full h-40 bg-slate-700/50 rounded-lg mb-3 flex items-center justify-center text-6xl">
          {listing.preview_image ? (
            <img src={listing.preview_image} alt={listing.title} className="w-full h-full object-cover rounded-lg" />
          ) : (
            <span>{itemTypeIcon(listing.item_type)}</span>
          )}
        </div>

        {/* Title */}
        <h3 className="text-lg font-bold text-white mb-2 line-clamp-2 flex-grow">
          {listing.title}
        </h3>

        {/* Type & Category */}
        <div className="flex gap-2 mb-3">
          <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-xs">
            {listing.item_type}
          </span>
          <span className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs">
            {listing.category}
          </span>
        </div>

        {/* Rating */}
        {listing.rating > 0 && (
          <div className="flex items-center gap-2 mb-3">
            <span className="text-yellow-400">⭐</span>
            <span className="text-white font-medium">{listing.rating.toFixed(1)}</span>
            <span className="text-gray-400 text-sm">({listing.review_count})</span>
          </div>
        )}

        {/* Stats */}
        <div className="flex items-center justify-between text-sm text-gray-400 mb-3">
          <span>By {listing.seller_name}</span>
          <span>{listing.sales_count} sales</span>
        </div>

        {/* Price */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-700">
          <span className="text-2xl font-bold text-purple-400">{listing.price}</span>
          <span className="text-gray-400">Essence</span>
        </div>
      </div>
    </Link>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-5xl font-bold text-white mb-4">
            Genesis <span className="text-purple-400">Marketplace</span>
          </h1>
          <p className="text-xl text-gray-300">
            Discover and purchase digital beings, environments, and skills
          </p>
        </div>

        {/* Search & Filters */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <input
              type="text"
              placeholder="Search marketplace..."
              value={filter.query}
              onChange={(e) => setFilter({ ...filter, query: e.target.value })}
              className="col-span-2 px-4 py-2 bg-slate-700 text-white rounded border border-slate-600 focus:border-purple-500 outline-none"
            />

            {/* Item Type */}
            <select
              value={filter.item_type}
              onChange={(e) => setFilter({ ...filter, item_type: e.target.value })}
              className="px-4 py-2 bg-slate-700 text-white rounded border border-slate-600 focus:border-purple-500 outline-none"
            >
              <option value="">All Types</option>
              <option value="mind">Minds</option>
              <option value="environment">Environments</option>
              <option value="skill">Skills</option>
              <option value="memory_pack">Memory Packs</option>
              <option value="personality_trait">Traits</option>
              <option value="tool">Tools</option>
            </select>

            {/* Sort */}
            <select
              value={filter.sort_by}
              onChange={(e) => setFilter({ ...filter, sort_by: e.target.value })}
              className="px-4 py-2 bg-slate-700 text-white rounded border border-slate-600 focus:border-purple-500 outline-none"
            >
              <option value="created_at">Newest</option>
              <option value="price">Price</option>
              <option value="rating">Rating</option>
              <option value="sales_count">Most Popular</option>
            </select>
          </div>
        </div>

        {/* Featured Section */}
        {featured.length > 0 && (
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-white mb-4">⭐ Featured Items</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {featured.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          </div>
        )}

        {/* Trending Section */}
        {trending.length > 0 && (
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-white mb-4">🔥 Trending Now</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {trending.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          </div>
        )}

        {/* All Listings */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white mb-4">All Items</h2>
          {loading ? (
            <div className="text-center text-gray-400 py-12">
              <div className="animate-pulse">Loading marketplace...</div>
            </div>
          ) : listings.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              <p className="text-xl mb-4">No items found</p>
              <p>Try adjusting your filters</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {listings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>
          )}
        </div>

        {/* Back to Home */}
        <div className="text-center">
          <Link
            href="/"
            className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
          >
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
