// A batching preference, NOT an admission limit. Larger requests are allowed;
// the configured model/provider still has its own finite context capacity.
// No stage rejects or truncates a request merely because it exceeds this target.
export const VERIFICATION_PACKET_TARGET_CHARACTERS = 60_000;
