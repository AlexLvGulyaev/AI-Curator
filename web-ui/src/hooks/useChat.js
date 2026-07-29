import { useCallback, useState } from 'react';
import { getDeadlines, getProgress, searchRag } from '../api/backend';

const ORG_KEYWORDS = [
  'дедлайн',
  'дедлайны',
  'срок',
  'сдача',
  'задание',
  'задания',
  'когда',
  'до когда',
  'прогресс',
  'оценка',
  'оценки',
  'сколько осталось',
];

const STUDY_KEYWORDS = [
  'лекция',
  'лекции',
  'методичка',
  'инструкция',
  'объясни',
  'расскажи',
  'как работает',
  'что такое',
  'help',
  'помоги',
];

function detectIntent(text) {
  const lower = text.toLowerCase();
  const isOrg = ORG_KEYWORDS.some((kw) => lower.includes(kw));
  const isStudy = STUDY_KEYWORDS.some((kw) => lower.includes(kw));

  if (isOrg && isStudy) return 'mixed';
  if (isOrg) return 'organizational';
  if (isStudy) return 'study';
  return 'study';
}

function formatDate(dateString) {
  if (!dateString) return 'нет даты';
  const date = new Date(dateString);
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getDaysLeft(dateString) {
  if (!dateString) return null;
  const now = new Date();
  const due = new Date(dateString);
  const diffMs = due - now;
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  return diffDays;
}

function buildDeadlineResponse(deadlines, progress) {
  if (!deadlines || deadlines.length === 0) {
    return {
      content:
        'У меня нет данных о дедлайнах для этого курса. Возможно, задания ещё не опубликованы в LMS.',
      sources: [],
    };
  }

  const upcoming = deadlines
    .filter((d) => d.due_date && getDaysLeft(d.due_date) >= -7)
    .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    .slice(0, 5);

  if (upcoming.length === 0) {
    return {
      content: 'Ближайших дедлайнов не найдено.',
      sources: [],
    };
  }

  const lines = upcoming.map((d) => {
    const days = getDaysLeft(d.due_date);
    const daysText =
      days < 0
        ? `просрочено на ${Math.abs(days)} ${dayWord(Math.abs(days))}`
        : `осталось ${days} ${dayWord(days)}`;
    return `• **${d.name}** — ${formatDate(d.due_date)} (${daysText})`;
  });

  const overall = progress?.completion_status
    ? `\n\nТекущий статус прохождения курса: **${progress.completion_status}**.`
    : '';

  return {
    content: `Вот ближайшие дедлайны по курсу:${overall}\n\n${lines.join('\n')}`,
    sources: upcoming.map((d) => ({
      type: 'lms',
      title: d.name,
      url: d.url,
    })),
  };
}

function dayWord(n) {
  const last = n % 10;
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return 'дней';
  if (last === 1) return 'день';
  if (last >= 2 && last <= 4) return 'дня';
  return 'дней';
}

function buildRagResponse(searchResults) {
  if (!searchResults || searchResults.results.length === 0) {
    return {
      content:
        'Я не нашёл подходящих материалов в Knowledge Base по этому вопросу. Попробуйте переформулировать запрос или уточнить тему.',
      sources: [],
    };
  }

  const top = searchResults.results[0];
  const other = searchResults.results.slice(1, 3);

  let content = `Вот что я нашёл по вашему вопросу:\n\n${top.content}`;

  if (other.length > 0) {
    content += '\n\nДополнительные материалы:\n';
    other.forEach((result, index) => {
      content += `\n${index + 1}. ${result.content.substring(0, 160)}...`;
    });
  }

  return {
    content,
    sources: searchResults.results.map((r) => {
      const meta = r.metadata || {};
      return {
        type: 'kb',
        title: meta.document_id
          ? `Материал курса (chunk ${meta.chunk_index ?? 0})`
          : 'Материал Knowledge Base',
        url: `https://lms.alex-n8n.site/course/view.php?id=${meta.course_id || 3}`,
      };
    }),
    meta: `Найдено фрагментов: ${searchResults.total}`,
  };
}

function useChat({ role, courseId, difficulty }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Привет! Я AI Curator. Задайте вопрос по курсу — я найду ответ в учебных материалах или проверю дедлайны и прогресс.',
      sources: [],
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(
    async (text) => {
      setError(null);
      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      setIsLoading(true);

      try {
        const intent = detectIntent(text);
        let response;

        if (intent === 'organizational' || intent === 'mixed') {
          const [deadlines, progress] = await Promise.all([
            getDeadlines(courseId),
            getProgress(),
          ]);
          response = buildDeadlineResponse(deadlines, progress);
        } else {
          const searchResults = await searchRag(text, {
            course_id: courseId,
            difficulty,
            k: 3,
          });
          response = buildRagResponse(searchResults);
        }

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.content,
            sources: response.sources,
            meta: response.meta,
          },
        ]);
      } catch (err) {
        setError(err.message || 'Не удалось получить ответ от AI Curator.');
      } finally {
        setIsLoading(false);
      }
    },
    [courseId, difficulty]
  );

  return { messages, isLoading, error, sendMessage };
}

export default useChat;
