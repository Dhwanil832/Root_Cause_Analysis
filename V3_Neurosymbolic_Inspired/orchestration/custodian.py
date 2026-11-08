"""A fixed, model-independent simulated custodian for closed-loop synthetic replays.

The model under test never sees or influences this object. Everything it does is a
pure function of its holdings file, a clock, and the text of the requests put to it,
so two models run against the same custodian face the same simulated world:

- **Replies** to a request are chosen by word overlap between the request text and
  each held document's topic words (at least two shared words). A request that
  matches a held document that is not yet available waits; one that matches only a
  prepared statement gets that statement; the rest get an explicit "no record"
  note, except that every ``off_topic_every``-th unmatched request is answered with
  an unrelated document, to exercise the case where the reply is not what was asked.
- **Unprompted arrivals**: each document has an ``unprompted_at`` time; if nobody has
  asked for it by then it arrives on its own, whenever the system happens to be.
- **Time**: one unit per completed role job. While the system is idle the driver
  jumps the clock to the next due event, which models waiting for a reply.

This is a scenario simulator, not a person, and its realism against real custodians
has not been validated.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_STOP = frozenset("""a an and are as at be been but by for from had has have in into is it its of on or that
the their there these this those to was were which with not no than so such also please provide
need needed record records any all you your can could would should may""".split())
MIN_SHARED = 2


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def words(text: str) -> frozenset[str]:
    return frozenset(_stem(w) for w in re.findall(r"[a-z0-9]+", str(text).lower())
                     if w not in _STOP and len(w) > 1)


@dataclass(frozen=True)
class Holding:
    item_id: str
    available_at: int
    unprompted_at: int
    topics: frozenset[str]


@dataclass(frozen=True)
class Statement:
    statement_id: str
    topics: frozenset[str]
    text: str


@dataclass(frozen=True)
class RequestView:
    request_id: str
    text: str
    slots: tuple[tuple[str, str], ...] = ()      # (slot_id, description)


@dataclass
class Custodian:
    holdings: tuple[Holding, ...]
    statements: tuple[Statement, ...] = ()
    reply_delay: int = 6
    off_topic_every: int = 3
    delivered: set[str] = field(default_factory=set)
    _first_seen: dict[str, int] = field(default_factory=dict)
    _answered: set[str] = field(default_factory=set)
    _unmatched: int = 0

    @classmethod
    def from_file(cls, path: Path) -> "Custodian":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        policy = data.get("policy", {})
        return cls(
            holdings=tuple(Holding(d["item_id"], int(d["available_at"]), int(d["unprompted_at"]),
                                   words(" ".join(d["topics"]))) for d in data["documents"]),
            statements=tuple(Statement(s["statement_id"], words(" ".join(s["topics"])), s["text"])
                             for s in data.get("statements", [])),
            reply_delay=int(policy.get("reply_delay", 6)),
            off_topic_every=int(policy.get("off_topic_every", 3)),
        )

    # ------------------------------------------------------------------ matching
    def _matches(self, request: RequestView) -> list[tuple[int, Holding]]:
        asked = words(request.text)
        scored = [(len(asked & h.topics), h) for h in self.holdings]
        return sorted(((s, h) for s, h in scored if s >= MIN_SHARED),
                      key=lambda row: (-row[0], row[1].item_id))

    def _answered_slots(self, request: RequestView, chosen: list[Holding]) -> list[str]:
        covered = frozenset().union(*(h.topics for h in chosen)) if chosen else frozenset()
        return [sid for sid, desc in request.slots if len(words(desc) & covered) >= MIN_SHARED]

    # ------------------------------------------------------------------ stepping
    def step(self, clock: int, open_requests: list[RequestView]) -> list[dict[str, Any]]:
        """Everything the custodian does at this moment. Idempotent per request and document."""
        actions: list[dict[str, Any]] = []
        for request in open_requests:
            if request.request_id in self._answered:
                continue
            seen = self._first_seen.setdefault(request.request_id, clock)
            if clock < seen + self.reply_delay:
                continue
            matches = self._matches(request)
            available = [h for s, h in matches if h.available_at <= clock and h.item_id not in self.delivered]
            if available:
                chosen = available[:2]
                self.delivered.update(h.item_id for h in chosen)
                slots = self._answered_slots(request, chosen)
                actions.append({"kind": "documents", "request_id": request.request_id,
                                "item_ids": [h.item_id for h in chosen], "answered_slot_ids": slots,
                                "stance": "exact" if request.slots and len(slots) == len(request.slots) else "partial"})
            elif any(h.item_id not in self.delivered and h.available_at > clock for _s, h in matches):
                continue                                    # held but not yet retrieved: keep waiting
            else:
                statement = self._best_statement(request)
                if statement:
                    actions.append({"kind": "statement", "request_id": request.request_id,
                                    "statement_id": statement.statement_id, "text": statement.text,
                                    "stance": "partial"})
                else:
                    self._unmatched += 1
                    spare = sorted((h for h in self.holdings
                                    if h.available_at <= clock and h.item_id not in self.delivered),
                                   key=lambda h: h.item_id)
                    if self.off_topic_every and self._unmatched % self.off_topic_every == 0 and spare:
                        self.delivered.add(spare[0].item_id)
                        actions.append({"kind": "documents", "request_id": request.request_id,
                                        "item_ids": [spare[0].item_id], "answered_slot_ids": [],
                                        "stance": "off_topic"})
                    else:
                        actions.append({"kind": "no_record", "request_id": request.request_id,
                                        "stance": "unknown"})
            self._answered.add(request.request_id)
        due = [h for h in self.holdings if h.unprompted_at <= clock and h.item_id not in self.delivered]
        if due:
            due.sort(key=lambda h: (h.unprompted_at, h.item_id))
            self.delivered.update(h.item_id for h in due)
            actions.append({"kind": "unprompted", "item_ids": [h.item_id for h in due]})
        return actions

    def _best_statement(self, request: RequestView) -> Statement | None:
        asked = words(request.text)
        scored = sorted(((len(asked & s.topics), s.statement_id, s) for s in self.statements), key=lambda r: (-r[0], r[1]))
        return scored[0][2] if scored and scored[0][0] >= MIN_SHARED else None

    def next_due(self, clock: int, open_requests: list[RequestView]) -> int | None:
        """Next clock value at which something will happen, or None if nothing ever will."""
        times: list[int] = []
        for h in self.holdings:
            if h.item_id not in self.delivered and h.unprompted_at > clock:
                times.append(h.unprompted_at)
        for request in open_requests:
            if request.request_id in self._answered:
                continue
            seen = self._first_seen.get(request.request_id, clock)
            ready = seen + self.reply_delay
            matches = [h for _s, h in self._matches(request) if h.item_id not in self.delivered]
            if matches and all(h.available_at > clock for h in matches):
                ready = max(ready, min(h.available_at for h in matches))
            times.append(ready if ready > clock else clock + 1)
        return min(times) if times else None
