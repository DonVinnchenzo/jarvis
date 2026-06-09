import { run } from '@grammyjs/runner';
import { createBot } from './bot/bot.js';
import { config } from './config.js';
import { stopCleanup } from './telegram/deduplication.js';

async function main() {
  console.log('Starting Jarvis...');
  console.log(`Allowed users: ${config.ALLOWED_USER_IDS.length > 0 ? config.ALLOWED_USER_IDS.join(', ') : '(none configured)'}`);
  console.log(`Mode: ${config.STREAMING_MODE}`);
  console.log(`Workspace: ${config.WORKSPACE_DIR}`);

  const bot = await createBot();

  // Initialize bot (fetches bot info from Telegram)
  await bot.init();
  console.log(`Bot started as @${bot.botInfo.username}`);

  // Start concurrent runner -- updates are processed in parallel,
  // with per-chat ordering enforced by the sequentialize middleware in bot.ts.
  // This lets /cancel bypass the per-chat queue and interrupt running queries.
  const runner = run(bot);

  // Graceful shutdown (guarded against duplicate signals)
  let shuttingDown = false;
  const shutdown = async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    console.log('\nShutting down...');
    stopCleanup();
    await runner.stop();
    process.exit(0);
  };

  process.on('SIGINT', () => { shutdown(); });
  process.on('SIGTERM', () => { shutdown(); });

  // Keep alive until the runner stops (crash or explicit stop)
  await runner.task();
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
