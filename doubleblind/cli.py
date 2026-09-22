"""Command line: trace numbers, lint a review brief, build a packet."""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys

from . import packet as _packet
from . import trace as _trace

ALLOW_DEFAULT = "doubleblind-allow.txt"

# Above this many evidence values, coincidental matches stop being negligible.
POOL_WARN = 2000


# --------------------------------------------------------------- allow files

def read_allow(path: str | None, document: str) -> dict[str, str]:
    """Numbers exempt from tracing in ONE document, each with a stated reason.

    Two rules, both of which exist because the obvious design fails:

    * **A reason is mandatory.** An allow list without reasons becomes the place
      inconvenient numbers go to stop being checked, and nobody reads it again.
    * **Every entry names the document it applies to.** A repository-wide list
      silently disarms the check everywhere: the entry that exempts an
      illustrative figure in the README also exempted the fabricated figure in a
      test fixture, and the test that was supposed to see the fixture fail
      started passing. An exemption is about one claim in one document.

    Format: ``<document glob>  <number>  <reason>``
    """
    path = path or ALLOW_DEFAULT
    if not os.path.exists(path):
        return {}
    out: dict[str, str] = {}
    doc = os.path.normpath(document)
    base = os.path.basename(doc)
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines, 1):
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[2].strip():
            sys.exit(f"{path}:{i}: each line needs <document> <number> <reason> "
                     f"and the reason may not be empty -> {line.strip()!r}")
        pattern, number, reason = parts[0], parts[1], parts[2].strip()
        if fnmatch.fnmatch(doc, pattern) or fnmatch.fnmatch(base, pattern):
            out[number] = reason
    return out


# ----------------------------------------------------------------- reporting

def _c(s: str, code: str, on: bool) -> str:
    return f"\033[{code}m{s}\033[0m" if on else s


def cmd_trace(args: argparse.Namespace) -> int:
    colour = sys.stdout.isatty() and not args.no_color
    with open(args.document, encoding="utf-8", errors="replace") as fh:
        prose = fh.read()
    evidence = _trace.load_evidence(args.data)
    evidence += _trace.run_derivations(args.derive or [])
    if not evidence:
        print(f"no numbers found in {args.data} - nothing to trace against", file=sys.stderr)
        return 2
    allow = read_allow(args.allow, args.document)
    findings = _trace.trace(prose, evidence, allow)

    bad = [f for f in findings if f.verdict == "unsupported"]
    ok = [f for f in findings if f.verdict == "traced"]
    allowed = [f for f in findings if f.verdict == "allowed"]

    for f in bad:
        n = f.number
        print(_c(f"  UNSUPPORTED  {n.raw}", "31;1", colour) +
              f"   {args.document}:{n.line_no}")
        print(f"      {n.line[:100]}")
        if f.nearest:
            near = ", ".join(f"{v.value:g} ({os.path.basename(v.source)} {v.where})"
                             for v in f.nearest)
            print(f"      nearest committed values: {near}")
    if args.verbose:
        for f in ok:
            print(f"  ok           {f.number.raw:<12} <- {os.path.basename(f.matched.source)} "
                  f"{f.matched.where}{'' if f.scale == 'exact' else f.scale}")
        for f in allowed:
            print(f"  allowed      {f.number.raw:<12} {f.reason}")

    vague = _trace.vague_quantities(prose)
    if vague and not args.no_vague:
        print()
        for line_no, phrase, line in vague:
            print(_c(f"  UNCHECKABLE  \"{phrase}\"", "33;1", colour) +
                  f"   {args.document}:{line_no}")
            print(f"      {line[:100]}")
            print("      A quantity written as words cannot be traced to a file. "
                  "Write the number.")

    rescaled = sum(1 for f in ok if f.scale == " x100")
    print()
    print(f"{len(findings)} numbers in {args.document}; {len(ok)} traced"
          + (f" ({rescaled} of them only after reading a stored fraction as a percentage)"
             if rescaled else "")
          + f", {len(allowed)} allowed, {len(bad)} unsupported.")
    print(f"Evidence: {len(evidence)} values from "
          f"{len(set(v.source for v in evidence))} sources.")
    if len(evidence) > POOL_WARN:
        print()
        print(_c(f"  NOTE  {len(evidence)} values is a large pool.", "33;1", colour))
        print("      Raw per-item dumps contain every id, index and token count, so a")
        print("      round number in prose will match one of them by coincidence and be")
        print("      reported as traced. Point --data at summary files and use --derive")
        print("      for quantities a script recomputes, or this check gets weaker the")
        print("      more data you give it.")

    failed = bool(bad) or (bool(vague) and args.strict)
    if not failed:
        print()
        print("Every number here exists in a committed file. That is all this says.")
        print("It does not say the sentences around them are true: a correct number")
        print("inside a claim that does not follow from it passes this check every")
        print("time. Run the reviewer layer - `doubleblind review` - for that.")
    return 1 if failed else 0


def cmd_lint(args: argparse.Namespace) -> int:
    colour = sys.stdout.isatty() and not args.no_color
    with open(args.brief, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    leaks = _packet.intent_leaks(text)
    by_mech: dict[str, list] = {}
    for l in leaks:
        by_mech.setdefault(l.mechanism, []).append(l)
    for mech in sorted(by_mech):
        print(_c(f"  {mech}", "33;1", colour))
        for l in by_mech[mech]:
            print(f"      {args.brief}:{l.line_no}  \"{l.phrase}\"")
            print(f"      {l.line[:100]}")
        print(f"      -> {by_mech[mech][0].fix}")
        print()
    if leaks:
        print(f"{len(leaks)} phrase(s) in this brief tell the reviewer what to conclude.")
        print("A reviewer that knows the wanted answer is not a second opinion.")
        return 1
    print("No intent leakage found. The brief asks a question that cannot be")
    print("answered by agreeing.")
    return 0


def cmd_packet(args: argparse.Namespace) -> int:
    text = _packet.build_packet(args.document, args.data, )
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"packet: {args.output}  ({len(text)} bytes, "
              f"sha256 {_packet.packet_fingerprint(text)[:16]}...)")
    return 0


ADAPTERS = {
    "claude": (
        "Claude Code",
        "Agent(\n"
        "    subagent_type='general-purpose',\n"
        "    model='<a model that is NOT the one that wrote the artifact>',\n"
        "    run_in_background=False,\n"
        "    prompt=open('{packet}').read(),\n"
        ")\n"
        "# A sub-agent starts with no conversation history by construction, so\n"
        "# zero context needs no extra work. Pick a different model explicitly:\n"
        "# same model with a fresh context still carries the priors that wrote it.",
    ),
    "codex": (
        "Codex CLI",
        "codex exec --skip-git-repo-check < {packet}\n"
        "# `exec` starts a fresh session. Do not use `codex resume`.",
    ),
    "deepseek": (
        "DeepSeek",
        "curl -s https://api.deepseek.com/chat/completions \\\n"
        "  -H \"Authorization: Bearer $DEEPSEEK_API_KEY\" -H 'Content-Type: application/json' \\\n"
        "  -d \"$(jq -Rs '{{model:\"deepseek-reasoner\",messages:[{{role:\"user\",content:.}}]}}' {packet})\"\n"
        "# One request, one message. Sending history is what you are avoiding.",
    ),
    "kimi": (
        "Kimi / Moonshot",
        "curl -s https://api.moonshot.cn/v1/chat/completions \\\n"
        "  -H \"Authorization: Bearer $MOONSHOT_API_KEY\" -H 'Content-Type: application/json' \\\n"
        "  -d \"$(jq -Rs '{{model:\"kimi-k2-turbo-preview\",messages:[{{role:\"user\",content:.}}]}}' {packet})\"",
    ),
    "generic": (
        "any OpenAI-compatible endpoint",
        "curl -s \"$OPENAI_BASE_URL/chat/completions\" \\\n"
        "  -H \"Authorization: Bearer $OPENAI_API_KEY\" -H 'Content-Type: application/json' \\\n"
        "  -d \"$(jq -Rs '{{model:\"'$MODEL'\",messages:[{{role:\"user\",content:.}}]}}' {packet})\"",
    ),
}


def cmd_review(args: argparse.Namespace) -> int:
    text = _packet.build_packet(args.document, args.data)
    out = args.output
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    fp = _packet.packet_fingerprint(text)
    name, cmd = ADAPTERS[args.agent]
    print(f"packet: {out}  ({len(text)} bytes, sha256 {fp[:16]}...)")
    print()
    print(f"Send it with {name}:")
    print()
    for line in cmd.format(packet=out).splitlines():
        print(f"    {line}")
    print()
    print("Then, before you believe the verdict, record two things next to it:")
    print("  1. which model answered - it must not be the one that wrote the artifact;")
    print(f"  2. this packet's sha256 - {fp}")
    print("Without both, 'a different model checked it' is a claim about a")
    print("conversation nobody can inspect.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="doubleblind",
        description="Two layers that cannot see each other's mistakes.")
    ap.add_argument("--no-color", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help):
        # --no-color is accepted on either side of the subcommand; people type
        # it where it reads naturally, not where argparse prefers it.
        sp = sub.add_parser(name, help=help)
        sp.add_argument("--no-color", action="store_true")
        return sp

    t = add("trace", "every number in a document must exist in a committed file")
    t.add_argument("document")
    t.add_argument("--data", nargs="+", required=True, help="result files or directories")
    t.add_argument("--allow", help=f"exemptions with reasons (default: {ALLOW_DEFAULT})")
    t.add_argument("--derive", action="append", metavar="CMD",
                   help="a committed command whose printed numbers also count as "
                        "evidence; repeatable")
    t.add_argument("--strict", action="store_true", help="fail on word-quantities too")
    t.add_argument("--no-vague", action="store_true", help="do not report word-quantities")
    t.add_argument("-v", "--verbose", action="store_true")
    t.set_defaults(func=cmd_trace)

    l = add("lint", "find phrases that tell the reviewer what to conclude")
    l.add_argument("brief")
    l.set_defaults(func=cmd_lint)

    p = add("packet", "assemble artifact + evidence into one review packet")
    p.add_argument("document", nargs="+")
    p.add_argument("--data", nargs="*", default=[])
    p.add_argument("-o", "--output", default="packet.md")
    p.set_defaults(func=cmd_packet)

    r = add("review", "build the packet and print how to send it")
    r.add_argument("document", nargs="+")
    r.add_argument("--data", nargs="*", default=[])
    r.add_argument("--agent", choices=sorted(ADAPTERS), default="claude")
    r.add_argument("-o", "--output", default="packet.md")
    r.set_defaults(func=cmd_review)

    args = ap.parse_args(argv)
    for attr in ("no_color", "strict", "no_vague", "verbose", "allow", "derive"):
        if not hasattr(args, attr):
            setattr(args, attr, False if attr not in ("allow", "derive") else None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
