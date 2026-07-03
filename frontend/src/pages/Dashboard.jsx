import { useEffect, useState } from "react";
import client from "../api/client";
import Sidebar from "../components/Sidebar";
import StatusDot from "../components/StatusDot";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const POLL_MS = 5000;

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let interval;

    async function fetchStats() {
      try {
        const res = await client.get("/dashboard/stats");
        setStats(res.data);
        setError(null);
      } catch {
        setError("Could not reach the scheduler API.");
      }
    }

    fetchStats();
    interval = setInterval(fetchStats, POLL_MS);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex">
      <Sidebar />

      <main className="flex-1 p-8">
        <h2 className="text-lg font-semibold mb-6">Dashboard</h2>

        {error && (
          <p className="text-danger text-sm mb-4">
            {error}
          </p>
        )}

        {!stats ? (
          <p className="text-muted text-sm">Loading...</p>
        ) : (
          <>
            {/* Job Status Cards */}
            <div className="grid grid-cols-5 gap-3 mb-8">
              {Object.entries(stats.job_status_counts).map(
                ([status, count]) => (
                  <div
                    key={status}
                    className="border border-border rounded-lg bg-surface p-4"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <StatusDot status={status} />
                      <span className="text-xs text-muted uppercase tracking-wide">
                        {status.replace("_", " ")}
                      </span>
                    </div>

                    <p className="text-2xl font-mono">
                      {count}
                    </p>
                  </div>
                )
              )}
            </div>

            {/* Pie Chart */}
            <div className="border border-border rounded-lg bg-surface p-4 mb-8">
              <h3 className="text-sm font-medium mb-3">
                Job Status Distribution
              </h3>

              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={Object.entries(stats.job_status_counts).map(
                      ([name, value]) => ({
                        name,
                        value,
                      })
                    )}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={80}
                  >
                    {[
                      "#D9A441",
                      "#4F9D94",
                      "#5C6165",
                      "#C96A5A",
                      "#C96A5A",
                    ].map((color, i) => (
                      <Cell
                        key={i}
                        fill={color}
                        stroke="#1A1C1F"
                      />
                    ))}
                  </Pie>

                  <Tooltip
                    contentStyle={{
                      background: "#232629",
                      border: "1px solid #33373B",
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Queues & Workers */}
            <div className="grid grid-cols-2 gap-6">
              {/* Queues */}
              <div className="border border-border rounded-lg bg-surface p-4">
                <h3 className="text-sm font-medium mb-3">
                  Queues
                </h3>

                {stats.queues.length === 0 ? (
                  <p className="text-sm text-muted">
                    No queues yet.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <tbody>
                      {stats.queues.map((q) => (
                        <tr
                          key={q.id}
                          className="border-t border-border"
                        >
                          <td className="py-2">
                            {q.name}
                          </td>

                          <td className="py-2 text-muted">
                            {q.is_paused
                              ? "Paused"
                              : "Active"}
                          </td>

                          <td className="py-2 font-mono text-right">
                            {q.pending_jobs} pending
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Workers */}
              <div className="border border-border rounded-lg bg-surface p-4">
                <h3 className="text-sm font-medium mb-3">
                  Workers
                </h3>

                {stats.workers.length === 0 ? (
                  <p className="text-sm text-muted">
                    No workers registered.
                  </p>
                ) : (
                  <table className="w-full text-sm">
                    <tbody>
                      {stats.workers.map((w) => (
                        <tr
                          key={w.id}
                          className="border-t border-border"
                        >
                          <td className="py-2 flex items-center gap-2">
                            <StatusDot status={w.status} />
                            {w.hostname}
                          </td>

                          <td className="py-2 text-muted text-right">
                            {w.status}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}