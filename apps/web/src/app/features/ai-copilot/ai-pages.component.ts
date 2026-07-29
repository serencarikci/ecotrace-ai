import { DecimalPipe, JsonPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import {
  AiCopilotService,
  ChatCitation,
  ChatMessageDto,
  ConversationDto,
} from '../../core/services/ai-copilot.service';
import { extractApiErrorMessage } from '../../core/services/error.util';

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [
    FormsModule,
    DecimalPipe,
    JsonPipe,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    RouterLink,
  ],
  template: `
    <section class="page chat-layout">
      <aside class="sidebar surface-card">
        <div class="sidebar-header">
          <h1 class="page-title">AI Copilot</h1>
          <button mat-stroked-button type="button" (click)="newChat()">New chat</button>
        </div>
        <p class="page-subtitle">Grounded sustainability answers with citations.</p>
        @if (loadingConversations()) {
          <mat-spinner diameter="28" />
        } @else {
          <mat-nav-list>
            @for (c of conversations(); track c.id) {
              <a
                mat-list-item
                [class.active]="c.id === activeConversationId()"
                (click)="selectConversation(c.id)"
              >
                <span matListItemTitle>{{ c.title }}</span>
                <span matListItemLine>
                  {{ c.isPinned ? 'Pinned · ' : '' }}{{ c.languageCode }}
                </span>
              </a>
            }
          </mat-nav-list>
        }
        <div class="sidebar-actions">
          <a mat-button routerLink="/app/ai/documents">Documents</a>
          <a mat-button routerLink="/app/ai/search">Search</a>
          <a mat-button routerLink="/app/ai/admin">Admin</a>
        </div>
      </aside>

      <div class="main">
        <div class="messages surface-card">
          @if (!messages().length && !sending()) {
            <div class="empty">
              Ask about carbon inventories, product footprints, passports, targets, or uploaded
              policies. Answers stay grounded in authorized EcoTrace evidence.
            </div>
          }
          @for (m of messages(); track m.id) {
            <article
              class="bubble"
              [class.user]="m.role === 'user'"
              [class.assistant]="m.role === 'assistant'"
            >
              <div class="role">{{ m.role }}</div>
              <pre class="content markdown">{{ m.content }}</pre>
              @if (m.role === 'assistant') {
                <div class="meta">
                  @if (m.confidence != null) {
                    <span>Confidence: {{ (m.confidence * 100 | number: '1.0-0') }}%</span>
                  }
                  <button mat-button type="button" (click)="copy(m.content)">Copy</button>
                  <button mat-button type="button" (click)="rate(m, 5)">Helpful</button>
                  <button mat-button type="button" (click)="rate(m, 1)">Poor</button>
                </div>
                @if (m.citations.length) {
                  <div class="citations">
                    @for (c of m.citations; track c.label) {
                      <button
                        type="button"
                        class="citation-card"
                        (click)="previewCitation(c)"
                        [matTooltip]="c.snippet || c.documentName"
                      >
                        <strong>{{ c.label }}</strong>
                        <span>{{ c.documentName }}</span>
                        @if (c.pageNumber) {
                          <span>p.{{ c.pageNumber }}</span>
                        }
                      </button>
                    }
                  </div>
                }
                @if (m.reasoning) {
                  <details class="reasoning">
                    <summary>Reasoning transparency</summary>
                    <pre>{{ m.reasoning | json }}</pre>
                  </details>
                }
              }
            </article>
          }
          @if (sending()) {
            <div class="typing">Generating grounded answer…</div>
          }
        </div>

        @if (preview()) {
          <div class="preview surface-card">
            <h3>Source preview</h3>
            <p>{{ preview()!.documentName }} · {{ preview()!.databaseSource }}</p>
            <pre>{{ preview()!.snippet }}</pre>
            <button mat-button type="button" (click)="preview.set(null)">Close</button>
          </div>
        }

        @if (errorMessage()) {
          <p class="error">{{ errorMessage() }}</p>
        }

        <form class="composer surface-card" (ngSubmit)="send()">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Ask in English</mat-label>
            <textarea
              matInput
              rows="3"
              [(ngModel)]="draft"
              name="draft"
              [disabled]="sending()"
              required
            ></textarea>
          </mat-form-field>
          <div class="composer-actions">
            <button
              mat-flat-button
              color="primary"
              type="submit"
              [disabled]="sending() || !draft.trim()"
            >
              Send
            </button>
            <button mat-stroked-button type="button" [disabled]="!sending()" (click)="stop()">
              Stop
            </button>
            <button
              mat-stroked-button
              type="button"
              [disabled]="sending() || !lastQuestion"
              (click)="retry()"
            >
              Retry
            </button>
          </div>
        </form>
      </div>
    </section>
  `,
  styles: `
    .chat-layout {
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 1rem;
      min-height: calc(100vh - 8rem);
    }
    .sidebar {
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .sidebar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
    }
    .sidebar a.active {
      background: color-mix(in srgb, var(--et-accent, #2f6f4e) 16%, transparent);
    }
    .sidebar-actions {
      margin-top: auto;
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem;
    }
    .main {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      min-width: 0;
    }
    .messages {
      flex: 1;
      overflow: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }
    .empty {
      color: var(--et-muted, #667);
      line-height: 1.5;
    }
    .bubble {
      max-width: 90%;
      padding: 0.85rem 1rem;
      border-radius: 12px;
      background: color-mix(in srgb, var(--et-surface, #fff) 88%, #dfe8e2);
    }
    .bubble.user {
      align-self: flex-end;
      background: color-mix(in srgb, var(--et-accent, #2f6f4e) 18%, transparent);
    }
    .bubble.assistant {
      align-self: flex-start;
    }
    .role {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      opacity: 0.7;
      margin-bottom: 0.35rem;
    }
    .content {
      white-space: pre-wrap;
      font-family: inherit;
      margin: 0;
      line-height: 1.45;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.25rem;
      align-items: center;
      margin-top: 0.5rem;
    }
    .citations {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }
    .citation-card {
      border: 1px solid color-mix(in srgb, var(--et-border, #ccd5cf) 100%, transparent);
      background: transparent;
      border-radius: 8px;
      padding: 0.45rem 0.65rem;
      display: grid;
      gap: 0.15rem;
      text-align: left;
      cursor: pointer;
      max-width: 220px;
    }
    .reasoning {
      margin-top: 0.5rem;
      font-size: 0.85rem;
    }
    .composer {
      padding: 0.75rem 1rem 1rem;
    }
    .full {
      width: 100%;
    }
    .composer-actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }
    .preview {
      padding: 1rem;
    }
    .typing {
      opacity: 0.75;
      font-style: italic;
    }
    @media (max-width: 900px) {
      .chat-layout {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class AiChatComponent implements OnInit {
  private readonly api = inject(AiCopilotService);

  readonly conversations = signal<ConversationDto[]>([]);
  readonly messages = signal<ChatMessageDto[]>([]);
  readonly loadingConversations = signal(false);
  readonly sending = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly activeConversationId = signal<string | null>(null);
  readonly preview = signal<ChatCitation | null>(null);
  draft = '';
  lastQuestion = '';
  private stopped = false;

  ngOnInit(): void {
    this.reloadConversations();
  }

  reloadConversations(): void {
    this.loadingConversations.set(true);
    this.api.listConversations().subscribe({
      next: (page) => {
        this.conversations.set(page.items ?? []);
        this.loadingConversations.set(false);
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.loadingConversations.set(false);
      },
    });
  }

  newChat(): void {
    this.api.createConversation().subscribe({
      next: (c) => {
        this.activeConversationId.set(c.id);
        this.messages.set([]);
        this.reloadConversations();
      },
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  selectConversation(id: string): void {
    this.activeConversationId.set(id);
    this.api.listMessages(id).subscribe({
      next: (msgs) => this.messages.set(msgs),
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  send(): void {
    const text = this.draft.trim();
    if (!text || this.sending()) return;
    this.stopped = false;
    this.sending.set(true);
    this.errorMessage.set(null);
    this.lastQuestion = text;
    this.draft = '';
    this.api.chat(text, this.activeConversationId()).subscribe({
      next: (res) => {
        if (this.stopped) {
          this.sending.set(false);
          return;
        }
        this.activeConversationId.set(res.conversationId);
        this.messages.update((msgs) => [...msgs, res.userMessage, res.assistantMessage]);
        this.sending.set(false);
        this.reloadConversations();
      },
      error: (err) => {
        this.errorMessage.set(extractApiErrorMessage(err));
        this.sending.set(false);
        this.draft = text;
      },
    });
  }

  stop(): void {
    this.stopped = true;
    this.sending.set(false);
  }

  retry(): void {
    if (!this.lastQuestion) return;
    this.draft = this.lastQuestion;
    this.send();
  }

  copy(text: string): void {
    void navigator.clipboard.writeText(text);
  }

  rate(message: ChatMessageDto, rating: number): void {
    const conversationId = this.activeConversationId();
    if (!conversationId) return;
    this.api
      .feedback({ conversationId, messageId: message.id, rating })
      .subscribe({ error: (err) => this.errorMessage.set(extractApiErrorMessage(err)) });
  }

  previewCitation(c: ChatCitation): void {
    this.preview.set(c);
  }
}

@Component({
  selector: 'app-ai-documents',
  standalone: true,
  imports: [
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    RouterLink,
  ],
  template: `
    <section class="page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Knowledge documents</h1>
          <p class="page-subtitle">Upload policies, reports, and evidence for RAG indexing.</p>
        </div>
        <a mat-button routerLink="/app/ai">Back to chat</a>
      </div>
      <form class="upload" (ngSubmit)="upload()">
        <input type="file" (change)="onFile($event)" />
        <mat-form-field appearance="outline">
          <mat-label>Title</mat-label>
          <input matInput [(ngModel)]="title" name="title" />
        </mat-form-field>
        <button mat-flat-button color="primary" type="submit" [disabled]="!file">
          Upload & index
        </button>
      </form>
      @if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      }
      <table mat-table [dataSource]="items()" class="surface-card full-width">
        <ng-container matColumnDef="title">
          <th mat-header-cell *matHeaderCellDef>Title</th>
          <td mat-cell *matCellDef="let row">{{ row['title'] }}</td>
        </ng-container>
        <ng-container matColumnDef="type">
          <th mat-header-cell *matHeaderCellDef>Type</th>
          <td mat-cell *matCellDef="let row">{{ row['documentType'] }}</td>
        </ng-container>
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let row">{{ row['status'] }}</td>
        </ng-container>
        <ng-container matColumnDef="language">
          <th mat-header-cell *matHeaderCellDef>Language</th>
          <td mat-cell *matCellDef="let row">{{ row['languageCode'] }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="cols"></tr>
        <tr mat-row *matRowDef="let row; columns: cols"></tr>
      </table>
    </section>
  `,
  styles: `
    .page-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .upload {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
      margin-bottom: 1rem;
    }
    .full-width {
      width: 100%;
    }
  `,
})
export class AiDocumentsComponent implements OnInit {
  private readonly api = inject(AiCopilotService);
  readonly items = signal<Array<Record<string, unknown>>>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly cols = ['title', 'type', 'status', 'language'];
  file: File | null = null;
  title = '';

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.api.listDocuments().subscribe({
      next: (page) => this.items.set(page.items ?? []),
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }

  onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file = input.files?.[0] ?? null;
  }

  upload(): void {
    if (!this.file) return;
    this.api.uploadDocument(this.file, this.title || undefined).subscribe({
      next: () => {
        this.file = null;
        this.title = '';
        this.reload();
      },
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-ai-search',
  standalone: true,
  imports: [
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    RouterLink,
  ],
  template: `
    <section class="page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Enterprise search</h1>
          <p class="page-subtitle">
            Hybrid search across documents and structured sustainability data.
          </p>
        </div>
        <a mat-button routerLink="/app/ai">Back to chat</a>
      </div>
      <form class="search" (ngSubmit)="run()">
        <mat-form-field appearance="outline" class="full">
          <mat-label>Query</mat-label>
          <input matInput [(ngModel)]="query" name="query" required />
        </mat-form-field>
        <button mat-flat-button color="primary" type="submit">Search</button>
      </form>
      @if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      }
      <table mat-table [dataSource]="items()" class="surface-card full-width">
        <ng-container matColumnDef="title">
          <th mat-header-cell *matHeaderCellDef>Title</th>
          <td mat-cell *matCellDef="let row">{{ row['title'] }}</td>
        </ng-container>
        <ng-container matColumnDef="source">
          <th mat-header-cell *matHeaderCellDef>Source</th>
          <td mat-cell *matCellDef="let row">{{ row['source'] }}</td>
        </ng-container>
        <ng-container matColumnDef="score">
          <th mat-header-cell *matHeaderCellDef>Score</th>
          <td mat-cell *matCellDef="let row">{{ row['score'] }}</td>
        </ng-container>
        <ng-container matColumnDef="snippet">
          <th mat-header-cell *matHeaderCellDef>Snippet</th>
          <td mat-cell *matCellDef="let row">{{ row['snippet'] }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="cols"></tr>
        <tr mat-row *matRowDef="let row; columns: cols"></tr>
      </table>
    </section>
  `,
  styles: `
    .page-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .search {
      display: flex;
      gap: 0.75rem;
      align-items: flex-start;
      margin-bottom: 1rem;
    }
    .full {
      flex: 1;
    }
    .full-width {
      width: 100%;
    }
  `,
})
export class AiSearchComponent {
  private readonly api = inject(AiCopilotService);
  readonly items = signal<Array<Record<string, unknown>>>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly cols = ['title', 'source', 'score', 'snippet'];
  query = '';

  run(): void {
    this.api.search(this.query).subscribe({
      next: (res) => this.items.set(res.items ?? []),
      error: (err) => this.errorMessage.set(extractApiErrorMessage(err)),
    });
  }
}

@Component({
  selector: 'app-ai-admin',
  standalone: true,
  imports: [MatButtonModule, RouterLink, JsonPipe],
  template: `
    <section class="page">
      <div class="page-header">
        <div>
          <h1 class="page-title">AI administration</h1>
          <p class="page-subtitle">
            Providers, prompts, retrieval logs, cost and evaluation dashboards.
          </p>
        </div>
        <a mat-button routerLink="/app/ai">Back to chat</a>
      </div>
      @if (errorMessage()) {
        <p class="error">{{ errorMessage() }}</p>
      }
      <div class="grid">
        <div class="surface-card metric">
          <h2>Conversation analytics</h2>
          <pre>{{ analytics() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Cost dashboard</h2>
          <pre>{{ cost() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Providers</h2>
          <pre>{{ providers() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Prompt templates</h2>
          <pre>{{ prompts() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Retrieval logs</h2>
          <pre>{{ logs() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Evaluations</h2>
          <pre>{{ evaluations() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Settings</h2>
          <pre>{{ settings() | json }}</pre>
        </div>
        <div class="surface-card metric">
          <h2>Chunks</h2>
          <pre>{{ chunks() | json }}</pre>
        </div>
      </div>
    </section>
  `,
  styles: `
    .page-header {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    .metric {
      padding: 1rem;
      overflow: auto;
      max-height: 320px;
    }
    pre {
      white-space: pre-wrap;
      font-size: 0.8rem;
    }
  `,
})
export class AiAdminComponent implements OnInit {
  private readonly api = inject(AiCopilotService);
  readonly analytics = signal<Record<string, unknown> | null>(null);
  readonly cost = signal<Record<string, unknown> | null>(null);
  readonly providers = signal<unknown>(null);
  readonly prompts = signal<unknown>(null);
  readonly logs = signal<unknown>(null);
  readonly evaluations = signal<unknown>(null);
  readonly settings = signal<unknown>(null);
  readonly chunks = signal<unknown>(null);
  readonly errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.api.analytics().subscribe({
      next: (v) => this.analytics.set(v),
      error: (e) => this.errorMessage.set(extractApiErrorMessage(e)),
    });
    this.api.costDashboard().subscribe({ next: (v) => this.cost.set(v) });
    this.api.providers().subscribe({
      next: (v) => this.providers.set(v),
      error: () =>
        this.providers.set([{ note: 'Admin role required for provider secrets listing' }]),
    });
    this.api.prompts().subscribe({ next: (v) => this.prompts.set(v) });
    this.api.retrievalLogs().subscribe({ next: (v) => this.logs.set(v) });
    this.api.evaluations().subscribe({ next: (v) => this.evaluations.set(v) });
    this.api.settings().subscribe({ next: (v) => this.settings.set(v) });
    this.api.chunks().subscribe({ next: (v) => this.chunks.set(v) });
  }
}
