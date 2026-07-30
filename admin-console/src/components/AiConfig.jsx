import { useEffect, useState } from 'react';
import { getActiveAiConfig, getAiConfigHistory, createAiConfig, activateAiConfig } from '../api/backend';

function AiConfig() {
  const [active, setActive] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: '',
    system_prompt: '',
    model: 'gpt-4o-mini',
    temperature: 0.3,
    max_tokens: 1024,
    top_k_retrieval: 5,
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [activeConfig, historyConfigs] = await Promise.all([
        getActiveAiConfig(),
        getAiConfigHistory(),
      ]);
      setActive(activeConfig);
      setHistory(historyConfigs);
      setForm({
        name: '',
        system_prompt: activeConfig.system_prompt,
        model: activeConfig.model,
        temperature: activeConfig.temperature,
        max_tokens: activeConfig.max_tokens,
        top_k_retrieval: activeConfig.top_k_retrieval,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createAiConfig(form);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (id) => {
    setError(null);
    try {
      await activateAiConfig(id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-ai-text-muted">
        <span className="mr-2 inline-block animate-pulse">●</span>
        Загрузка конфигурации…
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h2 className="font-display text-xl font-bold text-ai-text">AI Configuration</h2>
        <p className="text-sm text-ai-text-muted">
          Активная конфигурация: {active ? `${active.name} (${active.model})` : '—'}
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-ai border border-ai-error/20 bg-red-500/10 p-4 text-sm text-ai-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSave} className="ai-card mb-6 space-y-4 p-5">
        <div>
          <label className="mb-1 block text-sm text-ai-text-secondary">Название версии</label>
          <input
            type="text"
            value={form.name}
            onChange={(event) => handleChange('name', event.target.value)}
            placeholder="Например: Повышенная краткость"
            required
            className="ai-input w-full px-4 py-2"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-ai-text-secondary">System Prompt</label>
          <textarea
            value={form.system_prompt}
            onChange={(event) => handleChange('system_prompt', event.target.value)}
            rows={10}
            required
            className="ai-textarea w-full px-4 py-2 font-mono text-sm"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="mb-1 block text-sm text-ai-text-secondary">Модель</label>
            <input
              type="text"
              value={form.model}
              onChange={(event) => handleChange('model', event.target.value)}
              required
              className="ai-input w-full px-4 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ai-text-secondary">Temperature</label>
            <input
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={form.temperature}
              onChange={(event) => handleChange('temperature', parseFloat(event.target.value))}
              required
              className="ai-input w-full px-4 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ai-text-secondary">Max Tokens</label>
            <input
              type="number"
              min="1"
              max="4096"
              value={form.max_tokens}
              onChange={(event) => handleChange('max_tokens', parseInt(event.target.value, 10))}
              required
              className="ai-input w-full px-4 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ai-text-secondary">Top-K Retrieval</label>
            <input
              type="number"
              min="1"
              max="20"
              value={form.top_k_retrieval}
              onChange={(event) => handleChange('top_k_retrieval', parseInt(event.target.value, 10))}
              required
              className="ai-input w-full px-4 py-2"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="ai-btn px-5 py-2"
          >
            {saving ? 'Сохранение…' : 'Создать новую версию'}
          </button>
        </div>
      </form>

      <div className="ai-card p-5">
        <h3 className="mb-4 font-display font-semibold text-ai-text">История версий</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ai-border text-ai-text-muted">
                <th className="pb-2 pr-4">ID</th>
                <th className="pb-2 pr-4">Название</th>
                <th className="pb-2 pr-4">Модель</th>
                <th className="pb-2 pr-4">Temperature</th>
                <th className="pb-2 pr-4">Top-K</th>
                <th className="pb-2 pr-4">Создана</th>
                <th className="pb-2">Действие</th>
              </tr>
            </thead>
            <tbody className="text-ai-text-secondary">
              {history.map((config) => (
                <tr key={config.id} className="border-b border-ai-border-subtle">
                  <td className="py-3 pr-4">{config.id}</td>
                  <td className="py-3 pr-4">{config.name}</td>
                  <td className="py-3 pr-4">{config.model}</td>
                  <td className="py-3 pr-4">{config.temperature}</td>
                  <td className="py-3 pr-4">{config.top_k_retrieval}</td>
                  <td className="py-3 pr-4">{new Date(config.created_at).toLocaleString('ru-RU')}</td>
                  <td className="py-3">
                    {config.is_active ? (
                      <span className="text-xs font-medium text-ai-success">Активна</span>
                    ) : (
                      <button
                        onClick={() => handleActivate(config.id)}
                        className="ai-btn-outline px-3 py-1 text-xs"
                      >
                        Активировать
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default AiConfig;
