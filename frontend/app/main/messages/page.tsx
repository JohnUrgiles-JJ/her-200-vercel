import { Avatar, PageHeader } from "../_components/ui";
import { conversations } from "../_components/data";

export default function MessagesPage() {
  const active = conversations[0];
  return (
    <>
      <PageHeader eyebrow="Inbox" title="Messages" subtitle="Conversations with your mentors" />
      <div className="mt-10 grid overflow-hidden rounded border border-border bg-surface md:grid-cols-[18rem_1fr]">
        <ul className="border-b border-border md:border-b-0 md:border-r">
          {conversations.map((c, i) => (
            <li key={c.name} className={`flex items-center gap-3 border-b border-border p-4 last:border-b-0 ${i === 0 ? "bg-surface-muted" : "hover:bg-surface-muted"}`}>
              <Avatar initials={c.initials} size="sm" />
              <div className="min-w-0 flex-1">
                <div className="flex justify-between gap-2">
                  <p className={c.unread ? "font-semibold" : "font-medium"}>{c.name}</p>
                  <span className="text-xs text-subtle">{c.time}</span>
                </div>
                <p className="truncate text-sm text-muted">{c.preview}</p>
              </div>
            </li>
          ))}
        </ul>
        <div className="flex min-h-96 flex-col">
          <div className="flex items-center gap-3 border-b border-border p-4">
            <Avatar initials={active.initials} size="sm" />
            <p className="font-medium">{active.name}</p>
          </div>
          <div className="flex-1 space-y-3 p-6">
            <p className="max-w-sm rounded-lg bg-surface-muted p-3 text-sm">{active.preview}</p>
            <p className="ml-auto max-w-sm rounded-lg bg-primary p-3 text-sm text-on-primary">Thank you! I&apos;ll send it over tonight.</p>
          </div>
          <form className="flex gap-3 border-t border-border p-4">
            <input placeholder="Write a message…" className="flex-1 rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
            <button className="rounded bg-primary px-4 text-sm font-medium text-on-primary hover:bg-primary-hover">Send</button>
          </form>
        </div>
      </div>
    </>
  );
}
