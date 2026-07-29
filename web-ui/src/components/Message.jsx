function SourceLink({ source }) {
  if (source.type === 'kb') {
    return (
      <a
        href={source.url}
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
        href={source.url}
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
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {message.sources.map((source, index) => (
              <SourceLink key={index} source={source} />
            ))}
          </div>
        )}

        {!isUser && message.meta && (
          <p className="mt-3 text-xs text-ai-text-muted">{message.meta}</p>
        )}
      </div>
    </div>
  );
}

export default Message;
