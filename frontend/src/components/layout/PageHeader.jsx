import React from 'react';

export default function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="text-[11px] font-semibold text-[#73736D] uppercase tracking-wider mb-2">
            {eyebrow}
          </p>
        )}
        <h1 className="font-editorial text-3xl font-medium text-[#20201E] tracking-tight mb-2">
          {title}
        </h1>
        {description && (
          <p className="text-sm text-[#73736D] leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {action && (
        <div className="shrink-0">
          {action}
        </div>
      )}
    </div>
  );
}
