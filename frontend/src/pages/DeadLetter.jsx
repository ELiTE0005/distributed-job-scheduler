import { useEffect, useState } from "react";
import client from "../api/client";
import Sidebar from "../components/Sidebar";

const POLL_MS = 5000;

export default function DeadLetter() {
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
        <h2 className="text-lg font-semibold mb-2">Dead Letter Queue</h2>
        <p className="text-sm text-muted mb-6">
          Jobs that exhausted all retry attempts and require manual review.
        </p>

        <div className="border border-border rounded-lg bg-surface p-6">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-danger" />
            <span className="text-2xl font-mono">{stats?.dead_letter_count ?? "—"}</span>
            <span className="text-sm text-muted">jobs in dead letter queue</span>
          </div>
        </div>
      </main>
    </div>
  );
}