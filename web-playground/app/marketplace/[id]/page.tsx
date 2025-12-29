'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';

interface ListingDetail {
  id: string;
  seller_id: string;
  seller_name: string;
  item_type: string;
  title: string;
  description: string;
  price: number;
  category: string;
  tags: string[];
  rating: number;
  review_count: number;
  sales_count: number;
  view_count: number;
  data: any;
  preview_image?: string;
  screenshots: string[];
  created_at: string;
  updated_at: string;
}

interface Review {
  id: string;
  reviewer_name: string;
  rating: number;
  comment: string;
  helpful_count: number;
  timestamp: string;
}

export default function ListingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const listingId = params.id as string;

  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);

  useEffect(() => {
    loadListing();
    loadReviews();
  }, [listingId]);

  const loadListing = async () => {
    try {
      const data = await api.getListing(listingId);
      setListing(data);
    } catch (error) {
      console.error('Failed to load listing:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadReviews = async () => {
    try {
      const data = await api.getListingReviews(listingId);
      setReviews(data.reviews || []);
    } catch (error) {
      console.error('Failed to load reviews:', error);
    }
  };

  const handlePurchase = async () => {
    setPurchasing(true);
    try {
      const result = await api.purchaseItem(listingId);

      alert(`✅ Purchase successful!\n\n${result.installation.message}\n\nID: ${result.installation.mind_id || result.installation.environment_id || 'N/A'}`);

      setShowPurchaseModal(false);

      // Redirect based on item type
      if (listing?.item_type === 'mind') {
        router.push('/');
      } else if (listing?.item_type === 'environment') {
        router.push('/environments');
      }
    } catch (error: any) {
      alert(`❌ Purchase failed: ${error.message}`);
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl animate-pulse">Loading listing...</div>
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-white text-xl mb-4">Listing not found</p>
          <Link href="/marketplace" className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg">
            ← Back to Marketplace
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="mb-6 text-gray-400">
          <Link href="/" className="hover:text-white">Home</Link>
          <span className="mx-2">/</span>
          <Link href="/marketplace" className="hover:text-white">Marketplace</Link>
          <span className="mx-2">/</span>
          <span className="text-white">{listing.title}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Images & Purchase */}
          <div className="lg:col-span-1">
            {/* Main Image */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6 mb-6">
              <div className="w-full h-64 bg-slate-700/50 rounded-lg flex items-center justify-center text-8xl mb-4">
                {listing.preview_image ? (
                  <img src={listing.preview_image} alt={listing.title} className="w-full h-full object-cover rounded-lg" />
                ) : (
                  <span>🧠</span>
                )}
              </div>

              {/* Screenshots */}
              {listing.screenshots && listing.screenshots.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                  {listing.screenshots.map((screenshot, i) => (
                    <div key={i} className="h-20 bg-slate-700/50 rounded overflow-hidden">
                      <img src={screenshot} alt={`Screenshot ${i + 1}`} className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Purchase Box */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6">
              <div className="mb-4">
                <div className="text-4xl font-bold text-purple-400 mb-2">{listing.price}</div>
                <div className="text-gray-400">Essence</div>
              </div>

              <button
                onClick={() => setShowPurchaseModal(true)}
                className="w-full px-6 py-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold text-lg transition"
              >
                💎 Purchase Now
              </button>

              {/* Stats */}
              <div className="mt-6 space-y-2 text-sm text-gray-400">
                <div className="flex justify-between">
                  <span>Sales:</span>
                  <span className="text-white">{listing.sales_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Views:</span>
                  <span className="text-white">{listing.view_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Seller:</span>
                  <span className="text-white">{listing.seller_name}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Details */}
          <div className="lg:col-span-2">
            {/* Title & Meta */}
            <div className="mb-6">
              <h1 className="text-4xl font-bold text-white mb-4">{listing.title}</h1>

              <div className="flex flex-wrap gap-2 mb-4">
                <span className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm">
                  {listing.item_type}
                </span>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                  {listing.category}
                </span>
                {listing.tags.map((tag) => (
                  <span key={tag} className="px-3 py-1 bg-slate-700 text-gray-300 rounded-full text-sm">
                    #{tag}
                  </span>
                ))}
              </div>

              {/* Rating */}
              {listing.rating > 0 && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <span className="text-yellow-400 text-2xl">⭐</span>
                    <span className="text-white text-2xl font-bold">{listing.rating.toFixed(1)}</span>
                  </div>
                  <span className="text-gray-400">({listing.review_count} reviews)</span>
                </div>
              )}
            </div>

            {/* Description */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6 mb-6">
              <h2 className="text-2xl font-bold text-white mb-4">Description</h2>
              <p className="text-gray-300 whitespace-pre-wrap">{listing.description}</p>
            </div>

            {/* Configuration Details */}
            {listing.data && (
              <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6 mb-6">
                <h2 className="text-2xl font-bold text-white mb-4">Details</h2>

                {/* Personality Traits */}
                {listing.data.personality_traits && (
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-purple-300 mb-2">Personality Traits</h3>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(listing.data.personality_traits).map(([trait, value]: [string, any]) => (
                        <div key={trait} className="flex items-center justify-between bg-slate-700/50 p-2 rounded">
                          <span className="text-gray-300 capitalize">{trait.replace('_', ' ')}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-2 bg-slate-600 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-purple-500"
                                style={{ width: `${value * 100}%` }}
                              />
                            </div>
                            <span className="text-white text-sm">{(value * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Skills */}
                {listing.data.skills && listing.data.skills.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-purple-300 mb-2">Skills</h3>
                    <div className="flex flex-wrap gap-2">
                      {listing.data.skills.map((skill: string) => (
                        <span key={skill} className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Plugins */}
                {listing.data.plugins && listing.data.plugins.length > 0 && (
                  <div>
                    <h3 className="text-lg font-semibold text-purple-300 mb-2">Plugins</h3>
                    <div className="flex flex-wrap gap-2">
                      {listing.data.plugins.map((plugin: string) => (
                        <span key={plugin} className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">
                          {plugin}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Reviews */}
            <div className="bg-slate-800/50 backdrop-blur-sm border border-purple-500/30 rounded-lg p-6">
              <h2 className="text-2xl font-bold text-white mb-4">Reviews ({reviews.length})</h2>

              {reviews.length === 0 ? (
                <p className="text-gray-400">No reviews yet. Be the first to review!</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((review) => (
                    <div key={review.id} className="bg-slate-700/50 p-4 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{review.reviewer_name}</span>
                          <div className="flex items-center gap-1">
                            {Array.from({ length: 5 }).map((_, i) => (
                              <span key={i} className={i < review.rating ? 'text-yellow-400' : 'text-gray-600'}>
                                ⭐
                              </span>
                            ))}
                          </div>
                        </div>
                        <span className="text-sm text-gray-400">
                          {new Date(review.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                      {review.comment && (
                        <p className="text-gray-300">{review.comment}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Purchase Modal */}
        {showPurchaseModal && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onClick={() => setShowPurchaseModal(false)}>
            <div className="bg-slate-800 border border-purple-500 rounded-lg p-8 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
              <h2 className="text-2xl font-bold text-white mb-4">Confirm Purchase</h2>

              <div className="mb-6">
                <p className="text-gray-300 mb-4">You are about to purchase:</p>
                <div className="bg-slate-700/50 p-4 rounded-lg">
                  <p className="text-white font-semibold mb-2">{listing.title}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Price:</span>
                    <span className="text-2xl font-bold text-purple-400">{listing.price} Essence</span>
                  </div>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setShowPurchaseModal(false)}
                  disabled={purchasing}
                  className="flex-1 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePurchase}
                  disabled={purchasing}
                  className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition disabled:opacity-50"
                >
                  {purchasing ? 'Purchasing...' : 'Confirm Purchase'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
