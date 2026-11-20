"use client";

import { useState } from "react";
import Feed from "./_components/Feed";
import Today from "./_components/Today";
import { Avatar, Eyebrow, Icon } from "./_components/ui";
import { useSession } from "./_components/session";
import { initials, postJSON, type Question } from "@/lib/api";

export default function HomePage() {
  const { user } = useSession();
  const [feedKey, setFeedKey] = useState(0);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function ask(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("question") ?? "").trim();
    if (!text) return;
    setError("");
    setSending(true);
    try {
      await postJSON<Question>("/api/questions/", { text });
      form.reset();
      setFeedKey((k) => k + 1);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <Eyebrow><Today /></Eyebrow>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Welcome back, {user.full_name.split(" ")[0]}</h1>

      {user.role === "mentee" && (
        <>
          <form id="ask" onSubmit={ask} className="mt-12 flex items-center gap-4 rounded border border-border bg-surface p-5">
            <Avatar initials={initials(user.full_name)} />
            <input
              name="question"
              required
              disabled={sending}
              placeholder="Ask the community anything…"
              className="flex-1 bg-transparent text-lg outline-none placeholder:text-subtle"
            />
            <button type="submit" disabled={sending} aria-label="Ask" className="flex h-12 w-12 items-center justify-center rounded bg-primary text-on-primary hover:bg-primary-hover disabled:opacity-60">
              <Icon name="plus" className="h-6 w-6" />
            </button>
          </form>
          {sending && <p className="mt-3 text-sm text-muted">Finding mentors for your question…</p>}
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}
        </>
      )}

      <Feed key={feedKey} />
    </>
  );
}
