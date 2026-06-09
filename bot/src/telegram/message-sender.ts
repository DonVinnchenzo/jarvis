import { Context, Api } from 'grammy';
import { config } from '../config.js';
import { processMessageForTelegram, escapeMarkdownV2, splitMessage } from './markdown.js';

interface StreamState {
  chatId: number;
  messageId: number | null;
  content: string;
  lastUpdate: number;
  updateScheduled: boolean;
  typingInterval: NodeJS.Timeout | null;
}

const TYPING_INTERVAL_MS = 4000; // Send typing every 4 seconds

export class MessageSender {
  private streamStates: Map<number, StreamState> = new Map();

  /**
   * Send a message with MarkdownV2 formatting and chunking.
   */
  async sendMessage(ctx: Context, text: string): Promise<void> {
    const parts = processMessageForTelegram(text, config.MAX_MESSAGE_LENGTH);

    for (const part of parts) {
      try {
        await ctx.reply(part, { parse_mode: 'MarkdownV2' });
      } catch (error) {
        // MarkdownV2 failed -- send as plain text chunks
        console.error('MarkdownV2 send failed, falling back to plain text:', error);
        const plainChunks = splitMessage(text);
        for (const chunk of plainChunks) {
          await ctx.reply(chunk, { parse_mode: undefined });
        }
        return;
      }
    }
  }

  async startStreaming(ctx: Context): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    const message = await ctx.reply('...', { parse_mode: undefined });

    // Start continuous typing indicator
    const typingInterval = this.startTypingIndicator(ctx.api, chatId);

    const state: StreamState = {
      chatId,
      messageId: message.message_id,
      content: '',
      lastUpdate: Date.now(),
      updateScheduled: false,
      typingInterval,
    };

    this.streamStates.set(chatId, state);
  }

  private startTypingIndicator(api: Api, chatId: number): NodeJS.Timeout {
    api.sendChatAction(chatId, 'typing').catch(() => {});

    return setInterval(() => {
      api.sendChatAction(chatId, 'typing').catch(() => {});
    }, TYPING_INTERVAL_MS);
  }

  private stopTypingIndicator(state: StreamState): void {
    if (state.typingInterval) {
      clearInterval(state.typingInterval);
      state.typingInterval = null;
    }
  }

  async updateStream(ctx: Context, content: string): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    const state = this.streamStates.get(chatId);
    if (!state || !state.messageId) return;

    state.content = content;

    if (state.updateScheduled) return;

    const timeSinceLastUpdate = Date.now() - state.lastUpdate;

    if (timeSinceLastUpdate >= config.STREAMING_DEBOUNCE_MS) {
      await this.flushUpdate(ctx, state);
    } else {
      state.updateScheduled = true;
      setTimeout(async () => {
        state.updateScheduled = false;
        await this.flushUpdate(ctx, state);
      }, config.STREAMING_DEBOUNCE_MS - timeSinceLastUpdate);
    }
  }

  private async flushUpdate(ctx: Context, state: StreamState): Promise<void> {
    if (!state.messageId) return;

    // Plain text during streaming for stability
    const displayContent = state.content.length > 0
      ? state.content.substring(0, config.MAX_MESSAGE_LENGTH - 10) + ' ...'
      : '...';

    try {
      await ctx.api.editMessageText(
        state.chatId,
        state.messageId,
        displayContent,
        { parse_mode: undefined }
      );
      state.lastUpdate = Date.now();
    } catch (error: unknown) {
      if (error instanceof Error) {
        const msg = error.message.toLowerCase();
        if (!msg.includes('message is not modified') && !msg.includes('message_id_invalid')) {
          console.error('Error updating stream:', error);
        }
      }
    }
  }

  async finishStreaming(ctx: Context, finalContent: string): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    const state = this.streamStates.get(chatId);

    if (state) {
      this.stopTypingIndicator(state);

      if (state.messageId) {
        const parts = processMessageForTelegram(finalContent, config.MAX_MESSAGE_LENGTH);

        try {
          const firstPart = parts[0] || 'Done\\.';

          try {
            await ctx.api.editMessageText(
              chatId,
              state.messageId,
              firstPart,
              { parse_mode: 'MarkdownV2' }
            );

            for (let i = 1; i < parts.length; i++) {
              try {
                await ctx.reply(parts[i], { parse_mode: 'MarkdownV2' });
              } catch (partError) {
                console.error(`MarkdownV2 failed for part ${i + 1}:`, partError);
                await ctx.reply(parts[i], { parse_mode: undefined });
              }
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          } catch (mdError) {
            const errMsg = mdError instanceof Error ? mdError.message : '';
            if (errMsg.includes('message is not modified')) {
              console.debug('[Stream] Edit skipped -- content unchanged');
            } else {
              // MarkdownV2 failed -- delete placeholder and re-send
              console.error('MarkdownV2 edit failed, falling back to sendMessage:', mdError);
              try {
                await ctx.api.deleteMessage(chatId, state.messageId);
              } catch { /* ignore */ }

              this.streamStates.delete(chatId);
              await this.sendMessage(ctx, finalContent);
              return;
            }
          }
        } catch (error) {
          console.error('Error finishing stream:', error);
        }
      }
    }

    this.streamStates.delete(chatId);
  }

  async cancelStreaming(ctx: Context): Promise<void> {
    const chatId = ctx.chat?.id;
    if (!chatId) return;

    const state = this.streamStates.get(chatId);
    if (state) {
      this.stopTypingIndicator(state);

      if (state.messageId) {
        try {
          await ctx.api.editMessageText(
            chatId,
            state.messageId,
            'Request cancelled',
            { parse_mode: undefined }
          );
        } catch (error) {
          console.error('Error cancelling stream:', error);
        }
      }
    }

    this.streamStates.delete(chatId);
  }
}

export const messageSender = new MessageSender();
