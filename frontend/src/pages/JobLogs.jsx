import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import client from "../api/client";
import Sidebar from "../components/Sidebar";

export default function JobLogs() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project_id");
  const queueId = searchParams.get("queue_id");

  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchJob() {
      try {
        const res = await client.get(
          `/projects/${projectId}/queues/${queueId}/jobs/${jobId}`
        );
        setJob(res.data);
      } catch {
        setError("Could not load job.");
      }
    }
    fetchJob();
    const interval = setInterval(fetchJob, 5000);
    return () => clearInterval(interval);
  }, [jobId, projectId, queueId]);

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link to={`/queues/${queueId}?project_id=${projectId}`} className="text-xs text-muted hover:text-teal">
          ← Back to jobs
        </Link>
        <h2 className="text-lg font-semibold mt-2 mb-6">Job Detail</h2>

        {error && <p className="text-danger text-sm mb-4">{error}</p>}

        {job && (
          <div className="border border-border rounded-lg bg-surface p-4 text-sm space-y-2">
            <p><span className="text-muted">ID:</span> <span className="font-mono">{job.id}</span></p>
            <p><span className="text-muted">Type:</span> {job.job_type}</p>
            <p><span className="text-muted">Status:</span> {job.status}</p>
            <p><span className="text-muted">Attempts:</span> {job.attempt_count}</p>
            <p><span className="text-muted">Run at:</span> {new Date(job.run_at).toLocaleString()}</p>
            <p><span className="text-muted">Payload:</span></p>
            <pre className="bg-graphite border border-border rounded p-3 font-mono text-xs overflow-x-auto">
              {JSON.stringify(job.payload, null, 2)}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}