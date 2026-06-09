import { Bot, type Context } from 'grammy';
import { autoRetry } from '@grammyjs/auto-retry';
import { sequentialize } from '@grammyjs/runner';
import { config } from '../config.js';
import { authMiddleware } from './middleware/auth.middleware.js';
import {
  handleStart,
  handleCancel,
  handleClear,
  handleHelp,
  handleUpcoming,
  handleContacts,
  handleSearch,
} from './handlers/command.handler.js';
import { handleMessage } from './handlers/message.handler.js';

// Resolve sequentialize constraint: same-chat updates are ordered,
// but /cancel is registered BEFORE this middleware so it bypasses it.
function getSequentializeKey(ctx: Context): string | undefined {
  return ctx.chat?.id.toString();
}

export async function createBot(): Promise<Bot> {
  const bot = new Bot(config.TELEGRAM_BOT_TOKEN);

  // Auto-retry on transient network errors and 429 rate limits
  bot.api.config.use(autoRetry({
    maxRetryAttempts: 5,
    maxDelaySeconds: 60,
    rethrowInternalServerErrors: false,
  }));

  // Register command menu for autocomplete (non-blocking)
  const commandList = [
    { command: 'start', description: 'Welcome message and help' },
    { command: 'upcoming', description: 'Show upcoming events' },
    { command: 'contacts', description: 'List all contacts' },
    { command: 'search', description: 'Search contacts and notes' },
    { command: 'clear', description: 'Clear conversation history' },
    { command: 'cancel', description: 'Cancel current request' },
    { command: 'help', description: 'What Jarvis can do' },
  ];

  bot.api.setMyCommands(commandList).then(() => {
    console.log('Command menu registered');
  }).catch((err) => {
    console.warn('Failed to register commands:', err.message);
  });

  // Apply auth middleware to all updates
  bot.use(authMiddleware);

  // /cancel fires BEFORE sequentialize so it bypasses per-chat ordering.
  // This lets it interrupt a running query without waiting for it to finish.
  bot.command('cancel', handleCancel);

  // Sequentialize: same-chat updates are processed in order.
  // Runs AFTER /cancel so cancel bypasses it.
  bot.use(sequentialize(getSequentializeKey));

  // Command handlers (sequentialized per chat)
  bot.command('start', handleStart);
  bot.command('clear', handleClear);
  bot.command('help', handleHelp);

  // Shortcut commands: rewrite ctx.message.text and fall through to message handler
  bot.command('upcoming', async (ctx) => {
    await handleUpcoming(ctx);
    await handleMessage(ctx);
  });
  bot.command('contacts', async (ctx) => {
    await handleContacts(ctx);
    await handleMessage(ctx);
  });
  bot.command('search', async (ctx) => {
    // handleSearch may reply with usage if no query; otherwise rewrites text
    const text = ctx.message?.text || '';
    const searchQuery = text.replace(/^\/search\s*/i, '').trim();
    if (!searchQuery) {
      await handleSearch(ctx);
      return;
    }
    await handleSearch(ctx);
    await handleMessage(ctx);
  });

  // Handle regular text messages
  bot.on('message:text', handleMessage);

  // Error handler
  bot.catch((err) => {
    console.error('Bot error:', err);
  });

  return bot;
}
