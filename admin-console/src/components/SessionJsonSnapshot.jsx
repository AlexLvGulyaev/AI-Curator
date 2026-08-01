import { formatDetailsJson } from '../utils/operationalConsoleUi';

export default function SessionJsonSnapshot({
  body,
  className = '',
  summaryLabel = 'Технический снимок сессии (JSON)',
}) {
  const text = typeof body === 'string' ? body : formatDetailsJson(body);
  return (
    <details className={`session-json-snapshot ${className}`.trim()}>
      <summary className="session-json-snapshot__summary">{summaryLabel}</summary>
      <pre className="session-json-snapshot__pre mono">{text}</pre>
    </details>
  );
}
