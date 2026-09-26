import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiRequestError } from "@/lib/api";

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: "error",
      json: async () => body,
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api.health", () => {
  it("parses a successful response", async () => {
    mockFetchOnce(200, { status: "ok", live_mode_available: false });
    const result = await api.health();
    expect(result.status).toBe("ok");
  });
});

describe("error handling", () => {
  it("throws ApiRequestError with code/message/hint on a non-ok response", async () => {
    mockFetchOnce(422, { code: "estimate_failed", message: "bad plan", hint: "fix it" });
    await expect(api.estimate({ queries: [], cities: [], languages: [] })).rejects.toMatchObject({
      code: "estimate_failed",
      message: "bad plan",
      hint: "fix it",
      status: 422,
    });
  });

  it("wraps a network failure as a network_error ApiRequestError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    try {
      await api.health();
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiRequestError);
      expect((err as ApiRequestError).code).toBe("network_error");
    }
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => {
          throw new SyntaxError("not json");
        },
      }),
    );
    await expect(api.health()).rejects.toMatchObject({ code: "unknown_error" });
  });
});

describe("api.pollAudit", () => {
  it("returns immediately once the job is completed", async () => {
    mockFetchOnce(200, { id: "abc", status: "completed", progress: {}, result: { is_demo_data: true }, error: null });
    const job = await api.pollAudit("abc", { intervalMs: 1, timeoutMs: 1000 });
    expect(job.status).toBe("completed");
  });

  it("polls again while pending, then resolves once completed", async () => {
    const responses = [
      { id: "abc", status: "pending", progress: {}, result: null, error: null },
      { id: "abc", status: "running", progress: { completed_queries: 0 }, result: null, error: null },
      { id: "abc", status: "completed", progress: {}, result: { is_demo_data: true }, error: null },
    ];
    let call = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async () => ({
        ok: true,
        status: 200,
        statusText: "ok",
        json: async () => responses[Math.min(call++, responses.length - 1)],
      })),
    );
    const job = await api.pollAudit("abc", { intervalMs: 1, timeoutMs: 1000 });
    expect(job.status).toBe("completed");
    expect(call).toBe(3);
  });

  it("throws a poll_timeout error if the job never completes in time", async () => {
    mockFetchOnce(200, { id: "abc", status: "running", progress: {}, result: null, error: null });
    await expect(api.pollAudit("abc", { intervalMs: 1, timeoutMs: 5 })).rejects.toMatchObject({
      code: "poll_timeout",
    });
  });
});
