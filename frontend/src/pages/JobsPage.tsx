import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { JobSummary } from "./DashboardPage";

const JOBS_STORAGE_KEY = "ai-debugger-jobs";

export function JobsPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(JOBS_STORAGE_KEY);
      const parsed: JobSummary[] = raw ? JSON.parse(raw) : [];
      setJobs(parsed);
    } catch {
      setJobs([]);
    }
  }, []);

  return (
    <div className="card">
      <h1>Jobs</h1>
      {!jobs.length && <p className="muted">No jobs yet. Create one from the dashboard.</p>}
      {jobs.length > 0 && (
        <table className="jobs-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Repository</th>
              <th>Task</th>
              <th>Branch</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map(job => (
              <tr key={job.id}>
                <td>
                  <Link to={`/jobs/${encodeURIComponent(job.id)}`}>{job.id}</Link>
                </td>
                <td>{job.repoUrl}</td>
                <td>{job.taskType}</td>
                <td>{job.branch}</td>
                <td>{new Date(job.createdAt).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

