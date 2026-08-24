"""Plan frozen bee confirmation updates for targets outside +/-0.005."""

from __future__ import annotations

import json

import m82lib as M


def main() -> None:
    confirm = json.loads(
        (M.HERE / "bee-confirm-results.json").read_text(encoding="utf-8")
    )
    ladder = json.loads(
        (M.HERE / "bee-ladder-results.json").read_text(encoding="utf-8")
    )
    entries = []
    for stack in M.BEE_SIBLINGS:
        for request in M.REQUESTS:
            key = f"{request:.2f}"
            target = confirm["stacks"][stack]["targets"][key]
            if target["confirmed"]:
                continue
            attempts = target.get(
                "attempts",
                [
                    {
                        "gate": target["solved_gate"],
                        "predicted_sigma_gain": target["predicted_sigma_gain"],
                    }
                ],
            )
            if len(attempts) >= 3:
                raise RuntimeError(f"{stack} {key}: registered two-update limit reached")
            points = [
                {
                    "gate": row["gate"],
                    "predicted_sigma_gain": row["predicted_sigma_gain"],
                }
                for row in ladder["stacks"][stack]["rows"]
            ]
            points.extend(attempts)
            points.sort(key=lambda row: row["gate"])
            solve = M.solve_gate(points, request)
            entries.append(
                {
                    "stack": stack,
                    "request": key,
                    "iteration": len(attempts),
                    "gate": solve["gate"],
                    "bracket": solve["bracket"],
                }
            )
    plan = {"entries": entries, "registered_update_limit": 2}
    (M.HERE / "bee-refine-plan.json").write_text(
        json.dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    for entry in entries:
        print(
            f"{entry['stack']} S={entry['request']} update={entry['iteration']} "
            f"gate={entry['gate']:.9f}"
        )
    print(f"REFINEMENTS={len(entries)}")


if __name__ == "__main__":
    main()
