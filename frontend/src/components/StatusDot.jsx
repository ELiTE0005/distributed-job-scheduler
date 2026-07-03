// The one recurring visual signature across the whole app: a colored dot
// encoding job/worker state, used consistently on Dashboard, Jobs, and
// Workers pages so the operator learns one visual language, not several.
const COLORS = {
  pending: "bg-amber",
  running: "bg-teal",
  completed: "bg-[#5C6165]",
  failed: "bg-danger",
  dead_letter: "bg-danger",
  idle: "bg-[#5C6165]",
  busy: "bg-teal",
  offline: "bg-[#3D4145]",
};

export default function StatusDot({ status }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${COLORS[status] || "bg-muted"}`} />
  );
}