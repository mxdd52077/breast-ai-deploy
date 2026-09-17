import assert from "node:assert/strict";
import test from "node:test";
import { relatedDatedFacts } from "./scheduleReview.ts";

test("a broad OCR quote does not attach item 2's date to item 3", () => {
  const second = {
    id: "second",
    page: 1,
    value: "术后第五天同时引流液清凉，乳房无红肿可拔除引流管",
    quote: "术后第五天同时引流液清凉，乳房无红肿可拔除引流管",
    scheduled_date: "2024-12-31",
  };
  const third = {
    id: "third",
    page: 1,
    value: "术后两周杜正贵教授门诊就诊",
    quote: "术后两周杜正贵教授门诊就诊",
    scheduled_date: "2025-01-09",
  };
  const parent = {
    id: "parent",
    page: 1,
    value: "术后复查：术后两周杜正贵教授门诊就诊（已约号），后每3–6月复查一次",
    quote: `${second.quote}；${third.quote}（已约号），后每3–6月复查一次`,
    scheduled_date: null,
  };
  assert.deepEqual(relatedDatedFacts(parent, [parent, second, third]).map((fact) => fact.id), ["third"]);
  assert.deepEqual(relatedDatedFacts({ ...parent, value: second.value }, [parent, second, third]).map((fact) => fact.id), ["second"]);
  assert.deepEqual(relatedDatedFacts({ ...parent, scheduled_date: "2025-01-09" }, [parent, second, third]), []);
});
