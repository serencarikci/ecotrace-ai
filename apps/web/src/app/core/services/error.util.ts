import { HttpErrorResponse } from '@angular/common/http';
import { ApiErrorBody } from '../models/api.models';

export function extractApiErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (error instanceof HttpErrorResponse) {
    const body = error.error as ApiErrorBody | null;
    if (body?.error?.message) {
      if (error.status === 409) {
        return 'This record was changed by another user. Please refresh the page and try again.';
      }
      return body.error.message;
    }
    if (error.status === 409) {
      return 'This record was changed by another user. Please refresh the page and try again.';
    }
    if (typeof error.error === 'string' && error.error.trim()) {
      return error.error;
    }
    if (error.status === 0) {
      return 'Unable to reach the EcoTrace API. Check that the backend is running.';
    }
  }
  return fallback;
}
