import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Button from '../components/ui/Button';

export default function Quizzes() {
  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Study"
        title="Quizzes"
        description="Test your knowledge on specific chapters."
        action={
          <Button>Generate New Quiz</Button>
        }
      />

      <div className="mt-8 flex flex-col items-center justify-center py-20 text-center border border-dashed border-[#E5E3DC] rounded-lg">
        <h3 className="text-[#20201E] font-medium mb-1">No quizzes yet</h3>
        <p className="text-sm text-[#73736D] max-w-sm mb-6">
          Generate your first quiz from your uploaded materials to start testing your knowledge.
        </p>
        <Button>Generate your first quiz</Button>
      </div>
    </div>
  );
}
