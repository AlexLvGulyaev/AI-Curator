const LEVELS = [
  { id: 'beginner', label: 'Базовый' },
  { id: 'intermediate', label: 'Средний' },
  { id: 'advanced', label: 'Углублённый' },
];

function DifficultyToggle({ value, onChange }) {
  return (
    <div className="flex items-center gap-1 rounded-ai border border-ai-border bg-ai-surface p-1">
      {LEVELS.map((level) => (
        <button
          key={level.id}
          onClick={() => onChange(level.id)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            value === level.id
              ? 'bg-ai-primary text-white shadow-sm'
              : 'text-ai-text-secondary hover:bg-ai-surface-hover hover:text-ai-text'
          }`}
        >
          {level.label}
        </button>
      ))}
    </div>
  );
}

export default DifficultyToggle;
