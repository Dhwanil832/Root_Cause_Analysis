// Application guard, not a tokenizer or a guarantee for every provider's context window.
// Until larger-document batching is implemented, stop explicitly instead of presenting
// prefixes as complete documents or silently discarding sources to fit a prompt.
export const MAX_STAGE_PACKET_CHARACTERS = 60_000;

export function assertPacketFits(stage: string, packet: unknown) {
  const characters = JSON.stringify(packet).length;
  if (characters > MAX_STAGE_PACKET_CHARACTERS) {
    throw new Error(`${stage}: evidence packet has ${characters} characters; the current limit is ${MAX_STAGE_PACKET_CHARACTERS}. No evidence was truncated. Split the investigation input or implement explicit evidence batching before retrying.`);
  }
}
