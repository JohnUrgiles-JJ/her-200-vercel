const menteeSteps = [
  "Sign up and choose Mentee.",
  "Type your question in the “Ask a question” box.",
  "AI picks the top 3 mentors, each with a one-line reason.",
  "Your question reaches them instantly by email and live in-app.",
  "Answers appear live on your dashboard.",
];

const mentorSteps = [
  "Sign up and choose Mentor.",
  "Add your headline, company, fields, topics, short bio and years of experience.",
  "Agree to answer questions about your experience and fields.",
  "Get questions by email and live notification when logged in.",
  "Answer right from your inbox — minutes, not hours.",
];

const exampleMatches = [
  { name: "Priya S.", role: "Senior UX Designer · Self-taught", reason: "Moved into UX from psychology with no design degree." },
  { name: "Maya L.", role: "Product Designer · Bootcamp grad", reason: "Built a portfolio through a bootcamp and freelance work." },
  { name: "Ana R.", role: "UX Research Lead", reason: "Hires junior designers and reviews portfolios regularly." },
];

const impact = [
  { title: "Lower barriers", body: "No network or cold message needed to reach a mentor." },
  { title: "Faster answers", body: "Questions go straight to mentors who've said they're happy to help." },
  { title: "More students in STEM", body: "Support at the moment it matters keeps students on their path." },
  { title: "Minutes, not hours", body: "Mentors spend minutes per question, not hours of back-and-forth." },
];

function Steps({ title, steps, accent }: { title: string; steps: string[]; accent: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-8 dark:border-zinc-800 dark:bg-zinc-950">
      <h3 className="text-xl font-semibold">{title}</h3>
      <ol className="mt-6 space-y-4">
        {steps.map((s, i) => (
          <li key={s} className="flex gap-4">
            <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white ${accent}`}>
              {i + 1}
            </span>
            <span className="text-zinc-600 dark:text-zinc-400">{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex flex-1 flex-col font-sans">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-xl font-bold tracking-tight">
          Connect<span className="text-fuchsia-600">HER</span>
        </span>
        <nav className="flex items-center gap-6 text-sm font-medium">
          <a href="#how" className="hidden text-zinc-600 hover:text-foreground sm:inline dark:text-zinc-400">How it works</a>
          <a href="#impact" className="hidden text-zinc-600 hover:text-foreground sm:inline dark:text-zinc-400">Impact</a>
          <a href="/login" className="text-zinc-600 hover:text-foreground dark:text-zinc-400">Log in</a>
          <a href="/signup" className="rounded-full bg-fuchsia-600 px-4 py-2 text-white hover:bg-fuchsia-700">Sign up</a>
        </nav>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-2">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-fuchsia-600">
              Mentorship without the network
            </p>
            <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Ask any career or STEM question. We&apos;ll find who should answer it.
            </h1>
            <p className="mt-6 text-lg leading-8 text-zinc-600 dark:text-zinc-400">
              ConnectHER uses AI to route your question to the mentors best placed to answer it.
              They&apos;re notified instantly by email and live in-app — no cold messages required.
            </p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <a href="/signup?role=mentee" className="flex h-12 items-center justify-center rounded-full bg-fuchsia-600 px-6 font-medium text-white hover:bg-fuchsia-700">
                Ask a question
              </a>
              <a href="/signup?role=mentor" className="flex h-12 items-center justify-center rounded-full border border-zinc-300 px-6 font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900">
                Become a mentor
              </a>
            </div>
          </div>

          {/* Example match preview */}
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Your question</p>
            <p className="mt-2 rounded-xl bg-white p-4 font-medium dark:bg-zinc-900">
              How do I break into UX design without a design degree?
            </p>
            <p className="mt-6 text-xs font-semibold uppercase tracking-wider text-zinc-500">Top 3 matched mentors</p>
            <ul className="mt-2 space-y-3">
              {exampleMatches.map((m) => (
                <li key={m.name} className="rounded-xl bg-white p-4 dark:bg-zinc-900">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-semibold">{m.name}</span>
                    <span className="text-xs text-zinc-500">{m.role}</span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{m.reason}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Problem */}
        <section className="bg-zinc-50 py-20 dark:bg-zinc-950">
          <div className="mx-auto max-w-3xl px-6 text-center">
            <h2 className="text-3xl font-bold tracking-tight">Too many questions go unasked</h2>
            <p className="mt-6 text-lg leading-8 text-zinc-600 dark:text-zinc-400">
              First-generation students, women, and students from marginalized communities in STEM
              often don&apos;t have a professional network. They don&apos;t know who to ask, or how to ask —
              and cold outreach is intimidating.
            </p>
            <p className="mt-4 text-lg leading-8 text-zinc-600 dark:text-zinc-400">
              With ConnectHER, you ask once. AI finds the right mentors — people who have already said
              they&apos;re happy to answer — and delivers your question to them.
            </p>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-center text-3xl font-bold tracking-tight">How it works</h2>
          <div className="mt-12 grid gap-8 md:grid-cols-2">
            <Steps title="For mentees" steps={menteeSteps} accent="bg-fuchsia-600" />
            <Steps title="For mentors" steps={mentorSteps} accent="bg-violet-600" />
          </div>
        </section>

        {/* Impact */}
        <section id="impact" className="bg-zinc-50 py-20 dark:bg-zinc-950">
          <div className="mx-auto max-w-6xl px-6">
            <h2 className="text-center text-3xl font-bold tracking-tight">The impact</h2>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {impact.map((i) => (
                <div key={i.title} className="rounded-2xl bg-white p-6 dark:bg-zinc-900">
                  <h3 className="font-semibold">{i.title}</h3>
                  <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{i.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="mx-auto max-w-3xl px-6 py-20 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Your question deserves an answer</h2>
          <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400">
            Join as a mentee to ask, or as a mentor to help the next generation in STEM.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-4 sm:flex-row">
            <a href="/signup?role=mentee" className="flex h-12 items-center justify-center rounded-full bg-fuchsia-600 px-6 font-medium text-white hover:bg-fuchsia-700">
              Join as a mentee
            </a>
            <a href="/signup?role=mentor" className="flex h-12 items-center justify-center rounded-full border border-zinc-300 px-6 font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900">
              Join as a mentor
            </a>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-200 py-8 text-center text-sm text-zinc-500 dark:border-zinc-800">
        © 2026 ConnectHER
      </footer>
    </div>
  );
}
