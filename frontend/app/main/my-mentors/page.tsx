import { Avatar, PageHeader } from "../_components/ui";
import { mentors } from "../_components/data";

export default function MyMentorsPage() {
  return (
    <>
      <PageHeader eyebrow="Your network" title="My mentors" subtitle="Mentors you follow and have been matched with" />
      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        {mentors.map((m) => (
          <div key={m.name} className="rounded border border-border bg-surface p-6">
            <div className="flex items-center gap-4">
              <Avatar initials={m.initials} />
              <div>
                <p className="font-semibold">{m.name}</p>
                <p className="text-sm text-muted">{m.role} · {m.company}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {m.fields.map((f) => (
                <span key={f} className="rounded bg-surface-muted px-2.5 py-1 text-xs text-muted">{f}</span>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between">
              <span className="text-sm font-semibold text-primary">{m.match}% match</span>
              <a href="/main/messages" className="rounded border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-muted">Message</a>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
