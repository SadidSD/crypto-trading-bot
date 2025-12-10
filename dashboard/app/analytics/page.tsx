'use client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import MarketHeatmap from '@/components/widgets/MarketHeatmap';

const data = [
    { name: 'Mon', pnl: 40 },
    { name: 'Tue', pnl: 30 },
    { name: 'Wed', pnl: 20 },
    { name: 'Thu', pnl: 27 },
    { name: 'Fri', pnl: 18 },
    { name: 'Sat', pnl: 23 },
    { name: 'Sun', pnl: 34 },
];

export default function AnalyticsPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">Analytics</h1>

            <Card>
                <CardHeader>
                    <CardTitle>Market Heatmap (4H Change)</CardTitle>
                </CardHeader>
                <CardContent>
                    <MarketHeatmap />
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Profit & Loss (7 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis dataKey="name" stroke="#888" />
                                <YAxis stroke="#888" />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                                />
                                <Line type="monotone" dataKey="pnl" stroke="#8884d8" strokeWidth={2} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
