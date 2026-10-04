import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Badge from '../components/ui/Badge';
import { uploadDocument, getDocument } from '../services/api';
import { FileText, Loader2, AlertCircle, ArrowRight, UploadCloud } from 'lucide-react';

export default function MaterialUpload() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  // Form state
  const [file, setFile] = useState(null);
  const [className, setClassName] = useState('');
  const [subject, setSubject] = useState('');
  
  // UI state
  const [error, setError] = useState('');
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, processed, failed
  const [documentId, setDocumentId] = useState(null);
  const [processedDoc, setProcessedDoc] = useState(null);

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) validateAndSetFile(selected);
  };

  const validateAndSetFile = (selected) => {
    setError('');
    if (selected.type !== 'application/pdf') {
      setError('Only PDF files are supported.');
      return;
    }
    if (selected.size > 25 * 1024 * 1024) {
      setError('File size exceeds the 25MB limit.');
      return;
    }
    setFile(selected);
  };

  const handleUpload = async () => {
    setError('');
    if (!file) return setError('Please select a PDF file.');
    if (!className) return setError('Please select a class.');
    if (!subject.trim()) return setError('Please enter a subject.');

    try {
      setStatus('uploading');
      const data = await uploadDocument(file, className, subject);
      setDocumentId(data.document_id);
      setStatus('processing');
    } catch (err) {
      console.error(err);
      setStatus('idle');
      setError(err.response?.data?.detail || 'Failed to upload document. Please try again.');
    }
  };

  // Polling effect
  useEffect(() => {
    let timeoutId;
    let attempts = 0;
    const maxAttempts = 150; // Roughly 5 minutes at 2s intervals

    const pollStatus = async () => {
      if (status !== 'processing' || !documentId) return;

      try {
        const doc = await getDocument(documentId);
        if (doc.processing_status === 'processed') {
          setProcessedDoc(doc);
          setStatus('processed');
          return;
        } else if (doc.processing_status === 'failed') {
          setError(doc.error_message || 'Processing failed.');
          setStatus('failed');
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          setError('Your material is taking longer than expected. You can return to Materials and check its status later.');
          setStatus('failed'); // Treated as failed from this view's perspective
          return;
        }

        timeoutId = setTimeout(pollStatus, 2000);
      } catch (err) {
        console.error("Polling error:", err);
        timeoutId = setTimeout(pollStatus, 3000);
      }
    };

    if (status === 'processing') {
      pollStatus();
    }

    return () => clearTimeout(timeoutId);
  }, [status, documentId]);

  if (status === 'processed' && processedDoc) {
    return (
      <div className="max-w-3xl mx-auto py-12 flex flex-col items-center">
        <div className="text-center mb-12">
          <p className="text-[11px] font-bold tracking-[0.2em] text-emerald-600 uppercase mb-4">
            Success
          </p>
          <h1 className="font-editorial text-5xl text-[var(--color-ink)] mb-4">
            Material ready
          </h1>
          <p className="text-[var(--color-muted)] text-lg">
            Your document has been processed and is ready for study.
          </p>
        </div>

        <div className="w-full bg-white border border-[var(--color-border)] rounded-[40px] p-10 md:p-14 shadow-lg flex flex-col items-center text-center">
          <div className="w-24 h-24 bg-emerald-50 rounded-full flex items-center justify-center mb-8">
            <FileText className="w-12 h-12 text-emerald-600" />
          </div>
          
          <h2 className="font-editorial text-3xl text-[var(--color-ink)] mb-2">{processedDoc.document_name}</h2>
          <p className="text-sm font-bold tracking-wider uppercase text-[var(--color-muted)] mb-6">
            Class {processedDoc.class_name} · {processedDoc.subject}
          </p>
          
          <div className="flex gap-4 mb-10">
            <div className="px-6 py-2 rounded-full bg-[var(--color-warm-bg)] text-sm font-medium text-[var(--color-ink)]">
              {processedDoc.chapters.length} Units
            </div>
            <div className="px-6 py-2 rounded-full bg-[var(--color-warm-bg)] text-sm font-medium text-[var(--color-ink)]">
              {processedDoc.page_count} Pages
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
            <Button variant="secondary" onClick={() => navigate('/materials')} className="rounded-full px-8 py-6">
              Back to Library
            </Button>
            <Button onClick={() => navigate('/tutor', { state: { documentId: processedDoc.document_id } })} className="rounded-full px-8 py-6 bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white">
              Open AI Tutor <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-12">
      <div className="text-center mb-12">
        <h1 className="font-editorial text-5xl md:text-6xl text-[var(--color-ink)] mb-6">
          Add a new book
        </h1>
        <p className="text-lg text-[var(--color-muted)]">
          Upload your study material and turn it into an<br/>interactive learning space.
        </p>
      </div>

      <div className="w-full bg-white border border-[var(--color-border)] rounded-[40px] p-8 md:p-12 shadow-xl relative overflow-hidden">
        {/* Subtle decorative shapes */}
        <div className="absolute -top-24 -right-24 w-64 h-64 bg-[var(--color-accent)]/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 space-y-8">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-red-700">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="w-full">
              <label className="block text-[11px] font-bold tracking-[0.1em] uppercase text-[var(--color-muted)] mb-3">Class</label>
              <select 
                value={className} 
                onChange={(e) => setClassName(e.target.value)}
                disabled={status !== 'idle' && status !== 'failed'}
                className="w-full px-5 py-4 bg-[var(--color-warm-bg)] border border-transparent rounded-2xl text-[var(--color-ink)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50 focus:border-[var(--color-accent)] focus:bg-white transition-all cursor-pointer font-medium"
              >
                <option value="" disabled>Select Class</option>
                {['8', '9', '10', '11', '12'].map(cls => (
                  <option key={cls} value={cls}>Class {cls}</option>
                ))}
              </select>
            </div>
            
            <div className="w-full">
              <label className="block text-[11px] font-bold tracking-[0.1em] uppercase text-[var(--color-muted)] mb-3">Subject</label>
              <input 
                type="text"
                placeholder="e.g. Science, Mathematics" 
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                disabled={status !== 'idle' && status !== 'failed'}
                className="w-full px-5 py-4 bg-[var(--color-warm-bg)] border border-transparent rounded-2xl text-[var(--color-ink)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50 focus:border-[var(--color-accent)] focus:bg-white transition-all font-medium placeholder:text-[var(--color-muted)]/50"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold tracking-[0.1em] uppercase text-[var(--color-muted)] mb-3">Upload PDF Document</label>
            <input 
              type="file" 
              accept=".pdf,application/pdf" 
              ref={fileInputRef} 
              className="hidden" 
              onChange={handleFileSelect}
              disabled={status !== 'idle' && status !== 'failed'}
            />
            
            {!file ? (
              <div 
                onClick={() => status === 'idle' || status === 'failed' ? fileInputRef.current?.click() : null}
                className={`w-full bg-[var(--color-warm-bg)]/50 border-2 border-dashed border-[var(--color-border)] hover:border-[var(--color-accent)]/50 rounded-[32px] p-12 flex flex-col items-center justify-center text-center transition-all ${
                  status === 'idle' || status === 'failed' ? 'hover:bg-white cursor-pointer group' : 'opacity-50'
                }`}
              >
                <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mb-4 shadow-sm group-hover:scale-110 group-hover:text-[var(--color-accent)] transition-all">
                  <UploadCloud className="w-7 h-7 text-[var(--color-muted)] group-hover:text-[var(--color-accent)] transition-colors" />
                </div>
                <div className="text-lg font-medium text-[var(--color-ink)] mb-1">Drop your PDF here</div>
                <div className="text-sm font-medium text-[var(--color-muted)] uppercase tracking-wider">PDF · Max 25 MB</div>
              </div>
            ) : (
              <div className="border border-[var(--color-accent)]/30 rounded-[24px] p-6 flex flex-col md:flex-row items-center justify-between bg-[var(--color-accent)]/5">
                <div className="flex items-center gap-5 overflow-hidden w-full md:w-auto mb-4 md:mb-0">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shrink-0 shadow-sm">
                    <FileText className="w-6 h-6 text-[var(--color-accent)]" />
                  </div>
                  <div className="truncate">
                    <p className="text-base font-semibold text-[var(--color-ink)] truncate">{file.name}</p>
                    <p className="text-xs font-bold tracking-wider text-[var(--color-muted)] uppercase mt-1">{(file.size / (1024 * 1024)).toFixed(1)} MB</p>
                  </div>
                </div>
                {(status === 'idle' || status === 'failed') && (
                  <button 
                    onClick={() => setFile(null)} 
                    className="px-4 py-2 text-sm font-bold tracking-wider uppercase text-[var(--color-muted)] hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors"
                  >
                    Remove
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="pt-6 flex justify-end">
            {(status === 'idle' || status === 'failed') && (
              <Button onClick={handleUpload} className="w-full md:w-auto px-10 py-6 rounded-full text-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] text-white shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5">
                Process material <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            )}
            
            {(status === 'uploading' || status === 'processing') && (
              <Button disabled className="w-full md:w-auto px-10 py-6 rounded-full text-lg bg-[var(--color-accent)]/80 text-white cursor-not-allowed">
                <Loader2 className="w-5 h-5 animate-spin mr-3" /> 
                {status === 'uploading' ? 'Uploading...' : 'Processing material...'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
