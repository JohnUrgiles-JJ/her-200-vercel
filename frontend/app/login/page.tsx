"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthShell, { buttonClass, inputClass, labelClass } from "../AuthShell";
import { postJSON, saveToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(e.currentTarget);
    try {
      const { token } = await postJSON<{ token: string }>("/api/auth/login/", {
        email: form.get("email"),
        password: form.get("password"),
      });
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
      title="Welcome back"
      subtitle={<>New to ConnectHER? <Link href="/signup" className="font-medium text-primary">Sign up</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <label className={labelClass}>
          Email
          <input name="email" type="email" required className={inputClass} />
        </label>
        <label className={labelClass}>
          Password
          <input name="password" type="password" required className={inputClass} />
        </label>
        {error && <p className="text-sm text-danger">{error}</p>}
        <button type="submit" disabled={loading} className={buttonClass}>
          {loading ? "Logging in…" : "Log in"}
        </button>
      </form>
    </AuthShell>
  );
}
