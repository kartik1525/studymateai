import React, { useEffect, useState } from 'react';
import { checkHealth } from '../../services/api';
import { Activity } from 'lucide-react';

export default function Topbar() {
  const [backendStatus, setBackendStatus] = useState({
    checking: true,
    healthy: false,
    version: null,
  });

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (isMounted) {
          setBackendStatus({
            checking: false,
            healthy: data.status === 'healthy',
            version: data.version,
          });
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendStatus({
            checking: false,
            healthy: false,
            version: null,
          });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="h-14 border-b border-[#E5E3DC] bg-[#FFFFFF] px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="font-editorial text-lg text-[#20201E]">
          Study Desk
        </h1>
        <span className="text-[#E5E3DC]">|</span>
        <span className="text-xs text-[#73736D]">
          Class 10 · AI Textbook
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* Backend Connectivity Status Indicator */}
        <div className="flex items-center gap-2 text-xs font-mono px-2.5 py-1 bg-[#F7F6F2] border border-[#E5E3DC] rounded text-[#73736D]">
          <Activity
            className={`w-3.5 h-3.5 ${
              backendStatus.checking
                ? 'text-amber-500 animate-pulse'
                : backendStatus.healthy
                ? 'text-emerald-600'
                : 'text-red-500'
            }`}
          />
          <span>
            API:{' '}
            {backendStatus.checking
              ? 'Connecting...'
              : backendStatus.healthy
              ? `Online (v${backendStatus.version || '1.0.0'})`
              : 'Disconnected'}
          </span>
        </div>
      </div>
    </header>
  );
}
