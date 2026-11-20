"use client";

import { Avatar } from "./ui";
import { Status, useApi, type useActivity } from "./session";
import {
  initials, patchJSON, postJSON, timeAgo,
  type Answer, type CommunityMatch, type CommunityQuestion, type InboxItem, type Match, type Question,
} from "@/lib/api";

type Activity = ReturnType<typeof useActivity>;
type Tab = "mine" | "community";

export default function Feed({ activity }: { activity: Activity }) {
  const mentor = activity.user.role === "mentor";
  const [tab, setTab] = useState<Tab>("mine");
  // Loaded the first time the tab is opened, then kept.
  const [communityOpened, setCommunityOpened] = useState(false);
  const community = useApi<CommunityQuestion[]>(communityOpened ? "/api/questions/community/" : null);

  function open(next: Tab) {
    setTab(next);
    if (next === "community") {
      if (communityOpened) community.reload();
      setCommunityOpened(true);
    }
  }

  const tabs: { id: Tab; label: string; subtitle: string }[] = [
    mentor
      ? { id: "mine", label: "Questions for you", subtitle: "Students matched with you based on your fields" }
      : { id: "mine", label: "Your questions", subtitle: "Mentors matched to what you asked" },
    { id: "community", label: "Community", subtitle: "Questions other mentees shared, and the answers they got" },
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
              onClick={() => open(t.id)}
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
        <Community {...community} />
      ) : mentor ? (
        <Inbox {...activity.inbox} />
      ) : (
        <Questions {...activity.questions} />
      )}
    </section>
  );
}

function Questions({ data, error, loading, reload }: Activity["questions"]) {
  return (
    <>
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="You haven't asked anything yet." />
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

function Community({ data, error, loading }: ReturnType<typeof useApi<CommunityQuestion[]>>) {
  return (
    <>
      <Status loading={loading} error={error} empty={data?.length === 0} emptyText="No one has shared a question yet." />
      {data?.map((q) => (
        <article key={q.id} className="border-b border-border py-8">
          <div className="flex items-center gap-3">
            <Avatar initials={initials(q.mentee_name)} size="sm" />
            <p className="text-sm">
              <span className="font-medium">{q.mentee_name}</span>
              <span className="text-subtle"> · asked {timeAgo(q.created_at)}</span>
            </p>
          </div>
          <h3 className="mt-3 text-xl font-semibold leading-snug">{q.text}</h3>
          {q.matches.length === 0 ? (
            <p className="mt-4 text-sm italic text-subtle">No answers yet.</p>
          ) : (
            <ul className="mt-6 space-y-6">
              {q.matches.map((m) => <MentorReply key={m.match_id} match={m} />)}
            </ul>
          )}
        </article>
      ))}
    </>
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
