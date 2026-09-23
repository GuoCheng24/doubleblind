# Recording that the reviewer was blind

"A different model checked it" is a claim about a conversation nobody else can
inspect. This file is about what you can honestly write next to a verdict, what
each part of that record actually establishes, and the four ways blindness is
lost in practice — none of which is "somebody pasted the conversation".

Two questions get confused, and they have different answers:

|  | question | answered by |
|---|---|---|
| **is it blind** | did the reviewer see anything beyond the packet | how you launched it |
| **can you prove it** | could a sceptic confirm that from outside | your host's session log, if it keeps one |

`doubleblind` answers the first and deliberately does not pretend to answer the
second. It has no access to your session. A record is a record; if you need the
property *proven* rather than *stated*, you need a host that persists session
events, and you should say which one.

## What to write down

Next to the verdict, three lines:

```
reviewer   <model id, as the model stated it in its own first line>
packet     sha256 <64 hex chars>   (doubleblind review prints it)
session    no prior turns; launched as <sub-agent | codex exec | one API request>
```

The digest is the plain sha256 of the packet file, so anyone can check it:

```bash
sha256sum packet.md      # must equal the line above
```

Which is the point of printing it in full rather than as a prefix. A truncated
hash catches a slip; it is not a commitment to what the reviewer was given.

## What each line does and does not establish

**The model id** rules out the accident, not the lie. Asking the model to state
its own identifier catches the case that actually happens — the flag defaulted,
and the "second model" was the one that wrote the artifact. It does not survive
anyone who wants to fake it: a model can be told what to say about itself, and
its self-report is not an attestation. Treat it as a checksum on your own
launch command.

**The packet digest** is the strongest of the three, and it is one-sided. It
pins exactly what you sent, so a packet edited after the fact stops matching.
It says nothing at all about what *else* was in the context — and what else was
in the context is the whole question.

**"No prior turns"** is the load-bearing line and the one you cannot verify
from outside. In a sub-agent it is true by construction: the sub-agent starts
with no conversation history, so blindness costs nothing extra and there is no
discipline to forget. In a chat window it is a claim about your own behaviour,
which is a weaker thing, and you should write it as one.

That asymmetry is the argument for the sub-agent route over "I opened a fresh
tab". Not that a fresh tab is dishonest — that one of them cannot be got wrong.

## The four ways blindness is actually lost

**1. Project instructions reach the reviewer even at zero turns.** A sub-agent
launched inside your repository reads the same project-level instruction files
you do — `CLAUDE.md`, `AGENTS.md`, and their equivalents — and those files are
written by the author of the artifact, in the author's voice, usually with the
project's goals and current claims in them. The conversation history is empty
and the context is not.

> Run the reviewer from a directory that contains the packet and nothing else.
> It also removes the second version of the same leak: a repository the
> reviewer can read is a repository whose commit messages it can read.

```bash
mkdir -p /tmp/review && cp packet.md /tmp/review/ && cd /tmp/review
```

**2. Provenance smuggled into the packet.** `packet` takes explicit paths
rather than a repository for this reason. A commit message, a changelog entry
or a `## What we tried` section carries intent, and intent is the thing being
withheld. If you assemble a packet by hand, assemble it out of the artifact and
the evidence, and nothing about how either came to exist.

**3. The filename.** `results_confirming_the_gain.json` is a brief. So is a
figure called `improvement_v3_final.png`, and so is a directory named after the
hypothesis. `lint` reads the request you wrote; it does not rename your files.

**4. Resuming instead of starting.** `codex resume` continues a session;
`codex exec` starts one. The same distinction exists in every tool that has a
history feature, and the resumed session is indistinguishable from a fresh one
in its output.

## The adversarial case, plainly

None of this survives someone determined to fake it. A record is not a proof,
and a self-reported model id is not an attestation. This protocol is built for
the case that is actually common and actually expensive — an author checking
their own work, wanting the check to be worth something — and for that case the
construction matters more than the attestation. What makes the sub-agent route
good is not that it is hard to forge. It is that it is hard to get wrong.

If you need the adversarial property, the honest statement is that you need a
different mechanism than this one, hosted somewhere neither party controls.

## Worked record, including the part that is missing

From the run recorded in [`../ledger/`](../ledger/) — the first zero-context
cross-model audit here, on a README whose author had already corrected it twice:

```
reviewer   Fable 5.1 (a different model from the one that wrote the artifact)
packet     NOT RECORDED - this run predates the practice
session    no prior turns; launched as a sub-agent
findings   9 returned, 5 survived their own commands
```

The second line is left as it is on purpose. That run is the reason this file
exists, and going back to fill in a digest now would produce a number that
matches a packet reassembled today rather than the one the reviewer was given.
A missing record is a weaker claim than a present one; a manufactured record is
not a claim at all.

The last line matters as much as the first three. A reviewer whose findings are
all accepted has not been checked either — run every command yourself, and
record what did not survive, so the same objection is not re-litigated next
time. Four of the nine did not survive.
