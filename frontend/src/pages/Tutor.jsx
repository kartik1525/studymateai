import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ChatInput from '../components/tutor/ChatInput';
import ChatMessage from '../components/tutor/ChatMessage';
import TutorChapterSidebar from '../components/tutor/TutorChapterSidebar';
import { getDocuments, getDocument, askTutor } from '../services/api';
import { FileText, Loader2, Sparkles, BookOpen, Settings2 } from 'lucide-react';
import { useStudyContext } from '../context/StudyContext';

export default function Tutor() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setActiveDocument } = useStudyContext();
  
  // State
  const [documents, setDocuments] = useState([]);
  const [activeDocId, setActiveDocId] = useState(location.state?.documentId || null);
  const [activeDoc, setActiveDoc] = useState(null);
  const [selectedChapters, setSelectedChapters] = useState([]); // Empty array means entire material
  
  const [chatHistory, setChatHistory] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showScopePanel, setShowScopePanel] = useState(false);

  const chatContainerRef = useRef(null);

  // Fetch all documents on mount
  useEffect(() => {
    let isMounted = true;
    const fetchDocs = async () => {
      try {
        const docs = await getDocuments();
        if (isMounted) {
          setDocuments(docs.filter(d => d.processing_status === 'processed'));
        }
      } catch (err) {
        console.error('Failed to fetch documents:', err);
      }
    };
    fetchDocs();
    return () => isMounted = false;
  }, []);

  // Fetch active document details when activeDocId changes
  useEffect(() => {
    if (!activeDocId) {
      setActiveDoc(null);
      setSelectedChapters([]);
      setChatHistory([]);
      setActiveDocument(null);
      return;
    }

    let isMounted = true;
    const fetchDocDetails = async () => {
      try {
        const doc = await getDocument(activeDocId);
        if (isMounted) {
          if (doc.chapters) {
            const unique = [];
            const seen = new Set();
            for (const ch of doc.chapters) {
              if (!seen.has(ch.chapter_number)) {
                seen.add(ch.chapter_number);
                unique.push(ch);
              }
            }
            doc.chapters = unique;
          }

          setActiveDoc(doc);
          setActiveDocument(doc);
          setSelectedChapters([]); 
          setChatHistory([]); 
        }
      } catch (err) {
        if (isMounted) {
          console.error('Failed to load document details:', err);
        }
      }
    };
    fetchDocDetails();
    return () => isMounted = false;
  }, [activeDocId, setActiveDocument]);

  // Auto-scroll chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, isLoading]);

  const toggleChapter = (chapterNum) => {
    setSelectedChapters(prev => {
      if (prev.includes(chapterNum)) {
        return prev.filter(c => c !== chapterNum);
      } else {
        return [...prev, chapterNum].sort((a, b) => a - b);
      }
    });
  };

  const handleAsk = async (customQuestion = null) => {
    const questionToAsk = customQuestion || inputMessage;
    if (!questionToAsk.trim() || isLoading || !activeDoc) return;

    setShowScopePanel(false); // Close mobile panel

    const userMessage = { role: 'user', content: questionToAsk.trim() };
    setChatHistory(prev => [...prev, userMessage]);
    
    if (!customQuestion) setInputMessage('');
    setIsLoading(true);

    let scopeToSend = selectedChapters;
    if (selectedChapters.length === 0) {
      scopeToSend = activeDoc.chapters.map(ch => ch.chapter_number);
    }

    try {
      const response = await askTutor(activeDoc.document_id, scopeToSend, questionToAsk.trim());
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: response.answer }
      ]);
    } catch (err) {
      console.error(err);
      let errorMsg = 'I couldn\'t answer that right now. Please try again.';
      if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
        errorMsg = 'The tutor is taking longer than expected. Please try again.';
      }
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: `⚠️ ${errorMsg}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDocName = (name) => {
    if (!name) return '';
    return name.replace('.pdf', '').replace(/_/g, ' ');
  };

  // Document Selector View
  if (!activeDocId) {
    return (
      <div className="max-w-7xl mx-auto py-10 px-4 md:px-8">
        <div className="text-left mb-10">
          <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-3">
            AI TUTOR
          </p>
          <h1 className="font-editorial text-4xl md:text-[50px] text-[var(--color-ink)] leading-[1.1] mb-4">
            Select a study material
          </h1>
          <p className="text-[var(--color-muted)] text-base md:text-lg max-w-lg">
            Choose a document to begin an interactive study session with the AI Tutor.
          </p>
        </div>

        {documents.length === 0 ? (
          <div className="p-16 border border-dashed border-[var(--color-border)] rounded-[32px] text-center bg-white/50 backdrop-blur-sm shadow-sm max-w-2xl">
            <BookOpen className="w-10 h-10 text-[var(--color-muted)]/50 mx-auto mb-6" />
            <h3 className="font-editorial text-3xl text-[var(--color-ink)] mb-4">No processed materials</h3>
            <p className="text-[var(--color-muted)] text-lg mb-8">
              You need at least one processed textbook to use the AI Tutor.
            </p>
            <button 
              onClick={() => navigate('/materials/upload')}
              className="bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white px-8 py-4 rounded-full font-medium transition-transform hover:-translate-y-0.5 shadow-md"
            >
              Upload Material
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {documents.map(doc => (
              <div 
                key={doc.document_id}
                onClick={() => setActiveDocId(doc.document_id)}
                className="group bg-white border border-[var(--color-border)] rounded-[24px] hover:border-[var(--color-accent)] cursor-pointer transition-all duration-300 shadow-sm hover:shadow-md p-6 flex flex-col min-h-[140px]"
              >
                <div className="flex-1 mb-6">
                  <p className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-2">
                    Class {doc.class_name} · {doc.subject}
                  </p>
                  <h3 className="font-editorial text-xl md:text-[22px] text-[var(--color-ink)] group-hover:text-[var(--color-accent)] transition-colors leading-tight">
                    {formatDocName(doc.document_name)}
                  </h3>
                </div>
                <div className="text-[10px] text-[var(--color-muted)] font-bold uppercase tracking-widest border-t border-[var(--color-border)] pt-4 flex justify-between items-center">
                  <span>{doc.chapter_count} Units</span>
                  <span className="group-hover:translate-x-1 transition-transform">Start →</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  let scopeText = "Entire material";
  if (selectedChapters.length === 1) {
    const ch = activeDoc?.chapters.find(c => c.chapter_number === selectedChapters[0]);
    scopeText = `Chapter ${selectedChapters[0]} — ${ch?.chapter_title || 'Unknown'}`;
  } else if (selectedChapters.length > 1) {
    scopeText = selectedChapters.map(c => `Chapter ${c}`).join(' + ');
  }

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-8rem)] min-h-[500px] flex flex-col relative px-4 md:px-8">
      
      {/* Top Title Area */}
      <div className="mb-6 flex justify-between items-end">
        <div>
          <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-2">
            AI TUTOR
          </p>
          <h1 className="font-editorial text-[44px] md:text-[50px] text-[var(--color-ink)] leading-[1.1]">
            Ask your material anything.
          </h1>
        </div>
      </div>

      <div className="flex-1 flex gap-6 min-h-0 relative z-10 w-full">
        
        {/* Chat Workspace */}
        <div className="flex-1 flex bg-[#19171F] rounded-[24px] overflow-hidden shadow-xl relative group/workspace border border-white/10 max-h-[700px]">
          
          <TutorChapterSidebar 
            activeDoc={activeDoc}
            selectedChapters={selectedChapters}
            toggleChapter={toggleChapter}
            setSelectedChapters={setSelectedChapters}
          />

          <div className="flex-1 flex flex-col relative min-w-0">
            <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-b from-[var(--color-accent)]/10 to-transparent pointer-events-none"></div>

            {/* Current Material Header Inside Chat */}
            <div className="px-6 md:px-8 py-4 border-b border-white/10 flex justify-between items-center relative z-10 shrink-0">
               <div className="min-w-0">
                 <h2 className="font-editorial text-[20px] text-white leading-tight truncate">{formatDocName(activeDoc?.document_name)}</h2>
                 <p className="text-[10px] font-medium text-white/50 tracking-wider uppercase mt-1">Class {activeDoc?.class_name} · {activeDoc?.subject}</p>
               </div>
            </div>

            <div 
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto scroll-smooth py-6 relative z-10 custom-scrollbar dark-scrollbar"
            >
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-col justify-center items-center text-center px-4">
                  <h3 className="font-editorial text-[28px] md:text-[32px] text-white font-medium mb-3">Start learning.</h3>
                  <p className="text-white/60 max-w-sm mx-auto mb-8 leading-relaxed text-[14px]">
                    Ask about concepts, definitions, examples, or exam preparation based on your material.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-md mx-auto">
                    <button disabled={isLoading} onClick={() => handleAsk("Explain the selected material in simple language.")} className="px-4 py-3 bg-white/5 border border-white/10 rounded-[16px] text-left hover:bg-white/10 hover:border-white/20 transition-all disabled:opacity-50 h-[75px] flex flex-col justify-center">
                      <span className="block text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-1">Simplify</span>
                      <span className="text-white/80 font-medium text-[13px]">Explain this in simple language.</span>
                    </button>
                    <button disabled={isLoading} onClick={() => handleAsk("Give me a detailed breakdown of this material.")} className="px-4 py-3 bg-white/5 border border-white/10 rounded-[16px] text-left hover:bg-white/10 hover:border-white/20 transition-all disabled:opacity-50 h-[75px] flex flex-col justify-center">
                      <span className="block text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-1">Deep Dive</span>
                      <span className="text-white/80 font-medium text-[13px]">Give me a detailed explanation.</span>
                    </button>
                    <button disabled={isLoading} onClick={() => handleAsk("Give me an example based on this material.")} className="px-4 py-3 bg-white/5 border border-white/10 rounded-[16px] text-left hover:bg-white/10 hover:border-white/20 transition-all disabled:opacity-50 h-[75px] flex flex-col justify-center">
                      <span className="block text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-1">Examples</span>
                      <span className="text-white/80 font-medium text-[13px]">Show examples from this material.</span>
                    </button>
                    <button disabled={isLoading} onClick={() => handleAsk("Give me an exam-ready answer about this topic from the selected material.")} className="px-4 py-3 bg-white/5 border border-white/10 rounded-[16px] text-left hover:bg-white/10 hover:border-white/20 transition-all disabled:opacity-50 h-[75px] flex flex-col justify-center">
                      <span className="block text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-1">Exam Prep</span>
                      <span className="text-white/80 font-medium text-[13px]">Give me an exam-ready explanation.</span>
                    </button>
                  </div>
                </div>
            ) : (
              <div className="pb-8">
                {chatHistory.map((msg, idx) => (
                  <ChatMessage key={idx} message={msg} />
                ))}
                {isLoading && (
                  <div className="flex px-4 md:px-8 mt-4">
                    <div className="bg-white/5 border border-white/10 px-5 py-4 rounded-[20px] rounded-tl-sm flex items-center gap-3 backdrop-blur-md">
                      <Loader2 className="w-4 h-4 text-[var(--color-accent)] animate-spin" />
                      <span className="text-sm text-white/70 font-light">Synthesizing answer...</span>
                    </div>
                  </div>
                )}
              </div>
            )}
            </div>
            
            <div className="relative z-10 px-4 pb-4 md:px-8 md:pb-8 pt-4 shrink-0">
              <ChatInput 
                value={inputMessage}
                onChange={setInputMessage}
                onSubmit={() => handleAsk()}
                isLoading={isLoading}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
