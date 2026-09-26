import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <div className="rounded-full bg-surface-yellow px-3 py-1 text-[13px] font-semibold text-yellow-dark">404</div>
      <h1 className="text-[36px] tracking-[-0.5px]">Page not found</h1>
      <p className="max-w-md text-slate">That page doesn't exist. It may have moved when the dashboard was rebuilt.</p>
      <Link to="/" className="inline-flex min-h-10 items-center rounded-full bg-ink px-5 text-[14px] font-medium text-white hover:bg-charcoal">
        Back to overview
      </Link>
    </div>
  );
}
