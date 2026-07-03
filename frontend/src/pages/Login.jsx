import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid email or password.");
    }
  }

  return (
    <div className="h-screen flex items-center justify-center bg-graphite">
      <form
        onSubmit={handleSubmit}
        className="w-80 border border-border rounded-lg bg-surface p-6"
      >
        <h1 className="text-base font-semibold mb-1">Sign in</h1>
        <p className="text-sm text-muted mb-5">Distributed Job Scheduler</p>

        <label className="block text-xs text-muted mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-3 px-3 py-2 rounded bg-graphite border border-border text-sm focus:outline-none focus:border-teal"
          required
        />

        <label className="block text-xs text-muted mb-1">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded bg-graphite border border-border text-sm focus:outline-none focus:border-teal"
          required
        />

        {error && <p className="text-sm text-danger mb-3">{error}</p>}

        <button
          type="submit"
          className="w-full py-2 rounded bg-teal text-graphite text-sm font-medium hover:opacity-90"
        >
          Sign in
        </button>
      </form>
    </div>
  );
}