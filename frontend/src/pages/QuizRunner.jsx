import React, { useState } from 'react';
import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check } from 'lucide-react';

export default function QuizRunner() {
  const location = useLocation();
  const navigate = useNavigate();
  
  const quizState = location.state;
  
  if (!quizState || !quizState.quiz || !quizState.quiz.questions) {
    return <Navigate to="/quizzes" replace />;
  }

  const { quiz, config } = quizState;
  const questions = quiz.questions;
  
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  
  const currentQuestion = questions[currentIndex];
  
  const handleSelectOption = (optionIndex) => {
    setAnswers(prev => ({
      ...prev,
      [currentIndex]: optionIndex
    }));
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(prev => prev - 1);
    }
  };

  const handleSubmit = () => {
    navigate(`${location.pathname}/results`, {
      state: {
        quiz,
        config,
        answers
      },
      replace: true
    });
  };

  const progressPercent = Math.round(((currentIndex) / questions.length) * 100);

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 flex flex-col min-h-[calc(100vh-8rem)]">
      
      {/* Examination Container */}
      <div className="flex-1 flex flex-col bg-white border border-[var(--color-border)] rounded-[24px] shadow-sm overflow-hidden relative w-full">
        
        {/* Progress Bar Top */}
        <div className="w-full h-1 bg-[var(--color-warm-bg)]">
          <div 
            className="h-full bg-[var(--color-accent)] transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Header */}
        <div className="px-8 md:px-12 py-6 border-b border-[var(--color-border)] flex justify-between items-center bg-white">
          <div>
            <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-muted)] uppercase mb-1">
              {config.subject}
            </p>
            <h1 className="font-editorial text-xl font-medium text-[var(--color-ink)] truncate max-w-[200px] md:max-w-[400px]">
              {quiz.title}
            </h1>
          </div>
          <div className="text-right">
            <div className="text-[11px] font-bold tracking-widest text-[var(--color-accent)] uppercase bg-[var(--color-accent)]/10 px-4 py-2 rounded-full">
              Question {currentIndex + 1} / {questions.length}
            </div>
          </div>
        </div>

        {/* Question Area */}
        <div className="flex-1 px-8 md:px-12 py-10 md:py-14 flex flex-col bg-white">
          <h2 className="font-editorial text-[24px] md:text-[28px] text-[var(--color-ink)] mb-10 leading-relaxed max-w-3xl">
            {currentQuestion.question}
          </h2>

          <div className="space-y-4 max-w-3xl">
            {currentQuestion.options.map((option, idx) => {
              const isSelected = answers[currentIndex] === idx;
              const letter = String.fromCharCode(65 + idx); // A, B, C, D
              return (
                <button
                  key={idx}
                  onClick={() => handleSelectOption(idx)}
                  className={`w-full text-left px-5 py-4 rounded-[16px] border transition-all group flex items-start gap-4 ${
                    isSelected 
                      ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/5 shadow-sm' 
                      : 'border-[var(--color-border)] bg-white hover:bg-[var(--color-warm-bg)] hover:border-[var(--color-accent)]/30'
                  }`}
                >
                  <div className={`mt-0.5 w-6 h-6 shrink-0 rounded-[6px] border flex items-center justify-center transition-colors font-mono text-[11px] font-bold ${
                    isSelected 
                      ? 'border-[var(--color-accent)] bg-[var(--color-accent)] text-white' 
                      : 'border-[var(--color-border)] bg-[var(--color-warm-bg)] text-[var(--color-muted)] group-hover:border-[var(--color-accent)]/50 group-hover:text-[var(--color-accent)]'
                  }`}>
                    {letter}
                  </div>
                  <span className={`leading-relaxed text-[15px] md:text-[16px] mt-0.5 ${isSelected ? 'text-[var(--color-ink)] font-medium' : 'text-[var(--color-muted)]'}`}>
                    {option}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Minimal Bottom Bar Navigation */}
        <div className="px-8 md:px-12 py-6 border-t border-[var(--color-border)] bg-[var(--color-warm-bg)]/30 flex items-center justify-between">
          <button 
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className={`flex items-center gap-2 text-[14px] font-medium tracking-wide transition-colors ${currentIndex === 0 ? 'text-[var(--color-muted)]/30 cursor-not-allowed' : 'text-[var(--color-muted)] hover:text-[var(--color-ink)]'}`}
          >
            <ArrowLeft className="w-4 h-4" /> Previous
          </button>

          {currentIndex === questions.length - 1 ? (
            <button 
              onClick={handleSubmit} 
              disabled={answers[currentIndex] === undefined}
              className={`flex items-center gap-2 px-6 py-3 rounded-full text-[14px] font-medium text-white transition-all shadow-sm ${
                answers[currentIndex] === undefined 
                  ? 'bg-[var(--color-muted)]/30 cursor-not-allowed text-white/50' 
                  : 'bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] hover:-translate-y-0.5 hover:shadow-md'
              }`}
            >
              Submit Quiz <Check className="w-4 h-4" />
            </button>
          ) : (
            <button 
              onClick={handleNext}
              className="flex items-center gap-2 text-[14px] font-medium tracking-wide text-[var(--color-ink)] hover:text-[var(--color-accent)] transition-colors"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
