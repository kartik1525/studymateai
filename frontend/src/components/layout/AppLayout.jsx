import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { StudyProvider } from '../../context/StudyContext';

export default function AppLayout() {
  return (
    <StudyProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-[var(--color-warm-bg)] text-[var(--color-ink)]">
        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative">
          <Topbar />
          <main className="flex-1 overflow-y-auto relative z-10 custom-scrollbar">
            <Outlet />
          </main>
        </div>
      </div>
    </StudyProvider>
  );
}
