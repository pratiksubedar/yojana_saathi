import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:';
  } catch {
    return false;
  }
}

/**
 * Renders inline Markdown tokens (**bold**, *italic*, [label](url), and bare https:// URLs)
 * without using dangerouslySetInnerHTML.
 */
function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Match markdown links, bold, italic, or bare http(s) URLs
  const tokenRegex = /(\[[^\]]+\]\(https?:\/\/[^\s)]+\)|\*\*[^*]+\*\*|\*[^*]+\*|https?:\/\/[^\s<>()]+)/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyCounter = 0;

  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('[') && token.includes('](')) {
      const splitIdx = token.indexOf('](');
      const label = token.slice(1, splitIdx);
      const url = token.slice(splitIdx + 2, -1);
      if (isSafeUrl(url)) {
        nodes.push(
          <a
            key={`md-a-${keyCounter++}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-indigo underline font-medium hover:text-brand-indigo-hover break-all"
          >
            {label}
          </a>
        );
      } else {
        nodes.push(label);
      }
    } else if (token.startsWith('**') && token.endsWith('**')) {
      nodes.push(
        <strong key={`md-b-${keyCounter++}`} className="font-bold text-neutral-ink">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      nodes.push(
        <em key={`md-i-${keyCounter++}`} className="italic">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith('http://') || token.startsWith('https://')) {
      const cleanUrl = token.replace(/[.,;!?]+$/, '');
      const trailing = token.slice(cleanUrl.length);
      if (isSafeUrl(cleanUrl)) {
        nodes.push(
          <a
            key={`md-u-${keyCounter++}`}
            href={cleanUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-indigo underline font-medium hover:text-brand-indigo-hover break-all"
          >
            {cleanUrl}
          </a>
        );
        if (trailing) nodes.push(trailing);
      } else {
        nodes.push(token);
      }
    }

    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  const lines = (content || '').split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: { ordered: boolean; text: string }[] = [];
  let keyCounter = 0;

  const flushList = () => {
    if (listItems.length === 0) return;
    const isOrdered = listItems[0].ordered;
    const Tag = isOrdered ? 'ol' : 'ul';
    elements.push(
      <Tag
        key={`md-list-${keyCounter++}`}
        className={`my-1.5 pl-5 space-y-1 text-sm leading-relaxed ${
          isOrdered ? 'list-decimal' : 'list-disc'
        }`}
      >
        {listItems.map((item, idx) => (
          <li key={idx}>{renderInline(item.text)}</li>
        ))}
      </Tag>
    );
    listItems = [];
  };

  for (const rawLine of lines) {
    const trimmed = rawLine.trim();

    if (!trimmed) {
      flushList();
      continue;
    }

    // Headings: ###, ##, #
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`md-h3-${keyCounter++}`} className="font-heading font-bold text-sm text-brand-indigo mt-2.5 mb-1">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`md-h2-${keyCounter++}`} className="font-heading font-bold text-base text-neutral-ink mt-2.5 mb-1">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`md-h1-${keyCounter++}`} className="font-heading font-bold text-base text-neutral-ink mt-2.5 mb-1">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Unordered list: - item or * item
    const ulMatch = /^[-*]\s+(.+)$/.exec(trimmed);
    if (ulMatch) {
      if (listItems.length > 0 && listItems[0].ordered) {
        flushList();
      }
      listItems.push({ ordered: false, text: ulMatch[1] });
      continue;
    }

    // Ordered list: 1. item
    const olMatch = /^\d+\.\s+(.+)$/.exec(trimmed);
    if (olMatch) {
      if (listItems.length > 0 && !listItems[0].ordered) {
        flushList();
      }
      listItems.push({ ordered: true, text: olMatch[1] });
      continue;
    }

    // Standard paragraph
    flushList();
    elements.push(
      <p key={`md-p-${keyCounter++}`} className="text-sm leading-relaxed my-1">
        {renderInline(trimmed)}
      </p>
    );
  }

  flushList();

  return <div className={`space-y-0.5 ${className}`}>{elements}</div>;
};

