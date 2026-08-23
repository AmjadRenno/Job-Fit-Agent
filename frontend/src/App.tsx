import { useMemo, useState, type FormEvent } from 'react';

import { analyzeJob, generateCoverLetter, matchJob } from './api';
import type {
  BestMatchResponse,
  CoverLetterResponse,
  ExecutionTrace,
  JobAnalysisResponse,
} from './types';

type Phase = 'idle' | 'analysis' | 'match' | 'cover' | 'done';
type SectionKey = 'analysis' | 'match' | 'evidence' | 'cover' | 'trace';

const DEFAULT_JOB_DESCRIPTION = `We are looking for a Senior Backend Engineer to build reliable APIs and AI-assisted workflows.
The role requires strong C# and ASP.NET Core experience, SQL knowledge, and practical familiarity with cloud services.
You will collaborate across product and engineering, improve existing systems, and turn complex requirements into grounded solutions.`;

function formatDuration(value: number): string {
  return `${value.toFixed(2)} ms`;
}

function statusLabel(status: string): string {
  return status.replaceAll('_', ' ');
}

function dedupeClaims(
  items: Array<{ claim: string; evidence_source: string; claim_type: string; evidence_excerpt: string }>,
) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.claim}|${item.evidence_source}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function traceCards(
  analysis: JobAnalysisResponse | null,
  match: BestMatchResponse | null,
  cover: CoverLetterResponse | null,
): Array<{ label: string; trace: ExecutionTrace }> {
  return [
    analysis?.execution_trace ? { label: 'Job Analysis', trace: analysis.execution_trace } : null,
    match?.execution_trace ? { label: 'Match Breakdown', trace: match.execution_trace } : null,
    cover?.execution_trace ? { label: 'Cover Letter', trace: cover.execution_trace } : null,
  ].filter((item): item is { label: string; trace: ExecutionTrace } => item !== null);
}

export function App() {
  const [jobTitle, setJobTitle] = useState('Senior Backend Engineer');
  const [companyName, setCompanyName] = useState('Contoso');
  const [language, setLanguage] = useState<'en' | 'da'>('en');
  const [tone, setTone] = useState<'professional' | 'concise' | 'technical'>('professional');
  const [jobDescription, setJobDescription] = useState(DEFAULT_JOB_DESCRIPTION);
  const [phase, setPhase] = useState<Phase>('idle');
  const [runId, setRunId] = useState<string>('');
  const [analysisResponse, setAnalysisResponse] = useState<JobAnalysisResponse | null>(null);
  const [matchResponse, setMatchResponse] = useState<BestMatchResponse | null>(null);
  const [coverLetterResponse, setCoverLetterResponse] = useState<CoverLetterResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [sectionOpen, setSectionOpen] = useState<Record<SectionKey, boolean>>({
    analysis: true,
    match: true,
    evidence: false,
    cover: true,
    trace: false,
  });

  const traces = useMemo(
    () => traceCards(analysisResponse, matchResponse, coverLetterResponse),
    [analysisResponse, matchResponse, coverLetterResponse],
  );

  const primaryMatch = matchResponse?.best_match ?? null;
  const analysis = analysisResponse?.analysis ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedTitle = jobTitle.trim();
    const trimmedDescription = jobDescription.trim();

    if (!trimmedTitle || !trimmedDescription) {
      setError('Job title and job description are required.');
      return;
    }

    const nextRunId = crypto.randomUUID();
    setRunId(nextRunId);
    setPhase('analysis');
    setError('');
    setAnalysisResponse(null);
    setMatchResponse(null);
    setCoverLetterResponse(null);

    try {
      const analysisResult = await analyzeJob(trimmedDescription, nextRunId);
      setAnalysisResponse(analysisResult);

      if (analysisResult.status === 'invalid') {
        setPhase('done');
        return;
      }

      setPhase('match');
      const matchResult = await matchJob(trimmedDescription, trimmedTitle, nextRunId);
      setMatchResponse(matchResult);

      setPhase('cover');
      const coverResult = await generateCoverLetter(
        trimmedDescription,
        trimmedTitle,
        companyName.trim(),
        language,
        tone,
        nextRunId,
      );
      setCoverLetterResponse(coverResult);
      setPhase('done');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unexpected request failure.');
      setPhase('idle');
    }
  }

  async function copyCoverLetter() {
    if (!coverLetterResponse?.cover_letter) {
      return;
    }

    await navigator.clipboard.writeText(coverLetterResponse.cover_letter);
  }

  const approvedClaims = dedupeClaims(analysis?.matched_candidate_claims ?? []);
  const usedClaims = coverLetterResponse?.used_candidate_claims ?? [];

  function setSectionState(section: SectionKey, open: boolean) {
    setSectionOpen((current) => ({
      ...current,
      [section]: open,
    }));
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <header className="hero">
        <div>
          <p className="eyebrow">Grounded Agentic AI UX</p>
          <h1>Job Fit Agent</h1>
          <p className="hero-copy">
            A portfolio backend surfaced as a trustworthy, evidence-first workflow. The UI shows
            actual backend output, not a fabricated progress story.
          </p>
        </div>
      </header>

      <main className="content-grid">
        <section className="panel panel-form">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Job Input</p>
              <h2>Paste the role, then run the real pipeline</h2>
            </div>
          </div>

          <form className="job-form" onSubmit={handleSubmit}>
            <div className="field-grid">
              <label>
                <span>Job title</span>
                <input value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} />
              </label>
              <label>
                <span>Company</span>
                <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} />
              </label>
              <label>
                <span>Language</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value as 'en' | 'da')}>
                  <option value="en">English</option>
                  <option value="da">Danish</option>
                </select>
              </label>
              <label>
                <span>Tone</span>
                <select
                  value={tone}
                  onChange={(event) =>
                    setTone(event.target.value as 'professional' | 'concise' | 'technical')
                  }
                >
                  <option value="professional">Professional</option>
                  <option value="concise">Concise</option>
                  <option value="technical">Technical</option>
                </select>
              </label>
            </div>

            <label className="textarea-field">
              <span>Job description</span>
              <textarea
                rows={13}
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                placeholder="Paste the job description here."
              />
            </label>

            <div className="form-actions">
              <button type="submit">Run analysis</button>
              <p>
                The backend executes the analysis, match breakdown, evidence validation, and
                grounded letter generation.
              </p>
            </div>
          </form>

          {error ? <div className="error-banner">{error}</div> : null}
        </section>

        <section className="panel summary-panel">
          <div className="summary-card score-card">
            <span className="panel-kicker">Match Score</span>
            <div className="score-value">{primaryMatch ? `${primaryMatch.score.toFixed(1)}%` : '—'}</div>
            {primaryMatch ? (
              <p>
                {primaryMatch.matched_requirements.length} matched · {primaryMatch.partial_matches.length}{' '}
                partial · {primaryMatch.missing_requirements.length} missing · {primaryMatch.critical_gaps.length}{' '}
                critical gap{primaryMatch.critical_gaps.length === 1 ? '' : 's'}
              </p>
            ) : (
              <p>Run the pipeline to see a grounded score.</p>
            )}
          </div>

          {analysis?.grounding_warnings?.length || analysis?.missing_requirements?.length || usedClaims.length ? (
            <div className="summary-card">
              <span className="panel-kicker">Quality Signals</span>
              <ul className="signal-list">
                {analysis?.grounding_warnings?.length ? <li>Grounding warnings present</li> : null}
                {analysis?.missing_requirements?.length ? (
                  <li>{analysis.missing_requirements.length} missing requirements</li>
                ) : null}
                {usedClaims.length ? <li>{usedClaims.length} approved claims used in the letter</li> : null}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="panel result-panel">
          <details open={sectionOpen.analysis} onToggle={(event) => setSectionState('analysis', event.currentTarget.open)}>
            <summary>
              <span>Job Analysis</span>
              <strong>{analysisResponse?.status ?? 'Waiting'}</strong>
            </summary>
            <div className="section-body">
              {analysis ? (
                <>
                  <div className="analysis-grid">
                    {analysis.summary ? (
                      <div>
                        <h3>Job summary</h3>
                        <p>{analysis.summary}</p>
                      </div>
                    ) : null}
                    {analysis.experience_level || analysis.location || analysis.education.length ? (
                      <div>
                      <h3>Context</h3>
                      <dl className="definition-list">
                        {analysis.experience_level ? <div><dt>Experience level</dt><dd>{analysis.experience_level}</dd></div> : null}
                        {analysis.location ? <div><dt>Location</dt><dd>{analysis.location}</dd></div> : null}
                        {analysis.education.length ? <div><dt>Education</dt><dd>{analysis.education.join(', ')}</dd></div> : null}
                      </dl>
                      </div>
                    ) : null}
                  </div>

                  <div className="pill-columns">
                    <PillGroup label="Required skills" items={analysis.required_skills} />
                    <PillGroup label="Preferred skills" items={analysis.preferred_skills} />
                    <PillGroup label="Responsibilities" items={analysis.responsibilities} />
                  </div>

                  {analysis.missing_requirements.length ? <PillGroup label="Missing requirements" items={analysis.missing_requirements} /> : null}
                </>
              ) : (
                <p className="empty-state">Run the workflow to render grounded analysis.</p>
              )}
            </div>
          </details>

          <details open={sectionOpen.match} onToggle={(event) => setSectionState('match', event.currentTarget.open)}>
            <summary>
              <span>Match Breakdown</span>
              <strong>{primaryMatch ? 'ready' : 'Waiting'}</strong>
            </summary>
            <div className="section-body">
              {primaryMatch ? (
                <>
                  <div className="match-snapshot" aria-label="Match summary">
                    <span>
                      <strong>{primaryMatch.matched_requirements.length}</strong>
                      Matched
                    </span>
                    <span>
                      <strong>{primaryMatch.partial_matches.length}</strong>
                      Partial
                    </span>
                    <span>
                      <strong>{primaryMatch.missing_requirements.length}</strong>
                      Missing
                    </span>
                    <span>
                      <strong>{primaryMatch.critical_gaps.length}</strong>
                      Critical gaps
                    </span>
                  </div>

                  {primaryMatch.critical_gaps.length ? (
                    <div className="critical-gaps">
                      <h3>Critical gaps</h3>
                      <ul>{primaryMatch.critical_gaps.map((gap) => <li key={gap}>{gap}</li>)}</ul>
                    </div>
                  ) : null}

                  <details className="nested-details">
                    <summary>View all requirements ({primaryMatch.requirement_results.length})</summary>
                    <div className="requirement-table compact">
                      {primaryMatch.requirement_results.map((item) => (
                        <article key={item.requirement} className="requirement-row">
                          <div>
                            <strong>{item.requirement}</strong>
                            <p>{item.requirement_type} · {item.importance}</p>
                          </div>
                          <span className={`status-chip ${item.status}`}>{statusLabel(item.status)}</span>
                        </article>
                      ))}
                    </div>
                  </details>
                </>
              ) : (
                <p className="empty-state">The backend match result appears here after analysis completes.</p>
              )}
            </div>
          </details>

          <details open={sectionOpen.evidence} onToggle={(event) => setSectionState('evidence', event.currentTarget.open)}>
            <summary>
              <span>Evidence</span>
              <strong>{approvedClaims.length ? `${approvedClaims.length} claims` : 'Waiting'}</strong>
            </summary>
            <div className="section-body">
              {approvedClaims.length ? (
                <div className="evidence-list">
                  {approvedClaims.map((claim) => (
                    <details key={`${claim.claim}|${claim.evidence_source}`} className="evidence-item">
                      <summary>
                        <span>
                          <strong>{claim.claim}</strong>
                          <em>{claim.claim_type}</em>
                        </span>
                        <strong>{claim.evidence_source}</strong>
                      </summary>
                      <div className="evidence-details">
                        <p className="source-path">Source: {claim.evidence_source}</p>
                        <blockquote>{claim.evidence_excerpt}</blockquote>
                      </div>
                    </details>
                  ))}
                </div>
              ) : (
                <p className="empty-state">Only approved claims are shown here.</p>
              )}
            </div>
          </details>

          <details open={sectionOpen.cover} onToggle={(event) => setSectionState('cover', event.currentTarget.open)}>
            <summary>
              <span>Cover Letter</span>
              <strong>{coverLetterResponse ? 'ready' : 'Waiting'}</strong>
            </summary>
            <div className="section-body">
              {coverLetterResponse ? (
                <>
                  <div className="cover-letter-toolbar">
                    <p className="summary-line">{coverLetterResponse.relevant_match_summary}</p>
                    <button type="button" className="secondary-button" onClick={copyCoverLetter}>
                      Copy letter
                    </button>
                  </div>
                  <pre className="letter-block">{coverLetterResponse.cover_letter}</pre>
                  {coverLetterResponse.grounding_warnings.length ? (
                    <details className="nested-details excluded-claims">
                      <summary>Why were some claims excluded?</summary>
                      <ul className="warning-list">
                        {coverLetterResponse.grounding_warnings.map((warning) => <li key={warning}>{warning}</li>)}
                      </ul>
                    </details>
                  ) : null}
                </>
              ) : (
                <p className="empty-state">The grounded cover letter appears here after the pipeline finishes.</p>
              )}
            </div>
          </details>

          <details open={sectionOpen.trace} onToggle={(event) => setSectionState('trace', event.currentTarget.open)}>
            <summary>
              <span>Agent Execution Trace</span>
              <strong>{traces.length ? `${traces.length} runs` : 'Waiting'}</strong>
            </summary>
            <div className="section-body">
              {traces.length ? (
                <div className="trace-stack">
                  {traces.map((item) => (
                    <article key={`${item.label}-${item.trace.operation_id}`} className="trace-card">
                      <header className="trace-card-header">
                        <div>
                          <span className="panel-kicker">{item.label}</span>
                          <h3>{item.trace.operation}</h3>
                        </div>
                        <div className={`status-chip ${item.trace.status}`}>{statusLabel(item.trace.status)}</div>
                      </header>
                      <div className="trace-meta">
                        <span>run_id: {item.trace.run_id}</span>
                        <span>operation_id: {item.trace.operation_id}</span>
                      </div>
                      <div className="trace-events">
                        {item.trace.events.map((event, eventIndex) => (
                          <div key={`${item.trace.operation_id}-${event.step}-${eventIndex}`} className="trace-event">
                            <div>
                              <strong>{event.step}</strong>
                              <p>{event.detail ?? 'Completed successfully'}</p>
                            </div>
                            <div className="trace-event-meta">
                              <span className={`status-chip ${event.status}`}>{event.status}</span>
                              <span>{formatDuration(event.duration_ms)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="empty-state">The UI shows real backend execution trace after a run completes.</p>
              )}
            </div>
          </details>
        </section>
      </main>
    </div>
  );
}

function PillGroup({ label, items }: { label: string; items: string[] }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="pill-group">
      <h3>{label}</h3>
      <div className="pill-list">
        {items.map((item) => <span key={item}>{item}</span>)}
      </div>
    </div>
  );
}
