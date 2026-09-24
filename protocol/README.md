# The protocol

Running a second model is easy. Keeping it blind is the part that takes care,
and it is the part that decides whether the verdict means anything.

## 1. Assemble the packet

The artifact, the evidence it rests on, and nothing else.

```bash
doubleblind packet README.md --data results/ -o packet.md
```

Nothing about how the artifact came to exist goes in: no commit messages, no
changelog, no summary of what was tried, no conversation. Those are where intent
lives, which is why `packet` takes explicit paths rather than a repository.

## 2. Lint the request before you send it

```bash
doubleblind lint my-brief.md
```

Six mechanisms, because the wording changes and the mechanism does not:

| mechanism | example | why it matters |
|---|---|---|
| **answer-in-the-request** | "confirm that all four fall below" | there is one way to answer and still sound useful |
| **conclusion-stated** | "we show that X", "as expected" | disagreement becomes contradiction of you |
| **polarity-steering** | "should be", "obviously", "a minor issue" | pre-sizes the problem before anyone looks |
| **social-pressure** | "I already checked", "quick sanity check" | licenses a shallow pass; makes a finding an accusation |
| **scope-narrowing** | "ignore the appendix", "only look at" | pre-decides where the error is not |
| **authorship-leak** | "my README", "I wrote" | makes the reviewer a guest in your work |

The rule underneath all six: **ask what the evidence supports, never ask to
verify that X.** The first question cannot be answered by agreeing.

## 3. Choose a model that did not write it

Same model, fresh context is not enough — it carries the priors that produced
the artifact. Different model, zero context is the bar.

### Claude Code

```python
Agent(
    subagent_type='general-purpose',
    model='<not the model that wrote the artifact>',
    run_in_background=False,
    prompt=open('packet.md').read(),
)
```

A sub-agent starts with no conversation history by construction, but not with
nothing: it still loads your `CLAUDE.md` files, any `AGENTS.md` loaded as project
instructions, and a git-status snapshot. (A fork started with `/subtask` inherits
the whole conversation; it is never the reviewer.) Pick the model explicitly; ask
the agent to state its own model id in its first line.

To withhold the project instructions as well, define the reviewer once as a
project sub-agent (Claude Code 2.1.271 or later) and launch it from a directory
that holds the packet alone:

```markdown
---
name: blind-reviewer
description: Reviews a sealed packet with no project context. Use only when handed a packet.
tools: Read
omitClaudeMd: true
model: sonnet   # anything but the model that wrote the artifact
---
Review the packet you are given. You know nothing else about this project.
```

Saved as `.claude/agents/blind-reviewer.md`. `claude plugin validate` accepts a
misspelled field name without a word, so copy `omitClaudeMd` exactly.

### Codex CLI

```bash
codex exec --skip-git-repo-check < packet.md
```

`exec` starts a fresh session. Do not use `codex resume`.

### DeepSeek

```bash
curl -s https://api.deepseek.com/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{model:"'${DEEPSEEK_MODEL:?set DEEPSEEK_MODEL}'",messages:[{role:"user",content:.}]}' packet.md)"
```

Model names change: `deepseek-reasoner` is no longer in DeepSeek's model list.
Set `DEEPSEEK_MODEL` from [the current one](https://api-docs.deepseek.com/quick_start/pricing)
(`deepseek-v4-pro` as of 2026-09).

### Kimi / Moonshot

```bash
curl -s https://api.moonshot.cn/v1/chat/completions \
  -H "Authorization: Bearer $MOONSHOT_API_KEY" -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{model:"'${KIMI_MODEL:?set KIMI_MODEL}'",messages:[{role:"user",content:.}]}' packet.md)"
```

The `kimi-k2` series was discontinued on 2026-05-25. Set `KIMI_MODEL` from
[the current list](https://platform.kimi.ai/docs/models.md) (`kimi-k3` as of 2026-09).

### Anything OpenAI-compatible

```bash
curl -s "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H 'Content-Type: application/json' \
  -d "$(jq -Rs '{model:"'"$MODEL"'",messages:[{role:"user",content:.}]}' packet.md)"
```

One request, one message. Sending history is the thing you are avoiding.

## 4. Demand findings that can be settled

The shipped brief asks for this shape:

```
<file>:<line>  CLAIM: "<quoted sentence>"
               EVIDENCE: <what the data says>
               COMMAND: <one shell command that settles it>
```

**A finding with no command is an opinion.** Drop it or convert it. This single
rule does more than any prompt wording: it makes a wrong finding cheap to
dismiss and a right one impossible to argue with.

## 5. Run every command yourself

The reviewer is a different model, not an oracle. In the run recorded in
[`../ledger/`](../ledger/), 9 findings came back and 5 survived their own
commands. Record the ones that did not, with the command, so the same objection
is not re-litigated next time.

## 6. Record that it was blind

"A different model checked it" is a claim about a conversation nobody can
inspect. Next to the verdict, write down:

- the **model id** that answered, stated by the model itself;
- the **sha256 of the packet** it was given (`doubleblind review` prints it);
- that the session had **no prior turns**.

Without all three, the claim is decoration. `doubleblind` deliberately does not
try to prove any of it for you — it has no access to your session — so if you
need it proven rather than recorded, use a host that persists session events and
check them.

[`blindness.md`](blindness.md) has the record format, what each of the three
lines does and does not establish, and the four ways blindness is actually lost
— the first of which is that a sub-agent launched inside your repository reads
your project instruction files at zero conversation turns.

## 7. Turn what it found into a check

This is the step that compounds. A finding that stays a report is worth one
catch; the same finding as a check that fails on a deliberately broken input is
worth every future catch. Add it to [`../ledger/findings.json`](../ledger/findings.json)
with the layer that missed it, and write the check.

Some findings convert and some do not. The four in the ledger marked
`correct-number-false-sentence` have **no** mechanical equivalent, and recording
that is the point: it is how you know the reviewer layer is not optional.
