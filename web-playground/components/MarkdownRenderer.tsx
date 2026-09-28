import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

/**
 * Escape a string so it is inert inside an HTML attribute or text node.
 *
 * This exists because the renderer below builds HTML as a string and hands it to
 * `dangerouslySetInnerHTML`. Model output is untrusted input: it can contain
 * literal markup, and it is produced by a system that reads untrusted input
 * (your messages, uploaded files, web pages it retrieves), so "the model would
 * not emit that" is not a control.
 *
 * Escaping happens *before* the markdown transformations, so the tags this
 * renderer deliberately produces are added afterwards and survive, while
 * anything the content brought with it is neutered.
 */
export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Accept a link only if its scheme is one that cannot execute script.
 *
 * Without this, `[click me](javascript:alert(1))` in a model reply produced a
 * real anchor with a real `javascript:` href, which runs on click in the
 * reader's session. Rejecting the href keeps the link text visible but inert,
 * which is the honest outcome: we do not silently rewrite it to something else.
 */
export function safeHref(rawUrl: string): string | null {
  const url = rawUrl.trim();
  if (!url) return null;

  // Protocol-relative and absolute-path links are same-install and harmless.
  if (url.startsWith('/') || url.startsWith('#')) return url;

  // Anything with an explicit scheme must be an allowlisted one.
  const match = /^([a-z][a-z0-9+.-]*):/i.exec(url);
  if (!match) {
    // No scheme: treat as relative.
    return url;
  }
  const scheme = match[1].toLowerCase();
  return scheme === 'http' || scheme === 'https' || scheme === 'mailto' ? url : null;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const result: string[] = [];
    let inTable = false;
    let tableRows: string[] = [];
    let inList = false;
    let listItems: string[] = [];

    /**
     * Apply inline markdown to already-escaped text.
     *
     * Order matters and is the whole point: `escapeHtml` runs first, so the only
     * tags present afterwards are the ones added here.
     */
    const processInlineFormatting = (rawLine: string) => {
      let line = escapeHtml(rawLine);

      // Bold
      line = line.replace(
        /\*\*(.*?)\*\*/g,
        '<strong class="font-semibold text-fg">$1</strong>'
      );
      // Italic
      line = line.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
      // Inline code
      line = line.replace(
        /`([^`]+)`/g,
        '<code class="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[0.85em] text-violet">$1</code>'
      );
      // Links. The href is validated; an unsafe one renders as plain text so the
      // reader can still see what was written without it being clickable.
      line = line.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_match, label: string, href: string) => {
        const safe = safeHref(href);
        if (!safe) {
          return `${label} <span class="text-fg-subtle">(link removed: unsafe address)</span>`;
        }
        return `<a href="${escapeHtml(safe)}" class="text-accent underline underline-offset-2 hover:opacity-80" target="_blank" rel="noopener noreferrer nofollow">${label}</a>`;
      });

      return line;
    };

    const flushTable = () => {
      if (tableRows.length > 0) {
        result.push('<div class="my-4 overflow-x-auto">');
        result.push('<table class="min-w-full border border-line">');

        tableRows.forEach((row, idx) => {
          const cells = row.split('|').filter((cell) => cell.trim());
          const isHeader = idx === 0;
          const isSeparator = idx === 1 && row.includes('---');

          if (!isSeparator) {
            result.push('<tr class="border-b border-line">');
            cells.forEach((cell) => {
              const processed = processInlineFormatting(cell.trim());
              if (isHeader) {
                result.push(
                  `<th class="bg-surface-3 px-4 py-2 text-left font-semibold text-fg">${processed}</th>`
                );
              } else {
                result.push(`<td class="px-4 py-2 text-fg-muted">${processed}</td>`);
              }
            });
            result.push('</tr>');
          }
        });

        result.push('</table>');
        result.push('</div>');
        tableRows = [];
        inTable = false;
      }
    };

    const flushList = () => {
      if (listItems.length > 0) {
        result.push('<ul class="my-3 ml-5 list-disc space-y-1.5">');
        listItems.forEach((item) => {
          const processed = processInlineFormatting(item);
          result.push(`<li class="text-fg-muted">${processed}</li>`);
        });
        result.push('</ul>');
        listItems = [];
        inList = false;
      }
    };


    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Check for table
      if (line.includes('|')) {
        if (inList) flushList();
        inTable = true;
        tableRows.push(line);
        continue;
      } else if (inTable) {
        flushTable();
      }

      // Check for list items
      if (line.match(/^[\s]*[•\-\*]\s/)) {
        if (!inList) inList = true;
        const itemText = line.replace(/^[\s]*[•\-\*]\s/, '');
        listItems.push(itemText);
        continue;
      } else if (inList && line.trim() === '') {
        continue; // Keep list going through empty lines
      } else if (inList && !line.match(/^[\s]*[•\-\*]\s/)) {
        flushList();
      }

      // Check for headers
      if (line.startsWith('###')) {
        if (inList) flushList();
        const headerText = processInlineFormatting(line.replace(/^###\s*/, ''));
        result.push(
          `<h3 class="mt-6 mb-2 text-base font-semibold text-fg">${headerText}</h3>`
        );
      } else if (line.startsWith('##')) {
        if (inList) flushList();
        const headerText = processInlineFormatting(line.replace(/^##\s*/, ''));
        result.push(
          `<h2 class="mt-6 mb-3 text-lg font-semibold text-fg">${headerText}</h2>`
        );
      } else if (line.startsWith('#')) {
        if (inList) flushList();
        const headerText = processInlineFormatting(line.replace(/^#\s*/, ''));
        result.push(
          `<h1 class="mt-6 mb-3 text-xl font-semibold text-fg">${headerText}</h1>`
        );
      } else if (line.trim() === '') {
        // A blank line separates blocks. The renderer used to emit `<br />` here,
        // which turned the paragraph structure of a long reply into a wall of
        // text broken by stray breaks.
        result.push('<div class="h-3"></div>');
      } else {
        const processed = processInlineFormatting(line);
        result.push(`<p class="my-1.5 leading-relaxed text-fg-muted">${processed}</p>`);
      }
    }

    // Flush any remaining table or list
    if (inTable) flushTable();
    if (inList) flushList();

    return result.join('\n');
  };

  // Split by code blocks
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="max-w-none text-sm">
      {parts.map((part, idx) => {
        if (part.startsWith('```')) {
          // Code block. Rendered as a JSX text child, so React escapes it — no
          // `dangerouslySetInnerHTML` on this path.
          const lines = part.split('\n');
          const language = lines[0].replace('```', '').trim();
          const code = lines.slice(1, -1).join('\n');

          return (
            <div key={idx} className="my-3">
              <div className="overflow-x-auto rounded-card border border-line bg-surface-2">
                <div className="border-b border-line px-3 py-1.5 font-mono text-xs text-fg-subtle">
                  {language || 'code'}
                </div>
                <pre className="p-3 font-mono text-xs text-fg">
                  <code>{code}</code>
                </pre>
              </div>
            </div>
          );
        }

        // Regular text with inline formatting. The string is HTML built from
        // escaped input above, which is what makes this call safe.
        return (
          <div key={idx} dangerouslySetInnerHTML={{ __html: renderContent(part) }} />
        );
      })}
    </div>
  );
}

