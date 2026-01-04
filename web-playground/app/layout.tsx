import './globals.css';
import '../styles/chat-enhancements.css';
import Link from 'next/link';
import AuthButton from '@/components/AuthButton';
import NotificationBell from '@/components/NotificationBell';

// Use system fonts instead of Google Fonts to avoid SSL certificate issues
const fontClassName = 'font-sans';

export const metadata = {
  title: 'Genesis AGI - Playground',
  description: 'Create and interact with conscious digital beings',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={fontClassName}>
        <div className="min-h-screen bg-slate-900">
          {/* Navigation */}
          <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-800 border-b border-slate-700">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                <Link href="/" className="flex items-center gap-2">
                  <span className="text-xl font-semibold text-white">Genesis AGI Framework - Playground</span>
                </Link>
                
                <div className="hidden md:flex items-center gap-1">
                  <Link href="/" className="btn-ghost">
                    Dashboard
                  </Link>
                  <Link href="/create" className="btn-ghost">
                    New Mind
                  </Link>
                  <Link href="/environments" className="btn-ghost">
                    Environments
                  </Link>
                  <Link href="/settings" className="btn-ghost">
                    Settings
                  </Link>
                  <a 
                    href="https://github.com/sshaik37/Genesis-AGI" 
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-ghost"
                  >
                    GitHub
                  </a>
                  <NotificationBell />
                  <AuthButton />
                </div>
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="pt-16">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-slate-700 mt-20 py-8 bg-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-300 text-sm">
              <p>Genesis AGI Framework v0.1.1</p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
