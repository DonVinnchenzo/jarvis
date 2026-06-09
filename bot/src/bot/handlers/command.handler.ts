import { Context } from 'grammy';
import { clearConversation } from '../../claude/agent.js';
import { cancelRequest, clearQueue } from '../../claude/request-queue.js';
import { sessionManager } from '../../claude/session-manager.js';
import { config } from '../../config.js';
import { escapeMarkdownV2 as esc } from '../../telegram/markdown.js';

export async function handleStart(ctx: Context): Promise<void> {
  const userId = ctx.from?.id;
  const userName = userId ? config.USER_NAMES.get(userId) || 'there' : 'there';

  const message = `Hi ${userName}! I'm Jarvis, your household assistant.

Here's what I can help with:

- Add and manage contacts (friends, family, colleagues)
- Track birthdays, anniversaries, and important dates
- Keep notes about people (gifts, preferences, life updates)
- Show upcoming events and reminders
- Search across all your contacts and notes

Just tell me what you need in plain language. For example:
"Add my friend Mark, birthday June 14, he just got promoted"
"What's coming up this month?"
"Find everything about Lisa"

Commands:
/upcoming - Show upcoming events
/contacts - List all contacts
/search <query> - Search contacts and notes
/clear - Start a fresh conversation
/cancel - Stop current request
/help - Show this message again`;

  await ctx.reply(message, { parse_mode: undefined });
}

export async function handleCancel(ctx: Context): Promise<void> {
  const chatId = ctx.chat?.id;
  if (!chatId) return;

  const cancelled = await cancelRequest(chatId);
  clearQueue(chatId);

  if (cancelled) {
    await ctx.reply('Cancelled.', { parse_mode: undefined });
  } else {
    await ctx.reply('Nothing running to cancel.', { parse_mode: undefined });
  }
}

export async function handleClear(ctx: Context): Promise<void> {
  const chatId = ctx.chat?.id;
  if (!chatId) return;

  // Cancel any running query first
  await cancelRequest(chatId);
  clearQueue(chatId);

  // Clear conversation history and Claude session
  clearConversation(chatId);
  sessionManager.clearSession(chatId);

  await ctx.reply('Conversation cleared. Fresh start!', { parse_mode: undefined });
}

export async function handleHelp(ctx: Context): Promise<void> {
  // Same as /start
  await handleStart(ctx);
}

/**
 * Shortcut commands that pass intent to Claude as natural language.
 * The Claude agent picks the right skill and calls the API.
 */

export async function handleUpcoming(ctx: Context): Promise<void> {
  // Rewrite as a message to Claude
  if (ctx.message) {
    (ctx.message as { text: string }).text = 'Show me upcoming events in the next 30 days';
  }
}

export async function handleContacts(ctx: Context): Promise<void> {
  if (ctx.message) {
    (ctx.message as { text: string }).text = 'List all contacts';
  }
}

export async function handleSearch(ctx: Context): Promise<void> {
  const text = ctx.message?.text || '';
  const searchQuery = text.replace(/^\/search\s*/i, '').trim();

  if (!searchQuery) {
    await ctx.reply('Usage: /search <query>\n\nExample: /search Mark', { parse_mode: undefined });
    return;
  }

  if (ctx.message) {
    (ctx.message as { text: string }).text = `Search for: ${searchQuery}`;
  }
}
