import Feed from "./_components/Feed";
import Today from "./_components/Today";
import { Avatar, Eyebrow, Icon } from "./_components/ui";
import { currentUser } from "./_components/data";

export default function HomePage() {
  return (
    <>
      <Eyebrow><Today /></Eyebrow>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Welcome back, {currentUser.name.split(" ")[0]}</h1>

      <form id="ask" className="mt-12 flex items-center gap-4 rounded border border-border bg-surface p-5">
        <Avatar initials={currentUser.initials} />
        <input
          name="question"
          placeholder="Ask the community anything…"
          className="flex-1 bg-transparent text-lg outline-none placeholder:text-subtle"
        />
        <button type="submit" aria-label="Ask" className="flex h-12 w-12 items-center justify-center rounded bg-primary text-on-primary hover:bg-primary-hover">
          <Icon name="plus" className="h-6 w-6" />
        </button>
      </form>

      <Feed />
    </>
  );
}
