import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { BookOpen, Award } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Overview"
        title="Welcome back"
        description="Pick up where you left off or start a new study session."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        {/* Continue Studying */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-editorial text-xl font-medium text-[#20201E]">Continue studying</h2>
          </div>
          
          <div className="space-y-4">
            {/* Placeholder Empty State */}
            <Card className="bg-transparent border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center border border-[#E5E3DC] mb-4 shadow-sm">
                  <BookOpen className="w-5 h-5 text-[#3157D5]" />
                </div>
                <h3 className="text-[#20201E] font-medium mb-1">No materials yet</h3>
                <p className="text-sm text-[#73736D] max-w-xs mb-4">
                  Upload your textbook PDF to generate a personalized study plan.
                </p>
                <Button>Upload Material</Button>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Recent Quizzes */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-editorial text-xl font-medium text-[#20201E]">Recent quizzes</h2>
          </div>

          <div className="space-y-4">
            <Card className="bg-transparent border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center border border-[#E5E3DC] mb-4 shadow-sm">
                  <Award className="w-5 h-5 text-[#3157D5]" />
                </div>
                <h3 className="text-[#20201E] font-medium mb-1">No quizzes taken</h3>
                <p className="text-sm text-[#73736D] max-w-xs mb-4">
                  Generate a quiz from your materials to test your knowledge.
                </p>
                <Button variant="secondary">Generate Quiz</Button>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
