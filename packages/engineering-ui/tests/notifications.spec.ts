// SPDX-License-Identifier: MIT
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createNotificationQueue } from "../src/workspace/notifications";

describe("createNotificationQueue", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("times out transient notices but keeps errors", () => {
    const queue = createNotificationQueue({ defaultTimeout: 1000 });
    queue.notify({ tone: "success", title: "Saved" });
    queue.notify({ tone: "danger", title: "Analysis failed" });
    vi.advanceTimersByTime(1001);
    expect(queue.items.value.map((item) => item.title)).toEqual(["Analysis failed"]);
  });

  it("replaces a notice with the same id and dismisses by id", () => {
    const queue = createNotificationQueue();
    queue.notify({ id: "job", tone: "info", title: "Running" });
    queue.notify({ id: "job", tone: "info", title: "Still running" });
    expect(queue.items.value).toHaveLength(1);
    expect(queue.items.value[0]?.title).toBe("Still running");
    queue.dismiss("job");
    expect(queue.items.value).toHaveLength(0);
  });

  it("drops the oldest non-error notices beyond the limit", () => {
    const queue = createNotificationQueue({ limit: 2 });
    queue.notify({ tone: "danger", title: "E1" });
    queue.notify({ tone: "info", title: "I1" });
    queue.notify({ tone: "info", title: "I2" });
    expect(queue.items.value.map((item) => item.title)).toEqual(["E1", "I2"]);
    queue.clear();
    expect(queue.items.value).toHaveLength(0);
  });
});
