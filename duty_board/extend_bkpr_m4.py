#!/usr/bin/env python3
"""Extend m4 — The Professional Bookkeeper — from 5 chapters to 9.

The judgement behind the choice, recorded so it can be argued with.

m4 was the biggest gap on the track at 5 chapters against a 9 standard, and the
gaps are content-shaped rather than length-shaped. What was missing is not more
words about confidentiality and client voice — those chapters are good — but
four situations a bookkeeper will actually meet and which the module was silent
on:

  PRESSURE. A client asking for something to be posted a particular way. The
  single most common professional difficulty in this work and entirely absent.
  Everything else in the module assumes the bookkeeper and the client want the
  same thing.

  SUSPICION. Transactions that look wrong in a way that is not a bookkeeping
  question. Written deliberately conservatively: tell the named person, do not
  investigate, do not confront, do not tip off, keep working normally. It does
  NOT assert what the firm's statutory obligations are, because those vary and
  a track that stated them confidently would be worse than one that says find
  out yours — the module names the shape of the duty and points at the person
  who holds it.

  YOUR OWN ERROR. The bad-news chapter covers a late statement and an error
  reaching a pack; it does not cover the protocol for a mistake that is yours,
  which is a different conversation and a harder one.

  THE LIMITS OF COMPETENCE. When a question is not a bookkeeping question. The
  module tells the reader to be professional and never says what to do when
  they are out of their depth, which is where most real damage originates.

Order places pressure and suspicion together, then the two self-facing
chapters, closing on competence rather than on suspicion — a module about
professional conduct should not end on its darkest material.

Run from the app package directory:  python3 extend_bkpr_m4.py
"""

import collections
import io
import json
import random
import re
import sys

DATA = "academy_bkpr_data.json"
KEY = "m4"
BANNED = ["at the end of the day"]

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


NEW = [
("Pressure — when a client asks for a particular answer", 6, """<p>Everything so far assumes you and the client want the same thing. Occasionally you will not, and this is the chapter for that day.</p>

<p><b>What it actually sounds like.</b> Almost never <i>falsify this</i>. It arrives as reasonable-sounding requests, usually from somebody under real strain: <i>can that sit in next month instead</i>; <i>treat the generator as a repair rather than an asset</i>; <i>my personal card bill went through the business, just put it to entertainment</i>; <i>leave the stock at last month's figure, the count was rushed</i>. Each has a version that is legitimate and a version that is not, which is exactly what makes them hard.</p>

<p><b>The distinction that resolves most of them.</b> Is this a judgement with a defensible basis, or a preference for a different answer? Cut-off, capitalisation and estimation are genuine judgements with rules behind them — and where the rules permit a range, the client's view is a legitimate input. Moving a transaction to a different month because the month looks better is not a judgement; it is a different answer, chosen for its appearance.</p>

<p><b>The three-step response, in order.</b></p>

<p><b>Understand it first.</b> <i>Help me understand the reasoning — what's driving that?</i> A surprising share of these turn out to be genuine and correctly argued, and you will have learned something about the business. Refusing before understanding is how a bookkeeper becomes somebody the client stops telling things to.</p>

<p><b>Say what you can and cannot do, without judgement of them.</b> <i>I can't move a July transaction into August — the date is the date. What I can do is show it clearly in the flux note so the month reads properly.</i> Naming the alternative matters: a flat no leaves them with the problem they started with.</p>

<p><b>Escalate rather than negotiate.</b> If it does not resolve there, it stops being yours. <i>Let me take this to the books manager and come back to you today.</i> That is not passing the difficulty upward to avoid it — the firm holds the relationship and the professional exposure, and a bookkeeper who settles these alone is carrying something that was never theirs.</p>

<p><b>What you never do, whatever the pressure.</b> Post something you believe to be wrong. Backdate a document to a period that has closed. Delete rather than reverse. Or agree verbally and hope it is forgotten — the request will be repeated next month, and the second refusal is harder than the first would have been.</p>

<p><b>And the thing worth understanding about the person asking.</b> They are usually not trying to make you complicit. They are under a bank covenant, a tax deadline, or a partner's question, and they have asked the person nearest the numbers. Treating it as an ordinary request handled firmly, rather than as an accusation, is what keeps the relationship intact through the refusal.</p>"""),

("Suspicion — what you must not ignore", 6, """<p>Rarely, something in the books is not a bookkeeping question. This chapter is about recognising that moment and what to do in the first hour, and it is deliberately narrow: your job is to notice and to tell one person, not to investigate or decide.</p>

<p><b>What the shape looks like.</b> Round-sum transfers to parties with no invoices and no obvious business purpose. Payments to a name that does not appear anywhere else in the client's affairs. Cash movements that do not fit the trade. A pattern of transactions just below a threshold. Instructions to route money through an account for no stated reason. Any of these can be entirely innocent and explained in a sentence — most are — which is precisely why the response is a question rather than a conclusion.</p>

<p><b>Ordinary curiosity first.</b> Raise it as you would any unclassifiable item: a query, help-shaped, same day. Most of what looks odd resolves there, and a bookkeeper who escalates everything unusual is one nobody can work with.</p>

<p><b>When the answer does not resolve it.</b> The answer does not fit the transaction, or the question is deflected, or the explanation changes. That is the moment this chapter is about, and from there the rules are firm.</p>

<p><b>Tell the named person in the firm, once, in writing, the same day.</b> Your firm has somebody who holds this — a partner, a compliance owner, the books manager. Find out who before you need to, because looking it up during the hour it matters is not the moment.</p>

<p><b>Then four things you do not do.</b> Do not confront the client or challenge them about it. Do not investigate — no digging through old periods, no assembling evidence, no calling the bank. Do not discuss it with colleagues, including the ones you trust. And do not tell the client that you have raised it, which matters more than it sounds: whether and how anything is disclosed is a decision for the firm, and a client who learns a report may be coming is a serious problem for everybody, including you.</p>

<p><b>Keep working normally unless told otherwise.</b> Changing how you behave toward that client is itself a signal. Post the ordinary transactions, deliver the pack, answer the queries — the firm will tell you if anything changes.</p>

<p><b>What this module deliberately does not tell you.</b> What your firm's reporting obligations are. Those depend on the firm's registrations and on rules that change, and a track that stated them confidently would eventually be confidently wrong. What does not change is the shape: notice, tell one named person, do not investigate, do not tip off. Ask your firm for the specifics on the day you join, and write down the name.</p>"""),

("When it was your mistake", 5, """<p>The bad-news protocol covered a late statement and an error reaching a delivered pack. This is the harder version: the error is yours, you found it, and nobody else knows.</p>

<p><b>The instinct, and why it is wrong.</b> To fix it quietly and say nothing. It is understandable, it usually works, and it costs you the one thing this job runs on — because the day a quiet fix is discovered, everything else you have ever attested becomes a question. A bookkeeper's value is that their word about the books can be relied on, and that is not divisible.</p>

<p><b>The protocol, and it is short.</b></p>

<p><b>Establish the size before you speak, but not for long.</b> What was wrong, which periods, what it affects. Twenty minutes, not two days — you are describing the problem, not solving it first.</p>

<p><b>Tell your reviewer or manager, plainly, without cushioning.</b> <i>I posted the March rent release twice; the P&amp;L is overstated by ₦200,000 for March and April. Statements went out for both.</i> That is the whole message. No preamble, no explanation of how it happened until asked, and no apology longer than the facts.</p>

<p><b>Bring what you propose to do.</b> The correcting entry, whether the client needs a reissued pack or a note, and what would stop it recurring. A mistake reported with a proposal reads completely differently from a mistake reported as a confession.</p>

<p><b>Then let somebody else decide what the client is told.</b> Whether a pack is reissued, and how it is described, is not yours alone — particularly where the numbers went to a bank or an adviser.</p>

<p><b>What happens next, honestly.</b> Far less than people fear. Reviewers and managers meet errors constantly; what they remember is how it arrived. The bookkeepers who become trusted are not the ones who never make mistakes — there are none of those — they are the ones whose mistakes arrive early, complete and without excuses.</p>

<p><b>And the corrections themselves.</b> Reverse and repost, never delete and never edit history. The trail should show the error, the correction and their link, because a corrected ledger that hides its correction is a ledger somebody will one day have to reconstruct without knowing why the figures moved.</p>

<p><b>What to do when the error is somebody else's.</b> The same, minus the ownership. Tell your reviewer or manager what you found, factually and without characterising the person — <i>the March rent release looks doubled</i>, not <i>somebody double-posted the rent</i>. It is not your place to work out who, and saying so as a finding rather than an accusation is what keeps a unit workable.</p>

<p><b>The one that is hardest.</b> An error you find months later, in a period nobody is looking at, that nobody would ever notice. The rule is the same and the reason is simpler than ethics: you already know, and the alternative is carrying it.</p>"""),

("The limits of your competence", 5, """<p>The most expensive errors in this work are rarely careless. They are a confident answer given by somebody slightly outside what they actually knew, and the whole of this chapter is about recognising that edge in yourself.</p>

<p><b>Where the edge usually is.</b> Tax treatment beyond the routine. Anything involving a director's personal affairs and the company's. Foreign currency and translation. A transaction structure you have not seen before — a lease that might be a purchase, a related-party arrangement, an unusual instrument. And any question phrased as <i>can we</i> rather than <i>how do I post</i>, which is almost always an advice question wearing bookkeeping clothes.</p>

<p><b>The tell.</b> You are reasoning by analogy — <i>it is probably like the other one</i> — rather than from a rule you can name. That feeling is reliable, and it is the moment to stop rather than the moment to look harder.</p>

<p><b>What to do with it, and it is three sentences.</b> <i>I want to check that rather than guess.</i> Take it to whoever holds it in your firm. Come back with the answer and the reasoning, not just the answer, because the reasoning is what you keep.</p>

<p><b>Saying it to a client.</b> <i>That's a good question and I don't want to give you a quick answer to it — let me check and come back today.</i> Clients do not lose confidence in a bookkeeper who checks. They lose confidence in one who was confident and wrong, and the second is unrecoverable in a way the first never is.</p>

<p><b>Where the line sits between bookkeeping and advice.</b> Recording what happened is yours. What the client should do about it frequently is not, and the boundary matters both ways — a bookkeeper who advises on tax structure is exposing themselves and the firm, and one who refuses to explain what a figure means is being unhelpful about their own work. Explaining the books is always yours. Recommending a course of action generally is not.</p>

<p><b>What competence actually grows from.</b> Not from getting things right, which teaches little. From the questions you escalated and the answers that came back — which is why bringing back the reasoning rather than the answer is the whole technique. Bookkeepers who do this for a year know why the rules are as they are; those who ask only for the answer know a list.</p>

<p><b>The pressure that produces the confident wrong answer.</b> A client on a call, waiting, and a question you half-know. The whole difficulty is that <i>let me check</i> feels like a failure in that specific moment and is forgotten within a day, while a wrong answer is acted on and remembered. Knowing in advance that the discomfort is momentary and the error is durable is most of what it takes to say it.</p>

<p><b>And the standard, stated once.</b> Nobody expects you to know everything. Everybody is entitled to expect that you know what you do not know, and say so before it matters rather than after.</p>"""),
]

# original chapter 1 sits below the depth floor; extended here rather than in a
# separate pass so one script owns the module's shape
EXTEND_EXISTING = {
0: """<p><b>The fifth scenario, which is the one that actually happens.</b> Nobody asks. You are on a call about Cascade and you mention, harmlessly, that another retail client had the same problem with their POS provider last quarter. You have named no one and disclosed no figure — and you have told Cascade's MD that you talk about clients on calls. Everything after that is heard differently, including the things you do not say.</p>

<p><b>What confidentiality protects that is not the data.</b> The client's willingness to tell you things. A bookkeeper who is told about the difficult month before it appears in the numbers can do their job; one the client manages information toward cannot. Discretion is the condition of being useful, rather than a constraint on it.</p>

<p><b>And the household case.</b> Working from home, on a shared machine, on a call somebody else can hear. The rules that are obvious in an office are the ones most often lost remotely, and they are the same rules: screens not visible, calls not overheard, files not on a personal drive, and nothing about a client in a message to somebody who is not on the engagement.</p>"""
}

CHECKS = {
5: [
 C("Pressure from a client almost never sounds like a request to falsify. It sounds like:",
   ["An instruction", "A reasonable-sounding request from somebody under real strain",
    "A complaint", "A threat to leave"], 1,
   "Each of these has a legitimate version and one that is not, which is what makes them hard."),
 C("The distinction that resolves most of these is whether it is a judgement with a defensible basis, or:",
   ["An accounting policy choice", "A preference for a different answer",
    "A timing question", "A materiality matter"], 1,
   "Moving a transaction because the month looks better is a different answer chosen for its appearance."),
 C("Where a request does not resolve, the correct move is to:",
   ["Refuse firmly and close it", "Escalate rather than negotiate",
    "Post it and note your objection", "Ask for it in writing"], 1,
   "The firm holds the relationship and the exposure; a bookkeeper who settles these alone carries something that was never theirs.")],
6: [
 C("Something that looks suspicious should first be raised as:",
   ["An escalation", "An ordinary query, help-shaped, the same day",
    "A note to the manager", "A file record"], 1,
   "Most of what looks odd resolves there, and somebody who escalates everything unusual is one nobody can work with."),
 C("Once an answer does not resolve it, you tell:",
   ["The client", "The named person in the firm, once, in writing, the same day",
    "Your reviewer and a colleague", "The bank"], 1,
   "Find out who holds it before you need to, because looking it up during the hour it matters is not the moment."),
 C("Telling the client that you have raised a concern is:",
   ["Courteous", "Not done — whether anything is disclosed is the firm's decision",
    "Required for transparency", "Left to your judgement"], 1,
   "A client who learns a report may be coming is a serious problem for everybody, including you.")],
7: [
 C("Fixing your own error quietly costs you:",
   ["Time", "The reliability of everything else you have attested",
    "A difficult conversation", "Nothing, if it works"], 1,
   "A bookkeeper's value is that their word about the books can be relied on, and that is not divisible."),
 C("Establishing the size of your own error should take:",
   ["As long as needed", "About twenty minutes, not two days",
    "A full review", "Until the correction is drafted"], 1,
   "You are describing the problem rather than solving it first."),
 C("A mistake reported with a proposal reads differently from one reported as:",
   ["An escalation", "A confession",
    "A finding", "A query"], 1,
   "Bring the correcting entry, whether the pack needs reissuing, and what would stop it recurring.")],
8: [
 C("The tell that you are at the edge of your competence is that you are reasoning:",
   ["Slowly", "By analogy rather than from a rule you can name",
    "From memory", "Without documentation"], 1,
   "That feeling is reliable, and it is the moment to stop rather than to look harder."),
 C("A question phrased as 'can we' rather than 'how do I post' is usually:",
   ["A bookkeeping question", "An advice question wearing bookkeeping clothes",
    "A policy question", "A timing question"], 1,
   "One of the places the edge usually sits."),
 C("When you escalate a question, what you bring back is:",
   ["The answer", "The answer and the reasoning",
    "The source", "The decision"], 1,
   "The reasoning is what you keep, and it is why competence grows from escalated questions rather than from being right.")],
}

EXTRA_QUESTIONS = [
 Q("A client asking to move a July transaction into August because the month looks better is:", ["A cut-off judgement", "A different answer chosen for its appearance", "Within materiality", "A policy choice"], 1,
   "The date is the date; the alternative is showing it clearly in the flux note.", "M4 L6", "Pressure"),
 Q("Refusing a client's request before understanding the reasoning risks:", ["Nothing", "Becoming somebody the client stops telling things to", "A complaint", "Escalation"], 1,
   "A surprising share of these turn out to be genuine and correctly argued.", "M4 L6", "Pressure"),
 Q("Agreeing verbally and hoping a request is forgotten fails because:", ["It is dishonest", "It will be repeated next month, and the second refusal is harder", "The reviewer will find it", "It is recorded"], 1,
   "One of the four things never done whatever the pressure.", "M4 L6", "Pressure"),
 Q("The person applying pressure is usually:", ["Testing you", "Under a covenant, a deadline or a partner's question", "Acting dishonestly", "Poorly advised"], 1,
   "They have asked the person nearest the numbers, which is what keeps it an ordinary request handled firmly.", "M4 L6", "Pressure"),
 Q("After raising a suspicion internally, you should:", ["Watch the account closely", "Keep working normally unless told otherwise", "Reduce contact", "Pause the postings"], 1,
   "Changing how you behave toward that client is itself a signal.", "M4 L7", "Suspicion"),
 Q("Investigating a suspicion yourself is:", ["Diligent", "Not done", "Expected before escalating", "Required for the report"], 1,
   "No digging through old periods, no assembling evidence, no calling the bank.", "M4 L7", "Suspicion"),
 Q("The module does not state the firm's reporting obligations because:", ["They are confidential", "They depend on registrations and rules that change", "They are the manager's concern", "They rarely apply"], 1,
   "What does not change is the shape: notice, tell one named person, do not investigate, do not tip off.", "M4 L7", "Suspicion"),
 Q("Most transactions that look suspicious are:", ["Reported", "Explained in a sentence", "Escalated", "Reversed"], 1,
   "Which is why the response is a question rather than a conclusion.", "M4 L7", "Suspicion"),
 Q("The message reporting your own error should contain no apology longer than:", ["A sentence", "The facts", "A paragraph", "The correction"], 1,
   "No preamble, and no explanation of how it happened until asked.", "M4 L8", "Your own mistake"),
 Q("Corrections are made by:", ["Editing the original", "Reversing and reposting", "Deleting and re-entering", "Adjusting the next period"], 1,
   "A corrected ledger that hides its correction is one somebody will have to reconstruct without knowing why figures moved.", "M4 L8", "Your own mistake"),
 Q("Bookkeepers who become trusted are those whose mistakes:", ["Are rare", "Arrive early, complete and without excuses", "Are caught in review", "Are immaterial"], 1,
   "There are no bookkeepers who never make mistakes.", "M4 L8", "Your own mistake"),
 Q("An error found months later that nobody would notice is:", ["Left alone", "Reported, because you already know", "Corrected silently", "A materiality judgement"], 1,
   "The alternative is carrying it.", "M4 L8", "Your own mistake"),
 Q("Telling a client you want to check rather than answer quickly:", ["Undermines confidence", "Does not lose their confidence — being confident and wrong does", "Should be avoided", "Delays the work"], 1,
   "The second is unrecoverable in a way the first never is.", "M4 L9", "Limits of competence"),
 Q("Explaining what a figure means is:", ["Advice", "Always yours", "The manager's role", "Outside scope"], 1,
   "Recommending a course of action generally is not.", "M4 L9", "Limits of competence"),
 Q("Competence grows mainly from:", ["Getting things right", "The questions you escalated and the answers that came back", "Volume of clients", "Formal training"], 1,
   "Which is why bringing back the reasoning rather than the answer is the whole technique.", "M4 L9", "Limits of competence"),
 Q("The standard stated at the close of the module is that you know:", ["Everything relevant", "What you do not know, and say so before it matters", "Where to find answers", "Your client's business"], 1,
   "Nobody expects you to know everything.", "M4 L9", "Limits of competence"),
]


def rebalance(items, seed):
    n = len(items)
    base, extra = divmod(n, 4)
    slots = []
    for i in range(4):
        slots += [i] * (base + (1 if i < extra else 0))
    random.Random(seed).shuffle(slots)
    for it, target in zip(items, slots):
        cur = it["ans"]
        if cur == target:
            continue
        shift = (target - cur) % 4
        it["opts"] = it["opts"][-shift:] + it["opts"][:-shift]
        it["ans"] = target
    return items


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data[KEY]

    if len(mod["lessons"]) == 5:
        for i, extra in sorted(EXTEND_EXISTING.items()):
            mod["lessons"][i]["html"] = mod["lessons"][i]["html"].rstrip() + "\n" + extra
        for title, est, html in NEW:
            mod["lessons"].append({"title": title, "est": est, "html": html})
        have = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
        for q in EXTRA_QUESTIONS:
            if re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() not in have:
                mod["questions"].append(q)
    if len(mod["lessons"]) != 9:
        sys.exit("ABORT: %d chapters, expected 9" % len(mod["lessons"]))

    rebalance(mod["questions"], "bkpr:m4:exam")
    rebalance([c for _i, ch in sorted(CHECKS.items()) for c in ch], "bkpr:m4:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
    problems, seen = [], set()
    for l in mod["lessons"]:
        for c in l.get("checks") or []:
            seen.add(re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip())
    for idx, checks in sorted(CHECKS.items()):
        if len(checks) != 3:
            problems.append("ch%d has %d checks" % (idx + 1, len(checks)))
        for c in checks:
            norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
            if norm in bank:
                problems.append("duplicates exam question: %s" % c["q"][:56])
            if norm in seen:
                problems.append("duplicate check: %s" % c["q"][:56])
            seen.add(norm)
            if len(c.get("why") or "") < 40:
                problems.append("weak rationale: %s" % c["q"][:50])
            if len(c["opts"]) != 4:
                problems.append("not 4 options: %s" % c["q"][:50])
        mod["lessons"][idx]["checks"] = [dict(c, sort=i) for i, c in enumerate(checks)]
    for i, l in enumerate(mod["lessons"]):
        if not l.get("checks"):
            problems.append("chapter %d has no checks" % (i + 1))
        flat = re.sub(r"<[^>]+>", " ", l["html"]).lower()
        for b in BANNED:
            if b in flat:
                problems.append("banned phrase in ch%d" % (i + 1))
    if problems:
        sys.exit("ABORT — %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("m4: %d chapters | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    print("checks %d | questions %d" % (
        sum(len(l["checks"]) for l in mod["lessons"]), len(mod["questions"])))
    sp = collections.Counter(q["ans"] for q in mod["questions"])
    print("spread %s | guessable %d%%" % (
        dict(sorted(sp.items())), round(max(sp.values()) * 100 / len(mod["questions"]))))
    print("thin:", [i + 1 for i, n in enumerate(lens) if n < 2500] or "NONE")


if __name__ == "__main__":
    main()
