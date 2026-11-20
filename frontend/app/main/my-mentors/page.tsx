"use client";

import Link from "next/link";
import { Avatar, EmptyState, PageHeader } from "../_components/ui";
import { Status, useActivity, useApi } from "../_components/session";
import { initials, timeAgo, type InboxItem, type MentorListItem } from "@/lib/api";

const split = (s?: string) => (s ?? "").split(",").map((x) => x.trim()).filter(Boolean);

export default function MyMentorsPage() {
  const { user, questions, inbox } = useActivity();
  const { data, error, loading } = useApi<MentorListItem[]>(user.role === "mentee" ? "/api/mentors/" : null);
  if (user.role === "mentor") return <MyMentees {...inbox} />;
  const matched = new Set(questions.data?.flatMap((q) => q.matches.map((m) => m.mentor_id)) ?? []);
  const sorted = [...(data ?? [])].sort((a, b) => Number(matched.has(b.mentor_id)) - Number(matched.has(a.mentor_id)));

  if (data && data.length === 0)
    return <EmptyState icon="users" title="My mentors" text="Your mentors will live here. Ask a question to get matched with your first one." />;

  return (
    <>
      <PageHeader eyebrow="Your network" title="Mentors" subtitle="Mentors you've been matched with and everyone open to questions" />
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="No mentors yet." />
      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        {sorted.map((m) => (
          <div key={m.mentor_id} className="rounded border border-border bg-surface p-6">
            <div className="flex items-center gap-4">
              <Avatar initials={initials(m.name)} />
              <div>
                <p className="font-semibold">{m.name}</p>
                <p className="text-sm text-muted">{m.headline}{m.company && ` · ${m.company}`}</p>
              </div>
            </div>
            {m.bio && <p className="mt-4 text-sm leading-6 text-muted">{m.bio}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              {split(m.fields).map((f) => (
                <span key={f} className="rounded bg-surface-muted px-2.5 py-1 text-xs text-muted">{f}</span>
              ))}
            </div>
            {m.open_to && <p className="mt-3 text-xs text-subtle">Open to: {m.open_to}</p>}
            <div className="mt-5 flex items-center justify-between">
              <span className="text-sm font-semibold text-primary">
                {matched.has(m.mentor_id) ? "Matched with you" : m.experience_years ? `${m.experience_years} yrs experience` : ""}
              </span>
              {matched.has(m.mentor_id) && (
                <Link href="/main/messages" className="rounded border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-muted">View answers</Link>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function MyMentees({ data, error, loading }: { data: InboxItem[] | null; error: string; loading: boolean }) {
  // Group inbox items by mentee: every student whose question was matched to this mentor.
  const mentees = new Map<string, InboxItem[]>();
  for (const item of data ?? []) mentees.set(item.mentee_name, [...(mentees.get(item.mentee_name) ?? []), item]);

  if (data && data.length === 0)
    return <EmptyState icon="users" title="My mentees" text="Your mentees will live here. Students matched to your fields will show up as they ask questions." />;

  return (
    <>
      <PageHeader eyebrow="Your network" title="My mentees" subtitle="Students whose questions were matched with you" />
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="No mentees matched with you yet." />
      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        {[...mentees].map(([name, items]) => {
          const open = items.filter((i) => i.status !== "answered").length;
          return (
            <div key={name} className="rounded border border-border bg-surface p-6">
              <div className="flex items-center gap-4">
                <Avatar initials={initials(name)} />
                <div>
                  <p className="font-semibold">{name}</p>
                  <p className="text-sm text-muted">{items.length} question{items.length === 1 ? "" : "s"}</p>
                </div>
              </div>
              <ul className="mt-4 space-y-2">
                {items.map((i) => (
                  <li key={i.match_id} className="text-sm leading-6 text-muted">
                    “{i.question_text}” <span className="text-xs text-subtle">· {timeAgo(i.created_at)}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-5 flex items-center justify-between">
                <span className="text-sm font-semibold text-primary">{open ? `${open} awaiting your answer` : "All answered"}</span>
                <Link href="/main/messages" className="rounded border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-muted">Message</Link>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
