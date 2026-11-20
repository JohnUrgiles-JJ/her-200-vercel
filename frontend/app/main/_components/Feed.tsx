"use client";

import { useState } from "react";
import { Avatar, Icon } from "./ui";
import { posts } from "./data";

const tabs = ["For you", "Following", "Latest"] as const;

export default function Feed() {
  const [tab, setTab] = useState<(typeof tabs)[number]>("For you");
  return (
    <section className="mt-14">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">From your community</h2>
          <p className="text-sm text-muted">Fresh ideas and honest questions</p>
        </div>
        <div className="flex gap-1 text-sm">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`border-b-2 px-3 py-2 ${tab === t ? "border-foreground font-medium" : "border-transparent text-muted hover:text-foreground"}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {posts.map((p) => (
        <article key={p.title} className="border-b border-border py-8">
          <div className="flex items-start gap-4">
            <Avatar initials={p.initials} />
            <div className="flex-1">
              <p className="font-medium">{p.author}</p>
              <p className="text-sm text-subtle">{p.meta}</p>
            </div>
            <button aria-label="More options" className="text-muted hover:text-foreground"><Icon name="dots" /></button>
          </div>
          <div className="pl-[4.5rem]">
            <span className="mt-4 inline-block rounded bg-primary/10 px-2.5 py-1 text-xs font-medium uppercase text-primary">{p.tag}</span>
            <h3 className="mt-3 text-xl font-semibold leading-snug">{p.title}</h3>
            <p className="mt-3 leading-7 text-muted">{p.body}</p>
            <div className="mt-6 flex items-center gap-6 border-t border-border pt-4 text-sm text-muted">
              <button className="flex items-center gap-2 hover:text-foreground"><Icon name="heart" /> {p.likes}</button>
              <button className="flex items-center gap-2 hover:text-foreground"><Icon name="chat" /> {p.comments}</button>
              <button className="ml-auto flex items-center gap-2 hover:text-foreground"><Icon name="bookmark" /> Save</button>
            </div>
          </div>
        </article>
      ))}
    </section>
  );
}
