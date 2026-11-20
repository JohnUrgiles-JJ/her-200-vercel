"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Avatar, Icon } from "./ui";
import { currentUser } from "./data";

const nav = [
  { href: "/main", label: "Home", icon: "home", badge: 0 },
  { href: "/main/messages", label: "Messages", icon: "chat", badge: 3 },
  { href: "/main/notifications", label: "Notifications", icon: "bell", badge: 7 },
  { href: "/main/my-mentors", label: "My mentors", icon: "users", badge: 0 },
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-border bg-surface px-5 py-8 md:flex">
      <Link href="/main" className="flex items-center gap-2 px-2 text-xl font-semibold tracking-tight">
        <span className="relative h-7 w-7">
          <span className="absolute left-0 top-0 h-4 w-4 rounded-full bg-secondary" />
          <span className="absolute right-0 top-0 h-4 w-4 rounded-full bg-primary" />
          <span className="absolute bottom-0 left-1.5 h-4 w-4 rounded-full bg-border-strong" />
        </span>
        connect<span className="text-primary">HER</span>
      </Link>

      <p className="mt-12 px-2 text-xs font-medium uppercase tracking-[0.2em] text-subtle">Your space</p>
      <nav className="mt-3 space-y-1">
        {nav.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg border-l-2 px-3 py-3 font-medium ${
                active ? "border-primary bg-surface-muted text-foreground" : "border-transparent text-muted hover:bg-surface-muted"
              }`}
            >
              <Icon name={item.icon} />
              <span className="flex-1">{item.label}</span>
              {item.badge > 0 && (
                <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-surface-sunken px-1.5 text-xs font-semibold">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <Link
        href="/main/profile"
        className={`mt-auto flex items-center gap-3 rounded-lg p-2 hover:bg-surface-muted ${pathname === "/main/profile" ? "bg-surface-muted" : ""}`}
      >
        <Avatar initials={currentUser.initials} size="sm" />
        <span className="flex-1">
          <span className="block font-medium">{currentUser.name}</span>
          <span className="block text-sm text-subtle">View profile</span>
        </span>
        <Icon name="dots" className="h-5 w-5 text-muted" />
      </Link>
    </aside>
  );
}
