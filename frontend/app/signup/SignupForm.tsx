"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import AuthShell, { buttonClass, inputClass, labelClass } from "../AuthShell";
import { postJSON, saveToken } from "@/lib/api";

type Role = "mentee" | "mentor";

const splitList = (v: FormDataEntryValue | null) =>
  String(v ?? "").split(",").map((s) => s.trim()).filter(Boolean);

export default function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [role, setRole] = useState<Role>(params.get("role") === "mentor" ? "mentor" : "mentee");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(e.currentTarget);
    const body: Record<string, unknown> = {
      role,
      name: form.get("name"),
      email: form.get("email"),
      password: form.get("password"),
    };
    if (role === "mentor") {
      body.profile = {
        headline: form.get("headline"),
        company: form.get("company"),
        fields: splitList(form.get("fields")),
        topics: splitList(form.get("topics")),
        bio: form.get("bio"),
        years_experience: Number(form.get("years_experience")),
      };
    }
    try {
      const { token } = await postJSON<{ token: string }>("/api/auth/register/", body);
      saveToken(token);
      router.push("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle={<>Already have an account? <Link href="/login" className="font-medium text-fuchsia-600">Log in</Link></>}
    >
      <div className="grid grid-cols-2 gap-2 rounded-full bg-zinc-100 p-1 dark:bg-zinc-900" role="radiogroup" aria-label="I am a">
        {(["mentee", "mentor"] as Role[]).map((r) => (
          <button
            key={r}
            type="button"
            role="radio"
            aria-checked={role === r}
            onClick={() => setRole(r)}
            className={`rounded-full py-2 text-sm font-medium capitalize ${
              role === r ? "bg-fuchsia-600 text-white" : "text-zinc-600 dark:text-zinc-400"
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">
        {role === "mentee"
          ? "Ask any career or STEM question and get matched with mentors."
          : "Answer questions from students in your fields — minutes per question."}
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <label className={labelClass}>
          Full name
          <input name="name" required className={inputClass} />
        </label>
        <label className={labelClass}>
          Email
          <input name="email" type="email" required className={inputClass} />
        </label>
        <label className={labelClass}>
          Password
          <input name="password" type="password" required minLength={8} className={inputClass} />
        </label>

        {role === "mentor" && (
          <>
            <label className={labelClass}>
              Headline
              <input name="headline" required placeholder="Senior UX Designer" className={inputClass} />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className={labelClass}>
                Company
                <input name="company" required className={inputClass} />
              </label>
              <label className={labelClass}>
                Years of experience
                <input name="years_experience" type="number" min={0} required className={inputClass} />
              </label>
            </div>
            <label className={labelClass}>
              Fields
              <input name="fields" required placeholder="UX design, Product" className={inputClass} />
              <span className="mt-1 block text-xs font-normal text-zinc-500">Separate with commas</span>
            </label>
            <label className={labelClass}>
              Topics you&apos;re open to
              <input name="topics" required placeholder="Career switching, Portfolios, Interviews" className={inputClass} />
              <span className="mt-1 block text-xs font-normal text-zinc-500">Separate with commas</span>
            </label>
            <label className={labelClass}>
              Short bio
              <textarea name="bio" required rows={3} className={inputClass} />
            </label>
            <label className="flex items-start gap-3 text-sm text-zinc-600 dark:text-zinc-400">
              <input name="agree" type="checkbox" required className="mt-1 accent-fuchsia-600" />
              I agree to answer questions from students about my experience and fields.
            </label>
          </>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className={buttonClass}>
          {loading ? "Creating account…" : `Sign up as a ${role}`}
        </button>
      </form>
    </AuthShell>
  );
}
