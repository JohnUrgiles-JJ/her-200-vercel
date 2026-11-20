import Sidebar from "./_components/Sidebar";
import RightRail from "./_components/RightRail";
import { Icon } from "./_components/ui";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex items-center gap-4 border-b border-border bg-surface px-8 py-4">
          <label className="flex max-w-xl flex-1 items-center gap-3 rounded border border-border bg-surface px-4 py-3">
            <Icon name="search" className="h-5 w-5 text-subtle" />
            <input placeholder="Search people, topics, or questions" className="flex-1 bg-transparent text-sm outline-none placeholder:text-subtle" />
            <kbd className="rounded border border-border px-1.5 py-0.5 text-xs text-subtle">⌘ K</kbd>
          </label>
          <a href="/main#ask" className="ml-auto flex items-center gap-2 rounded bg-foreground px-5 py-3 font-medium text-background hover:opacity-90">
            <Icon name="plus" className="h-5 w-5" /> Ask a question
          </a>
        </header>
        <main className="mx-auto w-full max-w-4xl flex-1 px-8 py-12">{children}</main>
      </div>
      <RightRail />
    </div>
  );
}
