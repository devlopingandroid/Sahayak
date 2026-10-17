export async function api<T = any>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers:
      data instanceof FormData ? {} : { "Content-Type": "application/json" },
    body:
      data === undefined
        ? undefined
        : data instanceof FormData
          ? data
          : JSON.stringify(data),
  }).catch(() => {
    throw new Error("Cannot reach the laptop backend. Start SAHAYAK on the laptop and keep its online launcher open.");
  });
  if ([502, 503, 504, 530].includes(response.status))
    throw new Error("The laptop backend is offline or reconnecting. Start SAHAYAK Online on the laptop, wait for deployment to finish, then refresh this page.");
  const text = await response.text();
  let value;
  try {
    value = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(
      `The server returned an invalid response (${response.status}). Please retry or restart the laptop server.`,
    );
  }
  if (!response.ok)
    throw new Error(value.error || `Request failed (${response.status})`);
  return value;
}

export const dateTime = (value: string) =>
  value
    ? new Date(value).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Not recorded";
export const timeOnly = (value: string) =>
  value
    ? new Date(value).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
export type Person = {
  id: string;
  name: string;
  relationship: string;
  introduction: string;
  photo_url: string | null;
  approved_samples: number;
  samples: { id: string; approved: number }[];
};
export type Memory = {
  id: string;
  first_seen: string;
  last_seen: string;
  location: string;
  location_source: string;
  people: { id: string; name: string; relationship?: string }[];
  objects: string[];
  image_url: string | null;
  verified: boolean;
  source: string;
  frames: number;
};
export type Routine = {
  id: string;
  title: string;
  time: string;
  steps: string[];
  step: number;
  enabled: boolean;
};
