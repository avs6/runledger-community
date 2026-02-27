// Server Component — fetches API health at request time (no caching)

interface HealthData {
  status: string;
  db: string;
  redis: string;
}

async function getHealth(): Promise<HealthData> {
  const apiUrl = process.env.API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    return (await res.json()) as HealthData;
  } catch {
    return { status: "unreachable", db: "unknown", redis: "unknown" };
  }
}

const statusClass = (s: string) =>
  s === "ok"
    ? "text-green-600 font-semibold"
    : s === "unknown"
      ? "text-yellow-600 font-semibold"
      : "text-red-600 font-semibold";

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-gray-50 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          RunLedger
        </h1>
        <p className="mt-2 text-lg text-gray-500">
          Billing-grade observability for AI agents.
        </p>
      </div>

      <div className="w-full max-w-xs rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-gray-400">
          System Status
        </h2>
        <dl className="space-y-3 text-sm">
          {(
            [
              ["API", health.status],
              ["Database", health.db],
              ["Redis", health.redis],
            ] as [string, string][]
          ).map(([label, value]) => (
            <div key={label} className="flex items-center justify-between">
              <dt className="text-gray-600">{label}</dt>
              <dd className={statusClass(value)}>{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <p className="text-xs text-gray-400">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="underline hover:text-gray-600"
        >
          API docs →
        </a>
      </p>
    </main>
  );
}
