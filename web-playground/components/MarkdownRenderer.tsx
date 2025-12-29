import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  // Enhanced markdown rendering
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const result: string[] = [];
    let inTable = false;
    let tableRows: string[] = [];
    let inList = false;
    let listItems: string[] = [];

    const processInlineFormatting = (line: string) => {
      // Bold
      line = line.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
      // Italic
      line = line.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
      // Code inline
      line = line.replace(/`([^`]+)`/g, '<code class="bg-slate-800 px-2 py-1 rounded text-purple-400 font-mono text-sm">$1</code>');
      // Links
      line = line.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">$1</a>');
      // Line breaks (HTML <br>)
      line = line.replace(/<br>/g, '<br />');
      return line;
    };

    const flushTable = () => {
      if (tableRows.length > 0) {
        result.push('<div class="overflow-x-auto my-4">');
        result.push('<table class="min-w-full border border-slate-600 rounded-lg">');
        
        tableRows.forEach((row, idx) => {
          const cells = row.split('|').filter(cell => cell.trim());
          const isHeader = idx === 0;
          const isSeparator = idx === 1 && row.includes('---');
          
          if (!isSeparator) {
            result.push('<tr class="border-b border-slate-600">');
            cells.forEach(cell => {
              const processed = processInlineFormatting(cell.trim());
              if (isHeader) {
                result.push(`<th class="px-4 py-3 text-left bg-slate-700 text-white font-semibold">${processed}</th>`);
              } else {
                result.push(`<td class="px-4 py-3 text-gray-200">${processed}</td>`);
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
        result.push('<ul class="list-disc list-inside space-y-2 my-3 ml-4">');
        listItems.forEach(item => {
          const processed = processInlineFormatting(item);
          result.push(`<li class="text-gray-200">${processed}</li>`);
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
        result.push(`<h3 class="text-xl font-bold text-white mt-6 mb-3">${headerText}</h3>`);
      } else if (line.startsWith('##')) {
        if (inList) flushList();
        const headerText = processInlineFormatting(line.replace(/^##\s*/, ''));
        result.push(`<h2 class="text-2xl font-bold text-white mt-6 mb-4">${headerText}</h2>`);
      } else if (line.startsWith('#')) {
        if (inList) flushList();
        const headerText = processInlineFormatting(line.replace(/^#\s*/, ''));
        result.push(`<h1 class="text-3xl font-bold text-white mt-6 mb-4">${headerText}</h1>`);
      } else if (line.trim() === '') {
        result.push('<br />');
      } else {
        const processed = processInlineFormatting(line);
        result.push(`<p class="text-gray-200 my-2">${processed}</p>`);
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
    <div className="prose prose-invert max-w-none">
      {parts.map((part, idx) => {
        if (part.startsWith('```')) {
          // Code block
          const lines = part.split('\n');
          const language = lines[0].replace('```', '').trim();
          const code = lines.slice(1, -1).join('\n');
          
          return (
            <div key={idx} className="my-4">
              <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                <div className="text-xs text-gray-400 mb-2">{language || 'code'}</div>
                <pre className="text-sm text-gray-100 font-mono">
                  <code>{code}</code>
                </pre>
              </div>
            </div>
          );
        }
        
        // Regular text with inline formatting
        return (
          <div 
            key={idx}
            dangerouslySetInnerHTML={{ __html: renderContent(part) }}
          />
        );
      })}
    </div>
  );
}
