"use client";

import { useState } from "react";
import Feed, { addLocalPost } from "./_components/Feed";
import Today from "./_components/Today";
import { Avatar, Eyebrow, Icon } from "./_components/ui";
import { useSession } from "./_components/session";
import { initials } from "@/lib/api";

export default function HomePage() {
  const { user } = useSession();
  const [feedKey, setFeedKey] = useState(0);

  function post(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const text = String(new FormData(form).get("post") ?? "").trim();
    if (!text) return;
    addLocalPost(user.full_name, text);
    form.reset();
    setFeedKey((k) => k + 1);
  }

  return (
    <>
      <Eyebrow><Today /></Eyebrow>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Welcome back, {user.full_name.split(" ")[0]}</h1>

      <form id="post" onSubmit={post} className="mt-12 flex items-center gap-4 rounded border border-border bg-surface p-5">
        <Avatar initials={initials(user.full_name)} />
        <input
          name="post"
          required
          placeholder="Share something with the community…"
          className="flex-1 bg-transparent text-lg outline-none placeholder:text-subtle"
        />
        <button type="submit" aria-label="Post" className="flex h-12 w-12 items-center justify-center rounded bg-primary text-on-primary hover:bg-primary-hover">
          <Icon name="plus" className="h-6 w-6" />
        </button>
      </form>

      <Feed key={feedKey} />
    </>
  );
}
