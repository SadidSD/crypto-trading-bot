'use client';
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface HeatmapItem {
    symbol: string;
    value: number;
    price: number;
}

export default function MarketHeatmap() {
    const [data, setData] = useState<HeatmapItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        fetch(`${API_URL}/insights/heatmap`)
            .then(res => res.json())
            .then(d => {
                setData(d);
                setLoading(false);
            })
            .catch(err => console.error(err));

        const interval = setInterval(() => {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            fetch(`${API_URL}/insights/heatmap`)
                .then(res => res.json())
                .then(setData);
        }, 10000); // Poll every 10s

        return () => clearInterval(interval);
    }, []);

    if (loading) return <div className="p-10 text-center text-muted-foreground">Loading Heatmap...</div>;

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {data.map((item) => (
                <div
                    key={item.symbol}
                    className={cn(
                        "flex flex-col items-center justify-center p-4 rounded-md border transition-all hover:scale-105 cursor-pointer",
                        item.value > 0
                            ? (item.value > 5 ? "bg-green-500/20 border-green-500/50 text-green-400" : "bg-green-900/20 border-green-800 text-green-300")
                            : (item.value < -5 ? "bg-red-500/20 border-red-500/50 text-red-400" : "bg-red-900/20 border-red-800 text-red-300")
                    )}
                >
                    <span className="text-xs font-bold text-gray-200">{item.symbol}</span>
                    <span className="text-lg font-bold">{item.value > 0 ? '+' : ''}{item.value}%</span>
                    <span className="text-[10px] text-gray-400 opacity-75">${item.price}</span>
                </div>
            ))}
            {data.length === 0 && <div className="col-span-full text-center p-10 text-gray-500">No market data available yet...</div>}
        </div>
    );
}
