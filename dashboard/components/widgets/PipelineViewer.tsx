'use client';
import { useBotStore } from '@/store/botStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Filter, Brain, Zap, CheckCircle2, XCircle, Clock } from 'lucide-react';

export function PipelineViewer() {
    const pipelineEvents = useBotStore((state) => state.pipelineEvents);

    // Filter events by stage for column view
    // Since we only keep 50, we just show them in a feed style per column
    const scannerEvents = pipelineEvents.filter(e => e.stage === 'scanner');
    const engineEvents = pipelineEvents.filter(e => e.stage === 'engine');
    const executionEvents = pipelineEvents.filter(e => e.stage === 'execution');

    const getStatusIcon = (status: string) => {
        if (status === 'pass' || status === 'executed') return <CheckCircle2 className="h-4 w-4 text-green-500" />;
        if (status === 'fail') return <XCircle className="h-4 w-4 text-red-500" />;
        if (status === 'processing') return <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />;
        return null;
    };

    const getStatusColor = (status: string) => {
        if (status === 'pass' || status === 'executed') return "bg-green-500/10 text-green-500 border-green-500/20";
        if (status === 'fail') return "bg-red-500/10 text-red-500 border-red-500/20";
        if (status === 'processing') return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
        return "bg-slate-800 text-slate-400";
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* LAYER 1: SCANNER */}
            <Card className="border-l-4 border-l-blue-500 bg-black/40 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Filter className="h-4 w-4 text-blue-500" /> Layer 1: Scanner
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
                    {scannerEvents.length === 0 && <div className="text-xs text-muted-foreground text-center py-4">Waiting for candidates...</div>}
                    {scannerEvents.map((evt, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5 animate-in fade-in slide-in-from-left-2 duration-300">
                            <div>
                                <div className="font-bold text-sm tracking-wide">{evt.symbol}</div>
                                <div className="text-[10px] text-muted-foreground">{evt.details}</div>
                            </div>
                            <Badge variant="outline" className="border-blue-500/30 text-blue-400">Found</Badge>
                        </div>
                    ))}
                </CardContent>
            </Card>

            {/* LAYER 2: AI ENGINE */}
            <Card className="border-l-4 border-l-purple-500 bg-black/40 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Brain className="h-4 w-4 text-purple-500" /> Layer 2: Decision
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
                    {engineEvents.length === 0 && <div className="text-xs text-muted-foreground text-center py-4">AI Idle...</div>}
                    {engineEvents.map((evt, i) => (
                        <div key={i} className={`flex items-center justify-between p-2 rounded border ${getStatusColor(evt.status)} animate-in fade-in zoom-in-95 duration-300`}>
                            <div>
                                <div className="font-bold text-sm">{evt.symbol}</div>
                                <div className="text-[10px] opacity-70">{evt.details}</div>
                            </div>
                            {getStatusIcon(evt.status)}
                        </div>
                    ))}
                </CardContent>
            </Card>

            {/* LAYER 3: EXECUTION */}
            <Card className="border-l-4 border-l-green-500 bg-black/40 backdrop-blur-sm">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Zap className="h-4 w-4 text-green-500" /> Layer 3: Execution
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 max-h-[400px] overflow-y-auto custom-scrollbar">
                    {executionEvents.length === 0 && <div className="text-xs text-muted-foreground text-center py-4">No recent trades</div>}
                    {executionEvents.map((evt, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded bg-green-500/10 border border-green-500/20 animate-in fade-in slide-in-from-right-2 duration-300">
                            <div>
                                <div className="font-bold text-sm text-green-400">{evt.symbol}</div>
                                <div className="text-[10px] text-green-300/70">{evt.details}</div>
                            </div>
                            <CheckCircle2 className="h-4 w-4 text-green-400" />
                        </div>
                    ))}
                </CardContent>
            </Card>
        </div>
    );
}
