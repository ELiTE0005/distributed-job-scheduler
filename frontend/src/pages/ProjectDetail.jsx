import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import client from "../api/client";
import Sidebar from "../components/Sidebar";

export default function ProjectDetail() {
  const { projectId } = useParams();
  const [queues, setQueues] = useState([]);
  const [name, setName] = useState("");
  const [concurrency, setConcurrency] = useState(5);
  const [error, setError] = useState(null);

  async function fetchQueues() {
    try {
      const res = await client.get(`/projects/${projectId}/queues`);
      setQueues(res.data.items);
    } catch {
      setError("Could not load queues.");
    }
  }

  useEffect(() => {
    fetchQueues();
  }, [projectId]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await client.post(`/projects/${projectId}/queues`, {
        name,
        max_concurrency: Number(concurrency),
      });
      setName("");
      fetchQueues();
    } catch {
      setError("Could not create queue (name may already exist).");
    }
  }

  async function togglePause(queue) {
    await client.patch(`/projects/${projectId}/queues/${queue.id}`, {
      is_paused: !queue.is_paused,
    });
    fetchQueues();
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8">
        <Link to="/projects" className="text-xs text-muted hover:text-teal">
          ← Projects
        </Link>
        <h2 className="text-lg font-semibold mt-2 mb-6">Queues</h2>

        <form onSubmit={handleCreate} className="flex gap-2 mb-6">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Queue name"
            className="px-3 py-2 rounded bg-surface border border-border text-sm w-52 focus:outline-none focus:border-teal"
          />
          <input
            type="number"
            value={concurrency}
            onChange={(e) => setConcurrency(e.target.value)}
            min="1"
            max="100"
            className="px-3 py-2 rounded bg-surface border border-border text-sm w-28 focus:outline-none focus:border-teal"
          />
          <button className="px-4 py-2 rounded bg-teal text-graphite text-sm font-medium">
            Create
          </button>
        </form>

        {error && <p className="text-danger text-sm mb-4">{error}</p>}

        <div className="border border-border rounded-lg bg-surface">
          {queues.length === 0 ? (
            <p className="p-4 text-sm text-muted">No queues yet. Create one above.</p>
          ) : (
            queues.map((q) => (
              <div
                key={q.id}
                className="flex justify-between items-center px-4 py-3 border-b border-border last:border-0 text-sm"
              >
                <Link to={`/queues/${q.id}?project_id=${projectId}`} className="hover:text-teal">
                  {q.name}
                </Link>
                <div className="flex items-center gap-4">
                  <span className="text-muted font-mono text-xs">
                    concurrency: {q.max_concurrency}
                  </span>
                  <button
                    onClick={() => togglePause(q)}
                    className={`px-3 py-1 rounded text-xs ${
                      q.is_paused ? "bg-amber text-graphite" : "bg-graphite text-muted border border-border"
                    }`}
                  >
                    {q.is_paused ? "Paused — Resume" : "Pause"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}