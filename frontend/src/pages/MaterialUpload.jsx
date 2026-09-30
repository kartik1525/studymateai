import React from 'react';
import PageHeader from '../components/layout/PageHeader';
import Card, { CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

export default function MaterialUpload() {
  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader
        eyebrow="Upload"
        title="Add new material"
        description="Upload a PDF textbook to process and extract chapters."
      />

      <Card className="mt-8">
        <CardContent className="space-y-6 p-8">
          {/* File Dropzone Placeholder */}
          <div className="border-2 border-dashed border-[#E5E3DC] rounded-lg p-12 text-center hover:bg-[#F7F6F2] transition-colors cursor-pointer">
            <div className="text-sm font-medium text-[#20201E] mb-1">Click to upload or drag and drop</div>
            <div className="text-xs text-[#73736D]">PDF (Max 25MB)</div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input label="Class" placeholder="e.g. 10" />
            <Input label="Subject" placeholder="e.g. Artificial Intelligence" />
          </div>

          <div className="pt-4 border-t border-[#E5E3DC] flex justify-end gap-3">
            <Button variant="ghost">Cancel</Button>
            <Button>Upload and Process</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
