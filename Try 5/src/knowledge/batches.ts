/** Bound individual operations, never the number of sources investigated. */
export function batchesBySize<T>(items: T[], maxCharacters = 18_000, maxItems = 8): T[][] {
  const batches: T[][] = [];
  let batch: T[] = [], characters = 0;
  for (const item of items) {
    const size = JSON.stringify(item).length;
    if (batch.length && (characters + size > maxCharacters || batch.length >= maxItems)) {
      batches.push(batch); batch = []; characters = 0;
    }
    batch.push(item); characters += size;
  }
  if (batch.length) batches.push(batch);
  return batches;
}
