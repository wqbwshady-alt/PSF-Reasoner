/* API client — fetch wrapper with server-error extraction. */

export async function api(url, opts) {
  const r = await fetch(url, opts);
  const b = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(b.detail || "请求失败");
  return b;
}
