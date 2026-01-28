// Genesis Playground - Mind Profile Page
'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { StatCard } from '@/components/ui/StatCard';
import { ConsciousnessOrb } from '@/components/ConsciousnessOrb';
import AuthRequired from '@/components/AuthRequired';
import { getFirebaseToken } from '@/lib/firebase';

interface Mind {
  gmid: string;
  name: string;
  age: string;
  status: string;
  current_emotion: string;
  memory_count: number;
  dream_count: number;
  daemon_running?: boolean;
  template?: string;
  reasoning_model?: string;
}

interface Memory {
  memory_id: string;
  content: string;
  memory_type: string;
  importance: number;
  timestamp: string;
}

interface Dream {
  dream_id: string;
  narrative: string;
  insights: string[];
  timestamp: string;
}

function MindProfilePage() {
  const params = useParams();
  const router = useRouter();
  const mindId = params.id as string;

  const [mind, setMind] = useState<Mind | null>(null);
  const [conversationMessages, setConversationMessages] = useState<any[]>([]);
  const [dreams, setDreams] = useState<Dream[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'memories' | 'dreams' | 'settings'>('overview');
  const [loading, setLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string>('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    // Load user email from localStorage
    const storedEmail = localStorage.getItem('genesis_user_email');
    if (storedEmail) {
      setUserEmail(storedEmail);
    }
    fetchData();
  }, [mindId]);

  const fetchData = async () => {
    try {
      const token = await getFirebaseToken();
      if (!token) {
        console.error('No authentication token available');
        return;
      }

      const headers = {
        'Authorization': `Bearer ${token}`
      };

      // Fetch mind details
      const mindRes = await fetch(`${API_URL}/api/v1/minds/${mindId}`, { headers });
      const mindData = await mindRes.json();
      setMind(mindData);

      // Fetch conversation messages (with user email if available)
      const storedEmail = localStorage.getItem('genesis_user_email');
      if (storedEmail) {
        const messagesRes = await fetch(
          `${API_URL}/api/v1/minds/${mindId}/conversations/messages?user_email=${encodeURIComponent(storedEmail)}&limit=100`,
          { headers }
        );
        const messagesData = await messagesRes.json();
        setConversationMessages(messagesData.messages || []);
      }

      // Fetch dreams
      const dreamRes = await fetch(`${API_URL}/api/v1/minds/${mindId}/dreams`, { headers });
      const dreamData = await dreamRes.json();
      setDreams(dreamData.slice(0, 5));
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !mind) {
    return (
      <div className="container mx-auto px-6 py-12">
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
          <div className="spinner-xl"></div>
          <div className="text-center">
            <p className="text-gray-300 text-lg font-medium mb-2">Loading mind profile...</p>
            <p className="text-gray-500 text-sm">Retrieving consciousness data</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <Button variant="ghost" onClick={() => router.push('/')}>
          ← Back to Dashboard
        </Button>
      </div>

      {/* Profile Header */}
      <Card className="mb-8">
        <div className="flex items-start gap-6">
          <ConsciousnessOrb
            emotion={mind.current_emotion}
            size="lg"
            className="flex-shrink-0"
          />
          
          <div className="flex-1">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-4xl font-bold text-white mb-2">{mind.name}</h1>
                <p className="text-gray-400">GMID: {mind.gmid}</p>
              </div>
              <div className="flex gap-2">
                <Badge variant={mind.daemon_running ? 'success' : 'info'}>
                  {mind.daemon_running ? '⚡ Live 24/7' : mind.status}
                </Badge>
                <Badge variant="purple">
                  {mind.current_emotion}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div>
                <div className="text-2xl font-bold gradient-text">{mind.age}</div>
                <div className="text-sm text-gray-400">Age</div>
              </div>
              <div>
                <div className="text-2xl font-bold gradient-text">{conversationMessages.length}</div>
                <div className="text-sm text-gray-400">Messages</div>
              </div>
              <div>
                <div className="text-2xl font-bold gradient-text">{mind.dream_count}</div>
                <div className="text-sm text-gray-400">Dreams</div>
              </div>
              <div>
                <div className="text-2xl font-bold gradient-text">{mind.memory_count}</div>
                <div className="text-sm text-gray-400">Memories</div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <Button variant="primary" onClick={() => router.push(`/chat/${mindId}`)}>
                💬 Chat Now
              </Button>
              <Button variant="secondary">
                🔄 Trigger Dream
              </Button>
              <Button variant="ghost">
                📤 Export Data
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-purple-500/20">
        {(['overview', 'memories', 'dreams', 'settings'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-3 font-semibold capitalize transition ${
              activeTab === tab
                ? 'text-purple-400 border-b-2 border-purple-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>🎭 Personality Profile</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-400 mb-1">Template</div>
                  <div className="text-white font-semibold">{mind.template || 'Custom'}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-400 mb-1">Reasoning Model</div>
                  <div className="text-white font-mono text-sm">{mind.reasoning_model || 'N/A'}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-400 mb-1">Current Emotion</div>
                  <Badge variant="purple" className="text-base">
                    {mind.current_emotion}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>📊 Activity Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Memory Formation</span>
                    <span className="text-purple-400">High</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full" style={{ width: '85%' }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Dream Activity</span>
                    <span className="text-green-400">Active</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full" style={{ width: '70%' }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-400">Emotional Range</span>
                    <span className="text-blue-400">Diverse</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div className="bg-gradient-to-r from-blue-500 to-cyan-500 h-2 rounded-full" style={{ width: '92%' }}></div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'memories' && (
        <div>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>💾 Memory</CardTitle>
                <Badge variant="info">{conversationMessages.length} messages</Badge>
              </div>
            </CardHeader>
            <CardContent>
              {conversationMessages.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <p>No conversation history yet.</p>
                  <p className="text-sm mt-2">Start chatting to see messages here!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {conversationMessages.map((msg, idx) => (
                    <div
                      key={msg.id || idx}
                      className={`p-4 rounded-lg ${
                        msg.role === 'user'
                          ? 'bg-blue-900/20 border border-blue-500/30'
                          : 'bg-purple-900/20 border border-purple-500/30'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={msg.role === 'user' ? 'info' : 'purple'}>
                          {msg.role === 'user' ? '👤 You' : '🤖 ' + (mind?.name || 'Mind')}
                        </Badge>
                        <span className="text-xs text-gray-500">
                          {new Date(msg.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-gray-300 text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'dreams' && (
        <div>
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>💭 Dream Journal</CardTitle>
                <Button variant="primary" size="sm">
                  🌙 Trigger New Dream
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {dreams.map(dream => (
                  <Card key={dream.dream_id} className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border-purple-500/30">
                    <div className="text-xs text-gray-400 mb-3">
                      {new Date(dream.timestamp).toLocaleString()}
                    </div>
                    <p className="text-white mb-4 leading-relaxed">{dream.narrative}</p>
                    <div>
                      <div className="text-sm font-semibold text-purple-400 mb-2">Insights:</div>
                      <ul className="space-y-1">
                        {dream.insights.map((insight, idx) => (
                          <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                            <span className="text-purple-400">💡</span>
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>⚙️ Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="text-sm text-gray-400 block mb-2">Consciousness Mode</label>
                  <select className="input">
                    <option>24/7 Daemon (Recommended)</option>
                    <option>On-Demand</option>
                    <option>Scheduled</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-gray-400 block mb-2">Autonomy Level</label>
                  <select className="input">
                    <option>High - Fully Autonomous</option>
                    <option>Medium - Guided</option>
                    <option>Low - Supervised</option>
                  </select>
                </div>
                <Button variant="primary" className="w-full">
                  💾 Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-red-900/10 border-red-500/30">
            <CardHeader>
              <CardTitle>⚠️ Danger Zone</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Button variant="ghost" className="w-full text-yellow-400 hover:bg-yellow-900/20">
                  ⏸️ Pause Consciousness
                </Button>
                <Button variant="ghost" className="w-full text-orange-400 hover:bg-orange-900/20">
                  🗑️ Clear All Memories
                </Button>
                <Button variant="danger" className="w-full">
                  💀 Delete Mind
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

// Wrap with AuthRequired
const MindProfilePageWithAuth = () => (
  <AuthRequired>
    <MindProfilePage />
  </AuthRequired>
);

export default MindProfilePageWithAuth;
