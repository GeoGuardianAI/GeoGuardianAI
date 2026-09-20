import React, { useState } from 'react';

export const BeforeAfterSlider: React.FC = () => {
  const [sliderPosition, setSliderPosition] = useState<number>(50);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSliderPosition(Number(e.target.value));
  };

  return (
    <div className="relative w-full h-[180px] rounded-lg overflow-hidden border border-slate-700 bg-slate-950 select-none">
      {/* Before Image (underneath) */}
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: 'url("/before_disaster.jpg")' }}
      >
        <span className="absolute top-2 left-2 px-2 py-0.5 text-[10px] bg-teal-900/90 text-teal-300 font-bold rounded border border-teal-500/30">
          BEFORE (Intact Bridge)
        </span>
      </div>

      {/* After Image (clipped width based on slider) */}
      <div 
        className="absolute inset-0 bg-cover bg-center transition-all duration-75"
        style={{ 
          backgroundImage: 'url("/after_disaster.jpg")',
          clipPath: `polygon(0 0, ${sliderPosition}% 0, ${sliderPosition}% 100%, 0 100%)`
        }}
      >
        <span className="absolute top-2 right-2 px-2 py-0.5 text-[10px] bg-red-950/90 text-red-400 font-bold rounded border border-red-500/30">
          AFTER (Bridge Collapsed)
        </span>
      </div>

      {/* Vertical Slider divider bar */}
      <div 
        className="absolute top-0 bottom-0 w-[2px] bg-cyan-400 shadow-[0_0_8px_#00f0ff] cursor-ew-resize pointer-events-none"
        style={{ left: `${sliderPosition}%` }}
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-cyan-500 border-2 border-cyan-300 flex items-center justify-center text-[10px] text-black font-bold shadow-[0_0_10px_#00f0ff]">
          ↔
        </div>
      </div>

      {/* Interactive invisible slider input overlapping */}
      <input 
        type="range" 
        min="0" 
        max="100" 
        value={sliderPosition} 
        onChange={handleSliderChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
      />
    </div>
  );
};
