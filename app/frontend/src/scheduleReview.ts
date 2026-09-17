import type { Fact } from "./api";

type ReviewFact = Pick<Fact, "id" | "page" | "value" | "quote" | "scheduled_date">;

function comparableText(value: string) {
  return value.replace(/[\s\p{P}\p{S}]/gu, "");
}

export function relatedDatedFacts<T extends ReviewFact>(current: T | undefined, facts: T[]): T[] {
  if (!current || current.scheduled_date) return [];
  const itemText = comparableText(current.value);
  if (!itemText) return [];
  return facts.filter((fact) => {
    const candidateText = comparableText(fact.quote);
    return fact.id !== current.id && fact.page === current.page && !!fact.scheduled_date &&
      candidateText.length >= 8 && itemText.includes(candidateText);
  });
}
