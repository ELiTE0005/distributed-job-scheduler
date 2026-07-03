import { useEffect, useState } from "react";
import client from "../api/client";
import Sidebar from "../components/Sidebar";
import StatusDot from "../components/StatusDot";

const POLL_MS = 5000;

export default function Workers() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    async function fetchStats() {
      const res = await client.get("/dashboard/stats");
      setStats(res.data);
    }
    fetchStats();
    const interval = setInterval(fetchStats, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8">
        <h2 className="text-lg font-semibold mb-6">Workers</h2>

        <div className="border border-border rounded-lg bg-surface">
          {!stats || stats.workers.length === 0 ? (
            <p className="p-4 text-sm text-muted">No workers registered yet.</p>
          ) : (
            stats.workers.map((w) => (
              <div
                key={w.id}
                className="flex justify-between items-center px-4 py-3 border-b border-border last:border-0 text-sm"
              >
                <div className="flex items-center gap-3">
                  <StatusDot status={w.status} />
                  {w.hostname}
                </div>
                <span className="text-muted font-mono text-xs">
                  last seen {new Date(w.last_seen_at).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}