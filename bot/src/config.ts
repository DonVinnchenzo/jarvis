import { config as loadEnv } from 'dotenv';
import { z } from 'zod';
import * as path from 'path';

// Load .env from the jarvis root (one level up from bot/)
const envPath = path.resolve(import.meta.dirname, '..', '..', '.env');
loadEnv({ path: envPath });

const envSchema = z.object({
  // Telegram
  TELEGRAM_BOT_TOKEN: z.string().min(1, 'Telegram bot token is required'),
  ALLOWED_USER_IDS: z
    .string()
    .default('')
    .transform((val) => {
      if (!val || val.trim() === '') return [] as number[];
      return val.split(',').map((id) => parseInt(id.trim(), 10));
    }),
  USER_NAMES: z
    .string()
    .default('{}')
    .transform((val): Map<number, string> => {
      try {
        const parsed = JSON.parse(val) as Record<string, string>;
        const map = new Map<number, string>();
        for (const [id, name] of Object.entries(parsed)) {
          map.set(parseInt(id, 10), name);
        }
        return map;
      } catch {
        return new Map();
      }
    }),

  // Jarvis
  JARVIS_API_KEY: z.string().min(1, 'JARVIS_API_KEY is required'),
  WORKSPACE_DIR: z.string().default('/Users/vincent/jarvis'),
  BOT_NAME: z.string().default('Jarvis'),

  // Claude Agent SDK
  DANGEROUS_MODE: z
    .string()
    .default('true')
    .transform((val) => val.toLowerCase() === 'true'),
  STREAMING_MODE: z.enum(['streaming', 'wait']).default('streaming'),
  MAX_MESSAGE_LENGTH: z
    .string()
    .default('4000')
    .transform((val) => parseInt(val, 10)),
  STREAMING_DEBOUNCE_MS: z
    .string()
    .default('500')
    .transform((val) => parseInt(val, 10)),
  CLAUDE_SDK_LOG_LEVEL: z.enum(['off', 'basic', 'verbose', 'trace']).default('basic'),
  CANCEL_ON_NEW_MESSAGE: z
    .string()
    .default('false')
    .transform((val) => val.toLowerCase() === 'true'),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('Invalid environment configuration:');
  console.error(parsed.error.message);
  process.exit(1);
}

export const config = parsed.data;

export type Config = typeof config;
