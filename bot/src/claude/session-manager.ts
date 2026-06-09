/**
 * Simplified session manager for Jarvis.
 * Always uses /Users/vincent/jarvis as the working directory.
 * Tracks Claude Code session ID per chat for conversation continuity.
 */

import { config } from '../config.js';

interface Session {
  claudeSessionId?: string;
  createdAt: Date;
  lastActivity: Date;
}

class SessionManager {
  private sessions: Map<number, Session> = new Map();

  getSession(chatId: number): Session {
    let session = this.sessions.get(chatId);
    if (!session) {
      session = this.createSession(chatId);
    }
    return session;
  }

  createSession(chatId: number): Session {
    const session: Session = {
      claudeSessionId: undefined,
      createdAt: new Date(),
      lastActivity: new Date(),
    };
    this.sessions.set(chatId, session);
    return session;
  }

  updateActivity(chatId: number): void {
    const session = this.sessions.get(chatId);
    if (session) {
      session.lastActivity = new Date();
    }
  }

  setClaudeSessionId(chatId: number, claudeSessionId: string): void {
    const session = this.getSession(chatId);
    session.claudeSessionId = claudeSessionId;
    session.lastActivity = new Date();
  }

  clearSession(chatId: number): void {
    this.sessions.delete(chatId);
  }

  getWorkingDirectory(): string {
    return config.WORKSPACE_DIR;
  }
}

export const sessionManager = new SessionManager();
