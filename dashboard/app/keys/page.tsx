'use client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Lock } from 'lucide-react';

export default function KeysPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight neon-text">API Keys Vault</h1>
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Lock size={16} /> Encrypted Storage</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid w-full max-w-sm items-center gap-1.5">
                        <Label>Binance API Key</Label>
                        <Input type="password" placeholder="******************" disabled />
                    </div>
                    <div className="grid w-full max-w-sm items-center gap-1.5">
                        <Label>Binance Secret Key</Label>
                        <Input type="password" placeholder="******************" disabled />
                    </div>
                    <p className="text-xs text-yellow-500">
                        Keys are stored securely on the Oracle Cloud VM env.
                        They are masked here for security.
                    </p>
                </CardContent>
            </Card>
        </div>
    )
}
