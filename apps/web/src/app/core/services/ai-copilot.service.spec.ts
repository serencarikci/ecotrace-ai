import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AiCopilotService } from './ai-copilot.service';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

describe('AiCopilotService', () => {
  let service: AiCopilotService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const auth = TestBed.inject(AuthService);
    auth.organizations.set([
      {
        organizationId: 'org-1',
        organizationName: 'Demo',
        organizationSlug: 'demo',
        roleCode: 'organization_admin',
        isActive: true,
      },
    ]);
    auth.selectedOrganizationId.set('org-1');
    service = TestBed.inject(AiCopilotService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts chat messages to the org AI endpoint', () => {
    service.chat('Hello').subscribe();
    const req = http.expectOne(
      `${environment.apiUrl}${environment.apiV1Prefix}/organizations/org-1/ai/chat`,
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.body.message).toBe('Hello');
    req.flush({
      conversationId: 'c1',
      userMessage: { id: '1', conversationId: 'c1', role: 'user', content: 'Hello', languageCode: 'en', citations: [] },
      assistantMessage: {
        id: '2',
        conversationId: 'c1',
        role: 'assistant',
        content: 'Answer [E1]',
        languageCode: 'en',
        citations: [{ label: 'E1', documentName: 'Policy', databaseSource: 'document' }],
      },
      citations: [{ label: 'E1', documentName: 'Policy', databaseSource: 'document' }],
      confidence: 0.7,
      reasoning: {},
      language: 'en',
      grounded: true,
    });
  });
});
