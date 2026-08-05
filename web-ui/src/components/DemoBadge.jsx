import { useEffect, useState } from 'react';
import useDemo from '../hooks/useDemo';

function formatRemaining(seconds) {
  if (seconds <= 0) return '00:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function DemoBadge() {
  const { status, error } = useDemo();
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (!status) {
    return (
      <span className="rounded-full bg-ai-error/10 px-3 py-1 text-xs font-medium text-ai-error">
        Демо-режим
      </span>
    );
  }

  const remaining = status.requests_remaining ?? 0;
  const expiresAt = status.expires_at ? new Date(status.expires_at).getTime() : null;
  const secondsLeft = expiresAt ? Math.max(0, Math.floor((expiresAt - now) / 1000)) : 0;
  const isExpired = secondsLeft === 0;
  const isExhausted = remaining === 0;

  let badgeClass = 'bg-ai-primary-light text-ai-primary';
  if (isExpired || isExhausted || error) {
    badgeClass = 'bg-ai-error/10 text-ai-error';
  } else if (remaining <= 5) {
    badgeClass = 'bg-orange-100 text-orange-600';
  }

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${badgeClass}`}>
      🔒 Демо · осталось {remaining} запросов · {formatRemaining(secondsLeft)}
      {error && ` · ${error}`}
    </span>
  );
}

export default DemoBadge;
