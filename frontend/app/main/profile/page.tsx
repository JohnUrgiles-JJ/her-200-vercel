"use client";

import { useState } from "react";
import { Avatar, Eyebrow } from "../_components/ui";
import { useActivity, useApi } from "../_components/session";
import { initials, postJSON, putJSON, type MentorProfile } from "@/lib/api";

const inputClass = "mt-1 w-full rounded border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-primary";

export default function ProfilePage() {
  const { user, questions, inbox } = useActivity();
  const mentor = user.role === "mentor";
  const profile = useApi<MentorProfile>(mentor && user.has_mentor_profile ? "/api/mentor-profile/" : null);
  const [editing, setEditing] = useState(false);

  const stats: [string, number | string][] = mentor
    ? [
        ["Questions received", inbox.data?.length ?? "–"],
        ["Answered", inbox.data?.filter((i) => i.status === "answered").length ?? "–"],
        ["Awaiting answer", inbox.data?.filter((i) => i.status !== "answered").length ?? "–"],
      ]
    : [
        ["Questions asked", questions.data?.length ?? "–"],
        ["Answers received", questions.data?.reduce((n, q) => n + q.matches.reduce((k, m) => k + m.answers.length, 0), 0) ?? "–"],
        ["Mentors", questions.data ? new Set(questions.data.flatMap((q) => q.matches.map((m) => m.mentor_id))).size : "–"],
      ];

  return (
    <>
      <div className="flex items-center gap-6">
        <Avatar initials={initials(user.full_name)} size="lg" />
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{user.full_name}</h1>
          <p className="text-muted">{profile.data?.headline ?? (mentor ? "Mentor" : "Mentee")}</p>
        </div>
        {mentor && (
          <button onClick={() => setEditing((e) => !e)} className="ml-auto rounded border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-muted">
            {editing ? "Cancel" : user.has_mentor_profile ? "Edit profile" : "Set up mentor profile"}
          </button>
        )}
      </div>

      <div className="mt-10 grid gap-5 sm:grid-cols-3">
        {stats.map(([label, value]) => (
          <div key={label} className="rounded border border-border bg-surface p-5">
            <Eyebrow>{label}</Eyebrow>
            <p className="mt-2 text-3xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      {mentor && editing && (
        <MentorProfileForm
          initial={profile.data}
          exists={user.has_mentor_profile}
          onSaved={() => {
            setEditing(false);
            if (user.has_mentor_profile) profile.reload();
            else window.location.reload();
          }}
        />
      )}

      <div className="mt-10 rounded border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold">Account</h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-subtle">Email</dt><dd>{user.email}</dd>
          <dt className="text-subtle">Role</dt><dd className="capitalize">{user.role}</dd>
          {profile.data && (
            <>
              <dt className="text-subtle">Company</dt><dd>{profile.data.company || "—"}</dd>
              <dt className="text-subtle">Fields</dt><dd>{profile.data.fields}</dd>
              <dt className="text-subtle">Open to</dt><dd>{profile.data.open_to}</dd>
              <dt className="text-subtle">Experience</dt><dd>{profile.data.experience_years ?? 0} years</dd>
              <dt className="text-subtle">Bio</dt><dd>{profile.data.bio || "—"}</dd>
            </>
          )}
        </dl>
      </div>
    </>
  );
}

function MentorProfileForm({ initial, exists, onSaved }: { initial: MentorProfile | null; exists: boolean; onSaved: () => void }) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body: MentorProfile = {
      headline: String(f.get("headline")).trim(),
      company: String(f.get("company")).trim(),
      fields: String(f.get("fields")).trim(),
      open_to: String(f.get("open_to")).trim(),
      bio: String(f.get("bio")).trim(),
      experience_years: Number(f.get("experience_years")) || 0,
    };
    setSaving(true);
    setError("");
    try {
      await (exists ? putJSON : postJSON)<MentorProfile>("/api/mentor-profile/", body);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const field = (name: keyof MentorProfile, label: string, required = false) => (
    <label className="block text-sm font-medium">
      {label}
      <input name={name} required={required} defaultValue={String(initial?.[name] ?? "")} className={inputClass} />
    </label>
  );

  return (
    <form onSubmit={save} className="mt-10 space-y-4 rounded border border-border bg-surface p-6">
      <h2 className="text-lg font-semibold">Mentor profile</h2>
      {field("headline", "Headline", true)}
      {field("company", "Company")}
      {field("fields", "Fields (comma separated)", true)}
      {field("open_to", "Open to (comma separated)", true)}
      <label className="block text-sm font-medium">
        Years of experience
        <input name="experience_years" type="number" min={0} defaultValue={initial?.experience_years ?? 0} className={inputClass} />
      </label>
      <label className="block text-sm font-medium">
        Bio
        <textarea name="bio" rows={3} defaultValue={initial?.bio ?? ""} className={inputClass} />
      </label>
      {error && <p className="text-sm text-danger">{error}</p>}
      <button disabled={saving} className="rounded bg-primary px-5 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-60">
        {saving ? "Saving…" : "Save"}
      </button>
    </form>
  );
}
