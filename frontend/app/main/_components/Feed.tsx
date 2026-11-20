"use client";

import { useState } from "react";
import { Avatar } from "./ui";
import { Status, type useActivity } from "./session";
import { initials, postJSON, timeAgo, type Answer, type InboxItem, type Question } from "@/lib/api";

type Activity = ReturnType<typeof useActivity>;

export default function Feed({ activity }: { activity: Activity }) {
  const mentor = activity.user.role === "mentor";
  return (
    <section className="mt-14">
      <div className="border-b border-border pb-4">
        <h2 className="text-2xl font-semibold tracking-tight">{mentor ? "Questions for you" : "Your questions"}</h2>
        <p className="text-sm text-muted">
          {mentor ? "Students matched with you based on your fields" : "Mentors matched to what you asked"}
        </p>
      </div>
      {mentor ? <Inbox {...activity.inbox} /> : <Questions {...activity.questions} />}
    </section>
  );
}

function Questions({ data, error, loading }: Activity["questions"]) {
  return (
    <>
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="You haven't asked anything yet." />
      {data?.map((q: Question) => (
        <article key={q.id} className="border-b border-border py-8">
          <p className="text-sm text-subtle">Asked {timeAgo(q.created_at)}</p>
          <h3 className="mt-2 text-xl font-semibold leading-snug">{q.text}</h3>
          {q.matches.length === 0 && <p className="mt-4 text-sm text-muted">No mentors matched yet.</p>}
          <ul className="mt-6 space-y-6">
            {q.matches.map((m) => (
              <li key={m.match_id} className="flex gap-4">
                <Avatar initials={initials(m.name)} size="sm" />
                <div className="flex-1">
                  <p className="font-medium">
                    {m.name} <span className="text-sm font-normal text-muted">· {m.headline}{m.company && ` at ${m.company}`}</span>
                  </p>
                  <p className="text-sm text-subtle">{m.reason}</p>
                  <Answers answers={m.answers} pending="Waiting for an answer…" />
                </div>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </>
  );
}

function Inbox({ data, error, loading, reload }: Activity["inbox"]) {
  return (
    <>
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="No questions matched to you yet." />
      {data?.map((item) => <InboxCard key={item.match_id} item={item} onAnswered={reload} />)}
    </>
  );
}

function InboxCard({ item, onAnswered }: { item: InboxItem; onAnswered: () => void }) {
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function answer(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("text") ?? "").trim();
    if (!text) return;
    setSending(true);
    setError("");
    try {
      await postJSON<Answer>(`/api/matches/${item.match_id}/answer/`, { text });
      form.reset();
      onAnswered();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <article className="border-b border-border py-8">
      <div className="flex items-start gap-4">
        <Avatar initials={initials(item.mentee_name)} />
        <div className="flex-1">
          <p className="font-medium">{item.mentee_name}</p>
          <p className="text-sm text-subtle">{timeAgo(item.created_at)} · {item.status === "answered" ? "Answered" : "Awaiting your answer"}</p>
        </div>
      </div>
      <div className="pl-[4.5rem]">
        <h3 className="mt-3 text-xl font-semibold leading-snug">{item.question_text}</h3>
        <p className="mt-2 text-sm text-muted">Why you: {item.reason}</p>
        <Answers answers={item.answers} />
        <form onSubmit={answer} className="mt-4 flex gap-3">
          <textarea name="text" required rows={2} placeholder="Write your answer…" className="flex-1 rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
          <button disabled={sending} className="self-end rounded bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60">
            {sending ? "Sending…" : "Answer"}
          </button>
        </form>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
      </div>
    </article>
  );
}

function Answers({ answers, pending }: { answers: Answer[]; pending?: string }) {
  if (answers.length === 0) return pending ? <p className="mt-2 text-sm italic text-subtle">{pending}</p> : null;
  return (
    <ul className="mt-3 space-y-2">
      {answers.map((a) => (
        <li key={a.id} className="rounded-lg bg-surface-muted p-3 text-sm leading-6">
          {a.text}
          <span className="ml-2 text-xs text-subtle">{timeAgo(a.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}
