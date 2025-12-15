'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PipelineViewer } from '@/components/widgets/PipelineViewer';
import { Button } from '@/components/ui/button';
import { useBotStore } from '@/store/botStore';
import { Activity, DollarSign, TrendingUp, Zap } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DashboardPage() {
  const { status, candidates, balance, pnl, updateStats } = useBotStore();
  const [loading, setLoading] = useState(false);

  const toggleBot = async () => {
    setLoading(true);
    const endpoint = status === 'active' ? '/control/stop' : '/control/start';
    try {
      await fetch(`${API_URL}${endpoint}`, { method: 'POST' });
      // Optimistic update, WS will confirm
      updateStats({ status: status === 'active' ? 'paused' : 'active' });
    } catch (e: any) {
      console.error("Toggle Bot Error:", e);
      alert(`Failed to toggle bot. API: ${API_URL}\nError: ${e.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight neon-text">Dashboard</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline">Refresh</Button>
          <Button
            variant={status === 'active' ? 'destructive' : 'default'}
            onClick={toggleBot}
            disabled={loading}
          >
            {loading ? 'Processing...' : (status === 'active' ? 'Stop Bot' : 'Start Bot')}
          </Button>
        </div>
      </div>

      {/* STATS GRID */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${balance.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">+20.1% from last month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily PnL</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">+${pnl.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground">Today's profit</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Candidates</CardTitle>
            <Zap className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{candidates}</div>
            <p className="text-xs text-muted-foreground">Scanning 200+ coins</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{status}</div>
            <p className="text-xs text-muted-foreground">Uptime: 4h 20m</p>
          </CardContent>
        </Card>
      </div>

      {/* PIPELINE VISUALIZATION (New) */}
      <PipelineViewer />

      {/* CHARTS / WIDGETS */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Market Overview (BTC/USDT)</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px] flex items-center justify-center bg-black/20 rounded-md border border-white/5">
              <span className="text-muted-foreground">TradingView Chart Loaded Here</span>
              {/* Implement TradingView Widget Here */}
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardContent>
              {/* Activity Feed */}
              <div className="space-y-4 pt-4">
                {[1, 2, 3].map((_, i) => (
                  <div key={i} className="flex items-center">
                    <div className="ml-4 space-y-1">
                      <p className="text-sm font-medium leading-none">Order Executed</p>
                      <p className="text-sm text-muted-foreground">Bought BTC at $98,000</p>
                    </div>
                    <div className="ml-auto font-medium">+$120</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </CardHeader>
        </Card>
      </div>
    </div>
  );
}
