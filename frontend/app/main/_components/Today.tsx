"use client";

import { useSyncExternalStore } from "react";

const noop = () => () => {};

export default function Today() {
  const today = useSyncExternalStore(
    noop,
    () => new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }),
    () => "",
  );
  return <>{today}</>;
}
