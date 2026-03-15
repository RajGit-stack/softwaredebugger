import { useState } from "react";
import axios from "axios";

type TaskType = "repo_analyser" | "bug_fixer" | "test_generator" | "doc_generator" | "code_search";

export type JobSummary = {
  id: string;
  repoUrl: string;
  taskType: TaskType;
  branch: string;
  description: string;
  createdAt: string;
  result: string;
  qualityScore: number;
  architectureSummary: string;
  architectureDiagram: string;
  customQuestion: string;
  customAnswer: string;
};

const JOBS_STORAGE_KEY = "ai-debugger-jobs";

function appendJobToStorage(job: JobSummary) {
  try {
    const raw = localStorage.getItem(JOBS_STORAGE_KEY);
    const existing: JobSummary[] = raw ? JSON.parse(raw) : [];
    localStorage.setItem(JOBS_STORAGE_KEY, JSON.stringify([job, ...existing]));
  } catch {
    // ignore storage errors
  }
}

export function DashboardPage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [taskType, setTaskType] = useState<TaskType>("repo_analyser");
  const [branch, setBranch] = useState("main");
  const [description, setDescription] = useState("");
  const [customQuestion, setCustomQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [architectureSummary, setArchitectureSummary] = useState<string | null>(null);
  const [architectureDiagram, setArchitectureDiagram] = useState<string | null>(null);
  const [customAnswer, setCustomAnswer] = useState<string | null>(null);

  const baseUrl = import.meta.env.VITE_AGENT_API_URL || "http://localhost:9000";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setArchitectureSummary(null);
    setArchitectureDiagram(null);
    setCustomAnswer(null);
    setLoading(true);
    try {
      const res = await axios.post(`${baseUrl}/tasks`, {
        repo_url: repoUrl,
        task_type: taskType,
        branch,
        description,
        custom_question: customQuestion
      });
      const newJobId: string = res.data.job_id;
      const jobResult: string = res.data.result;
      const qualityScore: number = res.data.quality_score;
      const archSummary: string = res.data.architecture_summary;
      const archDiagram: string = res.data.architecture_diagram;
      const qa: string = res.data.custom_answer;
      setJobId(newJobId);
      setResult(jobResult);
      setArchitectureSummary(archSummary || null);
      setArchitectureDiagram(archDiagram || null);
      setCustomAnswer(qa || null);

      appendJobToStorage({
        id: newJobId,
        repoUrl,
        taskType,
        branch,
        description,
        createdAt: new Date().toISOString(),
        result: jobResult,
        qualityScore,
        architectureSummary: archSummary,
        architectureDiagram: archDiagram,
        customQuestion,
        customAnswer: qa
      });
    } catch (err: any) {
      setError(err?.response?.data?.message ?? "Failed to create task");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h1>Create a debugging job</h1>
      <p className="muted">
        Point the agent at a GitHub repo and choose what you want it to do. The LangGraph supervisor will route to the right
        specialist.
      </p>
      <form onSubmit={handleSubmit} className="form">
        <label>
          <span>
            GitHub repository URL <span aria-hidden="true">*</span>
          </span>
          <input
            type="url"
            placeholder="https://github.com/owner/repo"
            value={repoUrl}
            onChange={e => setRepoUrl(e.target.value)}
            required
          />
        </label>

        <label>
          <span>
            Branch <span aria-hidden="true">*</span>
          </span>
          <input value={branch} onChange={e => setBranch(e.target.value)} required />
        </label>

        <label>
          <span>
            Task type <span aria-hidden="true">*</span>
          </span>
          <select value={taskType} onChange={e => setTaskType(e.target.value as TaskType)}>
            <option value="repo_analyser">Repo architecture overview</option>
            <option value="bug_fixer">Bug fixing</option>
            <option value="test_generator">Test generation</option>
            <option value="doc_generator">Documentation generation</option>
            <option value="code_search">AI code search</option>
          </select>
        </label>

        <label>
          <span>
            {taskType === "code_search"
              ? (
                <>
                  What do you want to search in this repo? <span aria-hidden="true">*</span>
                </>
                )
              : (
                <>
                  Task description <span aria-hidden="true">*</span>
                </>
                )}
          </span>
          <textarea
            rows={4}
            placeholder={
              taskType === "code_search"
                ? "e.g. 'payment webhook handler', 'UserService class', 'JWT middleware'"
                : "e.g. Analyse flaky tests in CI and propose fixes."
            }
            value={description}
            onChange={e => setDescription(e.target.value)}
            required={taskType === "code_search"}
          />
        </label>

        <label>
          <span>Custom question (optional)</span>
          <textarea
            rows={3}
            placeholder="Ask anything about this repo, e.g. 'Explain the login flow' or 'How does the scheduler work?'"
            value={customQuestion}
            onChange={e => setCustomQuestion(e.target.value)}
          />
        </label>

        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Creating…" : "Create job"}
        </button>

        {error && <p className="error">{error}</p>}
        {jobId && (
          <p className="success">
            Job created with id <code>{jobId}</code>. Check the Jobs tab to follow progress.
          </p>
        )}
        {result && (
          <div className="analysis-panel">
            <h2>Result preview</h2>
            <pre>{result}</pre>
          </div>
        )}
        {taskType === "repo_analyser" && architectureSummary && (
          <div className="analysis-panel">
            <h2>Repo architecture overview</h2>
            <pre>{architectureSummary}</pre>
          </div>
        )}
        {taskType === "repo_analyser" && architectureDiagram && (
          <div className="analysis-panel">
            <h2>High-level architecture diagram</h2>
            <pre>{architectureDiagram}</pre>
          </div>
        )}
        {customQuestion && customAnswer && (
          <div className="analysis-panel">
            <h2>Answer to your question</h2>
            <pre>{customAnswer}</pre>
          </div>
        )}
      </form>
    </div>
  );
}

