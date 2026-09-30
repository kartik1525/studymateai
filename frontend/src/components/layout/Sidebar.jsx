import React from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpen, MessageSquare, Award, Clock, Settings } from 'lucide-react';

export default function Sidebar() {
  const navLinkClass = ({ isActive }) =>
    `flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
      isActive
        ? 'bg-[#E5E3DC]/60 text-[#20201E] font-semibold'
        : 'text-[#73736D] hover:text-[#20201E] hover:bg-[#E5E3DC]/30'
    }`;

  return (
    <aside className="w-60 h-screen bg-[#F7F6F2] border-r border-[#E5E3DC] flex flex-col justify-between shrink-0 select-none">
      <div className="p-4">
        {/* Logo / Brand Header */}
        <div className="px-3 py-2 mb-6">
          <span className="font-editorial text-xl font-semibold tracking-wide text-[#20201E]">
            STUDYMATE
          </span>
          <p className="text-[11px] text-[#73736D] tracking-wider uppercase mt-0.5">
            Class-Aware AI Tutor
          </p>
        </div>

        {/* Navigation Sections */}
        <nav className="space-y-6">
          {/* Library Section */}
          <div>
            <div className="px-3 mb-1.5 text-[11px] font-semibold text-[#73736D] uppercase tracking-wider">
              Library
            </div>
            <div className="space-y-0.5">
              <NavLink to="/materials" className={navLinkClass}>
                <BookOpen className="w-4 h-4" />
                <span>Materials</span>
              </NavLink>
              <NavLink to="/dashboard" className={navLinkClass}>
                <Clock className="w-4 h-4" />
                <span>Recent</span>
              </NavLink>
            </div>
          </div>

          {/* Study Section */}
          <div>
            <div className="px-3 mb-1.5 text-[11px] font-semibold text-[#73736D] uppercase tracking-wider">
              Study
            </div>
            <div className="space-y-0.5">
              <NavLink to="/tutor" className={navLinkClass}>
                <MessageSquare className="w-4 h-4" />
                <span>AI Tutor</span>
              </NavLink>
              <NavLink to="/quizzes" className={navLinkClass}>
                <Award className="w-4 h-4" />
                <span>Quizzes</span>
              </NavLink>
            </div>
          </div>
        </nav>
      </div>

      {/* Footer Info & Settings */}
      <div className="p-4 border-t border-[#E5E3DC]">
        {/* Class Context Indicator */}
        <div className="px-3 py-2.5 mb-2 bg-[#FFFFFF] border border-[#E5E3DC] rounded-md">
          <p className="text-xs font-semibold text-[#20201E]">Class 10</p>
          <p className="text-[11px] text-[#73736D] truncate">Artificial Intelligence</p>
        </div>

        <button
          type="button"
          className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#73736D] hover:text-[#20201E] rounded-md transition-colors hover:bg-[#E5E3DC]/30 text-left"
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
}
