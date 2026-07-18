import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchRhessysChoropleth,
  fetchRhessysTimeSeries,
} from "../api/rhessysOutputsApi";

describe("RHESSys runtime queries", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts semantic choropleth dimensions without paths or SQL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ rows: [{ spatialId: 2, value: 4 }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const rows = await fetchRhessysChoropleth({
      runId: "runtime-run",
      scenario: "declared-scenario",
      variable: "declared-variable",
      spatialScale: "hillslope",
      year: 2001,
      signal: new AbortController().signal,
    });

    expect(rows).toEqual([{ spatialId: 2, value: 4 }]);
    const [, init] = fetchMock.mock.calls[0];
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      kind: "choropleth",
      scenario: "declared-scenario",
      variable: "declared-variable",
      spatial_scale: "hillslope",
      year: 2001,
    });
    expect(JSON.stringify(body)).not.toMatch(/parquet|dataset|select|sql/i);
  });

  it("posts semantic time-series dimensions to the same server endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          rows: [{ year: 2001, month: 2, day: 1, flow: 3.5 }],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const rows = await fetchRhessysTimeSeries({
      runId: "runtime-run",
      scenario: "declared-scenario",
      variables: ["flow"],
      spatialScale: "hillslope",
      signal: new AbortController().signal,
    });

    expect(rows[0].flow).toBe(3.5);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/watershed/runtime-run/rhessys/query",
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      kind: "time-series",
      scenario: "declared-scenario",
      variable: "flow",
      spatial_scale: "hillslope",
      year: null,
    });
  });
});
