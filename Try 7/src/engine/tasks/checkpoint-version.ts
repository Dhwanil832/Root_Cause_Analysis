import type { EngineInput, EngineState } from '../types';

/** No implicit compatibility override. Migration must form an auditable chain
 * from the immutable input version, otherwise dispatch still refuses the run. */
export function checkpointVersion(input: EngineInput, state: EngineState|null) {
  let version=input.engineVersion;
  for(const migration of state?.executionMigrations||[]) {
    if(migration.from!==version || !migration.reason.trim() || !/^[a-f0-9]{64}$/.test(migration.checkpointHash))
      throw Error('Invalid checkpoint migration lineage.');
    version=migration.to;
  }
  return version;
}
