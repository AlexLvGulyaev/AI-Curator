import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { useState } from 'react';
import { sendChatFeedback } from '../api/backend';

// Prevent markdown links inside the answer from duplicating the source list.
function PlainTextLink({ children }) {
  return <span>{children}</span>;
}

function SourceLink({ source }) {
  if (source.type === 'kb') {
    return (
      <a
        href={source.url || '#'}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1.5 rounded-md bg-ai-primary-light px-2.5 py-1 text-xs font-medium text-ai-primary hover:bg-ai-primary hover:text-white transition"
      >
        <span>📚</span>
        <span className="truncate max-w-[180px]">{source.title}</span>
      </a>
    );
  }

  if (source.type === 'lms') {
    return (
      <a
        href={source.url || '#'}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1.5 rounded-md bg-ai-teal-light px-2.5 py-1 text-xs font-medium text-ai-teal hover:bg-ai-teal hover:text-white transition"
      >
        <span>🎓</span>
        <span className="truncate max-w-[180px]">{source.title}</span>
      </a>
    );
  }

  return null;
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
              <SourceLink key={index} source={source} />
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
