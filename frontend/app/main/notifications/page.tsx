import { Avatar, PageHeader } from "../_components/ui";
import { notifications } from "../_components/data";

export default function NotificationsPage() {
  return (
    <>
      <PageHeader eyebrow="Activity" title="Notifications" subtitle="Answers, matches and updates" />
      <ul className="mt-10 overflow-hidden rounded border border-border bg-surface">
        {notifications.map((n) => (
          <li key={n.text} className={`flex items-start gap-4 border-b border-border p-5 last:border-b-0 ${n.unread ? "bg-primary/5" : ""}`}>
            <Avatar initials={n.initials} size="sm" />
            <p className="flex-1 text-sm leading-6">{n.text}</p>
            <span className="text-xs text-subtle">{n.time}</span>
            {n.unread && <span className="mt-2 h-2 w-2 rounded-full bg-primary" aria-label="Unread" />}
          </li>
        ))}
      </ul>
    </>
  );
}
