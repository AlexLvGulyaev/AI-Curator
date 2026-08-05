import { useDemo } from '../contexts/DemoContext';

const MENU_GROUPS = [
  {
    id: 'system',
    label: 'Системные настройки',
    items: [
      { id: 'dashboard', label: 'Панель состояния', icon: '📊' },
      { id: 'ai-config', label: 'AI и Retrieval', icon: '⚙️' },
      { id: 'orchestrator', label: 'Оркестратор', icon: '🧭' },
    ],
  },
  {
    id: 'content',
    label: 'Контент / База знаний',
    items: [
      { id: 'kb', label: 'База знаний', icon: '📚' },
    ],
  },
  {
    id: 'operations',
    label: 'Операционная консоль',
    items: [
      { id: 'logs', label: 'Логи', icon: '📜' },
      { id: 'dialogs', label: 'Диалоги', icon: '💬' },
      { id: 'audit', label: 'Журнал аудита', icon: '📋' },
    ],
  },
  {
    id: 'reports',
    label: 'Отчёты',
    items: [
      { id: 'analytics', label: 'Аналитика', icon: '📈' },
      { id: 'reports', label: 'Бизнес-отчёты', icon: '📉' },
    ],
  },
];

function Sidebar({ active, onChange, onLogout }) {
  const { isDemo } = useDemo();

  return (
    <aside className="ai-sidebar">
      <div className="ai-sidebar__brand">
        <span className="ai-sidebar__brand-icon">🤖</span>
        <span>AI Curator</span>
      </div>

      {isDemo && (
        <div className="mx-3 mb-3 rounded-ai border border-ai-warning/30 bg-ai-warning/10 px-3 py-2 text-xs text-ai-warning">
          🔒 Демо-режим: только просмотр
        </div>
      )}

      <nav className="ai-nav">
        {MENU_GROUPS.map((group) => (
          <div key={group.id} className="ai-nav__group">
            <p className="ai-nav__group-label">{group.label}</p>
            <div className="ai-nav__items">
              {group.items.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onChange(item.id)}
                  className={`ai-nav__link ${active === item.id ? 'ai-nav__link--active' : ''}`}
                  type="button"
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="ai-sidebar__footer">
        <button onClick={onLogout} className="ai-sidebar__logout" type="button">
          <span>🚪</span>
          <span>Выйти</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
