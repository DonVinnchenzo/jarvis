import { convert } from 'telegram-markdown-v2';

// Telegram limits
const MAX_MESSAGE_LENGTH = 4096;

/**
 * Convert standard markdown to Telegram MarkdownV2 format
 */
export function convertToTelegramMarkdown(text: string): string {
  try {
    // Pre-process: convert thematic breaks (---, ***, ___) to a unicode separator,
    // but only outside fenced code blocks.
    const preprocessed = replaceThematicBreaksOutsideCode(text);
    return convert(preprocessed, 'escape');
  } catch (error) {
    console.error('Markdown conversion error:', error);
    return escapeMarkdownV2(text);
  }
}

/**
 * Replace thematic breaks (***, ---, ___) only outside fenced code blocks.
 */
function replaceThematicBreaksOutsideCode(text: string): string {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((segment, i) => {
    if (i % 2 === 1) return segment;
    return segment.replace(/^[ \t]*([\*\-_]){3,}[ \t]*$/gm, '———');
  }).join('');
}

/**
 * Escape special characters for MarkdownV2 (fallback)
 */
export function escapeMarkdownV2(text: string): string {
  // IMPORTANT: Backslash MUST be first to avoid double-escaping
  const specialChars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'];
  let result = text;
  for (const char of specialChars) {
    result = result.replace(new RegExp(`\\${char}`, 'g'), `\\${char}`);
  }
  return result;
}

/**
 * Smart message splitter that respects code blocks and markdown formatting
 */
export function splitMessage(text: string, maxLength: number = MAX_MESSAGE_LENGTH): string[] {
  if (text.length <= maxLength) {
    return [text];
  }

  const parts: string[] = [];
  let remaining = text;
  let inCodeBlock = false;
  let codeBlockLang = '';

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      if (inCodeBlock) {
        remaining = remaining + '\n```';
      }
      parts.push(remaining);
      break;
    }

    let chunk = remaining.substring(0, maxLength);
    let splitIndex = maxLength;

    // Track code block state in this chunk
    const codeBlockMatches = chunk.matchAll(/```(\w*)?/g);
    let tempInCodeBlock: boolean = inCodeBlock;
    let tempLang: string = codeBlockLang;

    for (const match of codeBlockMatches) {
      if (tempInCodeBlock) {
        tempInCodeBlock = false;
        tempLang = '';
      } else {
        tempInCodeBlock = true;
        tempLang = match[1] || '';
      }
    }

    if (tempInCodeBlock) {
      const newlineSplit = chunk.lastIndexOf('\n');
      if (newlineSplit > maxLength / 2) {
        splitIndex = newlineSplit + 1;
        chunk = remaining.substring(0, splitIndex);

        const adjustedMatches = chunk.matchAll(/```(\w*)?/g);
        tempInCodeBlock = inCodeBlock;
        tempLang = codeBlockLang;

        for (const match of adjustedMatches) {
          if (tempInCodeBlock) {
            tempInCodeBlock = false;
            tempLang = '';
          } else {
            tempInCodeBlock = true;
            tempLang = match[1] || '';
          }
        }
      }
    } else {
      const paragraphBreak = chunk.lastIndexOf('\n\n');
      if (paragraphBreak > maxLength / 2) {
        splitIndex = paragraphBreak + 2;
      } else {
        const newlineBreak = chunk.lastIndexOf('\n');
        if (newlineBreak > maxLength / 2) {
          splitIndex = newlineBreak + 1;
        } else {
          const spaceBreak = chunk.lastIndexOf(' ');
          if (spaceBreak > maxLength / 2) {
            splitIndex = spaceBreak + 1;
          }
        }
      }

      chunk = remaining.substring(0, splitIndex);

      const adjustedMatches = chunk.matchAll(/```(\w*)?/g);
      tempInCodeBlock = inCodeBlock;
      tempLang = codeBlockLang;

      for (const match of adjustedMatches) {
        if (tempInCodeBlock) {
          tempInCodeBlock = false;
          tempLang = '';
        } else {
          tempInCodeBlock = true;
          tempLang = match[1] || '';
        }
      }
    }

    if (tempInCodeBlock) {
      chunk = chunk.trimEnd() + '\n```';
      inCodeBlock = true;
      codeBlockLang = tempLang;
    } else {
      inCodeBlock = tempInCodeBlock;
      codeBlockLang = tempLang;
    }

    parts.push(chunk);
    remaining = remaining.substring(splitIndex).trimStart();

    if (inCodeBlock && remaining.length > 0) {
      remaining = '```' + codeBlockLang + '\n' + remaining;
    }
  }

  if (parts.length > 1) {
    return parts.map((part, index) => {
      const indicator = `\n\n_\\[${index + 1}/${parts.length}\\]_`;
      if (part.length + indicator.length <= maxLength) {
        return part + indicator;
      }
      return part;
    });
  }

  return parts;
}

/**
 * Process and split a message for Telegram.
 * Converts markdown and splits into chunks.
 */
export function processMessageForTelegram(text: string, maxLength: number = MAX_MESSAGE_LENGTH): string[] {
  const converted = convertToTelegramMarkdown(text);
  return splitMessage(converted, maxLength);
}
