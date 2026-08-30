// import { useEffect, useState } from 'react';
// import { SCENARIO_EVENTS } from '../data/scenario';

// // Simulates ws://localhost:8000/ws/events by replaying the scripted
// // demo scenario on a timer. To go live: delete the interval below and
// // instead open a WebSocket, pushing each parsed message into setEvents
// // the same way (newest event unshifted to the front).
// export function useEventStream({ intervalMs = 3200, loop = true } = {}) {
//   const [events, setEvents] = useState([]);
//   const [cursor, setCursor] = useState(0);

//   useEffect(() => {
//     const id = setInterval(() => {
//       setCursor((prev) => {
//         const next = prev + 1;
//         if (next > SCENARIO_EVENTS.length) {
//           if (!loop) {
//             clearInterval(id);
//             return prev;
//           }
//           setEvents([]);
//           return 0;
//         }
//         return next;
//       });
//     }, intervalMs);
//     return () => clearInterval(id);
//   }, [intervalMs, loop]);

//   useEffect(() => {
//     if (cursor === 0) return;
//     setEvents(SCENARIO_EVENTS.slice(0, cursor).slice().reverse());
//   }, [cursor]);

//   const cameraStatus = {};
//   for (const ev of events) {
//     if (!cameraStatus[ev.camera_id]) {
//       cameraStatus[ev.camera_id] = ev;
//     }
//   }

//   return { events, cameraStatus, activeEvent: events[0] ?? null };
// }

import { useEffect, useState, useRef } from 'react';

export function useEventStream() {
  const [events, setEvents]     = useState([]);
  const wsRef                   = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/events');
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      const ev = JSON.parse(msg.data);
      // Keep newest first — matches how the UI reads events[0]
      setEvents((prev) => [ev, ...prev].slice(0, 200)); // cap at 200
    };

    ws.onerror  = (err) => console.error('[WS] error', err);
    ws.onclose  = ()    => console.warn('[WS] connection closed');

    return () => ws.close();
  }, []);

  // Build per-camera latest event map (used by TacticalMap + CameraTile)
  const cameraStatus = {};
  for (const ev of events) {
    if (!cameraStatus[ev.camera_id]) cameraStatus[ev.camera_id] = ev;
  }

  return { events, cameraStatus, activeEvent: events[0] ?? null };
}