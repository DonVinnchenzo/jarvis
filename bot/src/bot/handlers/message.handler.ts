import { Context } from 'grammy';
import { sendToAgent } from '../../claude/agent.js';
import { config } from '../../config.js';
import { messageSender } from '../../telegram/message-sender.js';
import { isDuplicate, markProcessed } from '../../telegram/deduplication.js';
import { isStaleMessage } from '../middleware/stale-filter.js';
import {
  queueRequest,
  isProcessing,
  getQueuePosition,
  setAbortController,
  cancelRequest,
  clearQueue,
} from '../../claude/request-queue.js';
import { escapeMarkdownV2 as esc } from '../../telegram/markdown.js';

export async function handleMessage(ctx: Context): Promise<void> {
  const chatId = ctx.chat?.id;
  const text = ctx.message?.text;
  const messageId = ctx.message?.message_id;
  const messageDate = ctx.message?.date;

  if (!chatId || !text || !messageId || !messageDate) return;

  // Filter stale messages (sent before bot started)
  if (isStaleMessage(messageDate)) {
    console.log(`[Message] Ignoring stale message ${messageId} from before bot start`);
    return;
  }

  // Check for duplicate messages (Telegram retries)
  if (isDuplicate(messageId)) {
    console.log(`[Message] Ignoring duplicate message ${messageId}`);
    return;
  }
  markProcessed(messageId);

  // Resolve user identity
  const userId = ctx.from?.id;
  if (!userId) return;
  const userName = config.USER_NAMES.get(userId) || `User ${userId}`;

  // If CANCEL_ON_NEW_MESSAGE is enabled, auto-cancel the running query;
  // otherwise queue the new message behind it and show the queue position.
  if (isProcessing(chatId)) {
    if (config.CANCEL_ON_NEW_MESSAGE) {
      await cancelRequest(chatId);
      clearQueue(chatId);
    } else {
      const position = getQueuePosition(chatId) + 1;
      await ctx.reply(`Queued (position ${position})`, { parse_mode: undefined });
    }
  }

  try {
    await queueRequest(chatId, text, async () => {
      if (config.STREAMING_MODE === 'streaming') {
        await handleStreamingResponse(ctx, chatId, text, userId, userName);
      } else {
        await handleWaitResponse(ctx, chatId, text, userId, userName);
      }
    });
  } catch (error) {
    if ((error as Error).message === 'Queue cleared') {
      return;
    }
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Error handling message:', error);
    await ctx.reply(`Error: ${esc(errorMessage)}`, { parse_mode: 'MarkdownV2' });
  }
}

async function handleStreamingResponse(
  ctx: Context,
  chatId: number,
  message: string,
  userId: number,
  userName: string
): Promise<void> {
  await messageSender.startStreaming(ctx);

  const abortController = new AbortController();
  setAbortController(chatId, abortController);

  try {
    const response = await sendToAgent(chatId, message, {
      userId,
      userName,
      onProgress: (progressText) => {
        messageSender.updateStream(ctx, progressText);
      },
      abortController,
    });

    await messageSender.finishStreaming(ctx, response.text);
  } catch (error) {
    await messageSender.cancelStreaming(ctx);
    throw error;
  }
}

async function handleWaitResponse(
  ctx: Context,
  chatId: number,
  message: string,
  userId: number,
  userName: string
): Promise<void> {
  // Send typing indicator
  await ctx.replyWithChatAction('typing');

  const abortController = new AbortController();
  setAbortController(chatId, abortController);

  const response = await sendToAgent(chatId, message, {
    userId,
    userName,
    abortController,
  });
  await messageSender.sendMessage(ctx, response.text);
}
