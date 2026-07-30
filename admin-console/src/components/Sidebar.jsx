const NAV_ITEMS = [
  { id: 'dashboard', label: 'Панель состояния', icon: '📊' },
  { id: 'kb', label: 'Knowledge Base', icon: '📚' },
  { id: 'ai-config', label: 'AI Configuration', icon: '🤖' },
  { id: 'analytics', label: 'Аналитика', icon: '📈' },
  { id: 'audit', label: 'Журнал аудита', icon: '📋' },
];

function Sidebar({ active, onChange, onLogout }) {
  return (
    <aside className="flex w-64 flex-col border-r border-ai-border bg-ai-surface">
      <div className="flex items-center gap-3 border-b border-ai-border px-5 py-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-ai bg-ai-primary-light text-xl">
          ⚙️
        </div>
        <div>
          <h1 className="font-display text-base font-bold text-ai-text">AI Curator</h1>
          <p className="text-xs text-ai-text-muted">Admin Console</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => onChange(item.id)}
                className={`sidebar-link w-full text-left ${active === item.id ? 'active' : ''}`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-ai-border p-3">
        <button
          onClick={onLogout}
          className="sidebar-link w-full text-left text-ai-error hover:text-ai-error"
        >
          <span>🚪</span>
          <span>Выйти</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
