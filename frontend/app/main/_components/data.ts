// Placeholder data until the API is wired up.
export const currentUser = { name: "Alex Smith", initials: "AJ", headline: "Computer science student", email: "alex@example.com" };

export const mentors = [
  { initials: "NK", name: "Nina Kim", role: "Creative director", company: "Adobe", match: 98, fields: ["Brand design", "Art direction"] },
  { initials: "OM", name: "Osei Mensah", role: "Product lead", company: "Are.na", match: 94, fields: ["Product", "UX"] },
  { initials: "SV", name: "Sofia Vega", role: "Type designer", company: "Monotype", match: 91, fields: ["Typography", "Visual design"] },
];

export const events = [
  { day: "26", month: "JUN", title: "Making work that feels like you", meta: "Live studio chat · 7 PM" },
  { day: "02", month: "JUL", title: "Portfolio swap: brand edition", meta: "Community session · 6 PM" },
];

export const posts = [
  {
    initials: "MR", author: "Maya Rodriguez", meta: "Brand design student · 18m", tag: "Creative direction",
    title: "How do you build a portfolio that feels cohesive without making every project look the same?",
    body: "I'm applying for junior brand roles and my work feels a little all over the place. Would love to hear how creative directors think about range vs. consistency.",
    likes: 42, comments: 12,
  },
  {
    initials: "JT", author: "Jordan Taylor", meta: "First-gen CS student · 1h", tag: "Career switching",
    title: "How do I break into UX design without a design degree?",
    body: "I'm in computer science but I keep gravitating to the design side of projects. Where should I start?",
    likes: 31, comments: 8,
  },
];

export const conversations = [
  { initials: "NK", name: "Nina Kim", preview: "Happy to look at your portfolio this week!", time: "2m", unread: true },
  { initials: "OM", name: "Osei Mensah", preview: "Great question — here's how I'd approach it…", time: "1h", unread: true },
  { initials: "SV", name: "Sofia Vega", preview: "Thanks for the follow-up.", time: "Mon", unread: false },
];

export const notifications = [
  { initials: "NK", text: "Nina Kim answered your question “How do I break into UX design without a design degree?”", time: "2m", unread: true },
  { initials: "OM", text: "Osei Mensah was matched to your question.", time: "1h", unread: true },
  { initials: "SV", text: "Sofia Vega accepted your mentor request.", time: "Yesterday", unread: false },
  { initials: "MR", text: "Maya Rodriguez liked your comment.", time: "2d", unread: false },
];
