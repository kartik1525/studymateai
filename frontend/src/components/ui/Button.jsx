import React from 'react';

const variants = {
  primary: 'bg-[#3157D5] text-white hover:bg-[#2646b2] border border-transparent shadow-sm',
  secondary: 'bg-white text-[#20201E] hover:bg-[#F7F6F2] border border-[#E5E3DC] shadow-sm',
  ghost: 'bg-transparent text-[#73736D] hover:text-[#20201E] hover:bg-[#E5E3DC]/30 border border-transparent',
  danger: 'bg-white text-red-600 hover:bg-red-50 border border-red-200 shadow-sm',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  disabled = false,
  ...props
}) {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-[#3157D5] focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  
  return (
    <button
      type={type}
      disabled={disabled}
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
