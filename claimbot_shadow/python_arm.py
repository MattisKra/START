import time

from claimbot import config, ensemble


def run(case, trace):
    members = ensemble.members(selective_by_default=True)
    trace.log("configured", readers=[m.name for m in members],
              weights={m.name: m.weight for m in members}, charge_factor=config.A_MEDIAN_MULT,
              limit_factor=config.B_MEDIAN_MULT, reject_p=config.REJECT_P,
              price_references=bool(case.refs), attached_image_count=len(case.image_blobs))
    seen = []

    def update(prices, done, total, member, estimate, meta):
        seen.append(member.name)
        evidence = {line.index: line.model_dump() for line in estimate.lines}
        lines = [dict(index=p.index + config.INDEX_BASE, charge_price=p.a, acceptance_limit=p.b,
                      median=p.t_median, validity=p.q, spread=p.sigma,
                      arriving_reader=evidence.get(p.index)) for p in prices]
        try:
            trace.record(lines, dict(member=member.name, arrived=list(seen), meta=meta,
                                     damage_summary=estimate.damage_summary, policy_notes=estimate.policy_notes))
        except ValueError as exc:
            trace.log("invalid_revision", member=member.name, error=str(exc), lines=lines)

    deadline = time.monotonic() + max(0., trace.start + 60 - time.time())
    _, failures, pending = ensemble.run(case, deadline, update, members)
    trace.log("finished", failures=[dict(member=m.name, error=message) for m, message in failures],
              pending=[m.name for m in pending])
