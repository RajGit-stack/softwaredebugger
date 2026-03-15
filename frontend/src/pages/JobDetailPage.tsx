import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { JobSummary } from "./DashboardPage";

const JOBS_STORAGE_KEY = "ai-debugger-jobs";

export function JobDetailPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState<JobSummary | null>(null);

  useEffect(() => {
    if (!jobId) return;
    try {
      const raw = localStorage.getItem(JOBS_STORAGE_KEY);
      const parsed: JobSummary[] = raw ? JSON.parse(raw) : [];
      const found = parsed.find(j => j.id === jobId) ?? null;
      setJob(found);
    } catch {
      setJob(null);
    }
  }, [jobId]);

  return (
    <div className="card">
      <h1>Job {jobId}</h1>
      {!job && <p className="muted">Job details not found in this browser.</p>}
      {job && (
        <>
          <p className="muted">
            Created at {new Date(job.createdAt).toLocaleString()} for repository <code>{job.repoUrl}</code> on branch{" "}
            <code>{job.branch}</code>.
          </p>
          <p className="muted">
            Task type: <code>{job.taskType}</code>
          </p>
          {job.description && (
            <p className="muted">
              Description: <br />
              {job.description}
            </p>
          )}
          {job.customQuestion && (
            <p className="muted">
              Custom question: <br />
              {job.customQuestion}
            </p>
          )}
          {job.result && (
            <div className="analysis-panel">
              <h2>Result</h2>
              <pre>{job.result}</pre>
            </div>
          )}
          {job.taskType === "repo_analyser" && job.architectureSummary && (
            <div className="analysis-panel">
              <h2>Repo architecture overview</h2>
              <pre>{job.architectureSummary}</pre>
            </div>
          )}
          {job.taskType === "repo_analyser" && job.architectureDiagram && (
            <div className="analysis-panel">
              <h2>High-level architecture diagram</h2>
              <pre>{job.architectureDiagram}</pre>
            </div>
          )}
          {job.customQuestion && job.customAnswer && (
            <div className="analysis-panel">
              <h2>Answer to your question</h2>
              <pre>{job.customAnswer}</pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}

