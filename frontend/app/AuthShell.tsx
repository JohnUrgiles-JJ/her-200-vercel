import Link from "next/link";

export default function AuthShell({ title, subtitle, children }: { title: string; subtitle: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col items-center bg-zinc-50 px-6 py-12 font-sans dark:bg-black">
      <Link href="/" className="text-xl font-bold tracking-tight">
        Connect<span className="text-fuchsia-600">HER</span>
      </Link>
      <div className="mt-8 w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-8 dark:border-zinc-800 dark:bg-zinc-950">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{subtitle}</p>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

export const inputClass =
  "mt-1 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-fuchsia-600 focus:ring-1 focus:ring-fuchsia-600 dark:border-zinc-700 dark:bg-zinc-900";
export const labelClass = "block text-sm font-medium";
export const buttonClass =
  "flex h-11 w-full items-center justify-center rounded-full bg-fuchsia-600 font-medium text-white hover:bg-fuchsia-700 disabled:opacity-60";
