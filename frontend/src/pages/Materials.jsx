import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Button from '../components/ui/Button';
import { useNavigate } from 'react-router-dom';

export default function Materials() {
  const navigate = useNavigate();

  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader
        eyebrow="Library"
        title="Your study materials"
        description="Upload and organize the material you are studying."
        action={
          <Button onClick={() => navigate('/materials/upload')}>
            Add material
          </Button>
        }
      />

      <div className="mt-8 flex flex-col items-center justify-center py-20 text-center border border-dashed border-[#E5E3DC] rounded-lg">
        <h3 className="text-[#20201E] font-medium mb-1">Your library is empty</h3>
        <p className="text-sm text-[#73736D] max-w-sm mb-6">
          Get started by uploading your first textbook or study material. We support PDF files up to 25MB.
        </p>
        <Button onClick={() => navigate('/materials/upload')}>
          Upload your first PDF
        </Button>
      </div>
    </div>
  );
}
