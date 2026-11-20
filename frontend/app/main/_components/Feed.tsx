"use client";

import { useState } from "react";
import { Avatar, Icon } from "./ui";
import { Status, useActivity, useApi, useSession } from "./session";
import {
  initials, patchJSON, postJSON, timeAgo,
  type Answer, type CommunityMatch, type CommunityQuestion, type FeedPost, type InboxItem, type Match, type Question,
} from "@/lib/api";

type Activity = ReturnType<typeof useActivity>;
type Tab = "community" | "mine";

// The backend has no posts endpoint yet, so posts made on the home page are stored in this browser.
const LOCAL_KEY = "localPosts";

function readLocalPosts(): FeedPost[] {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function addLocalPost(author_name: string, text: string) {
  const post: FeedPost = { id: -Date.now(), author_name, text, created_at: new Date().toISOString(), answer_count: 0 };
  localStorage.setItem(LOCAL_KEY, JSON.stringify([post, ...readLocalPosts()]));
}

// Likes and comments are also stored in this browser until the backend supports them.
type Comment = { id: number; author_name: string; text: string; created_at: string };
type Reactions = { liked: boolean; likes: number; comments: Comment[] };
const REACTIONS_KEY = "postReactions";

function readReactions(): Record<string, Reactions> {
  try {
    return JSON.parse(localStorage.getItem(REACTIONS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

/** Home page feed. Loads its own data; the page remounts it (via `key`) after a new post. */
export default function Feed() {
  const activity = useActivity();
  const mentor = activity.user.role === "mentor";
  const [tab, setTab] = useState<Tab>("community");

  const tabs: { id: Tab; label: string; subtitle: string }[] = [
    { id: "community", label: "From your community", subtitle: "Fresh ideas, honest questions, and the answers mentors gave" },
    mentor
      ? { id: "mine", label: "Questions for you", subtitle: "Students matched with you based on your fields" }
      : { id: "mine", label: "Your questions", subtitle: "Mentors matched to what you asked. Share a question so others can learn from it." },
  ];

  return (
    <section className="mt-14">
      <div className="border-b border-border">
        <div role="tablist" className="flex gap-6">
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`-mb-px border-b-2 pb-3 text-2xl font-semibold tracking-tight ${
                tab === t.id ? "border-primary text-foreground" : "border-transparent text-subtle hover:text-muted"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">{tabs.find((t) => t.id === tab)!.subtitle}</p>
      {tab === "community" ? (
        <Community />
      ) : mentor ? (
        <Inbox {...activity.inbox} />
      ) : (
        <Questions {...activity.questions} />
      )}
    </section>
  );
}

// --- Community: home page posts (this browser) + questions mentees shared (backend) -------------

type Item = { post: FeedPost; matches?: CommunityMatch[] };

function Community() {
  const { data, error, loading } = useApi<CommunityQuestion[]>("/api/questions/community/");
  const [local] = useState(readLocalPosts);
  const [reactions, setReactions] = useState(readReactions);

  // Shared questions get positive ids and local posts negative ones, so reactions never collide.
  const shared: Item[] | null = error
    ? []
    : data &&
      data.map((q) => ({
        post: { id: q.id, text: q.text, created_at: q.created_at, author_name: q.mentee_name, answer_count: 0 },
        matches: q.matches,
      }));
  const items = shared && [...local.map((post): Item => ({ post })), ...shared].sort((a, b) =>
    b.post.created_at.localeCompare(a.post.created_at),
  );

  function update(id: number, change: (r: Reactions) => Reactions) {
    setReactions((all) => {
      const next = { ...all, [id]: change(all[id] ?? { liked: false, likes: 0, comments: [] }) };
      localStorage.setItem(REACTIONS_KEY, JSON.stringify(next));
      return next;
    });
  }

  return (
    <>
      {error && <p className="mt-4 text-sm text-danger">Couldn&apos;t load shared questions: {error}</p>}
      <Status loading={loading} empty={!loading && (items?.length ?? 0) === 0} emptyText="No posts yet." />
      {items?.map(({ post: p, matches }) => (
        <article key={p.id} className="border-b border-border py-8">
          <div className="flex items-start gap-4">
            <Avatar initials={initials(p.author_name)} />
            <div className="flex-1">
              <p className="font-medium">{p.author_name}</p>
              <p className="text-sm text-subtle">{matches ? "Asked " : ""}{timeAgo(p.created_at)}</p>
            </div>
          </div>
          <div className="pl-[4.5rem]">
            <h3 className="mt-3 text-xl font-semibold leading-snug">{p.text}</h3>
            {matches &&
              (matches.length === 0 ? (
                <p className="mt-4 text-sm italic text-subtle">No mentor answers yet.</p>
              ) : (
                <ul className="mt-6 space-y-6">
                  {matches.map((m) => <MentorReply key={m.match_id} match={m} />)}
                </ul>
              ))}
            <PostActions
              post={p}
              reactions={reactions[p.id] ?? { liked: false, likes: 0, comments: [] }}
              onChange={(change) => update(p.id, change)}
            />
          </div>
        </article>
      ))}
    </>
  );
}

function PostActions({ post, reactions, onChange }: {
  post: FeedPost;
  reactions: Reactions;
  onChange: (change: (r: Reactions) => Reactions) => void;
}) {
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const { liked, likes, comments } = reactions;
  const commentCount = post.answer_count + comments.length;

  function comment(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("comment") ?? "").trim();
    if (!text) return;
    const c: Comment = { id: Date.now(), author_name: user.full_name, text, created_at: new Date().toISOString() };
    onChange((r) => ({ ...r, comments: [...r.comments, c] }));
    form.reset();
  }

  return (
    <>
      <div className="mt-4 flex items-center gap-6 border-t border-border pt-4 text-sm text-muted">
        <button
          onClick={() => onChange((r) => ({ ...r, liked: !r.liked, likes: r.likes + (r.liked ? -1 : 1) }))}
          aria-pressed={liked}
          className={`flex items-center gap-2 hover:text-foreground ${liked ? "font-medium text-primary" : ""}`}
        >
          <Icon name="heart" /> {likes} {likes === 1 ? "like" : "likes"}
        </button>
        <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex items-center gap-2 hover:text-foreground">
          <Icon name="chat" /> {commentCount} {commentCount === 1 ? "comment" : "comments"}
        </button>
      </div>

      {open && (
        <div className="mt-4 space-y-3">
          {comments.map((c) => (
            <div key={c.id} className="flex gap-3">
              <Avatar initials={initials(c.author_name)} size="sm" />
              <div className="flex-1 rounded-lg bg-surface-muted p-3 text-sm">
                <p className="font-medium">
                  {c.author_name} <span className="text-xs font-normal text-subtle">· {timeAgo(c.created_at)}</span>
                </p>
                <p className="mt-1 leading-6">{c.text}</p>
              </div>
            </div>
          ))}
          <form onSubmit={comment} className="flex gap-3">
            <input
              name="comment"
              required
              autoFocus
              placeholder="Write a comment…"
              className="flex-1 rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
            />
            <button className="rounded bg-primary px-4 text-sm font-medium text-on-primary hover:bg-primary-hover">Comment</button>
          </form>
        </div>
      )}
    </>
  );
}

// --- Your questions (mentee) -------------------------------------------------------------------

function Questions({ data, error, loading, reload }: Activity["questions"]) {
  return (
    <>
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="You haven't asked anything yet. Use “Pair up with a mentor” to ask." />
      {data?.map((q: Question) => (
        <article key={q.id} className="border-b border-border py-8">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-subtle">Asked {timeAgo(q.created_at)}</p>
            <ShareToggle question={q} onChange={reload} />
          </div>
          <h3 className="mt-2 text-xl font-semibold leading-snug">{q.text}</h3>
          {q.matches.length === 0 && <p className="mt-4 text-sm text-muted">No mentors matched yet.</p>}
          <ul className="mt-6 space-y-6">
            {q.matches.map((m) => (
              <MentorReply key={m.match_id} match={m} pending="Waiting for an answer…" />
            ))}
          </ul>
        </article>
      ))}
    </>
  );
}

function ShareToggle({ question, onChange }: { question: Question; onChange: () => void }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function toggle() {
    setSaving(true);
    setError("");
    try {
      await patchJSON<Question>(`/api/questions/${question.id}/`, { is_public: !question.is_public });
      onChange();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      {error && <span className="text-danger">{error}</span>}
      {question.is_public && <span className="text-subtle">Shared with the community ·</span>}
      <button onClick={toggle} disabled={saving} className="font-medium text-primary hover:text-primary-hover disabled:opacity-60">
        {saving ? "Saving…" : question.is_public ? "Make private" : "Share with the community"}
      </button>
    </div>
  );
}

/** A mentor with their answers. The matching reason is shown only when present (your own questions). */
function MentorReply({ match: m, pending }: { match: Match | CommunityMatch; pending?: string }) {
  return (
    <li className="flex gap-4">
      <Avatar initials={initials(m.name)} size="sm" />
      <div className="flex-1">
        <p className="font-medium">
          {m.name} <span className="text-sm font-normal text-muted">· {m.headline}{m.company && ` at ${m.company}`}</span>
        </p>
        {"reason" in m && <p className="text-sm text-subtle">{m.reason}</p>}
        <Answers answers={m.answers} pending={pending} />
      </div>
    </li>
  );
}

// --- Questions for you (mentor) ----------------------------------------------------------------

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
