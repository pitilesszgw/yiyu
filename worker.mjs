const FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScjINC9CbqMsOR3sbCdIb-lFAT80P395F_kjyaL4M-QBjLTNw/formResponse?hl=en";
const INTERESTS = ["了解产品", "预约演示", "获取报价", "合作咨询"];
const FIELDS = {
  "entry.659206793": 100,
  "entry.649232157": 32,
  "entry.1259853372": 200,
  "entry.1105577049": 20,
  "entry.853679754": 2000,
};

function json(body, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

export async function submitLead(request) {
  if (request.method !== "POST") {
    return new Response(null, { status: 405, headers: { Allow: "POST" } });
  }
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) {
    return json({ ok: false, message: "请从官网提交需求。" }, 403);
  }
  if (!request.headers.get("Content-Type")?.startsWith("application/x-www-form-urlencoded")) {
    return json({ ok: false, message: "提交格式不正确，请刷新页面后重试。" }, 415);
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).length > 32768) {
    return json({ ok: false, message: "填写内容过长，请精简后重试。" }, 413);
  }
  const input = new URLSearchParams(body);
  const data = new URLSearchParams();
  for (const [name, limit] of Object.entries(FIELDS)) {
    const value = (input.get(name) || "").trim();
    if (value.length > limit) {
      return json({ ok: false, message: "填写内容过长，请精简后重试。" }, 400);
    }
    data.set(name, value);
  }
  if (!data.get("entry.659206793") || data.get("entry.649232157").length < 6 ||
      !INTERESTS.includes(data.get("entry.1105577049")) || input.get("consent") !== "on") {
    return json({ ok: false, message: "请补全称呼、有效联系电话并勾选信息使用同意。" }, 400);
  }
  data.set("fvv", "1");
  data.set("pageHistory", "0");
  data.set("entry.1105577049_sentinel", "");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);
  try {
    const response = await fetch(FORM_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Accept-Language": "en-US,en;q=0.9",
      },
      body: data.toString(),
      signal: controller.signal,
      redirect: "follow",
    });
    const html = await response.text();
    const confirmed = /<div\b[^>]*class=["'][^"']*\bvHW8K\b[^"']*["'][^>]*>\s*Your response has been recorded\./i.test(html);
    if (!response.ok || !confirmed) {
      return json({ ok: false, message: "暂未确认提交结果，请勿重复提交，建议通过微信联系我们。" }, 502);
    }
    return json({ ok: true });
  } catch {
    return json({ ok: false, message: "暂未确认提交结果，请勿重复提交，建议通过微信联系我们。" }, controller.signal.aborted ? 504 : 502);
  } finally {
    clearTimeout(timer);
  }
}

export default {
  async fetch(request, env) {
    if (new URL(request.url).pathname === "/api/lead") return submitLead(request);
    return env.ASSETS.fetch(request);
  },
};
