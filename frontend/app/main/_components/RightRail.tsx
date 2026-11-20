"use client";

import Link from "next/link";
import { Eyebrow, Avatar } from "./ui";
import { useApi, useSession } from "./session";
import { initials, type InboxItem, type MentorListItem } from "@/lib/api";

// No events endpoint on the backend yet — these stay static.
const events = [
  { day: "26", month: "JUN", title: "Making work that feels like you", meta: "Live studio chat · 7 PM" },
  { day: "02", month: "JUL", title: "Portfolio swap: brand edition", meta: "Community session · 6 PM" },
];

export default function RightRail() {
  const { user } = useSession();
  const isMentor = user.role === "mentor";
  // Mentors only see mentees (from their inbox); mentees see mentors.
  const mentorList = useApi<MentorListItem[]>(isMentor ? null : "/api/mentors/");
  const inbox = useApi<InboxItem[]>(isMentor ? "/api/inbox/" : null);

  const people = isMentor
    ? [...new Map((inbox.data ?? []).map((i) => [i.mentee_name, i])).values()].map((i) => ({
        key: `q${i.match_id}`, name: i.mentee_name, line1: "Mentee", line2: i.question_text,
      }))
    : (mentorList.data ?? []).map((m) => ({
        key: `m${m.mentor_id}`, name: m.name, line1: `${m.headline}${m.company ? ` · ${m.company}` : ""}`, line2: m.fields,
      }));
  const loaded = (isMentor ? inbox.data : mentorList.data) !== null;
  return (
    <aside className="sticky top-0 hidden h-screen w-80 shrink-0 overflow-y-auto border-l border-border bg-surface-muted px-7 py-10 xl:block">
      <Eyebrow>People to know</Eyebrow>
      <div className="mt-1 flex items-baseline justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">{isMentor ? "Your mentees" : "Mentors"}</h2>
        <Link href={isMentor ? "/main/messages" : "/main/my-mentors"} className="text-sm font-medium text-primary">See all</Link>
      </div>
      <ul className="mt-6 space-y-5 border-b border-border pb-8">
        {people.slice(0, 3).map((p) => (
          <li key={p.key} className="flex items-center gap-3">
            <Avatar initials={initials(p.name)} />
            <div className="min-w-0 flex-1">
              <p className="font-medium">{p.name}</p>
              <p className="text-xs text-muted">{p.line1}</p>
              <p className="mt-1 truncate text-xs font-semibold text-primary">{p.line2}</p>
            </div>
          </li>
        ))}
        {loaded && people.length === 0 && (
          <li className="text-sm text-muted">{isMentor ? "No mentees matched with you yet." : "No mentors yet."}</li>
        )}
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
