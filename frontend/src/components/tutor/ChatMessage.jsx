import React from 'react';
import ReactMarkdown from 'react-markdown';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  const markdownComponents = {
    p: ({children}) => <p className="mb-4 last:mb-0 leading-relaxed">{children}</p>,
    h1: ({children}) => <h1 className="text-xl font-bold mb-4 mt-6 text-white">{children}</h1>,
    h2: ({children}) => <h2 className="text-lg font-bold mb-3 mt-5 text-white">{children}</h2>,
    h3: ({children}) => <h3 className="text-base font-bold mb-3 mt-4 text-white">{children}</h3>,
    ul: ({children}) => <ul className="list-disc pl-5 mb-4 space-y-1">{children}</ul>,
    ol: ({children}) => <ol className="list-decimal pl-5 mb-4 space-y-1">{children}</ol>,
    li: ({children}) => <li className="pl-1 mb-1">{children}</li>,
    strong: ({children}) => <strong className="font-semibold text-white">{children}</strong>,
    em: ({children}) => <em className="italic">{children}</em>,
    code: ({children}) => <code className="bg-white/10 px-1.5 py-0.5 rounded text-sm font-mono text-[var(--color-accent)]">{children}</code>,
  };

  let content = message.content;
  if (!isUser) {
    content = content.replace(/Source:(.*)(\n|$)/g, '').replace(/Page \d+/g, '').trim();
  }

  return (
    <div className="w-full flex mb-8 px-4 md:px-12 border-b border-white/5 pb-8 last:border-0">
      <div className="max-w-[800px] flex gap-6 w-full">
        <div className="w-24 shrink-0 text-right">
          <span className={`text-[10px] font-bold tracking-[0.2em] uppercase ${isUser ? 'text-[var(--color-accent)]' : 'text-white/40'}`}>
            {isUser ? 'You' : 'StudyMate'}
          </span>
        </div>
        <div className={`flex-1 text-lg leading-relaxed ${isUser ? 'text-white font-medium' : 'text-white/70 font-light'}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <ReactMarkdown components={markdownComponents}>
              {content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}
