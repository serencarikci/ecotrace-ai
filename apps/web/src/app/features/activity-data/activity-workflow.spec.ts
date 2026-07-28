import { activityWorkflowActions } from '../../core/services/roles.util';

describe('activity workflow button visibility', () => {
  it('shows submit for analyst on draft', () => {
    expect(activityWorkflowActions('draft', ['analyst'])).toEqual(['submit']);
  });

  it('shows approve and reject for sustainability_manager on submitted', () => {
    expect(activityWorkflowActions('submitted', ['sustainability_manager'])).toEqual([
      'approve',
      'reject',
      'archive',
    ]);
  });

  it('shows correct for approved records to managers', () => {
    expect(activityWorkflowActions('approved', ['organization_admin'])).toContain('correct');
  });

  it('hides workflow actions for viewers', () => {
    expect(activityWorkflowActions('draft', ['viewer'])).toEqual([]);
    expect(activityWorkflowActions('submitted', ['viewer'])).toEqual([]);
  });

  it('does not allow analysts to approve', () => {
    expect(activityWorkflowActions('submitted', ['analyst'])).not.toContain('approve');
  });
});
