"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { Avatar, Icon } from "./ui";
import { useSession } from "./session";
import { initials, postJSON, type Question } from "@/lib/api";

/** Header button + popup: a mentee describes what they need and gets matched with mentors. */
export default function PairUp() {
  const { user } = useSession();
  const dialog = useRef<HTMLDialogElement>(null);
  const [result, setResult] = useState<Question | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  if (user.role !== "mentee") return null;

  function open() {
    setResult(null);
    setError("");
    dialog.current?.showModal();
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("text") ?? "").trim();
    if (!text) return;
    setSending(true);
    setError("");
    try {
      setResult(await postJSON<Question>("/api/questions/", { text }));
      form.reset();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button onClick={open} className="ml-auto flex items-center gap-2 rounded bg-foreground px-5 py-3 font-medium text-background hover:opacity-90">
        <Icon name="plus" className="h-5 w-5" /> Pair up with a mentor
      </button>

      <dialog
        ref={dialog}
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
        className="m-auto w-full max-w-lg rounded border border-border bg-surface p-0 text-foreground backdrop:bg-foreground/40"
      >
        <div className="p-8">
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-2xl font-semibold tracking-tight">{result ? "Your matches" : "Pair up with a mentor"}</h2>
            <button onClick={() => dialog.current?.close()} aria-label="Close" className="text-2xl leading-none text-muted hover:text-foreground">×</button>
          </div>

          {!result ? (
            <form onSubmit={submit} className="mt-4">
              <p className="text-sm text-muted">
                Tell us what you need help with: your goals, the field you&apos;re interested in, or a specific question. We&apos;ll match you with mentors whose experience fits.
              </p>
              <textarea
                name="text"
                required
                autoFocus
                rows={5}
                disabled={sending}
                placeholder="e.g. I'm a CS student wanting to move into UX design. How do I build a portfolio without a design degree?"
                className="mt-4 w-full rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
              />
              {error && <p className="mt-2 text-sm text-danger">{error}</p>}
              <button disabled={sending} className="mt-4 w-full rounded bg-primary py-3 font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60">
                {sending ? "Finding your mentors…" : "Find my mentors"}
              </button>
            </form>
          ) : (
            <div className="mt-4">
              {result.matches.length === 0 ? (
                <p className="text-sm text-muted">No mentors matched yet. We&apos;ll keep looking. Check Notifications for updates.</p>
              ) : (
                <ul className="space-y-4">
                  {[...result.matches].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0)).map((m) => (
                    <li key={m.match_id} className="flex items-center gap-3">
                      <Avatar initials={initials(m.name)} size="sm" />
                      <div className="min-w-0 flex-1">
                        <p className="font-medium">{m.name}</p>
                        <p className="truncate text-xs text-muted">{m.headline}{m.company && ` · ${m.company}`}</p>
                        <p className="mt-1 text-xs font-semibold text-primary">
                          {m.match_score != null ? `${Math.round(m.match_score)}% match` : m.reason}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <Link
                href="/main/messages"
                onClick={() => dialog.current?.close()}
                className="mt-6 block rounded bg-foreground py-3 text-center font-medium text-background hover:opacity-90"
              >
                Go to messages
              </Link>
            </div>
          )}
        </div>
      </dialog>
    </>
  );
}
