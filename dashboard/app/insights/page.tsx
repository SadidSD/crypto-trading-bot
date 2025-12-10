'use client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Brain, TrendingUp } from 'lucide-react';

export default function InsightsPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">AI Insights</h1>
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader><CardTitle className="flex items-center gap-2"><Brain className="text-purple-500" /> Pattern Recognition</CardTitle></CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground">Latest pattern analysis from Gemini Vision will appear here.</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="text-blue-500" /> Sentiment Analysis</CardTitle></CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground">News sentiment score: <span className="text-green-500 font-bold">BULLISH (72%)</span></p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
