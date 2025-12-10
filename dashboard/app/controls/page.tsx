'use client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input'; // Need to create Input
import { Label } from '@/components/ui/label'; // Need to create Label

export default function ControlsPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">Bot Configuration</h1>
            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader><CardTitle>Strategy Parameters</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <span className="text-sm font-medium">Stop Loss %</span>
                            <input className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="1.5" />
                        </div>
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <span className="text-sm font-medium">Take Profit 1 %</span>
                            <input className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" placeholder="2.0" />
                        </div>
                        <Button className="w-full mt-4">Save Configuration</Button>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader><CardTitle>Danger Zone</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="p-4 border border-red-500/20 bg-red-500/10 rounded-lg">
                            <h4 className="text-red-400 font-bold mb-2">Panic Button</h4>
                            <p className="text-xs text-gray-400 mb-4">Immediately close all open positions and stop the bot.</p>
                            <Button variant="destructive" className="w-full">KILL SWITCH (CLOSE ALL)</Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
