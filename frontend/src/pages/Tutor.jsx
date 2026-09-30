import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { Send, FileText } from 'lucide-react';

export default function Tutor() {
  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      <PageHeader
        eyebrow="Study"
        title="AI Tutor"
        description="Ask questions grounded in your selected chapters."
      />

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Chat Area */}
        <Card className="flex-1 flex flex-col">
          <div className="flex-1 p-6 overflow-y-auto flex flex-col justify-center items-center text-center">
            <div className="w-12 h-12 bg-[#F7F6F2] rounded-full flex items-center justify-center mb-4">
              <span className="text-xl">👋</span>
            </div>
            <h3 className="text-[#20201E] font-medium mb-2">How can I help you study?</h3>
            <p className="text-sm text-[#73736D] max-w-sm">
              Select a chapter from the right and ask me any question. I'll answer using only your textbook material.
            </p>
          </div>
          
          <div className="p-4 border-t border-[#E5E3DC] bg-[#F7F6F2]/50">
            <div className="relative">
              <input 
                type="text" 
                placeholder="Ask a question..."
                className="w-full pl-4 pr-12 py-3 bg-white border border-[#E5E3DC] rounded-lg text-sm focus:outline-none focus:border-[#3157D5] focus:ring-1 focus:ring-[#3157D5] shadow-sm"
              />
              <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-[#3157D5] hover:bg-[#F7F6F2] rounded-md transition-colors">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </Card>

        {/* Context Selection Sidebar */}
        <div className="w-80 shrink-0 flex flex-col gap-4">
          <Card>
            <div className="px-4 py-3 border-b border-[#E5E3DC] bg-[#F7F6F2]/50 flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#73736D]" />
              <h3 className="font-medium text-sm text-[#20201E]">Current Context</h3>
            </div>
            <CardContent className="p-4">
              <div className="text-sm text-[#73736D] mb-4">
                Select chapters to restrict the AI's knowledge base.
              </div>
              <div className="space-y-2">
                {/* Fake Chapters for UI design */}
                {[1, 2, 3].map(num => (
                  <label key={num} className="flex items-center gap-3 p-3 border border-[#E5E3DC] rounded-md hover:bg-[#F7F6F2] cursor-pointer">
                    <input type="checkbox" className="w-4 h-4 text-[#3157D5] rounded border-[#E5E3DC] focus:ring-[#3157D5]" />
                    <span className="text-sm text-[#20201E] font-medium">Chapter {num}</span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
