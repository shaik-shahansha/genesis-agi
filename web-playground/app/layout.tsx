import './globals.css';
import '../styles/chat-enhancements.css';
import type { Metadata, Viewport } from 'next';
import { AuthProvider } from '@/lib/auth-context';
import { MindProvider } from '@/lib/MindContext';
import { ThemeProvider, THEME_STORAGE_KEY } from '@/components/shell/ThemeProvider';
import AppShell from '@/components/shell/AppShell';

export const metadata: Metadata = {
  title: 'Genesis — Digital Beings Workspace',
  description:
    'Operate persistent digital beings: conversation, memory, workspace, and a governed action ' +
    'boundary with approvals and auditable receipts.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f8f9fb' },
    { media: '(prefers-color-scheme: dark)', color: '#090a0d' },
  ],
};

/**
 * Applies the stored theme before the first paint.
 *
 * Without this the page renders in the default (light) theme and then snaps to
 * the user's choice, which is a visible flash on every navigation. It must stay
 * inline and synchronous, so it cannot live in the React tree.
 */
const themeBootstrapScript = `
(function () {
  try {
    var stored = localStorage.getItem('${THEME_STORAGE_KEY}');
    var preference = (stored === 'light' || stored === 'dark' || stored === 'system') ? stored : 'light';
    var dark = preference === 'dark' ||
      (preference === 'system' && window.matchMedia &&
       window.matchMedia('(prefers-color-scheme: dark)').matches);
    var root = document.documentElement;
    if (dark) root.classList.add('dark');
    root.style.colorScheme = dark ? 'dark' : 'light';
  } catch (e) { /* keep the default theme */ }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body className="font-sans">
        <ThemeProvider>
          <AuthProvider>
            <MindProvider>
              <AppShell>{children}</AppShell>
            </MindProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
