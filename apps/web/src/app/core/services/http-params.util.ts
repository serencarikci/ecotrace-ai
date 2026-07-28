import { HttpParams } from '@angular/common/http';

export function buildHttpParams(
  values: Record<string, string | number | boolean | null | undefined>,
): HttpParams {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === '') {
      continue;
    }
    params = params.set(key, String(value));
  }
  return params;
}
