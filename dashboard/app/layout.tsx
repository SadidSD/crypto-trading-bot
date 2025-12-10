import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/layout/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Exhaustion Bot Dashboard',
  description: 'AI Trading Bot Control Center',
};

import { WebSocketProvider } from '@/components/providers/WebSocketProvider';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-foreground flex`}>
        <Sidebar />
        <main className="flex-1 max-h-screen overflow-y-auto p-8">
          <WebSocketProvider>
            {children}
          </WebSocketProvider>
        </main>
      </body>
    </html>
  );
}
