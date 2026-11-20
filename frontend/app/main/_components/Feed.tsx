"use client";

import { Avatar } from "./ui";
import { Status, useApi } from "./session";
import { initials, timeAgo, type FeedPost } from "@/lib/api";

export default function Feed() {
  const { data, error, loading } = useApi<FeedPost[]>("/api/questions/");
  // The backend currently only supports POST on this URL, so a GET fails (405) — treat that as an empty feed.
  const posts = error ? [] : data;

  return (
    <section className="mt-14">
      <div className="border-b border-border pb-4">
        <h2 className="text-2xl font-semibold tracking-tight">From your community</h2>
        <p className="text-sm text-muted">Fresh ideas and honest questions</p>
      </div>
      <Status loading={loading} empty={!loading && (posts?.length ?? 0) === 0} emptyText="No posts yet." />
      {posts?.map((p) => (
        <article key={p.id} className="border-b border-border py-8">
          <div className="flex items-start gap-4">
            <Avatar initials={initials(p.author_name)} />
            <div className="flex-1">
              <p className="font-medium">{p.author_name}</p>
              <p className="text-sm text-subtle">{timeAgo(p.created_at)}</p>
            </div>
          </div>
          <div className="pl-[4.5rem]">
            <h3 className="mt-3 text-xl font-semibold leading-snug">{p.text}</h3>
            <p className="mt-4 border-t border-border pt-4 text-sm text-muted">
              {p.answer_count} answer{p.answer_count === 1 ? "" : "s"}
            </p>
          </div>
        </article>
      ))}
    </section>
  );
}
