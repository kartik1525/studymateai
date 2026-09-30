import React from 'react';

const variants = {
  default: 'bg-[#F7F6F2] text-[#73736D] border-[#E5E3DC]',
  primary: 'bg-[#3157D5]/10 text-[#3157D5] border-[#3157D5]/20',
  success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border-amber-200',
  error: 'bg-red-50 text-red-700 border-red-200',
};

export default function Badge({ children, variant = 'default', className = '' }) {
  return (
    <span 
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${variants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
