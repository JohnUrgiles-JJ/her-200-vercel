import { Eyebrow, Avatar, Icon } from "./ui";
import { events, mentors } from "./data";

export default function RightRail() {
  return (
    <aside className="sticky top-0 hidden h-screen w-80 shrink-0 overflow-y-auto border-l border-border bg-surface-muted px-7 py-10 xl:block">
      <Eyebrow>People to know</Eyebrow>
      <div className="mt-1 flex items-baseline justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Mentors for you</h2>
        <a href="/main/my-mentors" className="text-sm font-medium text-primary">See all</a>
      </div>
      <ul className="mt-6 space-y-5 border-b border-border pb-8">
        {mentors.map((m) => (
          <li key={m.name} className="flex items-center gap-3">
            <Avatar initials={m.initials} />
            <div className="flex-1">
              <p className="font-medium">{m.name}</p>
              <p className="text-xs text-muted">{m.role} · {m.company}</p>
              <p className="mt-1 text-xs font-semibold text-primary">{m.match}% match</p>
            </div>
            <button aria-label={`Follow ${m.name}`} className="flex h-10 w-10 items-center justify-center rounded border border-border-strong bg-surface hover:bg-surface-sunken">
              <Icon name="plus" className="h-4 w-4" />
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-8">
        <Eyebrow>Save the date</Eyebrow>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight">Happening soon</h2>
        <ul className="mt-6 space-y-4 border-b border-border pb-8">
          {events.map((e, i) => (
            <li key={e.title} className="flex items-center gap-4">
              <span className={`flex h-16 w-14 shrink-0 flex-col items-center justify-center rounded ${i === 0 ? "bg-primary text-on-primary" : "bg-secondary/20 text-secondary"}`}>
                <span className="text-lg font-semibold leading-none">{e.day}</span>
                <span className="mt-1 text-[10px] font-semibold">{e.month}</span>
              </span>
              <div>
                <p className="font-medium">{e.title}</p>
                <p className="text-xs text-muted">{e.meta}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
