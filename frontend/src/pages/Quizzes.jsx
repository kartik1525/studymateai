import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import { getDocuments, getDocument, generateQuiz } from '../services/api';
import { FileText, Loader2, Sparkles, BookOpen, AlertCircle, ArrowRight } from 'lucide-react';
import { useStudyContext } from '../context/StudyContext';

export default function Quizzes() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setActiveDocument } = useStudyContext();

  // State
  const [documents, setDocuments] = useState([]);
  const [activeDocId, setActiveDocId] = useState(location.state?.documentId || null);
  const [activeDoc, setActiveDoc] = useState(null);
  
  // Quiz config
  const [selectedChapters, setSelectedChapters] = useState([]); // Empty = Entire material
  const [questionCount, setQuestionCount] = useState(10);
  const [difficulty, setDifficulty] = useState('medium');
  const [questionTypes, setQuestionTypes] = useState(['multiple_choice', 'true_false']);
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');

  // Fetch documents
  useEffect(() => {
    let isMounted = true;
    const fetchDocs = async () => {
      try {
        const docs = await getDocuments();
        if (isMounted) {
          setDocuments(docs.filter(d => d.processing_status === 'processed'));
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchDocs();
    return () => isMounted = false;
  }, []);

  // Fetch active document details
  useEffect(() => {
    if (!activeDocId) {
      setActiveDoc(null);
      setActiveDocument(null);
      setSelectedChapters([]);
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
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchDocDetails();
    return () => isMounted = false;
  }, [activeDocId, setActiveDocument]);

  const toggleChapter = (chapterNum) => {
    setSelectedChapters(prev => {
      if (prev.includes(chapterNum)) {
        return prev.filter(c => c !== chapterNum);
      } else {
        return [...prev, chapterNum].sort((a, b) => a - b);
      }
    });
  };

  const toggleQuestionType = (type) => {
    setQuestionTypes(prev => {
      if (prev.includes(type)) {
        if (prev.length === 1) return prev;
        return prev.filter(t => t !== type);
      }
      return [...prev, type];
    });
  };

  const handleGenerate = async () => {
    if (!activeDoc) return;
    
    setIsGenerating(true);
    setError('');

    let scopeToSend = selectedChapters;
    if (selectedChapters.length === 0) {
      scopeToSend = activeDoc.chapters.map(ch => ch.chapter_number);
    }

    if (scopeToSend.length === 0) {
      setError('Document has no chapters to generate a quiz from.');
      setIsGenerating(false);
      return;
    }

    try {
      const quiz = await generateQuiz(
        activeDoc.document_id,
        scopeToSend,
        questionCount,
        difficulty,
        questionTypes
      );
      
      const quizId = `qz_${Math.random().toString(36).substr(2, 9)}`;
      navigate(`/quiz/${quizId}`, { state: { quiz, config: {
        document_name: activeDoc.document_name,
        subject: activeDoc.subject,
        chapters: scopeToSend,
        difficulty,
        activeDocId
      }}});

    } catch (err) {
      console.error(err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to generate quiz. Please try again.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const formatDocName = (name) => {
    if (!name) return '';
    return name.replace('.pdf', '').replace(/_/g, ' ');
  };

  return (
    <div className="max-w-7xl mx-auto py-10 px-4 md:px-8 pb-24">
      <div className="mb-10">
        <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-3">
          TEST YOURSELF
        </p>
        <h1 className="font-editorial text-4xl md:text-[50px] text-[var(--color-ink)] leading-[1.1] mb-4">
          Build a quiz from what you've studied.
        </h1>
      </div>

      <div className="flex flex-col lg:flex-row gap-12 lg:gap-20">
        {/* LEFT: Material & Chapter Selection */}
        <div className="flex-1 max-w-xl">
          <h3 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-6">STUDY MATERIAL</h3>
          
          {!activeDocId ? (
            <div className="space-y-2">
              {documents.length === 0 ? (
                <div className="py-8 text-[var(--color-muted)] italic">No processed materials available.</div>
              ) : (
                documents.map(doc => (
                  <div 
                    key={doc.document_id}
                    onClick={() => setActiveDocId(doc.document_id)}
                    className="group flex items-center justify-between p-4 border border-[var(--color-border)] rounded-[16px] cursor-pointer transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent)]/5"
                  >
                    <div>
                      <h4 className="font-editorial text-xl text-[var(--color-ink)] group-hover:text-[var(--color-accent)] transition-colors">
                        {formatDocName(doc.document_name)}
                      </h4>
                      <p className="text-[10px] font-bold tracking-widest text-[var(--color-muted)] uppercase mt-1">
                        Class {doc.class_name} · {doc.subject}
                      </p>
                    </div>
                    <ArrowRight className="w-5 h-5 text-[var(--color-muted)] group-hover:text-[var(--color-accent)] transition-colors" />
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-8">
              {/* Selected Document Row */}
              <div className="flex items-center justify-between p-4 border-2 border-[var(--color-accent)] bg-[var(--color-accent)]/5 rounded-[16px]">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-[var(--color-accent)] shrink-0"></div>
                  <div>
                    <h4 className="font-editorial text-xl text-[var(--color-ink)]">
                      {formatDocName(activeDoc?.document_name)}
                    </h4>
                    <p className="text-[10px] font-bold tracking-widest text-[var(--color-accent)] uppercase mt-1">
                      Class {activeDoc?.class_name} · {activeDoc?.subject}
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => setActiveDocId(null)}
                  className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors px-3 py-1.5 border border-[var(--color-border)] rounded-full bg-white"
                >
                  Change
                </button>
              </div>

              {/* Chapter Selection */}
              <div>
                <h3 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-4">CHAPTERS</h3>
                
                <div className="bg-white border border-[var(--color-border)] rounded-[20px] overflow-hidden p-2">
                  <label className={`flex items-start gap-4 p-3 rounded-[12px] cursor-pointer transition-colors hover:bg-[var(--color-warm-bg)] ${selectedChapters.length === 0 ? 'bg-[var(--color-accent)]/10' : ''}`}>
                    <div className={`mt-0.5 w-4 h-4 rounded-[4px] border-2 flex items-center justify-center transition-colors ${selectedChapters.length === 0 ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-[var(--color-border)] bg-white'}`}>
                      {selectedChapters.length === 0 && <span className="w-2 h-2 bg-white rounded-sm"></span>}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-[14px] font-bold ${selectedChapters.length === 0 ? 'text-[var(--color-accent)]' : 'text-[var(--color-ink)]'}`}>Entire material</div>
                    </div>
                  </label>
                  
                  <div className="my-2 border-t border-[var(--color-border)]/50 mx-4"></div>
                  
                  <div className="max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
                    {activeDoc?.chapters?.map(ch => {
                      const isSelected = selectedChapters.includes(ch.chapter_number);
                      return (
                        <label 
                          key={ch.chapter_number} 
                          className={`flex items-start gap-4 p-3 rounded-[12px] cursor-pointer transition-colors hover:bg-[var(--color-warm-bg)] ${isSelected ? 'bg-[var(--color-accent)]/10' : ''}`}
                        >
                          <div className={`mt-0.5 w-4 h-4 rounded-[4px] border-2 flex items-center justify-center transition-colors ${isSelected ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-[var(--color-border)] bg-white'}`}>
                            {isSelected && <span className="w-2 h-2 bg-white rounded-sm"></span>}
                          </div>
                          <div className="flex-1 min-w-0 flex items-start gap-3">
                            <div className={`font-mono text-[11px] mt-0.5 ${isSelected ? 'text-[var(--color-accent)]' : 'text-[var(--color-muted)]'}`}>
                              {String(ch.chapter_number).padStart(2, '0')}
                            </div>
                            <div className={`text-[14px] leading-tight ${isSelected ? 'text-[var(--color-accent)] font-semibold' : 'text-[var(--color-ink)] font-medium'}`}>
                              {ch.chapter_title}
                            </div>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>

                {selectedChapters.length > 0 && (
                  <div className="mt-4 p-4 bg-[var(--color-warm-bg)] border border-[var(--color-border)] rounded-[16px]">
                    <p className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-2">QUIZ SCOPE</p>
                    <p className="text-[13px] text-[var(--color-ink)] font-medium leading-relaxed">
                      Questions will be generated only from the selected {selectedChapters.length === 1 ? 'chapter' : 'chapters'}.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Quiz Settings */}
        <div className={`flex-1 max-w-sm transition-opacity duration-300 ${!activeDocId ? 'opacity-30 pointer-events-none' : 'opacity-100'}`}>
          <h3 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-6">QUIZ SETTINGS</h3>
          
          <div className="space-y-10">
            {/* Question Count */}
            <div>
              <label className="block text-[13px] font-bold text-[var(--color-ink)] mb-3">Questions</label>
              <div className="flex bg-white border border-[var(--color-border)] rounded-[12px] p-1 shadow-sm">
                {[5, 10, 15, 20].map(count => (
                  <button
                    key={count}
                    onClick={() => setQuestionCount(count)}
                    disabled={!activeDocId}
                    className={`flex-1 py-2 text-[13px] font-semibold rounded-[8px] transition-colors ${questionCount === count ? 'bg-[var(--color-accent)] text-white shadow-sm' : 'text-[var(--color-muted)] hover:bg-[var(--color-warm-bg)] hover:text-[var(--color-ink)]'}`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>

            {/* Difficulty */}
            <div>
              <label className="block text-[13px] font-bold text-[var(--color-ink)] mb-3">Difficulty</label>
              <div className="flex bg-white border border-[var(--color-border)] rounded-[12px] p-1 shadow-sm">
                {['easy', 'medium', 'hard'].map(diff => (
                  <button
                    key={diff}
                    onClick={() => setDifficulty(diff)}
                    disabled={!activeDocId}
                    className={`flex-1 py-2 text-[13px] font-semibold capitalize rounded-[8px] transition-colors ${difficulty === diff ? 'bg-[var(--color-accent)] text-white shadow-sm' : 'text-[var(--color-muted)] hover:bg-[var(--color-warm-bg)] hover:text-[var(--color-ink)]'}`}
                  >
                    {diff}
                  </button>
                ))}
              </div>
            </div>

            {/* Question Types */}
            <div>
              <label className="block text-[13px] font-bold text-[var(--color-ink)] mb-3">Question type</label>
              <div className="space-y-3">
                <label className={`flex items-center gap-3 p-3 border border-[var(--color-border)] rounded-[12px] cursor-pointer transition-colors hover:bg-[var(--color-warm-bg)] ${questionTypes.includes('multiple_choice') ? 'bg-[var(--color-accent)]/5 border-[var(--color-accent)]' : 'bg-white'}`}>
                  <div className={`w-4 h-4 rounded-[4px] border-2 flex items-center justify-center transition-colors ${questionTypes.includes('multiple_choice') ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-[var(--color-border)] bg-white'}`}>
                    {questionTypes.includes('multiple_choice') && <span className="w-2 h-2 bg-white rounded-sm"></span>}
                  </div>
                  <input 
                    type="checkbox" 
                    checked={questionTypes.includes('multiple_choice')}
                    onChange={() => toggleQuestionType('multiple_choice')}
                    disabled={!activeDocId}
                    className="hidden"
                  />
                  <span className={`text-[13px] font-medium ${questionTypes.includes('multiple_choice') ? 'text-[var(--color-accent)]' : 'text-[var(--color-ink)]'}`}>Multiple Choice</span>
                </label>
                <label className={`flex items-center gap-3 p-3 border border-[var(--color-border)] rounded-[12px] cursor-pointer transition-colors hover:bg-[var(--color-warm-bg)] ${questionTypes.includes('true_false') ? 'bg-[var(--color-accent)]/5 border-[var(--color-accent)]' : 'bg-white'}`}>
                  <div className={`w-4 h-4 rounded-[4px] border-2 flex items-center justify-center transition-colors ${questionTypes.includes('true_false') ? 'bg-[var(--color-accent)] border-[var(--color-accent)]' : 'border-[var(--color-border)] bg-white'}`}>
                    {questionTypes.includes('true_false') && <span className="w-2 h-2 bg-white rounded-sm"></span>}
                  </div>
                  <input 
                    type="checkbox" 
                    checked={questionTypes.includes('true_false')}
                    onChange={() => toggleQuestionType('true_false')}
                    disabled={!activeDocId}
                    className="hidden"
                  />
                  <span className={`text-[13px] font-medium ${questionTypes.includes('true_false') ? 'text-[var(--color-accent)]' : 'text-[var(--color-ink)]'}`}>True / False</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-600 text-xs rounded-xl flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Generate Button */}
            <div className="pt-4 border-t border-[var(--color-border)]">
              <button 
                onClick={handleGenerate}
                disabled={isGenerating || !activeDocId}
                className="w-full md:w-auto min-w-[200px] h-[52px] bg-[var(--color-accent)] text-white rounded-full font-medium text-[14px] flex items-center justify-center gap-2 transition-all hover:-translate-y-0.5 hover:shadow-lg disabled:opacity-50 disabled:hover:translate-y-0 disabled:shadow-none"
              >
                {isGenerating ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Preparing...</>
                ) : (
                  <>Generate Quiz <ArrowRight className="w-4 h-4 ml-1" /></>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
