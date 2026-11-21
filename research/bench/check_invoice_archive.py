"""Check printed positions, quantities and units in archived PDF and text against the live reader logs."""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from claimbot.case import pdf_text
from claimbot.refs import invoice_lines
from claimbot_multiagent.settlement import invoice_items


def archive(ref, game, filename):
    spec = f"{ref}:past-cases/case_{game:03d}/{filename}"
    return subprocess.check_output(["git", "show", spec], cwd=ROOT)


def check(ref, last_game):
    games = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
    units = Counter()
    checks = 0
    with TemporaryDirectory() as directory:
        for game in range(1, last_game + 1):
            pdf = Path(directory) / f"case_{game:03d}.pdf"
            pdf.write_bytes(archive(ref, game, "invoices.pdf"))
            layout = pdf_text(pdf)
            printed = invoice_items(layout)
            plain = invoice_items(archive(ref, game, "invoice.txt").decode())
            expected = sorted(int(p) for p in json.loads(archive(ref, game, "results.json"))["lines"])
            if [r.position for r in printed] != expected or len(invoice_lines(layout)) != len(expected):
                raise ValueError(f"Game {game} has unmatched PDF or reference positions")
            signature = [(r.position, r.quantity, r.unit.casefold()) for r in printed]
            if signature != [(r.position, r.quantity, r.unit.casefold()) for r in plain]:
                raise ValueError(f"Game {game} PDF and plain text disagree")
            units.update(r.unit for r in printed)
            for member in games.get(str(game), {}).get("members", []):
                lines = member["estimate"]["lines"]
                seen = [(l["index"] + 1, l["quantity_invoiced"], l["unit"].casefold()) for l in lines]
                if sorted(seen) != signature:
                    raise ValueError(f"Game {game} {member['member']} disagrees with the invoice")
                checks += len(lines)
    print(f"Games 1–{last_game}: {sum(units.values())} printed positions, {checks} logged reader lines.")
    print(dict(units))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ref", help="Git revision containing the archived cases")
    parser.add_argument("last_game", type=int)
    args = parser.parse_args()
    check(args.ref, args.last_game)
