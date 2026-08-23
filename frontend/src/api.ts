import type {
  BestMatchResponse,
  CoverLetterResponse,
  JobAnalysisResponse,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

async function postJson<T>(path: string, body: unknown, runId: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Run-Id': runId,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function analyzeJob(jobDescription: string, runId: string): Promise<JobAnalysisResponse> {
  return postJson<JobAnalysisResponse>('/job-analysis', { job_description: jobDescription }, runId);
}

export function matchJob(
  jobDescription: string,
  jobTitle: string,
  runId: string,
): Promise<BestMatchResponse> {
  return postJson<BestMatchResponse>(
    '/best-match',
    {
      jobs: [
        {
          id: 'current-job',
          title: jobTitle,
          description: jobDescription,
        },
      ],
    },
    runId,
  );
}

export function generateCoverLetter(
  jobDescription: string,
  jobTitle: string,
  companyName: string,
  language: 'en' | 'da',
  tone: 'professional' | 'concise' | 'technical',
  runId: string,
): Promise<CoverLetterResponse> {
  return postJson<CoverLetterResponse>(
    '/cover-letter',
    {
      job_id: 'current-job',
      job_title: jobTitle,
      company_name: companyName || null,
      job_description: jobDescription,
      language,
      tone,
    },
    runId,
  );
}

export { API_BASE_URL };
