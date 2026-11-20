"use client";

import { useState } from "react";
import Feed from "./_components/Feed";
import Today from "./_components/Today";
import { Avatar, Eyebrow, Icon } from "./_components/ui";
<<<<<<< HEAD
import { useActivity } from "./_components/session";
import { initials, postJSON, shortName, type Question } from "@/lib/api";
=======
import { useSession } from "./_components/session";
import { initials, postJSON, type Question } from "@/lib/api";
>>>>>>> d820997e213fdb82b442e83e8bb3f189a6f7c2a1

export default function HomePage() {
  const { user } = useSession();
  const [feedKey, setFeedKey] = useState(0);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function ask(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const text = String(data.get("question") ?? "").trim();
    const is_public = data.get("is_public") === "on";
    if (!text) return;
    setError("");
    setSending(true);
    try {
      await postJSON<Question>("/api/questions/", { text, is_public });
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
          <label className="mt-3 flex items-center gap-2 text-sm text-muted">
            <input form="ask" type="checkbox" name="is_public" disabled={sending} className="h-4 w-4 accent-primary" />
            Share with the community, so other mentees can see it and its answers (shown as {shortName(user.full_name)})
          </label>
          {sending && <p className="mt-3 text-sm text-muted">Finding mentors for your question…</p>}
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}
        </>
      )}

      <Feed key={feedKey} />
    </>
  );
}
