import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

export default function QuizResults() {
  const navigate = useNavigate();

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10">
        <h1 className="font-editorial text-4xl font-medium text-[#20201E] mb-2">Quiz Complete</h1>
        <p className="text-[#73736D]">You scored 8 out of 10</p>
      </div>

      <Card className="mb-6">
        <CardContent className="p-8">
          <h2 className="font-editorial text-xl font-medium text-[#20201E] mb-6">Review your answers</h2>
          
          <div className="space-y-6">
            {/* Fake Question Review */}
            <div className="pb-6 border-b border-[#E5E3DC] last:border-0 last:pb-0">
              <div className="flex gap-2 mb-2">
                <span className="text-emerald-600 font-medium text-sm">Correct</span>
                <span className="text-[#73736D] text-sm">• Question 1</span>
              </div>
              <p className="text-[#20201E] font-medium mb-3">Which of the following best describes the primary concern regarding bias in training data?</p>
              <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-md text-emerald-800 text-sm">
                Your answer: It can lead to unfair predictions.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-center gap-4">
        <Button variant="secondary" onClick={() => navigate('/quizzes')}>Back to Quizzes</Button>
        <Button onClick={() => navigate('/tutor')}>Review Weak Areas in Tutor</Button>
      </div>
    </div>
  );
}
