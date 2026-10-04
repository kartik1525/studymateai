import React, { useEffect, useState } from 'react';
import { checkHealth } from '../../services/api';
import { useStudyContext } from '../../context/StudyContext';

export default function Topbar() {
  const { activeDocument } = useStudyContext();
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
    <header className="h-24 bg-transparent px-8 md:px-12 flex items-center justify-between relative z-20">
      <div className="flex items-center gap-6">
        <div className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-ink)] uppercase">
          Study Desk
        </div>
        {activeDocument && (
          <>
            <span className="text-[var(--color-border)] text-lg leading-none">/</span>
            <span className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-muted)] uppercase">
              Class {activeDocument.class_name} · {activeDocument.subject}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center">
        {/* Tiny Backend Connectivity Status Indicator */}
        <div 
          className={`w-2 h-2 rounded-full shadow-sm ${
            backendStatus.checking
              ? 'bg-amber-400 animate-pulse'
              : backendStatus.healthy
              ? 'bg-emerald-400'
              : 'bg-red-500'
          }`}
          title={`API: ${backendStatus.healthy ? 'Online' : 'Offline'}`}
        />
      </div>
    </header>
  );
}
