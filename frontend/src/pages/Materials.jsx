import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDocuments } from '../services/api';
import { Loader2, AlertCircle, ArrowRight, Plus } from 'lucide-react';

export default function Materials() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;
    
    const fetchDocs = async () => {
      try {
        const data = await getDocuments();
        if (isMounted) {
          setDocuments(data);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError('Failed to load materials. Please try again later.');
          setLoading(false);
        }
      }
    };
    
    fetchDocs();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const formatDocName = (name) => {
    if (!name) return '';
    return name.replace('.pdf', '').replace(/_/g, ' ');
  };

  return (
    <div className="max-w-7xl mx-auto pb-20 px-4 md:px-8">
      {/* Header */}
      <div className="mb-10 mt-6 max-w-2xl">
        <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-3">
          YOUR LIBRARY
        </p>
        <h1 className="font-editorial text-4xl md:text-[50px] text-[var(--color-ink)] leading-[1.1] mb-4">
          Your study material.
        </h1>
        <p className="text-base md:text-lg text-[var(--color-muted)]">
          Everything you need to learn from, all in one place.
        </p>
      </div>

      {/* Dark Upload Area */}
      <div 
        onClick={() => navigate('/materials/upload')}
        className="w-full bg-[#18161E] rounded-[24px] p-8 md:p-10 mb-16 h-[250px] cursor-pointer transition-transform hover:-translate-y-1 shadow-xl flex flex-col justify-center border border-white/5 relative overflow-hidden group"
      >
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-accent)]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
        
        <div className="relative z-10">
          <p className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-4 flex items-center gap-2">
            <Plus className="w-3.5 h-3.5" /> ADD STUDY MATERIAL
          </p>
          <h2 className="font-editorial text-3xl md:text-4xl text-white mb-3">
            Upload a PDF document
          </h2>
          <p className="text-white/60 text-sm md:text-base max-w-md">
            Turn your textbook into an interactive study space where you can ask questions and take quizzes.
          </p>
        </div>
      </div>

      {/* Editorial Rows */}
      <div>
        <h2 className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-8">
          YOUR MATERIALS
        </h2>
        
        <div className="flex flex-col">
          {loading ? (
            <div className="py-20 flex justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-[var(--color-muted)]" />
            </div>
          ) : error ? (
            <div className="p-6 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <p className="text-red-700">{error}</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="py-12">
              <p className="text-[var(--color-muted)] text-lg italic">Your library is currently empty.</p>
            </div>
          ) : (
            documents.map((doc, idx) => (
              <div 
                key={doc.document_id}
                onClick={() => doc.processing_status === 'processed' ? navigate('/tutor', { state: { documentId: doc.document_id } }) : null}
                className={`group flex flex-col md:flex-row md:items-center justify-between py-6 border-b border-[var(--color-border)] cursor-pointer transition-colors hover:bg-[var(--color-lavender)]/20 px-4 -mx-4 rounded-xl ${doc.processing_status !== 'processed' ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex-1 mb-4 md:mb-0 pr-8">
                  <p className="text-[10px] font-bold tracking-[0.15em] text-[var(--color-accent)] uppercase mb-2">
                    Class {doc.class_name} · {doc.subject}
                  </p>
                  <h3 className="font-editorial text-[22px] text-[var(--color-ink)] group-hover:text-[var(--color-accent)] transition-colors mb-2 leading-tight">
                    {formatDocName(doc.document_name)}
                  </h3>
                  <div className="flex items-center gap-4 text-[10px] font-bold tracking-widest text-[var(--color-muted)] uppercase">
                    <span>{doc.chapter_count || 0} UNITS</span>
                    <span className="w-1 h-1 rounded-full bg-[var(--color-border)]"></span>
                    <span>{doc.page_count || 0} PAGES</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-6">
                  {doc.processing_status !== 'processed' ? (
                    <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider bg-amber-100 px-3 py-1.5 rounded-full">
                      {doc.processing_status}
                    </span>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-[var(--color-ink)] font-medium group-hover:text-[var(--color-accent)] transition-colors">
                      Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
