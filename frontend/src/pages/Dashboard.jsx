import React, { useEffect, useState } from 'react';
import Button from '../components/ui/Button';
import { BookOpen, Award, FileText, Loader2, AlertCircle, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getDocuments } from '../services/api';
import { useStudyContext } from '../context/StudyContext';

export default function Dashboard() {
  const navigate = useNavigate();
  const { setActiveDocument } = useStudyContext();
  const [recentDocs, setRecentDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;
    
    const fetchDocs = async () => {
      try {
        const data = await getDocuments();
        if (isMounted) {
          setRecentDocs(data.slice(0, 3));
          setLoading(false);
          const processed = data.find(d => d.processing_status === 'processed');
          if (processed) {
            setActiveDocument(processed);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError('Failed to load recent materials.');
          setLoading(false);
        }
      }
    };
    
    fetchDocs();
    return () => {
      isMounted = false;
    };
  }, [setActiveDocument]);

  const currentDoc = recentDocs.find(d => d.processing_status === 'processed') || recentDocs[0];

  const formatDocName = (name) => {
    if (!name) return '';
    return name.replace('.pdf', '').replace(/_/g, ' ');
  };

  return (
    <div className="max-w-7xl mx-auto pb-20 px-4 md:px-8">
      
      {/* 1. TOP HERO */}
      <div className="flex flex-col lg:flex-row gap-12 lg:gap-16 mb-20 mt-8 items-center">
        {/* Left: Text */}
        <div className="flex-1 max-w-2xl">
          <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-4">
            YOUR STUDY DESK
          </p>
          <h1 className="font-editorial text-4xl md:text-5xl lg:text-[60px] text-[var(--color-ink)] leading-[1.05] mb-6 tracking-tight">
            Learn from your material.<br />
            Ask anything.<br />
            Test yourself.
          </h1>
          <p className="text-base md:text-lg text-[var(--color-muted)] mb-8 max-w-md leading-relaxed">
            One place to understand your material, practice concepts, and find what to revisit.
          </p>
          <button 
            onClick={() => currentDoc ? navigate('/tutor', { state: { documentId: currentDoc.document_id } }) : navigate('/materials/upload')} 
            className="group flex items-center gap-2 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white px-6 py-3 rounded-full text-sm font-medium transition-all shadow-md hover:shadow-xl hover:-translate-y-0.5"
          >
            Start studying <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        {/* Right: Editorial Visual Composition (Textbook Metaphor) */}
        <div className="flex-1 w-full relative min-h-[440px] hidden md:block select-none">
          {/* Base textbook cover */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[280px] h-[380px] bg-[var(--color-dark-surface)] rounded-[20px] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.3)] transform -rotate-6 transition-transform duration-700 hover:-rotate-3 overflow-hidden">
            {/* Book spine decoration */}
            <div className="absolute left-0 top-0 bottom-0 w-6 bg-black/20 border-r border-white/5"></div>
            
            <div className="p-8 flex flex-col h-full justify-between">
              <div>
                <p className="text-[10px] font-bold tracking-[0.2em] text-white/50 uppercase mb-2">CHAPTER 03</p>
                <h2 className="font-editorial text-3xl text-white leading-tight">Chemical<br/>Reactions</h2>
              </div>
              <div className="text-[96px] font-editorial font-light text-white/10 leading-none mt-auto">
                10
              </div>
            </div>
            {/* Subject Label */}
            <div className="absolute bottom-8 right-8">
              <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase">SCIENCE</p>
            </div>
          </div>

          {/* Overlapping Page / Surface */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/4 -translate-y-[45%] w-[260px] h-[360px] bg-[#F7F6F2] rounded-[12px] shadow-2xl transform rotate-3 transition-transform duration-700 hover:rotate-6 border border-black/5 overflow-hidden">
            <div className="p-6">
              <div className="w-10 h-1 bg-[var(--color-accent)] mb-6"></div>
              <p className="font-editorial text-xl text-[var(--color-ink)] leading-snug mb-4">
                The process in which new substances with new properties are formed from one or more substances is called a Chemical Reaction.
              </p>
              <p className="font-mono text-[10px] text-[var(--color-muted)] mt-10 bg-white p-3 rounded-lg border border-[var(--color-border)] shadow-sm">
                2Mg(s) + O₂(g) → 2MgO(s)
              </p>
            </div>
          </div>

          {/* Floating Labels */}
          <div className="absolute top-[15%] right-[10%] px-4 py-2 bg-[var(--color-accent)] text-white text-[10px] font-bold tracking-[0.1em] uppercase rounded-full shadow-lg transform rotate-6">
            5 UNITS
          </div>
          <div className="absolute bottom-[25%] left-[5%] px-4 py-2 bg-white text-[var(--color-ink)] text-[10px] font-bold tracking-[0.1em] uppercase rounded-full shadow-xl border border-[var(--color-border)] transform -rotate-12">
            RECENTLY STUDIED
          </div>
        </div>
      </div>

      {/* 2. MAIN DARK STUDY PANEL */}
      <div className="w-full bg-[#19171F] rounded-[24px] md:rounded-[32px] p-6 md:p-10 mb-20 shadow-2xl overflow-hidden relative flex flex-col md:flex-row gap-10 group border border-white/5">
        {/* Glow behind */}
        <div className="absolute top-0 right-1/4 w-[400px] h-[400px] bg-[var(--color-accent)]/10 blur-[100px] rounded-full pointer-events-none -translate-y-1/2"></div>
        
        {/* LEFT: Current Material Details */}
        <div className="flex-1 relative z-10 flex flex-col justify-center">
          <p className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            CURRENT MATERIAL
          </p>
          
          {currentDoc ? (
            <>
              <h2 className="font-editorial text-3xl md:text-5xl text-white leading-[1.1] mb-4">
                {formatDocName(currentDoc.document_name)}
              </h2>
              <div className="text-[10px] md:text-[11px] font-bold tracking-[0.1em] text-white/50 uppercase flex items-center gap-2 mb-8">
                <span>Class {currentDoc.class_name} · {currentDoc.subject}</span>
                <span className="w-1 h-1 rounded-full bg-white/20"></span>
                <span>{currentDoc.chapter_count || 0} Units</span>
                <span className="w-1 h-1 rounded-full bg-white/20"></span>
                <span>{currentDoc.page_count || 0} Pages</span>
              </div>
              <div>
                <button 
                  onClick={() => navigate('/tutor', { state: { documentId: currentDoc.document_id } })}
                  className="inline-flex items-center gap-2 bg-white text-[var(--color-ink)] hover:bg-[var(--color-warm-bg)] px-6 py-3 rounded-full text-sm font-medium transition-all"
                >
                  Continue studying <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <div>
              <h2 className="font-editorial text-3xl md:text-4xl text-white mb-4">No active material</h2>
              <p className="text-base text-white/50 mb-8 max-w-sm">Upload a new document to your library to start studying.</p>
              <button 
                onClick={() => navigate('/materials/upload')} 
                className="inline-flex items-center gap-2 bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] px-6 py-3 text-sm rounded-full font-medium transition-all"
              >
                Upload Document <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* RIGHT: Editorial Chapter Visual */}
        {currentDoc && (
          <div className="flex-1 relative z-10 hidden md:flex items-center justify-end">
            <div className="relative w-full max-w-[300px] h-[220px] border-l border-white/10 pl-8 flex flex-col justify-center">
              {/* Oversized background number */}
              <div className="absolute -left-8 top-0 text-[140px] font-editorial text-white/5 leading-none select-none pointer-events-none">
                01
              </div>
              
              <p className="text-[10px] font-mono text-[var(--color-accent)] mb-3">CH. 01</p>
              <h3 className="font-editorial text-2xl md:text-3xl text-white leading-tight uppercase tracking-wide">
                {currentDoc.chapters && currentDoc.chapters.length > 0 
                  ? currentDoc.chapters[0].chapter_title 
                  : "INTRODUCTION"}
              </h3>
              <p className="font-mono text-[10px] text-white/30 mt-6 tracking-widest uppercase">
                VOL. I — SEC. A
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-col lg:flex-row gap-12 lg:gap-16">
        
        {/* 3. CONTINUE LEARNING (Table of Contents Style) */}
        <section className="flex-1">
          <h2 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-8">
            CONTINUE LEARNING
          </h2>
          
          <div className="flex flex-col">
            {loading ? (
              <div className="py-8 flex flex-col items-center">
                <Loader2 className="w-5 h-5 animate-spin text-[var(--color-muted)] mb-4" />
              </div>
            ) : error ? (
              <p className="text-red-500 py-4">{error}</p>
            ) : recentDocs.length === 0 ? (
              <p className="text-[var(--color-muted)] text-base italic">Your library is empty.</p>
            ) : (
              recentDocs.map((doc, idx) => (
                <div 
                  key={doc.document_id}
                  onClick={() => doc.processing_status === 'processed' ? navigate('/tutor', { state: { documentId: doc.document_id } }) : null}
                  className={`group flex items-center justify-between py-6 border-b border-[var(--color-border)] cursor-pointer transition-colors hover:bg-[var(--color-lavender)]/20 px-3 -mx-3 rounded-xl ${doc.processing_status !== 'processed' ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <div className="flex items-center gap-6">
                    <span className="font-editorial text-3xl text-[var(--color-muted)]/30 group-hover:text-[var(--color-accent)] transition-colors w-10">
                      0{idx + 1}
                    </span>
                    <div>
                      <h4 className="font-editorial text-xl text-[var(--color-ink)] mb-1 group-hover:text-[var(--color-accent)] transition-colors">
                        {formatDocName(doc.document_name)}
                      </h4>
                      <p className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-muted)] uppercase">
                        Class {doc.class_name} · {doc.subject}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {doc.processing_status !== 'processed' && (
                      <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider bg-amber-100 px-2.5 py-1 rounded-full">
                        {doc.processing_status}
                      </span>
                    )}
                    <ArrowRight className="w-4 h-4 text-[var(--color-muted)] group-hover:text-[var(--color-accent)] group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* 4. RECENT ACTIVITY (Editorial Text Style) */}
        <section className="lg:w-[320px] shrink-0">
          <h2 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-8">
            RECENT ACTIVITY
          </h2>

          <div className="space-y-8">
            
            <div className="relative pl-5 border-l border-[var(--color-border)]">
              <div className="absolute left-[-4.5px] top-1.5 w-2 h-2 rounded-full bg-[var(--color-accent)]"></div>
              <p className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-muted)] uppercase mb-1">Today</p>
              <h4 className="font-editorial text-lg text-[var(--color-ink)] mb-0.5">Studied Chemical Substances</h4>
              <p className="text-[12px] text-[var(--color-muted)]">Class 10 · Science</p>
            </div>

            <div className="relative pl-5 border-l border-[var(--color-border)]">
              <div className="absolute left-[-4.5px] top-1.5 w-2 h-2 rounded-full bg-[var(--color-border)]"></div>
              <p className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-muted)] uppercase mb-1">Yesterday</p>
              <h4 className="font-editorial text-lg text-[var(--color-ink)] mb-0.5">Quiz Generated</h4>
              <p className="text-[12px] text-[var(--color-muted)]">Chemical Reactions · Score: 8/10</p>
            </div>

            <div className="relative pl-5 border-l border-[var(--color-border)]">
              <div className="absolute left-[-4.5px] top-1.5 w-2 h-2 rounded-full bg-[var(--color-border)]"></div>
              <p className="text-[10px] font-bold tracking-[0.1em] text-[var(--color-muted)] uppercase mb-1">2 days ago</p>
              <h4 className="font-editorial text-lg text-[var(--color-ink)] mb-0.5">Asked AI Tutor</h4>
              <p className="text-[12px] text-[var(--color-muted)] italic">"What is oxidation?"</p>
            </div>

          </div>
        </section>
        
      </div>
    </div>
  );
}
