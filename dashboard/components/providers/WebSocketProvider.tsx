'use client';
import { useEffect, useRef } from 'react';
import { useBotStore } from '@/store/botStore';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
    const updateStats = useBotStore((state) => state.updateStats);
    const setBotStatus = useBotStore((state) => state.setBotStatus);
    const addLog = useBotStore((state) => state.addLog);
    const addPipelineEvent = useBotStore((state) => state.addPipelineEvent);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        let reconnectTimeout: NodeJS.Timeout;

        const connect = () => {
            ws.current = new WebSocket(WS_URL);

            ws.current.onopen = () => {
                console.log('WS Connected');
                // Fetch actual status on connect
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                fetch(`${API_URL}/status`)
                    .then(res => res.json())
                    .then(data => {
                        setBotStatus(data.status);
                        updateStats({ candidates: data.active_candidates });
                    })
                    .catch(() => setBotStatus('active')); // Fallback

                // Subscribe
                ws.current?.send(JSON.stringify({
                    action: "subscribe",
                    channels: ["bot_status", "trade_updates", "market_updates"]
                }));
            };

            ws.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'status_change') {
                        setBotStatus(data.status);
                    }
                    if (data.type === 'info') {
                        addLog(data.message);
                    }
                    if (data.type === 'pipeline_event') {
                        addPipelineEvent(data.payload);
                    }
                    // Handle other types
                } catch (e) {
                    console.error("WS Parse Error", e);
                }
            };

            ws.current.onclose = () => {
                console.log('WS Disconnected');
                setBotStatus('offline');
                reconnectTimeout = setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            if (ws.current) {
                ws.current.onclose = null; // Prevent offline trigger on cleanup
                ws.current.close();
            }
            clearTimeout(reconnectTimeout);
        };
    }, []);

    return <>{children}</>;
}
