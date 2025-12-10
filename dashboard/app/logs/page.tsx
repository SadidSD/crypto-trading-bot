'use client';
import { useBotStore } from '@/store/botStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function LogsPage() {
    const { logs } = useBotStore();

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">System Logs</h1>
            <Card className="bg-black/40 border-gray-800">
                <CardHeader>
                    <CardTitle>Live Feed</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="font-mono text-sm space-y-2 h-[500px] overflow-y-auto">
                        {logs.map((log, i) => (
                            <div key={i} className="border-b border-gray-800 pb-1 text-gray-400">
                                <span className="text-blue-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
                                {typeof log === 'string' ? log : JSON.stringify(log)}
                            </div>
                        ))}
                        {logs.length === 0 && <span className="text-gray-600">No logs received yet...</span>}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
