import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { UnauthorizedComponent } from './unauthorized.component';
import { NotFoundComponent } from './not-found.component';

describe('error pages', () => {
  it('renders unauthorized page', async () => {
    await TestBed.configureTestingModule({
      imports: [UnauthorizedComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture: ComponentFixture<UnauthorizedComponent> =
      TestBed.createComponent(UnauthorizedComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Unauthorized');
  });

  it('renders not found page', async () => {
    await TestBed.configureTestingModule({
      imports: [NotFoundComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    const fixture: ComponentFixture<NotFoundComponent> =
      TestBed.createComponent(NotFoundComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Page not found');
  });
});
