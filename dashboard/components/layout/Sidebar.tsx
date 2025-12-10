'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Activity, Settings, BarChart2, Terminal, Shield, Cpu } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Trades', href: '/trades', icon: Activity },
    { name: 'Analytics', href: '/analytics', icon: BarChart2 },
    { name: 'Controls', href: '/controls', icon: Settings },
    { name: 'AI Insights', href: '/insights', icon: Cpu },
    { name: 'Logs', href: '/logs', icon: Terminal },
    { name: 'API Keys', href: '/keys', icon: Shield },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="w-64 h-screen bg-black/50 border-r border-white/10 flex flex-col p-4">
            <div className="flex items-center gap-2 mb-8 px-2">
                <Shield className="text-blue-500" />
                <h1 className="font-bold text-lg tracking-wider">EXHAUSTION</h1>
            </div>

            <nav className="space-y-2">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 rounded-md transition-all text-sm font-medium",
                                isActive ? "bg-blue-600/20 text-blue-400" : "text-gray-400 hover:text-white hover:bg-white/5"
                            )}
                        >
                            <Icon size={18} />
                            {item.name}
                        </Link>
                    )
                })}
            </nav>

            <div className="mt-auto px-2">
                <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 p-4 rounded-xl border border-blue-500/20">
                    <h4 className="text-xs text-gray-400 mb-1">Status</h4>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                        <span className="text-sm font-bold text-green-400">Online</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
