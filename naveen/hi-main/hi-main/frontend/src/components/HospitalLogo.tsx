type HospitalLogoProps = {
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
};

export default function HospitalLogo({
  size = 'md',
  showSubtitle = true,
  className = '',
}: HospitalLogoProps) {
  const iconSizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-14 h-14',
  };

  const titleSizes = {
    sm: 'text-sm font-extrabold',
    md: 'text-base font-extrabold tracking-tight',
    lg: 'text-xl font-black tracking-tight',
  };

  const subtitleSizes = {
    sm: 'text-[9px]',
    md: 'text-[11px]',
    lg: 'text-xs',
  };

  return (
    <div className={`flex items-center gap-3 select-none group cursor-pointer ${className}`}>
      <img
        src="/logo.svg"
        alt=""
        aria-hidden="true"
        className={`${iconSizes[size]} flex-shrink-0 rounded-2xl shadow-lg transition-transform duration-200 group-hover:scale-105`}
      />

      {/* Typography & Sub-branding */}
      <div className="pl-1.5">
        <div className="flex items-center gap-1.5">
          <span className={`bg-gradient-to-r from-teal-900 via-cyan-900 to-indigo-950 bg-clip-text text-transparent ${titleSizes[size]}`}>
            AI Health Copilot
          </span>
          <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-wider bg-teal-100 text-teal-800 border border-teal-300">
            PRO
          </span>
        </div>
        {showSubtitle && (
          <p className={`font-semibold text-teal-700 flex items-center gap-1.5 ${subtitleSizes[size]}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
            Hospital & Patient Portal
          </p>
        )}
      </div>
    </div>
  );
}
