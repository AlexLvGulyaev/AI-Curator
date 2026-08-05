import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { useState } from 'react';
import { sendChatFeedback } from '../api/backend';

// Prevent markdown links inside the answer from duplicating the source list.
function PlainTextLink({ children }) {
  return <span>{children}</span>;
}

function SourceCard({ source }) {
  const isKb = source.type === 'kb';
  const details = source.document_type || source.module || source.section;

  if (isKb) {
    return (
      <div className="flex flex-col gap-1 rounded-ai border border-ai-primary-light bg-ai-primary-light/40 px-3 py-2 text-sm text-ai-primary">
        <div className="flex items-center gap-2">
          <span>📚</span>
          <span className="font-medium line-clamp-1">{source.title}</span>
        </div>
        {details && (
          <div className="flex flex-wrap gap-1 text-xs opacity-80">
            {source.document_type && (
              <span className="rounded-full bg-white/60 px-2 py-0.5 capitalize">
                {source.document_type}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <a
      href={source.url || '#'}
      target="_blank"
      rel="noreferrer"
      className="flex flex-col gap-1 rounded-ai border border-ai-teal-light bg-ai-teal-light/40 px-3 py-2 text-sm text-ai-teal transition hover:shadow-ai"
    >
      <div className="flex items-center gap-2">
        <span>🎓</span>
        <span className="font-medium line-clamp-1">{source.title}</span>
      </div>
      {details && (
        <div className="flex flex-wrap gap-1 text-xs opacity-80">
          {source.module && (
            <span className="rounded-full bg-white/60 px-2 py-0.5">
              {source.module}
            </span>
          )}
          {source.section && (
            <span className="rounded-full bg-white/60 px-2 py-0.5">
              {source.section}
            </span>
          )}
        </div>
      )}
    </a>
  );
}

function StarRating({ initialScore, logId }) {
  const [score, setScore] = useState(initialScore || 0);
  const [hover, setHover] = useState(0);
  const [submitted, setSubmitted] = useState(Boolean(initialScore));
  const [error, setError] = useState(null);

  const handleRate = async (value) => {
    if (!logId) return;
    setScore(value);
    setSubmitted(true);
    setError(null);
    try {
      await sendChatFeedback(logId, value);
    } catch (err) {
      setError('Не удалось сохранить оценку');
      setSubmitted(false);
    }
  };

  return (
    <div className="mt-3 flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs text-ai-text-muted">
          {submitted ? 'Спасибо за оценку!' : 'Оцените ответ:'}
        </span>
        <div className="flex">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => (
            <button
              key={value}
              type="button"
              aria-label={`Оценить ответ на ${value} из 10`}
              disabled={submitted}
              className={`px-0.5 py-0 text-lg leading-none transition ${
                submitted ? 'cursor-default' : 'cursor-pointer hover:scale-110'
              } ${
                value <= (hover || score)
                  ? 'text-ai-warning'
                  : 'text-ai-text-muted/40'
              }`}
              style={{ color: value <= (hover || score) ? 'var(--ai-warning)' : 'var(--ai-text-muted)' }}
              onMouseEnter={() => !submitted && setHover(value)}
              onMouseLeave={() => setHover(0)}
              onClick={() => handleRate(value)}
            >
              ★
            </button>
          ))}
        </div>
      </div>
      {error && <p className="text-xs text-ai-error">{error}</p>}
    </div>
  );
}

function Message({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded-ai px-5 py-4 sm:max-w-[80%] ${
          isUser
            ? 'bg-ai-primary text-white'
            : 'ai-card'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm leading-relaxed text-ai-text">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
              skipHtml
              components={{
                a: PlainTextLink,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.sources.map((source, index) => (
              <SourceCard key={index} source={source} />
            ))}
          </div>
        )}

        {!isUser && message.logId && (
          <StarRating initialScore={message.feedbackScore} logId={message.logId} />
        )}

        {!isUser && message.meta && (
          <p className="mt-3 text-xs text-ai-text-muted">{message.meta}</p>
        )}
      </div>
    </div>
  );
}

export default Message;
