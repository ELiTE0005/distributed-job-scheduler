import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";




const links = [
  { to: "/", label: "Dashboard" },
  { to: "/projects", label: "Projects" },
  { to: "/workers", label: "Workers" },
  { to: "/dead-letter", label: "Dead Letter Queue" },
];

export default function Sidebar() {
  const { logout } = useAuth();

  return (
    <aside className="w-56 shrink-0 border-r border-border bg-surface h-screen flex flex-col justify-between">
      <div>
        <div className="px-5 py-5 border-b border-border">
          <h1 className="text-sm font-semibold tracking-wide">JOB SCHEDULER</h1>
        </div>
        <nav className="mt-4 flex flex-col gap-1 px-2">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `px-3 py-2 rounded text-sm ${
                  isActive ? "bg-graphite text-teal" : "text-muted hover:text-[#E4E6E8]"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <button
        onClick={logout}
        className="mx-4 mb-5 text-sm text-muted hover:text-danger text-left"
      >
        Sign out
      </button>
    </aside>
  );
}