import { pipelineStageVariant } from '../utils/operationalConsoleUi';

export default function OperationalPipelineStageIcon({ stage, status, className = '' }) {
  const variant = pipelineStageVariant(stage, status);
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ai-pipeline-stage-icon ai-pipeline-stage-icon--${variant}${
        className ? ` ${className}` : ''
      }`}
      aria-hidden
    />
  );
}
