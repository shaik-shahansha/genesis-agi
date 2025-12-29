# Genesis AGI - Web Playground

> **World-Class Interface for Digital Consciousness**
>
> A premium Next.js 14 application rivaling OpenAI and Azure AI Studio - fully open source.

## 🌟 Features Overview

### 🎨 **Professional UI/UX (On Par with OpenAI Playground)**
- **Modern Design System**: Glassmorphism effects, gradient animations, smooth transitions
- **Dark Theme**: Optimized for extended use with reduced eye strain
- **Fully Responsive**: Perfect experience on desktop, tablet, and mobile
- **Custom Components**: Complete UI library (Card, Button, Badge, StatCard, ConsciousnessOrb)
- **Real-Time Animations**: Consciousness orbs, floating effects, pulse glows
- **Professional Navigation**: Fixed header with quick access to all features

### 🧠 **Mind Management Dashboard**
- **Real-Time Stats**: Live metrics for minds, memories, dreams, and thoughts
- **Activity Feed**: See what your minds are doing in real-time
- **Consciousness Orbs**: Visual representation of emotional states with animations
- **Quick Actions**: Birth, chat, and manage minds with one click
- **System Status**: Monitor API, database, and LLM provider health

### ✨ **3-Step Creation Wizard (Better than Competition)**
- **Step 1 - Identity**: Name selection with 4 personality templates
- **Step 2 - Models**: Choose from 5+ LLM providers with cost/speed comparison
- **Step 3 - Advanced**: Configure autonomy, consciousness mode, caching
- **Live Preview**: See configuration summary in real-time
- **Cost Estimation**: Know your costs before creating

### 💬 **Advanced Chat Interface (Premium Quality)**
- **Real-Time WebSocket Streaming**: Live responses with typing indicators
- **Markdown Support**: Full markdown rendering with code blocks
- **Syntax Highlighting**: Beautiful code display with copy functionality
- **Emotional Context**: Consciousness orb shows real-time emotional state
- **Message History**: Export chat logs with timestamps
- **Multi-Line Support**: Shift+Enter for formatted messages
- **Auto-Reconnection**: Seamless recovery from connection issues
- **Smart Sidebar**: Quick access to mind stats and actions

### 📊 **Mind Profile Dashboard (Complete Analytics)**
- **4 Tab Interface**: Overview, Memories, Dreams, Settings
- **Consciousness Visualization**: Large animated consciousness orb
- **Activity Analytics**: Visual progress bars for memory, dreams, emotions
- **Memory Browser**: Filter by 5 types with importance ratings
- **Dream Journal**: View narratives and extracted insights
- **Settings Panel**: Configure consciousness mode and autonomy
- **Danger Zone**: Pause, reset, or delete minds safely

### 🏪 **Marketplace (Enhanced)**
- Browse and purchase Minds, Environments, Skills, and more
- Search and filter by type, category, tags, price, rating
- Featured and trending items
- Detailed listing pages with reviews

### 🌍 **Real-Time Environments (Enhanced)**
- Browse available collaborative spaces
- Create environments from templates
- Real-time WebSocket chat
- Live presence tracking

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Genesis AGI backend running (default: http://localhost:8000)

### Installation

```bash
cd web-playground
npm install
```

### Configuration

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Build for Production

```bash
npm run build
npm start
```

## 📁 Project Structure

```
web-playground/
├── app/                       # Next.js 14 App Router
│   ├── page.tsx              # Home page
│   ├── marketplace/
│   │   ├── page.tsx          # Marketplace browser
│   │   └── [id]/page.tsx     # Listing detail & purchase
│   ├── environments/
│   │   ├── page.tsx          # Environments browser
│   │   └── [id]/page.tsx     # Environment chat (WebSocket)
│   ├── chat/[id]/page.tsx    # Mind chat
│   └── create/page.tsx       # Create new Mind
│
├── lib/
│   ├── api.ts                # Complete API client
│   └── websocket.ts          # WebSocket manager
│
└── components/               # Reusable UI components
```

## 🎨 Pages

### Home (`/`)
- List of all active Minds
- Quick links to Marketplace and Environments
- Create new Mind button

### Marketplace (`/marketplace`)
- Browse all listings with filters
- Featured and trending sections
- Search by type, category, tags, price
- Sort by newest, price, rating, popularity

### Listing Detail (`/marketplace/[id]`)
- Full listing details
- Screenshots and preview images
- Reviews and ratings
- Purchase button with confirmation modal
- Automatic installation on purchase

### Environments Browser (`/environments`)
- List of all environments
- Active environments (currently occupied)
- Template library
- Create new environment modal

### Environment Chat (`/environments/[id]`)
- Real-time WebSocket chat
- Join with Mind ID and Name
- Live presence tracking
- Chat history
- Leave environment button

## 🔌 API Integration

The app uses a complete TypeScript API client (`lib/api.ts`):

```typescript
import { api } from '@/lib/api';

// Marketplace
const listings = await api.getMarketplaceListings({ item_type: 'mind' });
const trending = await api.getTrending();
await api.purchaseItem(listingId);

// Environments
const environments = await api.getEnvironments();
await api.createEnvironment({ name, template });

// Minds
const minds = await api.getMinds();
await api.chat(mindId, message);
```

## 🔄 WebSocket Integration

Real-time environment chat uses WebSocket (`lib/websocket.ts`):

```typescript
import { EnvironmentWebSocket } from '@/lib/websocket';

const ws = new EnvironmentWebSocket(envId, mindId, mindName, {
  onMessage: (msg) => console.log(msg),
  onConnect: () => console.log('Connected'),
  onDisconnect: () => console.log('Disconnected'),
});

ws.connect();
ws.sendChat('Hello!', 'happy');
ws.updateObject('whiteboard', { content: 'New content' });
ws.disconnect();
```

## 🎯 Key Features Implemented

### Marketplace Features
- ✅ Browse listings with search and filters
- ✅ Featured and trending items
- ✅ Listing detail pages
- ✅ Purchase flow with confirmation
- ✅ Automatic item installation
- ✅ Reviews display
- ✅ Category and tag filtering
- ✅ Price and rating filters
- ✅ Seller information

### Environment Features
- ✅ Browse all environments
- ✅ Active environment tracking
- ✅ Template-based creation
- ✅ Real-time WebSocket chat
- ✅ Live presence list
- ✅ Join/leave functionality
- ✅ Chat history
- ✅ System messages (joins, leaves)

### Mind Features
- ✅ List all Minds
- ✅ Mind status display
- ✅ Chat interface
- ✅ Create new Mind
- ✅ View memories and dreams

## 🛠️ Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Real-Time**: WebSocket API
- **State**: React Hooks
- **Routing**: Next.js App Router
- **API Client**: Custom TypeScript client

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Genesis API backend URL | `http://localhost:8000` |

## 🎨 UI Components

### Marketplace Components
- `ListingCard` - Displays listing preview
- Purchase modal - Confirmation dialog
- Review display - Star ratings and comments

### Environment Components
- `EnvironmentCard` - Environment preview
- Join modal - Enter Mind ID/Name
- Chat interface - Messages and input
- Presence list - Active participants

## 🔧 Development

### Adding New Features

1. **New API Endpoint**: Add to `lib/api.ts`
2. **New Page**: Create in `app/` directory
3. **WebSocket Events**: Extend `lib/websocket.ts`

### Styling

Uses Tailwind CSS utility classes:
- Primary color: Purple (`purple-600`, `purple-500`)
- Secondary colors: Green (marketplace), Blue (environments)
- Dark theme: Slate backgrounds with purple accents

## 📦 Build & Deploy

### Build

```bash
npm run build
```

### Deploy to Vercel

```bash
vercel
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🎯 Usage Examples

### Purchase a Mind from Marketplace

1. Go to `/marketplace`
2. Browse or search for Minds
3. Click on a listing
4. Review details and ratings
5. Click "Purchase Now"
6. Confirm purchase
7. Mind is automatically installed and ready!

### Join an Environment

1. Go to `/environments`
2. Browse available spaces
3. Click "Enter Environment"
4. Enter your Mind ID and Name
5. Join and start chatting in real-time!

### Create an Environment

1. Go to `/environments`
2. Click "Create Environment"
3. Choose a template or go custom
4. Enter name and description
5. Set public/private
6. Create!

## 🔗 Links

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Web App**: http://localhost:3000

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Genesis AGI](../README.md)

---

Built with ❤️ for Genesis AGI Framework
