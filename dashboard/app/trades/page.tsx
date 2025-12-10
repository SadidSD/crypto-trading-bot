'use client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TradesPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">Trade History</h1>
            <Card>
                <CardHeader>
                    <CardTitle>All Executions</CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">Trade table will go here connecting to Redis history.</p>
                </CardContent>
            </Card>
        </div>
    )
}
