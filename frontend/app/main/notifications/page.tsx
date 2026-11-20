"use client";

import { Avatar, PageHeader } from "../_components/ui";
import { Status, useActivity } from "../_components/session";
import { initials, timeAgo } from "@/lib/api";

type Note = { key: string; who: string; text: string; at: string; unread: boolean };

export default function NotificationsPage() {
  const { user, questions, inbox } = useActivity();
  const src = user.role === "mentor" ? inbox : questions;

  const notes: Note[] =
    user.role === "mentor"
      ? (inbox.data ?? []).map((i) => ({
          key: `m${i.match_id}`, who: i.mentee_name, at: i.created_at, unread: i.status !== "answered",
          text: `${i.mentee_name} asked “${i.question_text}”`,
        }))
      : (questions.data ?? []).flatMap((q) =>
          q.matches.flatMap((m) => [
            { key: `m${m.match_id}`, who: m.name, at: q.created_at, unread: false, text: `${m.name} was matched to your question “${q.text}”` },
            ...m.answers.map((a) => ({
              key: `a${a.id}`, who: m.name, at: a.created_at, unread: true, text: `${m.name} answered your question “${q.text}”`,
            })),
          ]),
        );
  notes.sort((a, b) => b.at.localeCompare(a.at));

  return (
    <>
      <PageHeader eyebrow="Activity" title="Notifications" subtitle="Answers, matches and updates" />
      <Status loading={src.loading} error={src.error} empty={src.data !== null && notes.length === 0} emptyText="Nothing new yet." />
      {notes.length > 0 && (
        <ul className="mt-10 overflow-hidden rounded border border-border bg-surface">
          {notes.map((n) => (
            <li key={n.key} className={`flex items-start gap-4 border-b border-border p-5 last:border-b-0 ${n.unread ? "bg-primary/5" : ""}`}>
              <Avatar initials={initials(n.who)} size="sm" />
              <p className="flex-1 text-sm leading-6">{n.text}</p>
              <span className="text-xs text-subtle">{timeAgo(n.at)}</span>
              {n.unread && <span className="mt-2 h-2 w-2 rounded-full bg-primary" aria-label="Unread" />}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
