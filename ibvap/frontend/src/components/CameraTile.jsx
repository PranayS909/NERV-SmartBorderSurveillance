import { useState, useEffect } from 'react';
import './CameraTile.css';
import { SEVERITY_COLOR } from '../data/scenario';

export default function CameraTile({ camera, latestEvent, isActive, onClick, streamUrl, snapshotUrl }) {
  const cameraID = camera?.camera_id || 'CAM-001';
  const displayName = camera?.name || cameraID;
  const severity = latestEvent?.severity || null;
  const accentColor = severity ? (SEVERITY_COLOR[severity] || 'var(--signal-teal)') : 'var(--signal-teal)';

  // Lightweight snapshot polling every 2s for inactive thumbnails (prevents browser stream starvation)
  const [snapSrc, setSnapSrc] = useState(snapshotUrl ? `${snapshotUrl}?_t=${Date.now()}` : null);

  useEffect(() => {
    if (!snapshotUrl || streamUrl) return;
    const interval = setInterval(() => {
      setSnapSrc(`${snapshotUrl}?_t=${Date.now()}`);
    }, 2000);
    return () => clearInterval(interval);
  }, [snapshotUrl, streamUrl]);

  return (
    <div
      className={`camera-tile ${isActive ? 'camera-tile--active' : ''} ${severity ? `camera-tile--${severity.toLowerCase()}` : ''}`}
      onClick={onClick}
      style={{ '--accent': accentColor }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(); }}
    >
      {/* ── Tile Header ── */}
      <div className="camera-tile__head">
        <div className="camera-tile__title-wrap">
          <span className="camera-tile__id">{cameraID}</span>
          <span className="camera-tile__name">{displayName}</span>
        </div>

        <div className="camera-tile__badges">
          {isActive && <span className="camera-tile__active-badge">MAIN FEED</span>}
          <span className="camera-tile__live-badge">
            <span className="camera-tile__live-dot" />
            LIVE
          </span>
        </div>
      </div>

      {/* ── Feed Preview ── */}
      <div className="camera-tile__feed">
        {streamUrl ? (
          <img src={streamUrl} alt={`Live feed for ${cameraID}`} className="camera-tile__thumb-img" />
        ) : snapSrc ? (
          <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            <img src={snapSrc} alt={`Snapshot for ${cameraID}`} className="camera-tile__thumb-img" />
            <div className="camera-tile__hover-overlay">
              <span>CLICK TO VIEW ON MAIN</span>
            </div>
          </div>
        ) : (
          <div className="camera-tile__placeholder">
            {/* Simulated Bounding Box Preview */}
            <div
              className="camera-tile__mini-bbox"
              style={{
                top: '30%',
                left: '30%',
                width: '35%',
                height: '45%',
              }}
            >
              <span className="camera-tile__mini-label">{latestEvent?.entity?.entity_id || 'G-017'}</span>
            </div>

            {/* Tactical Grid Pattern */}
            <div className="camera-tile__grid-pattern" />

            {/* Switch Prompt Overlay on Hover */}
            <div className="camera-tile__hover-overlay">
              <span>{isActive ? 'CURRENT MAIN FEED' : 'CLICK TO VIEW ON MAIN'}</span>
            </div>
          </div>
        )}
        <div className="camera-tile__scanline" />
      </div>


      {/* ── Tile Footer ── */}
      <div className="camera-tile__foot">
        <span className="camera-tile__status-text">
          {latestEvent ? (
            <span className="camera-tile__event-label" style={{ color: accentColor, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span className="camera-tile__live-dot" style={{ background: accentColor, width: '6px', height: '6px' }} />
              {latestEvent.label}
            </span>
          ) : (
            <span className="camera-tile__clear-label" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span className="camera-tile__live-dot" style={{ background: 'var(--signal-teal)', width: '6px', height: '6px' }} />
              NORMAL - CLEAR
            </span>
          )}
        </span>
        <span className="camera-tile__cam-fps">1080p • 30 FPS</span>
      </div>
    </div>
  );
}
