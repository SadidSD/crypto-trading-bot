import { create } from 'zustand';

interface Trade {
    symbol: string;
    side: string;
    entry: number;
    pnl: number;
    status: string;
}

interface PipelineEvent {
    timestamp: number | string;
    stage: 'scanner' | 'engine' | 'execution';
    symbol: string;
    status: 'pass' | 'fail' | 'processing' | 'executed';
    details: string;
}

interface BotState {
    status: 'active' | 'paused' | 'error' | 'offline';
    candidates: number;
    balance: number;
    pnl: number;
    trades: Trade[];
    logs: string[];
    pipelineEvents: PipelineEvent[]; // NEW: Pipeline History
    setBotStatus: (status: BotState['status']) => void;
    updateStats: (stats: Partial<BotState>) => void;
    addLog: (log: string) => void;
    addPipelineEvent: (event: PipelineEvent) => void;
}

export const useBotStore = create<BotState>((set) => ({
    status: 'offline',
    candidates: 0,
    balance: 0,
    pnl: 0,
    trades: [],
    logs: [],
    pipelineEvents: [],
    setBotStatus: (status) => set({ status }),
    updateStats: (stats) => set((state) => ({ ...state, ...stats })),
    addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 100) })),
    addPipelineEvent: (event) => set((state) => ({
        // Keep last 50 events, newest first
        pipelineEvents: [event, ...state.pipelineEvents].slice(0, 50)
    })),
}));
