import React from 'react';
import { NavLink } from 'react-router-dom';
import { useStudyContext } from '../../context/StudyContext';

export default function Sidebar() {
  const { activeDocument } = useStudyContext();

  const navLinkClass = ({ isActive }) =>
    `block py-1 text-sm font-medium transition-colors ${
      isActive
        ? 'text-[var(--color-ink)] font-semibold'
        : 'text-[var(--color-muted)] hover:text-[var(--color-ink)]'
    }`;

  return (
    <aside className="w-[180px] h-screen bg-transparent flex flex-col justify-between shrink-0 select-none relative z-20">
      <div className="py-8 px-6 flex flex-col h-full overflow-y-auto custom-scrollbar">
        {/* Logo / Brand Header */}
        <div className="mb-12">
          <span className="font-editorial text-2xl font-bold tracking-tight text-[var(--color-ink)] flex items-center">
            STUDYMATE
          </span>
        </div>

        {/* Navigation Sections */}
        <nav className="space-y-10 flex-1">
          {/* Library Section */}
          <div>
            <div className="mb-4 text-[10px] font-bold text-[var(--color-muted)]/60 uppercase tracking-[0.2em]">
              Library
            </div>
            <div className="space-y-3">
              <NavLink to="/materials" className={navLinkClass}>
                Materials
              </NavLink>
              <NavLink to="/dashboard" className={navLinkClass}>
                Recent
              </NavLink>
            </div>
          </div>

          {/* Study Section */}
          <div>
            <div className="mb-4 text-[10px] font-bold text-[var(--color-muted)]/60 uppercase tracking-[0.2em]">
              Study
            </div>
            <div className="space-y-3">
              <NavLink to="/tutor" className={navLinkClass}>
                AI Tutor
              </NavLink>
              <NavLink to="/quizzes" className={navLinkClass}>
                Quizzes
              </NavLink>
            </div>
          </div>
        </nav>

        {/* Context Block & Footer */}
        <div className="mt-8 pt-8 border-t border-[var(--color-border)]/50">
          {/* Class Context Indicator */}
          {activeDocument && (
            <div className="mb-6">
              <p className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-accent)] uppercase mb-1">
                Class {activeDocument.class_name}
              </p>
              <p className="text-sm font-semibold text-[var(--color-ink)] leading-tight line-clamp-2" title={activeDocument.subject}>
                {activeDocument.subject}
              </p>
            </div>
          )}

          <button
            type="button"
            className="text-sm font-medium text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors text-left"
          >
            Settings
          </button>
        </div>
      </div>
    </aside>
  );
}
