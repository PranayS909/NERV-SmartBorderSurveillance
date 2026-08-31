/**
 * useEventStream.js
 *
 * Unified hook that:
 *  1. Fetches initial state from REST: cameras, events, alerts, zones
 *  2. Opens WebSocket /ws/events for live event streaming
 *  3. Exposes videoMode state and setVideoMode() which calls POST /api/v1/mode
 */

import { useEffect, useState, useRef, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const WS_URL   = import.meta.env.VITE_WS_URL   || 'ws://localhost:8000/ws/events';
const MAX_EVENTS = 200;

async function fetchJSON(path) {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[API] Failed to fetch ${path}:`, err.message);
    return null;
  }
}

export function useEventStream() {
  const [events, setEvents]       = useState([]);
  const [cameras, setCameras]     = useState([]);
  const [alerts, setAlerts]       = useState([]);
  const [zones, setZones]         = useState([]);
  const [videoMode, setVideoModeState] = useState('SAMPLE');
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  // ── Initial REST fetch ──────────────────────────────────────────────────
  useEffect(() => {
    async function loadInitialData() {
      const [camsData, eventsData, alertsData, zonesData, modeData] = await Promise.all([
        fetchJSON('/api/v1/cameras'),
        fetchJSON('/api/v1/events?limit=50'),
        fetchJSON('/api/v1/alerts?limit=50'),
        fetchJSON('/api/v1/zones'),
        fetchJSON('/api/v1/mode'),
      ]);

      if (camsData)   setCameras(camsData);
      if (eventsData) setEvents(Array.isArray(eventsData) ? eventsData.reverse() : []);
      if (alertsData) setAlerts(Array.isArray(alertsData) ? alertsData : []);
      if (zonesData)  setZones(Array.isArray(zonesData)  ? zonesData  : []);
      if (modeData?.mode) setVideoModeState(modeData.mode);
    }
    loadInitialData();
  }, []);

  // ── WebSocket subscription with auto-reconnect ─────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return; // already open/connecting

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
    };

    ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        if (payload.type === 'NEW_EVENT' && payload.event) {
          setEvents((prev) => [payload.event, ...prev].slice(0, MAX_EVENTS));
        } else if (payload.type === 'NEW_ALERT' && payload.alert) {
          setAlerts((prev) => [payload.alert, ...prev].slice(0, MAX_EVENTS));
        } else if (payload.event_type) {
          // Bare event object broadcast
          setEvents((prev) => [payload, ...prev].slice(0, MAX_EVENTS));
        }
      } catch (err) {
        console.warn('[WS] parse error', err);
      }
    };

    ws.onerror = () => {
      console.warn('[WS] connection error — will retry');
    };

    ws.onclose = () => {
      setWsConnected(false);
      reconnectRef.current = setTimeout(connectWS, 3000);
    };
  }, []);

  useEffect(() => {
    connectWS();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connectWS]);

  // ── Video mode switcher ────────────────────────────────────────────────
  const setVideoMode = useCallback(async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/mode?mode=${mode}`, { method: 'POST' });
      const data = await res.json();
      if (data.mode) setVideoModeState(data.mode);
    } catch (err) {
      console.warn('[API] setVideoMode failed:', err);
    }
  }, []);

  // ── Per-camera latest event map (TacticalMap + CameraTile status) ──────
  const cameraStatus = {};
  for (const ev of events) {
    if (ev.camera_id && !cameraStatus[ev.camera_id]) {
      cameraStatus[ev.camera_id] = ev;
    }
  }

  return {
    events,
    cameras,
    alerts,
    zones,
    cameraStatus,
    activeEvent: events[0] ?? null,
    videoMode,
    setVideoMode,
    wsConnected,
  };
}