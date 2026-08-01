import {
  normalizeOperationalModality,
  operationalModalityBadgeClassList,
} from '../utils/operationalConsoleUi';

const LABELS = {
  rag: 'RAG',
  text: 'TEXT',
  lms: 'LMS',
  mixed: 'MIXED',
  log: 'LOG',
};

export default function OperationalModalityBadge({ modality, title, className = '' }) {
  const safe = normalizeOperationalModality(modality);
  const label = LABELS[safe] || safe.toUpperCase();
  return (
    <span
      className={`${operationalModalityBadgeClassList(safe)}${className ? ` ${className}` : ''}`}
      title={title ?? label}
    >
      {label}
    </span>
  );
}
