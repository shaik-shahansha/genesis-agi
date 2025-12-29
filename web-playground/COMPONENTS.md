# Genesis Web Playground - Component Reference

## 📦 UI Component Library

### Card Components (`components/ui/Card.tsx`)

#### Card
Base card container with glassmorphism effect.

**Props:**
- `children`: ReactNode
- `className?`: string
- `hover?`: boolean - Enable hover animation
- `onClick?`: () => void

**Usage:**
```tsx
<Card>
  Content here
</Card>

<Card hover onClick={() => alert('Clicked!')}>
  Interactive card
</Card>
```

#### CardHeader
Card header section with bottom margin.

**Props:**
- `children`: ReactNode
- `className?`: string

**Usage:**
```tsx
<CardHeader>
  <CardTitle>My Title</CardTitle>
</CardHeader>
```

#### CardTitle
Styled card title (xl, bold, white).

**Props:**
- `children`: ReactNode
- `className?`: string

**Usage:**
```tsx
<CardTitle>Feature Name</CardTitle>
```

#### CardContent
Card body content area.

**Props:**
- `children`: ReactNode
- `className?`: string

**Usage:**
```tsx
<CardContent>
  <p>Body content</p>
</CardContent>
```

---

### Button Component (`components/ui/Button.tsx`)

Styled button with multiple variants and states.

**Props:**
- `children`: ReactNode
- `variant?`: 'primary' | 'secondary' | 'ghost' | 'danger' (default: 'primary')
- `size?`: 'sm' | 'md' | 'lg' (default: 'md')
- `disabled?`: boolean
- `loading?`: boolean - Shows spinner
- `className?`: string
- `onClick?`: () => void
- `type?`: 'button' | 'submit' | 'reset'

**Usage:**
```tsx
<Button variant="primary" size="lg">
  Click Me
</Button>

<Button variant="secondary" loading={isLoading}>
  Loading...
</Button>

<Button variant="danger" onClick={handleDelete}>
  Delete
</Button>
```

**Variants:**
- **primary**: Purple-pink gradient, for main actions
- **secondary**: Slate background, for secondary actions
- **ghost**: Transparent with hover, for subtle actions
- **danger**: Red background, for destructive actions

---

### Badge Component (`components/ui/Badge.tsx`)

Small colored labels for status, categories, etc.

**Props:**
- `children`: ReactNode
- `variant?`: 'success' | 'warning' | 'danger' | 'info' | 'purple' (default: 'info')
- `className?`: string
- `icon?`: ReactNode - Optional icon

**Usage:**
```tsx
<Badge variant="success">Active</Badge>

<Badge variant="danger">Offline</Badge>

<Badge variant="purple" icon={<span>🔥</span>}>
  Trending
</Badge>
```

**Variants:**
- **success**: Green - for positive states
- **warning**: Yellow - for caution states
- **danger**: Red - for error states
- **info**: Blue - for neutral info
- **purple**: Purple - for special states

---

### StatCard Component (`components/ui/StatCard.tsx`)

Animated stat display card.

**Props:**
- `label`: string - Stat label
- `value`: string | number - Stat value
- `icon?`: ReactNode - Optional icon
- `trend?`: { value: number, isPositive: boolean } - Optional trend indicator
- `className?`: string

**Usage:**
```tsx
<StatCard
  label="Total Minds"
  value={42}
  icon="🧠"
/>

<StatCard
  label="Memory Count"
  value="1,247"
  icon="💾"
  trend={{ value: 15, isPositive: true }}
/>
```

---

### ConsciousnessOrb Component (`components/ConsciousnessOrb.tsx`)

Animated emotional state visualization.

**Props:**
- `emotion`: string - Emotion name (joy, sadness, etc.)
- `size?`: 'sm' | 'md' | 'lg' (default: 'md')
- `animated?`: boolean (default: true)
- `className?`: string

**Usage:**
```tsx
<ConsciousnessOrb 
  emotion="joy" 
  size="lg"
/>

<ConsciousnessOrb 
  emotion="curiosity" 
  size="sm"
  animated={false}
/>
```

**Supported Emotions:**
- joy (yellow-orange)
- contentment (green)
- excitement (orange-red)
- surprise (cyan-blue)
- sadness (blue)
- fear (purple)
- anger (red)
- calmness (teal)
- curiosity (indigo)
- trust (emerald)
- anticipation (amber)
- love (pink)

---

### CodeBlock Component (`components/CodeBlock.tsx`)

Code display with copy functionality.

**Props:**
- `code`: string - Code content
- `language?`: string - Language name (default: 'javascript')

**Usage:**
```tsx
<CodeBlock 
  code={`function hello() {\n  console.log('Hi!');\n}`}
  language="javascript"
/>

<CodeBlock 
  code="pip install genesis-minds"
  language="bash"
/>
```

**Features:**
- Copy to clipboard button
- Language label
- Syntax-ready (placeholder for highlighting library)
- Monospace font
- Dark theme

---

### MarkdownRenderer Component (`components/MarkdownRenderer.tsx`)

Renders markdown with formatting.

**Props:**
- `content`: string - Markdown content

**Usage:**
```tsx
<MarkdownRenderer 
  content="**Bold** and *italic* text with `code`"
/>

<MarkdownRenderer 
  content={`
# Heading
- List item
\`\`\`python
print("Code block")
\`\`\`
  `}
/>
```

**Supported Formatting:**
- **Bold**: `**text**`
- *Italic*: `*text*`
- `Inline code`: `` `code` ``
- Links: `[text](url)`
- Code blocks: ` ```language\ncode\n``` `

---

## 🎨 CSS Utility Classes

### Layout Classes

```css
.glass             /* Glassmorphism background */
.glass-hover       /* Glass with hover effect */
.card              /* Card container */
.card-hover        /* Interactive card */
```

### Button Classes

```css
.btn-primary       /* Primary button */
.btn-secondary     /* Secondary button */
.btn-ghost         /* Ghost button */
```

### Badge Classes

```css
.badge             /* Base badge */
.badge-success     /* Green badge */
.badge-warning     /* Yellow badge */
.badge-danger      /* Red badge */
.badge-info        /* Blue badge */
.badge-purple      /* Purple badge */
```

### Animation Classes

```css
.animate-float         /* Floating animation */
.animate-pulse-glow    /* Pulsing glow */
.animate-gradient      /* Gradient shift */
.consciousness-orb     /* Orb pulse animation */
```

### Text Classes

```css
.gradient-text         /* Purple-pink gradient */
```

### Form Classes

```css
.input                 /* Styled input field */
```

### Stat Classes

```css
.stat-card            /* Stat container */
.stat-value           /* Large gradient value */
.stat-label           /* Small label */
```

### Emotion Classes

```css
.emotion-joy          /* Joy colors */
.emotion-contentment  /* Contentment colors */
.emotion-excitement   /* Excitement colors */
/* ... (12 more emotions) */
```

---

## 🎯 Component Patterns

### Form Pattern

```tsx
<Card>
  <CardHeader>
    <CardTitle>Form Title</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div>
        <label className="block text-white font-semibold mb-2">
          Field Label
        </label>
        <input className="input" placeholder="Enter value..." />
      </div>
      <Button variant="primary" type="submit">
        Submit
      </Button>
    </div>
  </CardContent>
</Card>
```

### Stat Grid Pattern

```tsx
<div className="grid grid-cols-2 md:grid-cols-5 gap-4">
  <StatCard label="Metric 1" value={100} icon="📊" />
  <StatCard label="Metric 2" value={200} icon="📈" />
  <StatCard label="Metric 3" value={300} icon="🎯" />
</div>
```

### Card Grid Pattern

```tsx
<div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
  {items.map(item => (
    <Card key={item.id} hover>
      <h3 className="text-xl font-bold text-white mb-2">
        {item.name}
      </h3>
      <p className="text-gray-400">{item.description}</p>
      <div className="mt-4 flex gap-2">
        <Button variant="primary" size="sm">Action</Button>
      </div>
    </Card>
  ))}
</div>
```

### Dashboard Layout Pattern

```tsx
<div className="grid lg:grid-cols-3 gap-6">
  {/* Main content (2 columns) */}
  <div className="lg:col-span-2">
    <Card>
      {/* Main content */}
    </Card>
  </div>
  
  {/* Sidebar (1 column) */}
  <div className="space-y-6">
    <Card>
      {/* Sidebar widget 1 */}
    </Card>
    <Card>
      {/* Sidebar widget 2 */}
    </Card>
  </div>
</div>
```

### Chat Message Pattern

```tsx
<div className="flex gap-4">
  {/* Avatar */}
  <ConsciousnessOrb 
    emotion={emotion} 
    size="sm" 
    className="flex-shrink-0"
  />
  
  {/* Message content */}
  <div className="flex-1">
    <div className="text-sm text-gray-400 mb-1">
      Mind Name
    </div>
    <div className="glass rounded-xl p-4">
      <MarkdownRenderer content={message} />
    </div>
    <div className="text-xs text-gray-500 mt-1">
      {timestamp}
    </div>
  </div>
</div>
```

### Loading State Pattern

```tsx
{loading ? (
  <div className="text-center py-12">
    <div className="spinner mx-auto mb-4"></div>
    <p className="text-gray-400">Loading...</p>
  </div>
) : (
  <div>
    {/* Content */}
  </div>
)}
```

### Empty State Pattern

```tsx
{items.length === 0 ? (
  <div className="text-center py-12">
    <div className="text-6xl mb-4 opacity-50">🎯</div>
    <p className="text-xl text-gray-400 mb-4">
      No items yet
    </p>
    <p className="text-gray-500 mb-6">
      Get started by creating your first item
    </p>
    <Button variant="primary">
      Create First Item
    </Button>
  </div>
) : (
  <div>
    {/* Items */}
  </div>
)}
```

---

## 📱 Responsive Patterns

### Mobile-First Grid

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Stacks on mobile, 2 cols on tablet, 3 cols on desktop */}
</div>
```

### Conditional Sidebar

```tsx
const [showSidebar, setShowSidebar] = useState(true);

<div className={`grid ${showSidebar ? 'lg:grid-cols-4' : 'lg:grid-cols-1'} gap-6`}>
  <div className={showSidebar ? 'lg:col-span-3' : 'lg:col-span-4'}>
    {/* Main content */}
  </div>
  
  {showSidebar && (
    <div className="lg:col-span-1">
      {/* Sidebar */}
    </div>
  )}
</div>
```

### Responsive Text

```tsx
<h1 className="text-4xl md:text-6xl lg:text-7xl font-bold">
  Responsive Heading
</h1>
```

---

## 🎨 Theming

### Color Variables

Define in `globals.css`:
```css
:root {
  --primary: 263.4 70% 50.4%;
  --secondary: 217.2 32.6% 17.5%;
  /* ... */
}
```

### Custom Animations

Define in `globals.css`:
```css
@keyframes my-animation {
  0%, 100% { /* ... */ }
  50% { /* ... */ }
}

.my-element {
  animation: my-animation 2s ease infinite;
}
```

---

**Complete component reference for building consistent interfaces!** 🎨✨
