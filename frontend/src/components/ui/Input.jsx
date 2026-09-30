import React, { forwardRef } from 'react';

const Input = forwardRef(({ className = '', label, error, ...props }, ref) => {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-[#20201E] mb-1.5">
          {label}
        </label>
      )}
      <input
        ref={ref}
        className={`w-full px-3 py-2 bg-white border rounded-md text-sm text-[#20201E] placeholder:text-[#73736D]/60 focus:outline-none focus:ring-2 focus:ring-[#3157D5]/20 focus:border-[#3157D5] transition-colors ${
          error ? 'border-red-300' : 'border-[#E5E3DC]'
        } ${className}`}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-xs text-red-500">{error}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
