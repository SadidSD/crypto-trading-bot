import { create } from 'zustand';

interface Trade {
    symbol: string;
    side: string;
    entry: number;
    pnl: number;
    status: string;
}

interface BotState {
    status: 'active' | 'paused' | 'error' | 'offline';
    candidates: number;
    balance: number;
    pnl: number;
    trades: Trade[];
    logs: string[];
    setBotStatus: (status: BotState['status']) => void;
    updateStats: (stats: Partial<BotState>) => void;
    addLog: (log: string) => void;
}

export const useBotStore = create<BotState>((set) => ({
    status: 'offline',
    candidates: 0,
    balance: 0,
    pnl: 0,
    trades: [],
    logs: [],
    setBotStatus: (status) => set({ status }),
    updateStats: (stats) => set((state) => ({ ...state, ...stats })),
    addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 100) })),
}));
