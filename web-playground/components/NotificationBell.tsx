'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Notification {
  notification_id: string;
  mind_id: string;
  mind_name: string;
  recipient: string;
  title: string;
  message: string;
  priority: string;
  created_at: string;
  delivered: boolean;
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const userEmail = typeof window !== 'undefined' 
    ? localStorage.getItem('user_email') || 'web_user@genesis.local'
    : 'web_user@genesis.local';

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      
      // Use the new all-in-one endpoint
      const response = await fetch(
        `${API_URL}/api/v1/system/notifications/all?user_email=${encodeURIComponent(userEmail)}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.notifications || []);
      } else {
        console.error('Error fetching notifications:', response.statusText);
        setNotifications([]);
      }
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    
    // Poll for new notifications every 5 minutes
    const interval = setInterval(fetchNotifications, 300000);
    
    return () => clearInterval(interval);
  }, []);

  const handleNotificationClick = async (notification: Notification) => {
    // Mark as delivered
    try {
      await fetch(
        `${API_URL}/api/v1/minds/${notification.mind_id}/notifications/${notification.notification_id}/mark-delivered`,
        { method: 'POST' }
      );
      
      // Remove from list
      setNotifications(prev => prev.filter(n => n.notification_id !== notification.notification_id));
      
      // Navigate to chat with the Mind
      router.push(`/chat/${notification.mind_id}`);
    } catch (error) {
      console.error('Error marking notification as delivered:', error);
    }
    
    setShowDropdown(false);
  };

  const unreadCount = notifications.length;

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="relative p-2 text-gray-300 hover:text-white transition-colors"
        title="Notifications"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {showDropdown && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setShowDropdown(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute right-0 mt-2 w-80 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto">
            <div className="p-3 border-b border-slate-700">
              <h3 className="text-sm font-semibold text-white">Notifications</h3>
            </div>
            
            {loading ? (
              <div className="p-4 text-center text-gray-400">
                Loading...
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-400">
                No notifications
              </div>
            ) : (
              <div>
                {notifications.map((notification) => (
                  <button
                    key={notification.notification_id}
                    onClick={() => handleNotificationClick(notification)}
                    className="w-full text-left p-3 hover:bg-slate-700 border-b border-slate-700 last:border-b-0 transition-colors"
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-blue-400">
                            {notification.mind_name}
                          </span>
                          {notification.priority === 'urgent' && (
                            <span className="text-xs px-1.5 py-0.5 bg-red-500 text-white rounded">
                              Urgent
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-white mb-1 truncate">
                          {notification.title}
                        </p>
                        <p className="text-xs text-gray-400 line-clamp-2">
                          {notification.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(notification.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
