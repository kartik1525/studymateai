import React from 'react';

export default function TutorChapterSidebar({ 
  activeDoc, 
  selectedChapters, 
  toggleChapter, 
  setSelectedChapters 
}) {
  if (!activeDoc) return null;

  return (
    <div className="hidden md:flex w-[260px] flex-col border-r border-white/10 bg-white/[0.02] shrink-0">
      <div className="p-5 border-b border-white/10">
        <p className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-2">
          STUDY MATERIAL
        </p>
        <h3 className="font-editorial text-[18px] text-white leading-tight truncate" title={activeDoc.document_name}>
          {activeDoc.document_name ? activeDoc.document_name.replace('.pdf', '').replace(/_/g, ' ') : ''}
        </h3>
        <p className="text-[11px] text-white/40 uppercase tracking-wider mt-1">
          Class {activeDoc.class_name} · {activeDoc.subject}
        </p>
      </div>
      
      <div className="p-4 border-b border-white/10">
        <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase mb-3 px-1">
          CHAPTERS
        </p>
        <button 
          onClick={() => setSelectedChapters([])}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-left ${selectedChapters.length === 0 ? 'bg-[var(--color-accent)]/20 text-white' : 'hover:bg-white/5 text-white/70'}`}
        >
          <div className={`w-3 h-3 rounded-full border-2 flex items-center justify-center shrink-0 ${selectedChapters.length === 0 ? 'border-[var(--color-accent)]' : 'border-white/30'}`}>
             {selectedChapters.length === 0 && <div className="w-1.5 h-1.5 bg-[var(--color-accent)] rounded-full"></div>}
          </div>
          <span className="text-[13px] font-medium truncate">Entire material</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar dark-scrollbar p-3">
        {activeDoc.chapters?.map((ch) => {
          const isSelected = selectedChapters.includes(ch.chapter_number);
          return (
            <button
              key={ch.chapter_number}
              onClick={() => toggleChapter(ch.chapter_number)}
              className={`w-full flex items-start gap-3 px-3 py-2.5 mb-1 rounded-lg transition-colors text-left ${isSelected ? 'bg-[var(--color-accent)]/20 text-white' : 'hover:bg-white/5 text-white/60'}`}
            >
              <div className={`mt-0.5 w-3 h-3 rounded-[3px] border-2 flex items-center justify-center shrink-0 transition-colors ${isSelected ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-white/30'}`}>
                 {isSelected && <span className="w-1.5 h-1.5 bg-white rounded-[1px]"></span>}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-[10px] font-mono mb-0.5 ${isSelected ? 'text-[var(--color-accent)]' : 'text-white/40'}`}>
                  {String(ch.chapter_number).padStart(2, '0')}
                </div>
                <div className={`text-[13px] leading-tight ${isSelected ? 'font-semibold' : 'font-medium'}`}>
                  {ch.chapter_title}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
