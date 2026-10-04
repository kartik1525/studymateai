import React, { useState } from 'react';
import { useLocation, useNavigate, Navigate } from 'react-router-dom';
import { CheckCircle2, XCircle, FileText, ArrowRight, RotateCcw, Home, ChevronDown, ChevronUp } from 'lucide-react';

export default function QuizResults() {
  const location = useLocation();
  const navigate = useNavigate();

  const resultsState = location.state;

  if (!resultsState || !resultsState.quiz || !resultsState.answers) {
    return <Navigate to="/quizzes" replace />;
  }

  const { quiz, config, answers } = resultsState;
  const questions = quiz.questions;

  // Calculate score
  let correctCount = 0;
  const incorrectQuestions = [];

  questions.forEach((q, idx) => {
    const userAnswer = answers[idx];
    if (userAnswer === q.correct_answer) {
      correctCount++;
    } else {
      incorrectQuestions.push({
        questionNumber: idx + 1,
        question: q,
        userAnswer,
        correctAnswer: q.correct_answer
      });
    }
  });

  const percentage = Math.round((correctCount / questions.length) * 100);
  const [expandedExplanations, setExpandedExplanations] = useState({});

  const toggleExplanation = (idx) => {
    setExpandedExplanations(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const handleRetry = () => {
    navigate('/quizzes', {
      state: { documentId: config.activeDocId }
    });
  };

  let summaryMessage = "Review the questions you missed.";
  if (percentage === 100) {
    summaryMessage = "Excellent work. You mastered this quiz.";
  } else if (percentage === 0) {
    summaryMessage = "Review the explanations below to improve your understanding.";
  }
  return (
    <div className="max-w-4xl mx-auto py-10 px-4 pb-24">
      {/* Header & Score */}
      <div className="text-center mb-12">
        <p className="text-[11px] font-bold tracking-[0.2em] text-[var(--color-accent)] uppercase mb-3">
          RESULTS
        </p>
        <h1 className="font-editorial text-4xl md:text-5xl font-medium text-[var(--color-ink)] mb-10">
          Quiz Completed
        </h1>
        
        <div className="inline-flex flex-col items-center justify-center p-8 bg-white border border-[var(--color-border)] rounded-[32px] shadow-sm min-w-[240px]">
          <div className={`text-6xl font-editorial mb-2 ${percentage >= 70 ? 'text-[var(--color-accent)]' : 'text-[var(--color-ink)]'}`}>
            {percentage}%
          </div>
          <div className="text-[11px] font-bold text-[var(--color-muted)] uppercase tracking-wider">
            {correctCount} / {questions.length} Correct
          </div>
        </div>
        
        <p className="text-[var(--color-ink)] mt-8 text-lg font-medium">
          {summaryMessage}
        </p>
      </div>

      {/* Review Section */}
      {incorrectQuestions.length > 0 && (
        <div className="mb-16">
          <h2 className="font-editorial text-2xl text-[var(--color-ink)] mb-6 border-b border-[var(--color-border)] pb-4">
            Areas for Review
          </h2>
          
          <div className="space-y-6">
            {incorrectQuestions.map(item => (
              <div key={item.questionNumber} className="bg-white border border-[var(--color-border)] rounded-[20px] overflow-hidden shadow-sm">
                <div className="p-4 bg-[var(--color-warm-bg)]/50 border-b border-[var(--color-border)] flex items-center justify-between">
                  <div className="font-bold tracking-wider uppercase text-[10px] text-[var(--color-muted)]">Question {item.questionNumber}</div>
                </div>
                <div className="p-6 md:p-8">
                  <p className="font-editorial text-xl md:text-2xl text-[var(--color-ink)] mb-6 leading-snug">
                    {item.question.question}
                  </p>

                  <div className="space-y-3 mb-6">
                    {/* User's Answer */}
                    <div className="flex items-start gap-3 p-4 bg-red-50 rounded-[12px] border border-red-100">
                      <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-[10px] font-bold text-red-600 uppercase tracking-wider mb-1">Your Answer</div>
                        <div className="text-[var(--color-ink)] text-[14px] md:text-[15px]">
                          {item.userAnswer !== undefined 
                            ? item.question.options[item.userAnswer] 
                            : <span className="text-[var(--color-muted)] italic">Skipped</span>}
                        </div>
                      </div>
                    </div>

                    {/* Correct Answer */}
                    <div className="flex items-start gap-3 p-4 bg-emerald-50 rounded-[12px] border border-emerald-100">
                      <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-1">Correct Answer</div>
                        <div className="text-[var(--color-ink)] font-medium text-[14px] md:text-[15px]">
                          {item.question.options[item.correctAnswer]}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Explanation Accordion */}
                  <div className="border border-[var(--color-border)] rounded-[12px] overflow-hidden bg-[var(--color-warm-bg)]/30">
                    <button 
                      onClick={() => toggleExplanation(item.questionNumber)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-[var(--color-warm-bg)] transition-colors"
                    >
                      <span className="text-[11px] font-bold text-[var(--color-muted)] uppercase tracking-wider">View Explanation</span>
                      {expandedExplanations[item.questionNumber] ? (
                        <ChevronUp className="w-4 h-4 text-[var(--color-muted)]" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-[var(--color-muted)]" />
                      )}
                    </button>
                    {expandedExplanations[item.questionNumber] && (
                      <div className="p-4 pt-0 text-[14px] text-[var(--color-ink)] leading-relaxed border-t border-[var(--color-border)]/50 mt-1">
                        {item.question.explanation}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action footer */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-5 pt-10 border-t border-[var(--color-border)]">
        <button 
          onClick={() => navigate('/dashboard')}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-full text-[14px] font-medium border border-[var(--color-border)] text-[var(--color-ink)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] transition-all bg-white shadow-sm"
        >
          <Home className="w-4 h-4" /> Dashboard
        </button>
        <button 
          onClick={handleRetry} 
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-full text-[14px] font-medium text-white bg-[var(--color-accent)] hover:bg-[var(--color-accent-hover)] transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5 border border-[var(--color-accent)]"
        >
          <RotateCcw className="w-4 h-4" /> New Quiz
        </button>
      </div>
    </div>
  );
}
