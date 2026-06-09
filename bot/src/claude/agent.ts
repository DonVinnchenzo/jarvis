import {
  query,
  type SDKResultMessage,
  type SDKCompactBoundaryMessage,
  type SDKSystemMessage,
  type SDKStatusMessage,
  type SettingSource,
  type HookEvent,
  type HookCallbackMatcher,
} from '@anthropic-ai/claude-agent-sdk';
import { sessionManager } from './session-manager.js';
import { setActiveQuery, clearActiveQuery, isCancelled } from './request-queue.js';
import { config } from '../config.js';

export interface AgentUsage {
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  totalCostUsd: number;
  contextWindow: number;
  numTurns: number;
  model: string;
}

interface AgentResponse {
  text: string;
  toolsUsed: string[];
  usage?: AgentUsage;
}

interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AgentOptions {
  userId: number;
  userName: string;
  onProgress?: (text: string) => void;
  abortController?: AbortController;
}

const conversationHistory: Map<number, ConversationMessage[]> = new Map();

// Track Claude Code session IDs per chat for conversation continuity
const chatSessionIds: Map<number, string> = new Map();

function buildSystemPrompt(userId: number, userName: string): string {
  return `You are Jarvis, a household assistant for Vincent & Christianne.

CURRENT_USER: ${userName} (Telegram ID: ${userId})

You help manage their social circle: friends, family, important dates, and notes about people they care about. You communicate via Telegram.

How you work:
- You are a Claude Code agent with access to the Jarvis project directory
- You interact with the backend API via curl (http://localhost:8000)
- You ALWAYS include the X-API-Key header: -H "X-API-Key: $JARVIS_API_KEY"
- You NEVER access the database directly -- always through the API
- You follow the skills in .claude/skills/ for every operation
- You read CLAUDE.md for architecture and rules

API authentication:
- Every curl request to the API must include: -H "X-API-Key: $JARVIS_API_KEY"
- The JARVIS_API_KEY environment variable is available in your shell

When the user asks you to do something:
1. Identify the right skill (add-contact, search, add-note, upcoming, etc.)
2. Follow the skill's steps exactly
3. Use curl to call the API
4. Confirm what you did in a friendly, concise message

Data attribution:
- When creating contacts, events, or notes, always set created_by to "${userId}"
- When showing data, mention who added it (e.g., "Added by Vincent, 3 weeks ago")

Tone:
- Warm and helpful, like a thoughtful personal assistant
- Concise -- Telegram messages should be short
- Use emojis sparingly but naturally
- Never use jargon or technical language
- If Christianne is the user, be extra warm and example-driven (Christianne-first UX)

Response formatting:
- Keep responses short for Telegram (under 1000 chars when possible)
- Use bullet points for lists
- Bold names and dates for scannability`;
}

type LogLevel = 'off' | 'basic' | 'verbose' | 'trace';
const LOG_LEVELS: Record<LogLevel, number> = {
  off: 0,
  basic: 1,
  verbose: 2,
  trace: 3,
};

function getLogLevel(): LogLevel {
  return config.CLAUDE_SDK_LOG_LEVEL as LogLevel;
}

function logAt(level: LogLevel, message: string, data?: unknown): void {
  if (LOG_LEVELS[level] <= LOG_LEVELS[getLogLevel()]) {
    if (data !== undefined) {
      console.log(message, data);
    } else {
      console.log(message);
    }
  }
}

export async function sendToAgent(
  chatId: number,
  message: string,
  options: AgentOptions
): Promise<AgentResponse> {
  const { userId, userName, onProgress, abortController } = options;

  const session = sessionManager.getSession(chatId);
  sessionManager.updateActivity(chatId);

  // Get or initialize conversation history
  const history = conversationHistory.get(chatId) || [];

  // Add user message to history
  history.push({
    role: 'user',
    content: message,
  });

  let fullText = '';
  const toolsUsed: string[] = [];
  let gotResult = false;
  let resultUsage: AgentUsage | undefined;

  // Build dynamic system prompt with user identity
  const systemPrompt = buildSystemPrompt(userId, userName);

  logAt('basic', `[Claude] Query from ${userName} (${userId}) in chat ${chatId}: ${message.substring(0, 100)}`);

  try {
    const controller = abortController || new AbortController();

    const existingSessionId = chatSessionIds.get(chatId) || session.claudeSessionId;

    if (existingSessionId) {
      logAt('basic', `[Claude] Resuming session ${existingSessionId} for chat ${chatId}`);
    }

    const cwd = sessionManager.getWorkingDirectory();

    const preCompactHook: Partial<Record<HookEvent, HookCallbackMatcher[]>> = {
      PreCompact: [{
        hooks: [async (input) => {
          logAt('basic', '[Hook] PreCompact -- context is about to be compacted', {
            trigger: (input as Record<string, unknown>).trigger,
          });
          return { continue: true };
        }],
      }],
    };

    const hooks: Partial<Record<HookEvent, HookCallbackMatcher[]>> =
      LOG_LEVELS[getLogLevel()] >= LOG_LEVELS.verbose
        ? {
          ...preCompactHook,
          SessionStart: [{
            hooks: [async (input) => {
              logAt('basic', '[Hook] SessionStart', input);
              return { continue: true };
            }],
          }],
          SessionEnd: [{
            hooks: [async (input) => {
              logAt('basic', '[Hook] SessionEnd', input);
              return { continue: true };
            }],
          }],
        }
        : preCompactHook;

    const queryOptions: Parameters<typeof query>[0]['options'] = {
      cwd,
      tools: { type: 'preset' as const, preset: 'claude_code' as const },
      permissionMode: 'bypassPermissions',
      allowDangerouslySkipPermissions: true,
      abortController: controller,
      systemPrompt: {
        type: 'preset' as const,
        preset: 'claude_code' as const,
        append: systemPrompt,
      },
      settingSources: ['project', 'user'] as SettingSource[],
      model: 'opus',
      resume: existingSessionId,
      hooks,
      stderr: (data: string) => {
        console.error('[Claude stderr]:', data);
      },
    };

    const response = query({
      prompt: message,
      options: queryOptions,
    });

    // Store the Query object so /cancel can call interrupt()
    setActiveQuery(chatId, response);

    // Process response messages
    for await (const responseMessage of response) {
      if (controller.signal.aborted) {
        fullText = 'Request cancelled.';
        break;
      }

      logAt('trace', '[Claude] Message type:', responseMessage.type);

      if (responseMessage.type === 'assistant') {
        for (const block of responseMessage.message.content) {
          if (block.type === 'text') {
            fullText += block.text;
            onProgress?.(fullText);
          } else if (block.type === 'tool_use') {
            const toolInput = 'input' in block ? block.input as Record<string, unknown> : {};
            const inputSummary = toolInput.command
              ? String(toolInput.command).substring(0, 150)
              : toolInput.pattern
                ? String(toolInput.pattern)
                : toolInput.file_path
                  ? String(toolInput.file_path)
                  : '';
            logAt('verbose', `[Claude] Tool: ${block.name}${inputSummary ? ` -> ${inputSummary}` : ''}`);
            toolsUsed.push(block.name);
          }
        }
      } else if (responseMessage.type === 'system') {
        if (responseMessage.subtype === 'compact_boundary') {
          const cbMsg = responseMessage as SDKCompactBoundaryMessage;
          logAt('basic', `[Claude] COMPACTION: trigger=${cbMsg.compact_metadata.trigger}, pre_tokens=${cbMsg.compact_metadata.pre_tokens}`);
        } else if (responseMessage.subtype === 'init') {
          const sysMsg = responseMessage as SDKSystemMessage;
          logAt('basic', `[Claude] SESSION INIT: model=${sysMsg.model}, session=${sysMsg.session_id}`);
        } else if (responseMessage.subtype === 'status') {
          const statusMsg = responseMessage as SDKStatusMessage;
          if (statusMsg.status === 'compacting') {
            logAt('basic', '[Claude] STATUS: compacting in progress');
          }
        } else {
          logAt('verbose', `[Claude] System: ${responseMessage.subtype ?? 'unknown'}`, responseMessage);
        }
      } else if (responseMessage.type === 'result') {
        logAt('basic', '[Claude] Result:', JSON.stringify(responseMessage, null, 2).substring(0, 500));
        gotResult = true;

        // Capture session_id for conversation continuity
        if ('session_id' in responseMessage && responseMessage.session_id) {
          chatSessionIds.set(chatId, responseMessage.session_id);
          sessionManager.setClaudeSessionId(chatId, responseMessage.session_id);
          logAt('basic', `[Claude] Stored session ${responseMessage.session_id} for chat ${chatId}`);
        }

        // Extract usage data from result
        const resultMsg = responseMessage as SDKResultMessage;
        if (resultMsg.modelUsage) {
          const modelKey = Object.keys(resultMsg.modelUsage)[0];
          if (modelKey && resultMsg.modelUsage[modelKey]) {
            const mu = resultMsg.modelUsage[modelKey];
            resultUsage = {
              inputTokens: mu.inputTokens,
              outputTokens: mu.outputTokens,
              cacheReadTokens: mu.cacheReadInputTokens,
              cacheWriteTokens: mu.cacheCreationInputTokens,
              totalCostUsd: resultMsg.total_cost_usd,
              contextWindow: mu.contextWindow,
              numTurns: resultMsg.num_turns,
              model: modelKey,
            };
          }
        }

        if (responseMessage.subtype === 'success') {
          if (responseMessage.result && !fullText.includes(responseMessage.result)) {
            if (fullText.length > 0) {
              fullText += '\n\n';
            }
            fullText += responseMessage.result;
            onProgress?.(fullText);
          }
        } else if (responseMessage.subtype === 'error_during_execution' && isCancelled(chatId)) {
          fullText = 'Successfully cancelled.';
          onProgress?.(fullText);
        } else {
          fullText = `Error: ${responseMessage.subtype}`;
          onProgress?.(fullText);
        }
      }
    }
  } catch (error) {
    // If cancelled via /cancel, return clean message
    if (isCancelled(chatId) || abortController?.signal.aborted) {
      return {
        text: 'Successfully cancelled.',
        toolsUsed,
      };
    }

    // If we got a result, ignore process exit errors (SDK quirk)
    if (gotResult && error instanceof Error && error.message.includes('exited with code')) {
      console.log('[Claude] Ignoring exit code error after successful result');
    } else {
      console.error('[Claude] Full error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Claude error: ${errorMessage}`);
    }
  } finally {
    clearActiveQuery(chatId);
  }

  // Add assistant response to history
  if (fullText && !abortController?.signal.aborted) {
    history.push({
      role: 'assistant',
      content: fullText,
    });
  }

  conversationHistory.set(chatId, history);

  return {
    text: fullText || 'No response from Claude.',
    toolsUsed,
    usage: resultUsage,
  };
}

export function clearConversation(chatId: number): void {
  conversationHistory.delete(chatId);
  chatSessionIds.delete(chatId);
}
