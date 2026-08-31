import { useState, useMemo } from 'react';
import StatusBar   from './components/StatusBar';
import MainCCTVFeed from './components/MainCCTVFeed';
import CameraTile  from './components/CameraTile';
import TacticalMap  from './components/TacticalMap';
import AlertsFeed   from './components/AlertsFeed';

import ActiveAlertsPage from './components/ActiveAlertsPage';
import AlertDetailsModal from './components/AlertDetailsModal';
import GlobalTracksPage from './components/GlobalTracksPage';
import GlobalTrackDetailsModal from './components/GlobalTrackDetailsModal';
import { CAMERAS }  from './data/scenario';
import { useEventStream } from './hooks/useEventStream';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Build MJPEG stream URL for a camera
function streamUrl(camera_id) {
  return `${API_BASE}/api/v1/cameras/${camera_id}/stream`;
}

// Build snapshot URL for thumbnail refresh
function snapshotUrl(camera_id) {
  return `${API_BASE}/api/v1/cameras/${camera_id}/snapshot`;
}


export default function App() {
  const {
    events,
    cameras,
    alerts,
    cameraStatus,
    videoMode,
    setVideoMode,
    wsConnected,
  } = useEventStream();

  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' | 'alerts' | 'tracks'
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);

  // Manual camera focus state & toggle for auto-speaker view
  const [manualCamId, setManualCamId] = useState(null);
  const [isManualOverride, setIsManualOverride] = useState(false);

  // Use live cameras if loaded, else fall back to static seed data
  const allCameras = cameras.length > 0 ? cameras : CAMERAS;

  // Determine top priority / latest anomaly camera automatically (Zoom/Meet active-speaker style)
  const autoCamId = useMemo(() => {
    if (!events || events.length === 0) return allCameras[0]?.camera_id || 'CAM-001';
    const highEvent = events.find((ev) => ev.severity === 'HIGH' || ev.severity === 'CRITICAL');
    if (highEvent?.camera_id) return highEvent.camera_id;
    const medEvent = events.find((ev) => ev.severity === 'MEDIUM');
    if (medEvent?.camera_id) return medEvent.camera_id;
    return events[0]?.camera_id || allCameras[0]?.camera_id || 'CAM-001';
  }, [events, allCameras]);

  // Selected camera feed for the main display
  const activeCamId = isManualOverride && manualCamId ? manualCamId : autoCamId;
  const activeCamera = allCameras.find((c) => c.camera_id === activeCamId) || allCameras[0];

  const handleSelectIndividualAlert = (ev) => {
    const formatted = {
      id: ev.event_id || 'ALT-2026-LIVE',
      event_type: ev.event_type || 'intrusion',
      type_label: ev.label || ev.event_type?.replace(/_/g, ' '),
      severity: ev.severity || 'HIGH',
      timestamp: ev.timestamp || new Date().toISOString(),
      time_relative: 'Just now',
      camera_id: ev.camera_id || 'CAM-001',
      camera_name: allCameras.find(c => c.camera_id === ev.camera_id)?.name || ev.camera_id,
      global_id: ev.entity_id || 'G-017',
      description: `${ev.event_type?.replace(/_/g, ' ') || 'Security alert'} detected on ${ev.camera_id}`,
      status: ev.status || 'NEW',
      confidence: ev.confidence ? `${(ev.confidence * 100).toFixed(1)}%` : 'N/A',
      zone: ev.zone_id || 'ZONE-01',
      location: allCameras.find(c => c.camera_id === ev.camera_id)?.location || ev.camera_id,
      coordinates: { lat: 28.6139, lng: 77.2090 },
      entity: {
        type: ev.entity_type || 'Person',
        id: ev.entity_id || 'G-017',
        estimated_speed: '—',
        reid_score: ev.confidence ? `${(ev.confidence * 100).toFixed(1)}%` : '—',
      },
      audit_trail: [
        { time: ev.timestamp || new Date().toISOString(), note: 'Real-time alert from IBVAP AI Engine' },
      ]
    };
    setSelectedAlert(formatted);
  };

  if (activeView === 'alerts') {
    return (
      <ActiveAlertsPage
        onBackToDashboard={() => setActiveView('dashboard')}
        liveEvents={events}
      />
    );
  }

  if (activeView === 'tracks') {
    return (
      <GlobalTracksPage
        onBackToDashboard={() => setActiveView('dashboard')}
      />
    );
  }

  return (
    <div className="dashboard">
      {/* ── Top Status Bar ── */}
      <StatusBar
        cameraCount={allCameras.length}
        activeView={activeView}
        onNavigate={(view) => setActiveView(view)}
      />

      {/* ── Video Mode Toggle Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        padding: '6px 20px', background: 'rgba(10,14,20,0.7)',
        borderBottom: '1px solid rgba(52,217,180,0.15)',
        fontSize: '0.75rem', color: '#8899aa'
      }}>
        <span>VIDEO SOURCE:</span>
        <button
          onClick={() => setVideoMode('SAMPLE')}
          style={{
            padding: '3px 12px', borderRadius: '4px', cursor: 'pointer', border: 'none',
            background: videoMode === 'SAMPLE' ? '#34d9b4' : 'rgba(52,217,180,0.1)',
            color: videoMode === 'SAMPLE' ? '#0a0e14' : '#34d9b4',
            fontWeight: videoMode === 'SAMPLE' ? 700 : 400
          }}
        >
          SAMPLE FOOTAGE
        </button>
        <button
          onClick={() => setVideoMode('LIVE_PHONE')}
          style={{
            padding: '3px 12px', borderRadius: '4px', cursor: 'pointer', border: 'none',
            background: videoMode === 'LIVE_PHONE' ? '#34d9b4' : 'rgba(52,217,180,0.1)',
            color: videoMode === 'LIVE_PHONE' ? '#0a0e14' : '#34d9b4',
            fontWeight: videoMode === 'LIVE_PHONE' ? 700 : 400
          }}
        >
          LIVE SMARTPHONE
        </button>
        <span style={{ marginLeft: 'auto', color: wsConnected ? '#34d9b4' : '#ff4455' }}>
          {wsConnected ? '● WS CONNECTED' : '○ WS RECONNECTING...'}
        </span>
      </div>

      {/* ── Main Dashboard Body ── */}
      <main className="dashboard__body">

        {/* ── LEFT COLUMN: Main Dynamic CCTV Feed + Camera Tiles ── */}
        <div className="dashboard__left-col">
          {/* Main Large CCTV Feed */}
          <section className="dashboard__main-cctv-wrap">
            <MainCCTVFeed
              camera={activeCamera}
              latestEvent={cameraStatus[activeCamId]}
              isAutoSwitch={!isManualOverride}
              onToggleAutoSwitch={() => setIsManualOverride((prev) => !prev)}
              streamUrl={streamUrl(activeCamId)}
            />
          </section>

          {/* Camera Tiles Grid */}
          <section className="dashboard__tiles-wrap">
            <div className="dashboard__tiles-grid">
              {allCameras.map((cam) => (
                <CameraTile
                  key={cam.camera_id}
                  camera={cam}
                  latestEvent={cameraStatus[cam.camera_id]}
                  isActive={cam.camera_id === activeCamId}
                  streamUrl={cam.camera_id === activeCamId ? streamUrl(cam.camera_id) : null}
                  snapshotUrl={snapshotUrl(cam.camera_id)}
                  onClick={() => {
                    setManualCamId(cam.camera_id);
                    setIsManualOverride(true);
                  }}
                />
              ))}
            </div>
          </section>
        </div>

        {/* ── RIGHT COLUMN: Active Alerts + Tactical Zone Map ── */}
        <div className="dashboard__right-col">
          {/* Top: Active Alerts Panel */}
          <section className="dashboard__alerts-wrap">
            <AlertsFeed
              events={events}
              onViewAll={() => setActiveView('alerts')}
              onSelectAlert={handleSelectIndividualAlert}
            />
          </section>

          {/* Bottom: Tactical Zone Map */}
          <section className="dashboard__map-wrap">
            <TacticalMap cameraStatus={cameraStatus} />
          </section>
        </div>
      </main>

      {/* Individual Alert Details Modal */}
      {selectedAlert && (
        <AlertDetailsModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={(id) => {
            setSelectedAlert((prev) => prev ? { ...prev, status: 'ACKNOWLEDGED' } : null);
          }}
          onResolve={(id) => {
            setSelectedAlert((prev) => prev ? { ...prev, status: 'RESOLVED' } : null);
          }}
        />
      )}

      {/* Individual Global Track Details Modal */}
      {selectedTrack && (
        <GlobalTrackDetailsModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
        />
      )}
    </div>
  );
}
