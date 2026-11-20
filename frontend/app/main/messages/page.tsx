"use client";

import { useState } from "react";
import { Avatar, PageHeader } from "../_components/ui";
import { Status, useActivity } from "../_components/session";
import { initials, postJSON, timeAgo, type Answer } from "@/lib/api";

type Thread = { id: number; name: string; question: string; answers: Answer[]; at: string };

export default function MessagesPage() {
  const { user, questions, inbox } = useActivity();
  const mentor = user.role === "mentor";
  const src = mentor ? inbox : questions;
  const [activeId, setActiveId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const threads: Thread[] = mentor
    ? (inbox.data ?? []).map((i) => ({ id: i.match_id, name: i.mentee_name, question: i.question_text, answers: i.answers, at: i.created_at }))
    : (questions.data ?? []).flatMap((q) =>
        q.matches.map((m) => ({ id: m.match_id, name: m.name, question: q.text, answers: m.answers, at: m.answers.at(-1)?.created_at ?? q.created_at })),
      );
  threads.sort((a, b) => b.at.localeCompare(a.at));
  const active = threads.find((t) => t.id === activeId) ?? threads[0];

  async function send(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("text") ?? "").trim();
    if (!text || !active) return;
    setSending(true);
    setError("");
    try {
      await postJSON<Answer>(`/api/matches/${active.id}/answer/`, { text });
      form.reset();
      inbox.reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Inbox" title="Messages" subtitle={mentor ? "Questions from students" : "Conversations with your mentors"} />
      <Status loading={src.loading} error={src.error} empty={src.data !== null && threads.length === 0} emptyText="No conversations yet." />
      {active && (
        <div className="mt-10 grid overflow-hidden rounded border border-border bg-surface md:grid-cols-[18rem_1fr]">
          <ul className="border-b border-border md:border-b-0 md:border-r">
            {threads.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => setActiveId(t.id)}
                  className={`flex w-full items-center gap-3 border-b border-border p-4 text-left ${t.id === active.id ? "bg-surface-muted" : "hover:bg-surface-muted"}`}
                >
                  <Avatar initials={initials(t.name)} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="flex justify-between gap-2">
                      <p className="font-medium">{t.name}</p>
                      <span className="text-xs text-subtle">{timeAgo(t.at)}</span>
                    </div>
                    <p className="truncate text-sm text-muted">{t.answers.at(-1)?.text ?? t.question}</p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
          <div className="flex min-h-96 flex-col">
            <div className="flex items-center gap-3 border-b border-border p-4">
              <Avatar initials={initials(active.name)} size="sm" />
              <p className="font-medium">{active.name}</p>
            </div>
            <div className="flex-1 space-y-3 p-6">
              <p className={`max-w-sm rounded-lg p-3 text-sm ${mentor ? "bg-surface-muted" : "ml-auto bg-primary text-on-primary"}`}>{active.question}</p>
              {active.answers.map((a) => (
                <p key={a.id} className={`max-w-sm rounded-lg p-3 text-sm ${mentor ? "ml-auto bg-primary text-on-primary" : "bg-surface-muted"}`}>{a.text}</p>
              ))}
              {!mentor && active.answers.length === 0 && <p className="text-sm italic text-subtle">Waiting for {active.name} to answer…</p>}
            </div>
            {mentor && (
              <form onSubmit={send} className="flex gap-3 border-t border-border p-4">
                <input name="text" required placeholder="Write an answer…" className="flex-1 rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary" />
                <button disabled={sending} className="rounded bg-primary px-4 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60">Send</button>
              </form>
            )}
            {error && <p className="px-4 pb-4 text-sm text-danger">{error}</p>}
          </div>
        </div>
      )}
    </>
  );
}
