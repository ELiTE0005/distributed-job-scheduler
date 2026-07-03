import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import client from "../api/client";
import Sidebar from "../components/Sidebar";
import StatusDot from "../components/StatusDot";

const POLL_MS = 5000;

export default function QueueDetail() {
  // NOTE: queueId alone isn't enough to hit the nested API route, which
  // needs project_id too. Passed via query string from ProjectDetail's
  // link (?project_id=...) to avoid an extra lookup call here.
  const { queueId } = useParams();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project_id");

  const [jobs, setJobs] = useState([]);
  const [payload, setPayload] = useState('{"task": "example"}');
  const [jobType, setJobType] = useState("immediate");
  const [error, setError] = useState(null);

  async function fetchJobs() {
    try {
      const res = await client.get(`/projects/${projectId}/queues/${queueId}/jobs`);
      setJobs(res.data.items);
    } catch {
      setError("Could not load jobs.");
    }
  }

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, POLL_MS);
    return () => clearInterval(interval);
  }, [queueId, projectId]);

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const parsed = JSON.parse(payload);
      await client.post(`/projects/${projectId}/queues/${queueId}/jobs`, {
        job_type: jobType,
        payload: parsed,
        priority: 0,
      });
      fetchJobs();
    } catch {
      setError("Invalid JSON payload or request failed.");
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8">
        <h2 className="text-lg font-semibold mb-6">Jobs</h2>

        <form onSubmit={handleCreate} className="flex gap-2 mb-6">
          <select
            value={jobType}
            onChange={(e) => setJobType(e.target.value)}
            className="px-3 py-2 rounded bg-surface border border-border text-sm"
          >
            <option value="immediate">immediate</option>
            <option value="delayed">delayed</option>
          </select>
          <input
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            className="px-3 py-2 rounded bg-surface border border-border text-sm w-72 font-mono focus:outline-none focus:border-teal"
          />
          <button className="px-4 py-2 rounded bg-teal text-graphite text-sm font-medium">
            Submit Job
          </button>
        </form>

        {error && <p className="text-danger text-sm mb-4">{error}</p>}

        <div className="border border-border rounded-lg bg-surface">
          {jobs.length === 0 ? (
            <p className="p-4 text-sm text-muted">No jobs yet.</p>
          ) : (
            jobs.map((j) => (
              <div
                key={j.id}
                className="flex justify-between items-center px-4 py-3 border-b border-border last:border-0 text-sm"
              >
                <div className="flex items-center gap-3">
                  <StatusDot status={j.status} />
                  <span className="font-mono text-xs text-muted">{j.id.slice(0, 8)}</span>
                  <span>{j.job_type}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-muted">
                  <span>attempt {j.attempt_count}</span>
                  <span className="font-mono">{j.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}