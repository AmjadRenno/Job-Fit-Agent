export type TraceStatus = 'success' | 'partial' | 'failed';

export interface TraceEvent {
  step: string;
  status: 'success' | 'failed';
  duration_ms: number;
  detail?: string | null;
}

export interface ExecutionTrace {
  run_id: string;
  operation_id: string;
  operation: string;
  status: TraceStatus;
  events: TraceEvent[];
}

export interface ValidationResponse {
  is_valid: boolean;
  normalized_text: string | null;
  error_code: string | null;
  message: string;
}

export interface CandidateClaim {
  claim: string;
  claim_type: string;
  evidence_source: string;
  evidence_excerpt: string;
}

export interface JobAnalysis {
  title: string | null;
  summary: string | null;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  experience_level: string | null;
  education: string[];
  location: string | null;
  matched_candidate_claims: CandidateClaim[];
  missing_requirements: string[];
  analysis: string | null;
  grounding_warnings: string[];
}

export interface JobAnalysisResponse {
  status: 'invalid' | 'validated' | 'analyzed';
  validation: ValidationResponse;
  analysis: JobAnalysis | null;
  execution_trace?: ExecutionTrace | null;
}

export interface JobRequirement {
  requirement: string;
  requirement_type: string;
  importance: 'required' | 'preferred' | 'unknown';
  matched_candidate_claims: CandidateClaim[];
  status: 'matched' | 'partially_matched' | 'missing' | 'unknown';
  evidence: string[];
}

export interface JobMatchResult {
  job_id: string;
  title: string | null;
  score: number;
  rank: number;
  match_summary: string;
  requirement_results: JobRequirement[];
  matched_requirements: string[];
  partial_matches: string[];
  missing_requirements: string[];
  critical_gaps: string[];
  supporting_candidate_evidence: string[];
}

export interface BestMatchResponse {
  ranked_jobs: JobMatchResult[];
  best_match: JobMatchResult | null;
  score: number | null;
  concise_explanation: string;
  important_strengths: string[];
  important_gaps: string[];
  execution_trace?: ExecutionTrace | null;
}

export interface CoverLetterResponse {
  job_id: string;
  job_title: string;
  company_name: string | null;
  language: 'en' | 'da';
  cover_letter: string;
  used_candidate_claims: CandidateClaim[];
  grounding_warnings: string[];
  relevant_match_summary: string;
  execution_trace?: ExecutionTrace | null;
}
