import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';

export default function QuizRunner() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm font-medium text-[#73736D]">Question 1 of 10</p>
        <p className="text-sm text-[#73736D]">Chapter 3: Ethics in AI</p>
      </div>

      <Card>
        <CardContent className="p-8 space-y-8">
          <h2 className="font-editorial text-2xl text-[#20201E] font-medium">
            Which of the following best describes the primary concern regarding bias in training data?
          </h2>

          <div className="space-y-3">
            {[1, 2, 3, 4].map((opt) => (
              <label 
                key={opt}
                className="flex items-start gap-3 p-4 border border-[#E5E3DC] rounded-lg hover:bg-[#F7F6F2] cursor-pointer transition-colors"
              >
                <input type="radio" name="quiz_q1" className="mt-1 text-[#3157D5] focus:ring-[#3157D5] border-[#E5E3DC]" />
                <span className="text-[#20201E]">This is placeholder option {opt} for the quiz question.</span>
              </label>
            ))}
          </div>

          <div className="pt-6 border-t border-[#E5E3DC] flex justify-between items-center">
            <Button variant="ghost">Save & Exit</Button>
            <Button>Next Question</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
