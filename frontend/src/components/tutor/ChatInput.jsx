import React, { useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function ChatInput({ value, onChange, onSubmit, isLoading, placeholder }) {
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        onSubmit();
      }
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [value]);

  return (
    <div className="w-full relative">
      <div className="relative max-w-4xl mx-auto flex items-end gap-1.5 bg-white/10 backdrop-blur-md border border-white/20 rounded-[20px] focus-within:bg-white/15 focus-within:border-white/30 transition-all shadow-sm">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Ask something about your selected material..."}
          disabled={isLoading}
          className="flex-1 max-h-[120px] min-h-[52px] py-[16px] pl-[24px] pr-2 bg-transparent text-[14px] leading-tight text-white placeholder-white/40 resize-none focus:outline-none disabled:opacity-50 custom-scrollbar"
          rows={1}
        />
        <div className="p-2 shrink-0">
          <button 
            onClick={onSubmit}
            disabled={!value.trim() || isLoading}
            className="w-[36px] h-[36px] flex items-center justify-center bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] rounded-full transition-colors disabled:bg-white/5 disabled:text-white/20"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 -ml-0.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
