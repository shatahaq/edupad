export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-extrabold tracking-tight ${className}`}>
      Edu<span className="text-emerald-700 dark:text-emerald-400">Pad</span>
    </span>
  );
}
