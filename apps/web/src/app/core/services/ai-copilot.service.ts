import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

export interface ChatCitation {
  label: string;
  documentName: string;
  documentId?: string | null;
  pageNumber?: number | null;
  chunkId?: string | null;
  databaseSource: string;
  recordId?: string | null;
  url?: string | null;
  score?: number;
  snippet?: string;
}

export interface ChatMessageDto {
  id: string;
  conversationId: string;
  role: string;
  content: string;
  languageCode: string;
  citations: ChatCitation[];
  confidence?: number | null;
  reasoning?: Record<string, unknown> | null;
  createdAt?: string;
}

export interface ConversationDto {
  id: string;
  title: string;
  status: string;
  isPinned: boolean;
  isFavorite: boolean;
  isSharedOrg: boolean;
  languageCode: string;
  updatedAt?: string;
}

@Injectable({ providedIn: 'root' })
export class AiCopilotService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  private orgBase(suffix: string): string {
    const id = this.auth.requireOrganizationId();
    return `${environment.apiUrl}${environment.apiV1Prefix}/organizations/${id}${suffix}`;
  }

  chat(message: string, conversationId?: string | null) {
    return this.http.post<{
      conversationId: string;
      assistantMessage: ChatMessageDto;
      userMessage: ChatMessageDto;
      citations: ChatCitation[];
      confidence: number;
      reasoning: Record<string, unknown>;
      language: string;
      grounded: boolean;
    }>(this.orgBase('/ai/chat'), {
      message,
      conversationId: conversationId ?? null,
    });
  }

  listConversations() {
    return this.http.get<{ items: ConversationDto[] }>(this.orgBase('/ai/conversations'));
  }

  listMessages(conversationId: string) {
    return this.http.get<ChatMessageDto[]>(this.orgBase(`/ai/conversations/${conversationId}/messages`));
  }

  createConversation() {
    return this.http.post<ConversationDto>(this.orgBase('/ai/conversations'), {});
  }

  updateConversation(
    conversationId: string,
    body: Partial<{
      title: string;
      isPinned: boolean;
      isFavorite: boolean;
      shareOrg: boolean;
      archive: boolean;
    }>,
  ) {
    return this.http.patch<ConversationDto>(
      this.orgBase(`/ai/conversations/${conversationId}`),
      body,
    );
  }

  deleteConversation(conversationId: string) {
    return this.http.delete(this.orgBase(`/ai/conversations/${conversationId}`));
  }

  feedback(body: {
    conversationId: string;
    messageId: string;
    rating: number;
    comment?: string;
  }) {
    return this.http.post(this.orgBase('/ai/feedback'), body);
  }

  search(query: string) {
    return this.http.post<{ items: Array<Record<string, unknown>> }>(this.orgBase('/search'), {
      query,
      mode: 'hybrid',
    });
  }

  listDocuments() {
    return this.http.get<{ items: Array<Record<string, unknown>> }>(
      this.orgBase('/knowledge/documents'),
    );
  }

  uploadDocument(file: File, title?: string): Observable<unknown> {
    const form = new FormData();
    form.append('file', file);
    if (title) form.append('title', title);
    form.append('publish', 'true');
    return this.http.post(this.orgBase('/knowledge/documents'), form);
  }

  analytics() {
    return this.http.get<Record<string, unknown>>(this.orgBase('/ai/analytics'));
  }

  costDashboard() {
    return this.http.get<Record<string, unknown>>(this.orgBase('/ai/cost-dashboard'));
  }

  evaluations() {
    return this.http.get<Array<Record<string, unknown>>>(this.orgBase('/ai/evaluations'));
  }

  settings() {
    return this.http.get<Record<string, unknown>>(this.orgBase('/ai/settings'));
  }

  providers() {
    return this.http.get<Array<Record<string, unknown>>>(this.orgBase('/ai/providers'));
  }

  prompts() {
    return this.http.get<Array<Record<string, unknown>>>(this.orgBase('/ai/prompts'));
  }

  retrievalLogs() {
    return this.http.get<Array<Record<string, unknown>>>(this.orgBase('/ai/retrieval-logs'));
  }

  chunks() {
    return this.http.get<{ items: Array<Record<string, unknown>> }>(this.orgBase('/knowledge/chunks'));
  }
}
