import assert from "node:assert/strict";
import { test } from "node:test";
import worker, { submitLead } from "./worker.mjs";

const valid = {
  "entry.659206793": "测试联系人",
  "entry.649232157": "13800000000",
  "entry.1259853372": "测试公司",
  "entry.1105577049": "预约演示",
  "entry.853679754": "测试说明",
  consent: "on",
};
const confirmation = '<div class="vHW8K">Your response has been recorded.</div>';

function request(data = valid, headers = {}) {
  return new Request("https://www.yiyufish.com/api/lead", {
    method: "POST",
    headers: { Origin: "https://www.yiyufish.com", ...headers },
    body: new URLSearchParams(data),
  });
}

test("requires Google's confirmation and forwards all five fields", async (t) => {
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.match(url, /\/formResponse\?hl=en$/);
    assert.equal(options.method, "POST");
    const posted = new URLSearchParams(options.body);
    for (const [key, value] of Object.entries(valid)) {
      if (key !== "consent") assert.equal(posted.get(key), value);
    }
    assert.equal(posted.has("consent"), false);
    assert.equal(posted.get("pageHistory"), "0");
    return new Response(confirmation);
  });
  const response = await submitLead(request());
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(await response.json(), { ok: true });
});

test("a loaded HTTP 200 validation/login page never counts as saved", async (t) => {
  for (const html of [
    '<form><input name="entry.659206793"><span>This is required</span></form>',
    '<html>Sign in to Google</html>',
    '<script>const message = "Your response has been recorded."</script>',
    '<div class="vHW8K">This form is no longer accepting responses.</div>',
  ]) {
    const mock = t.mock.method(globalThis, "fetch", async () => new Response(html));
    const response = await submitLead(request());
    assert.equal(response.status, 502);
    assert.equal((await response.json()).ok, false);
    mock.mock.restore();
  }
});

test("one contact is enough and its type is recorded", async (t) => {
  for (const [type, contact, expected] of [
    ["phone", "+86 13800000000", "+86 13800000000"],
    ["wechat", "wxid_demo", "微信号：wxid_demo"],
    ["telegram", "@demo", "TG号：@demo"],
  ]) {
    const mock = t.mock.method(globalThis, "fetch", async (_url, options) => {
      const posted = new URLSearchParams(options.body);
      assert.equal(posted.get("entry.649232157"), expected);
      assert.equal(posted.has("contact_type"), false);
      return new Response(confirmation);
    });
    assert.equal((await submitLead(request({ ...valid, contact_type: type, "entry.649232157": contact }))).status, 200);
    mock.mock.restore();
  }
});

test("invalid contacts never reach Google", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => { throw new Error("must not send"); });
  for (const type of ["phone", "wechat", "telegram", "unknown", "toString", ""]) {
    for (const contact of ["", " ", "a".repeat(65)]) {
      assert.equal((await submitLead(request({ ...valid, contact_type: type, "entry.649232157": contact }))).status, 400);
    }
  }
  for (const type of ["unknown", "toString", ""]) {
    assert.equal((await submitLead(request({ ...valid, contact_type: type }))).status, 400);
  }
  assert.equal((await submitLead(request({ ...valid, contact_type: "phone", "entry.649232157": "1".repeat(33) }))).status, 400);
  assert.equal(mock.mock.callCount(), 0);
});

test("optional city preserves company and details", async (t) => {
  for (const [city, details, expected] of [
    [undefined, "说明", "说明"],
    ["   ", "说明", "说明"],
    [" 杭州 ", "说明", "公司所在城市：杭州\n补充说明：说明"],
    ["深圳", "", "公司所在城市：深圳"],
    ["a".repeat(100), "a".repeat(2000), `公司所在城市：${"a".repeat(100)}\n补充说明：${"a".repeat(2000)}`],
  ]) {
    const mock = t.mock.method(globalThis, "fetch", async (_url, options) => {
      const posted = new URLSearchParams(options.body);
      assert.equal(posted.get("entry.853679754"), expected);
      assert.equal(posted.get("entry.1259853372"), "");
      assert.equal(posted.has("company_city"), false);
      return new Response(confirmation);
    });
    const data = { ...valid, "entry.1259853372": "", "entry.853679754": details };
    if (city !== undefined) data.company_city = city;
    assert.equal((await submitLead(request(data))).status, 200);
    mock.mock.restore();
  }
});

test("oversized city never reaches Google", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => { throw new Error("must not send"); });
  assert.equal((await submitLead(request({ ...valid, company_city: "a".repeat(101) }))).status, 400);
  assert.equal(mock.mock.callCount(), 0);
});

test("upstream HTTP errors and network failures do not report success", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => new Response(confirmation, { status: 500 }));
  assert.equal((await submitLead(request())).status, 502);
  mock.mock.restore();
  t.mock.method(globalThis, "fetch", async () => { throw new TypeError("network unavailable"); });
  assert.equal((await submitLead(request())).status, 502);
});

test("stalled upstream is aborted in six seconds without retrying", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let start;
  const started = new Promise((resolve) => { start = resolve; });
  let calls = 0;
  t.mock.method(globalThis, "fetch", (_url, { signal }) => {
    calls++;
    start();
    return new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    });
  });
  const pending = submitLead(request());
  await started;
  t.mock.timers.tick(6000);
  const response = await pending;
  assert.equal(response.status, 504);
  assert.match((await response.json()).message, /暂未确认/);
  assert.equal(calls, 1);
});

test("invalid/oversized fields and missing consent never reach Google", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => { throw new Error("must not send"); });
  for (const data of [
    { ...valid, "entry.659206793": " " },
    { ...valid, "entry.649232157": "123" },
    { ...valid, "entry.1105577049": "无效选项" },
    { ...valid, consent: "" },
    { ...valid, "entry.853679754": "a".repeat(2001) },
  ]) assert.equal((await submitLead(request(data))).status, 400);
  assert.equal((await submitLead(request({ ...valid, extra: "a".repeat(32769) }))).status, 413);
  assert.equal(mock.mock.callCount(), 0);
});

test("cross-origin and unsupported requests are rejected", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => { throw new Error("must not send"); });
  assert.equal((await submitLead(request(valid, { Origin: "https://other.example" }))).status, 403);
  assert.equal((await submitLead(new Request("https://www.yiyufish.com/api/lead"))).status, 405);
  assert.equal((await submitLead(request(valid, { "Content-Type": "application/json" }))).status, 415);
  assert.equal(mock.mock.callCount(), 0);
});

test("the existing website continues through the assets binding", async () => {
  for (const path of ["/", "/yiyu", "/articles", "/static/images/wechat-contact-qr.png"]) {
    const req = new Request("https://www.yiyufish.com" + path);
    const response = await worker.fetch(req, {
      ASSETS: { fetch: async (received) => {
        assert.equal(received, req);
        return new Response("existing asset");
      } },
    });
    assert.equal(await response.text(), "existing asset");
  }
});
