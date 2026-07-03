import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../api/client";
import Sidebar from "../components/Sidebar";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);

  async function fetchProjects() {
    try {
      const res = await client.get("/projects");
      setProjects(res.data.items);
    } catch {
      setError("Could not load projects.");
    }
  }

  useEffect(() => {
    fetchProjects();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await client.post("/projects", { name });
      setName("");
      fetchProjects();
    } catch {
      setError("Could not create project.");
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8">
        <h2 className="text-lg font-semibold mb-6">Projects</h2>

        <form onSubmit={handleCreate} className="flex gap-2 mb-6">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New project name"
            className="px-3 py-2 rounded bg-surface border border-border text-sm w-64 focus:outline-none focus:border-teal"
          />
          <button className="px-4 py-2 rounded bg-teal text-graphite text-sm font-medium">
            Create
          </button>
        </form>

        {error && <p className="text-danger text-sm mb-4">{error}</p>}

        <div className="border border-border rounded-lg bg-surface">
          {projects.length === 0 ? (
            <p className="p-4 text-sm text-muted">No projects yet. Create one above.</p>
          ) : (
            projects.map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="flex justify-between px-4 py-3 border-b border-border last:border-0 hover:bg-graphite text-sm"
              >
                <span>{p.name}</span>
                <span className="text-muted font-mono text-xs">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
              </Link>
            ))
          )}
        </div>
      </main>
    </div>
  );
}