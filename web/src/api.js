// AL-Core REST client. Every request carries the signed-in user's Firebase ID token;
// AL-Core verifies it and answers from Firestore. The token is never stored by us.
import {getCurrentIdToken} from './authAPI.js';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : `Request failed (${status})`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest(path, {method = 'GET', body, forceRefresh = false} = {}) {
  const token = await getCurrentIdToken(forceRefresh);
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body !== undefined && {'Content-Type': 'application/json'}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'AL-Core is unreachable. Is the API running?');
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data?.detail);
  return data;
}

// GET /api/v1/users/me: profile record (Firestore) + account data (token)
export function getMyProfile() {
  return apiRequest('/api/v1/users/me');
}

// GET /api/v1/loan-applications: the caller's applications, newest first, paginated.
// AL-Core limits the list by role: a broker sees applications they claimed (or, with
// unclaimedOnly, the shared pool nobody has claimed yet); an underwriter sees the ones
// assigned to them. Filters left empty are not sent.
export function listLoanApplications({page = 1, pageSize = 15, unclaimedOnly = false, status, riskTier, ltvGroup} = {}) {
  const params = new URLSearchParams({page: String(page), pageSize: String(pageSize)});
  if (unclaimedOnly) params.set('unclaimedOnly', 'true');
  if (status) params.set('status', status);
  if (riskTier) params.set('riskTier', riskTier);
  if (ltvGroup) params.set('ltvGroup', ltvGroup);
  return apiRequest(`/api/v1/loan-applications?${params}`);
}

// GET /api/v1/loan-applications/{id}: one application. AL-Core answers 404 both when it
// does not exist and when the caller may not see it (brokers may see unclaimed ones).
export function getLoanApplication(id) {
  return apiRequest(`/api/v1/loan-applications/${encodeURIComponent(id)}`);
}

export const LOAN_STATUSES = ['Applied', 'AI Deliberated', 'Underwriter Approved', 'Funded', 'Closed'];
export const RISK_TIERS = ['Low', 'Medium', 'High'];
export const LTV_GROUPS = {
  up_to_60: 'Up to 60%',
  from_60_to_80: '60–80%',
  from_80_to_90: '80–90%',
  over_90: 'Over 90%',
};

export function loanErrorMessage(error, fallback = 'Loan applications could not be loaded. Please try again.') {
  switch (error?.status) {
    case 0: return error.message;
    case 401: return 'Your session could not be verified. Please sign in again.';
    case 403: return 'Your account does not have access to loan applications.';
    case 404: return 'This application was not found, or you no longer have access to it.';
    case 429: return 'Too many requests. Please wait a moment and try again.';
    default: return fallback;
  }
}

export const ROLE_LABELS = {
  retail_borrower: 'Borrower',
  mortgage_broker: 'Mortgage Broker',
  underwriting_bank_officer: 'Underwriter',
};

export function roleLabel(role) {
  return ROLE_LABELS[role] || 'No role assigned';
}

export function profileErrorMessage(error) {
  switch (error?.status) {
    case 0: return error.message;
    case 401: return 'Your session could not be verified. Please sign in again.';
    case 404: return 'No profile exists for this account yet. Contact your administrator.';
    case 429: return 'Too many requests. Please wait a moment.';
    default: return 'Your profile could not be loaded. Please try again.';
  }
}
