import Link from "next/link";

export default function AuthShell({ title, subtitle, children }: { title: string; subtitle: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center bg-surface-muted px-6 py-12 font-sans">
      <Link href="/" className="text-xl font-bold tracking-tight">
        Connect<span className="text-primary">HER</span>
      </Link>
      <div className="mt-8 w-full max-w-lg rounded-2xl border border-border bg-surface p-8">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-muted">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

export const inputClass =
  "mt-1 w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary";
export const labelClass = "block text-sm font-medium";
export const buttonClass =
  "flex h-11 w-full items-center justify-center rounded-full bg-primary font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60";
