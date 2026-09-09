import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { tokenStore } from "../../auth/tokenStore";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

/** Live WebSocket connection to /ws/notifications with auto-reconnect
 * (capped backoff). Invalidates the notifications query on every push so
 * the panel/unread badge refresh without polling. */

let audioCtx: AudioContext | null = null;
function playAlarmTone() {
  if (typeof window === 'undefined') return;
  if (!audioCtx) {
     try {
         audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
     } catch(e) { return; }
  }
  if (audioCtx.state === 'suspended') {
     audioCtx.resume();
  }
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = 'square';
  osc.frequency.setValueAtTime(800, audioCtx.currentTime);
  osc.frequency.linearRampToValueAtTime(1200, audioCtx.currentTime + 0.3);
  osc.frequency.linearRampToValueAtTime(800, audioCtx.currentTime + 0.6);
  osc.frequency.linearRampToValueAtTime(1200, audioCtx.currentTime + 0.9);
  gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 1.2);
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start();
  osc.stop(audioCtx.currentTime + 1.2);
}

export function useNotificationSocket() {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);
  const retryRef = useRef(0);
  const closedByUsRef = useRef(false);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;

    function connect() {
      const token = tokenStore.getAccessToken();
      if (!token) return;

      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${proto}//${window.location.host}${API_BASE}/ws/notifications?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);

      socket.onopen = () => {
        setConnected(true);
        retryRef.current = 0;
      };
            socket.onmessage = (msgEvent) => {
        try {
          const msg = JSON.parse(msgEvent.data);
          if (msg.type === "new_event" && msg.event && msg.event.severity === "high") {
            playAlarmTone();
          }
        } catch(e) {}
        qc.invalidateQueries({ queryKey: ["notifications"] });
      };
      socket.onclose = () => {
        setConnected(false);
        if (closedByUsRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 15_000);
        retryRef.current += 1;
        retryTimer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();
    return () => {
      closedByUsRef.current = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { connected };
}
