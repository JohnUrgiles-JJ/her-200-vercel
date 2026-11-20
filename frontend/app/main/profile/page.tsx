import { Avatar, Eyebrow } from "../_components/ui";
import { currentUser } from "../_components/data";

export default function ProfilePage() {
  return (
    <>
      <div className="flex items-center gap-6">
        <Avatar initials={currentUser.initials} size="lg" />
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{currentUser.name}</h1>
          <p className="text-muted">{currentUser.headline}</p>
        </div>
        <button className="ml-auto rounded border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-muted">Edit profile</button>
      </div>

      <div className="mt-10 grid gap-5 sm:grid-cols-3">
        {[["Questions asked", 4], ["Answers received", 9], ["Mentors", 3]].map(([label, value]) => (
          <div key={label} className="rounded border border-border bg-surface p-5">
            <Eyebrow>{label}</Eyebrow>
            <p className="mt-2 text-3xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 rounded border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold">Account</h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-subtle">Email</dt><dd>{currentUser.email}</dd>
          <dt className="text-subtle">Role</dt><dd>Mentee</dd>
        </dl>
      </div>
    </>
  );
}
