#!/usr/bin/env python3
"""Build 'The Auditor in a System Environment' into academy_control_data.json.

Module 1, written second to last so it can point at the seven modules that
exist rather than promise them.

Deliberately does not re-teach module 2's population-versus-sample material.
That chapter argued why an auditor must extract their own data; this module
takes the consequence and applies it to assurance language, planning and the
standing of the function.

Run from the app package directory:  python3 build_control_m1.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "auditor_role"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What changes when the record is complete", 12, """<p>Internal audit as a discipline was built for paper. Its methods — sampling, vouching, walkthroughs, the annual visit — are sensible responses to a world where evidence sat in filing cabinets at locations you had to travel to.</p>

<p>That world is gone in a business running ZhiftERP, and most audit functions have not adjusted.</p>

<p><b>What is different, in one sentence.</b> The record is complete, timestamped, attributed and queryable from where you are sitting. Every transaction, every change to every master record, every approval, every login. Not a sample of it — all of it.</p>

<p><b>Four consequences, and each changes the work.</b></p>

<p><b>You can test populations rather than samples.</b> Module 2 argued this and modules 4 to 8 spent it. The consequence for this module is what it does to what you are able to <i>say</i>, which is the next chapter.</p>

<p><b>You can test remotely and continuously.</b> The branch visit stops being how testing happens and becomes what you do when the data has told you where to go. A function of two people can examine twenty branches every month, which is not possible on a rota.</p>

<p><b>You can reconstruct history.</b> Version history means a document's state before a change is recoverable. In a paper environment, what a record said last March was gone unless somebody kept a copy.</p>

<p><b>The controls themselves are configuration rather than behaviour.</b> Whether approval is required is a setting, not a habit. That makes control existence testable in minutes — module 3's whole argument — where previously it required observing people.</p>

<p><b>What has not changed, and it is worth being clear.</b> Judgement. Scepticism. The ability to write something somebody will act on. Knowing when a pattern is a coincidence. The system gives you better evidence; it does not tell you what the evidence means, and an auditor who becomes a query-writer has traded the valuable half of the job for the mechanical one.</p>

<p><b>The uncomfortable implication for a function that has not adjusted.</b> An audit programme built on sampling and visits, in an environment where the population is queryable, is providing less assurance than it appears to and costing more than it needs to. Nobody will point this out, because the function's outputs look like audit outputs. The gap is only visible from inside.</p>

<blockquote>WATCH-OUT: The most common failure is not resistance but partial adoption — running the same rota, doing the same sample-based fieldwork, and adding a few reports. That produces the cost of both approaches and the benefit of neither, and it is where most functions in this market currently sit.</blockquote>

<p><b>What to do if you are inheriting a paper-era function.</b> Not a redesign announcement. Keep the existing plan running while building the test programme alongside it, and let the results argue for themselves — the first time a standing test finds something a rota visit would have missed by nine months, the case makes itself. Functions that announce a transformation before they can demonstrate one spend their credibility in advance and then have to earn it back.</p>"""
, [
 C("A function keeps its visit rota and sample-based fieldwork, adding a few reports. This produces:",
   ["A balanced approach", "The cost of both approaches and the benefit of neither",
    "A sensible transition", "Adequate coverage"], 1,
   "Partial adoption is the most common failure, not resistance."),
 C("What the system does NOT provide is:",
   ["Complete records", "Judgement about what the evidence means",
    "Attribution", "Historical reconstruction"], 1,
   "An auditor who becomes a query-writer has traded the valuable half of the job for the mechanical one."),
 C("Establishing whether adjustments require approval once took weeks of observation. It now takes minutes because controls are:",
   ["Better documented", "Configuration rather than behaviour",
    "Automated", "Externally certified"], 1,
   "Previously it required observing people over time.")]),

("What you can now say", 12, """<p>The point of testing is to say something. Population testing changes what you are entitled to say, and that change is the clearest way to explain to a board why the function is worth its cost.</p>

<p><b>The old sentence.</b> "We examined fifty purchase orders and found them to be in order." True, careful, and it carries sampling risk — the fifty may be clean while the population is not. Everybody in the room knows this and nobody says it.</p>

<p><b>The new sentence.</b> "No purchase order raised in the eighteen months to June was split below the approval limit." That is a statement about every order, and it is either right or wrong. It cannot be undermined by asking whether the sample was representative.</p>

<p><b>Be precise about what a clean population test does and does not establish.</b> It establishes that the condition you tested did not occur in the records. It does not establish that the underlying risk did not materialise by some route your test does not observe — module 8's point about risks with no observable signature. Overstating this is how a function loses credibility permanently, and the correction usually arrives in public.</p>

<p><b>So the honest formulation names the test rather than the outcome.</b> Not "procurement controls operate effectively" but "no order was split below the limit, no invoice was paid to an account changed within thirty days, and no supplier was created and transacted with on the same day by the same person." Three specific assurances a reader can weigh, rather than one general one they must accept.</p>

<p><b>What to say about coverage.</b> State what proportion of the risk map has tests against it, and name the risks that do not. That converts an audit opinion from a verdict into a map, and it puts untested risks in front of the people who can decide whether to accept them. Those gaps then become a business decision rather than an audit omission.</p>

<p><b>Assurance from a clean run is real and should be reported.</b> Functions that report only exceptions create the impression they find nothing when things work. A nil-expected test returning nothing for six months is evidence, and saying so gives the exception months their proper weight.</p>

<p><b>And the discipline behind all of it.</b> Every statement you make should be traceable to a defined population, a stated test and a retained result. If somebody asks how you know, the answer should take thirty seconds and involve opening a file rather than reconstructing a memory.</p>

<p><b>A word on the language of certainty.</b> ‘Appears’, ‘suggests’, ‘indicates’ and ‘shows’ are not interchangeable, and readers calibrate to them. Reserve the strong verb for what the data establishes directly and use weaker ones where a step of inference is involved. An auditor whose language tracks the strength of the evidence is believed when they use the strong verb; one who writes everything at the same pitch is discounted throughout.</p>

<blockquote>IMPLEMENTATION TIP: Rewrite one conclusion from your last report in the new form — name the population, the test and the result rather than the general assurance. The difference in what it commits you to, and in what a reader can do with it, is the whole argument of this module in a single paragraph.</blockquote>"""
, [
 C("Your split-order test returns nothing across eighteen months. You are entitled to say:",
   ["That procurement controls operate effectively", "That no order in the period was split below the limit",
    "That the risk did not materialise", "That management assertions are correct"], 1,
   "Overstating this is how a function loses credibility permanently, usually in public."),
 C("Which conclusion is the honest formulation?",
   ["'Procurement controls operate effectively'", "'No order was split below the limit and no invoice was paid to an account changed within thirty days'",
    "'No material weaknesses were identified'", "'Controls were tested and found adequate'"], 1,
   "Specific assurances a reader can weigh, rather than one general one they must accept."),
 C("Reporting only exceptions creates the impression that the function:",
   ["Is efficient", "Finds nothing when things are working",
    "Is well targeted", "Lacks coverage"], 1,
   "A nil-expected test returning nothing for six months is evidence and belongs in the report.")]),

("Independence, and authority without line power", 12, """<p>An internal auditor examines people who outrank them, using data those people control, and reports to somebody who may prefer not to hear it. Independence is what makes that possible, and it is structural rather than personal.</p>

<p><b>What independence actually requires.</b> Not that you are unbiased — everybody believes that of themselves. Four concrete things:</p>

<p><b>You do not audit what you operate.</b> An auditor who designed a control cannot assess it, and an auditor drawn into fixing a problem has become part of what they examine.</p>

<p><b>Your reporting line is not the person you examine.</b> If findings about the finance director are delivered to the finance director, the function is advisory at best.</p>

<p><b>Your access is not granted by somebody you may need to examine</b>, or at least, its removal would be visible to somebody else. Module 7 made this point about your own permissions.</p>

<p><b>Your remuneration and continuation do not depend on the people you report on.</b></p>

<p>Most internal audit functions in mid-sized businesses fail at least one of these, usually the second. That is worth stating in your own reports rather than leaving implicit — a function that reports its own structural limitations is more credible than one that does not mention them.</p>

<p><b>Authority without line power.</b> You cannot instruct anybody. You cannot stop a transaction, discipline a person, or require a change. Everything you achieve is achieved through somebody else deciding to act.</p>

<p><b>Which means influence is the operative skill, and it is built rather than granted.</b> Being right consistently. Being useful before being critical — module 4's point about price findings, which are commercially welcome and build the standing that harder findings later depend on. Never overstating. Withdrawing cleanly when wrong. And being predictable, so people know what you will and will not do with what they tell you.</p>

<p><b>The trap of becoming helpful.</b> Operating managers will ask you to fix things, sit on project teams, design controls, approve exceptions. It is flattering and it feels like value. Each acceptance costs a piece of independence, and the accumulation is invisible until you are asked to audit something you helped build. <b>Advise freely; own nothing.</b></p>

<p><b>And the boundary at the other end.</b> You establish what the data shows. You do not accuse, conduct disciplinary proceedings, or decide consequences. Auditors who step past that line usually do so from a sense of responsibility rather than ambition, which makes it harder to resist and no less damaging.</p>

<p><b>The small-business version of this problem.</b> In a business of two hundred people the auditor may be the only person able to fix what they found, and refusing looks obstructive. The workable compromise is to specify rather than implement: describe what the control should do and who should own it, help evaluate options, and stay out of the build. You keep the ability to audit it and they get most of the benefit of your expertise.</p>

<blockquote>WATCH-OUT: The most common erosion is being drawn into remediation. You find a problem, nobody else has capacity, and you fix it. Next year you audit it. State the boundary early and repeat it, because it will be tested by reasonable people with genuine needs.</blockquote>"""
, [
 C("A manager asks you to design the new approval workflow, since you found the gap. Accepting means:",
   ["Efficient remediation", "Next year you audit something you built",
    "Appropriate collaboration", "A stronger control"], 1,
   "Advise freely; own nothing. The erosion is invisible until it matters."),
 C("Your findings about the finance director are delivered to the finance director. The function is:",
   ["Independent in substance", "Advisory at best",
    "Adequately structured", "Compliant with practice"], 1,
   "A function that reports its own structural limitations is more credible than one that does not."),
 C("Since an internal auditor cannot instruct anybody, the operative skill is:",
   ["Escalation", "Influence, built through being right, useful and predictable",
    "Formal authority", "Regulatory backing"], 1,
   "Everything achieved is achieved through somebody else deciding to act.")]),

("The charter, and where authority comes from", 12, """<p>An internal audit charter is a document nobody reads until it matters, and then it is the only thing that matters. It is what converts a person asking questions into a function with a mandate.</p>

<p><b>What it must establish.</b></p>

<p><b>Purpose and scope.</b> What the function exists to do, and what is in scope — which should be everything, with any exclusions named and justified rather than assumed.</p>

<p><b>Reporting line.</b> To whom findings go, and specifically who receives them when the subject is a senior executive. This is the clause that matters most and is most often vague.</p>

<p><b>Access.</b> The right to see all records, systems, premises and people, without prior notice. Vague access rights become negotiations at exactly the moment negotiation is fatal.</p>

<p><b>Independence protections.</b> How the function is resourced, how its head is appointed and removed, and confirmation that it holds no operational responsibility.</p>

<p><b>Escalation.</b> Who is told when fraud is suspected, and specifically that it is not the line manager of the person concerned. Module 9 makes this a rule; the charter is what makes it enforceable when somebody objects at the time.</p>

<p><b>Why it must be agreed in advance.</b> Every clause above is uncontroversial when the business is calm and contested when it is not. Agreeing the escalation route while nothing is happening takes ten minutes. Agreeing it at the moment you have something to escalate is a negotiation with somebody who has an interest in the answer.</p>

<p><b>Who should approve it.</b> The audit committee where one exists, the board or the owner where it does not. Approval by the executive the function may need to examine defeats the purpose, though in an owner-managed business the owner is both — which is workable provided it is explicit rather than accidental.</p>

<p><b>What to do without one.</b> Most functions in this market operate without a charter or with one nobody has revisited in years. Draft it, keep it to two pages, and get it approved. It is the highest-return document an internal audit function can produce and it costs an afternoon.</p>

<p><b>And review it when circumstances change.</b> A new system, a new structure, a new reporting line, an acquisition. A charter written for a single-company business does not obviously cover a group, and the ambiguity will surface at the worst moment.</p>

<p><b>And keep it short.</b> A two-page charter people have read beats a twenty-page one modelled on an international standard that nobody has opened. The clauses in this chapter fit on two pages comfortably. Length here is not thoroughness; it is a way of ensuring the escalation clause is never found by anybody looking for it in a hurry.</p>

<blockquote>IMPLEMENTATION TIP: If you have no charter, write the escalation clause first. Who is told when you suspect fraud, in writing, approved. Everything else in the charter can wait; that clause is the one whose absence causes irreversible damage.</blockquote>"""
, [
 C("Which charter clause should be drafted first if you have nothing?",
   ["Scope and purpose", "The escalation route for suspected fraud",
    "Resourcing", "Reporting frequency"], 1,
   "Its absence causes irreversible damage; everything else can wait."),
 C("Agreeing the escalation route while nothing is happening takes ten minutes. Agreeing it when you have something to escalate is:",
   ["The same conversation later", "A negotiation with somebody who has an interest in the answer",
    "More informed", "Standard practice"], 1,
   "Every charter clause is uncontroversial when the business is calm and contested when it is not."),
 C("A charter approved by the executive the function may need to examine:",
   ["Is normal in a small business", "Defeats the purpose, unless the owner is explicitly both",
    "Provides sufficient authority", "Is preferable to none"], 1,
   "Approval belongs with the audit committee, board or owner.")]),

("Risk-based planning across an estate", 12, """<p>The annual plan decides where a small function spends a scarce year. Most plans are built from last year's plan, which means they find what somebody thought to look for several years ago.</p>

<p><b>What risk-based means concretely.</b> Rank what could go wrong by two things: how much it would cost if it happened, and how likely it is given the controls that actually exist. Then allocate time to the top of that list rather than to a rota.</p>

<p><b>Where the numbers come from, and this is what the system changes.</b> Value at risk is calculable: total purchasing, total cash handled, total stock value, total credit extended. Likelihood is informed by the control testing in modules 3 and 7 — a process with no approval mechanism is materially more likely to fail than one with a workflow and segregation.</p>

<p><b>So a plan can be built from evidence rather than judgement alone</b>, and it can be defended when somebody asks why their area is being examined and another is not.</p>

<p><b>The estate dimension.</b> With twenty branches you are not planning one audit but choosing among twenty similar units. Module 8's composite ranking answers this: branches appearing in the worst quartile on several measures, repeatedly, are where fieldwork goes. That is a defensible allocation and it is visibly not arbitrary, which matters when a branch manager asks why you are at their store.</p>

<p><b>Leave room, deliberately.</b> A plan filled to capacity has no space for the investigation that will arrive, the acquisition nobody mentioned, or the thing you find in March. Twenty to thirty per cent unallocated is realistic. Functions that plan every week either abandon the plan by April or refuse the work that mattered most.</p>

<p><b>What the plan should contain beyond fieldwork.</b> Building and maintaining the test programme. Follow-up on prior findings, which is where most functions under-allocate and where most value is lost. Time for exploration, which module 2 argued produces more new tests than any amount of repeating last year's work.</p>

<p><b>Getting it approved rather than merely accepted.</b> Present the risk map with the plan against it, including what is not being covered and why. That converts the plan from a schedule into a set of choices the audit committee has endorsed — and it means the risks you are not examining have been accepted by somebody with the authority to accept them.</p>

<blockquote>IMPLEMENTATION TIP: Build next year's plan from the composite ranking and the risk map rather than from this year's plan. If the two produce the same schedule, that is a useful confirmation. If they do not, this year's plan was describing history.</blockquote>

<p><b>Plan in quarters rather than a year.</b> A twelve-month schedule agreed in January is fiction by June in most businesses. Commit the first quarter in detail, sketch the rest, and re-cut it quarterly against what the programme has surfaced. That is both more honest and easier to defend than an annual plan that everybody knows will be abandoned and nobody says so.</p>"""
, [
 C("Next year's plan is drafted by amending this year's. The consequence is that fieldwork finds:",
   ["The most material risks", "Only what somebody thought to look for several years ago",
    "Recurring issues efficiently", "Results comparable to last year"], 1,
   "Build from the risk map and the composite ranking instead."),
 C("A plan filled to capacity will:",
   ["Maximise coverage", "Be abandoned by April, or refuse the work that mattered most",
    "Demonstrate rigour", "Satisfy the committee"], 1,
   "Twenty to thirty per cent unallocated is realistic."),
 C("Presenting the risk map alongside the plan means the risks you are not covering:",
   ["Are hidden", "Have been accepted by somebody with authority to accept them",
    "Can be added later", "Are outside scope"], 1,
   "It converts the plan from a schedule into endorsed choices.")]),

("What this architecture removes, and adds", 12, """<p>Every system has a risk profile of its own. An auditor arriving from a different environment will carry assumptions that no longer apply, and will miss risks that are specific to this one. Both errors cost time.</p>

<p><b>What ZhiftERP removes from the risk register.</b></p>

<p><b>The POS-to-ledger reconciliation.</b> Module 6 established this: the till writes the same backend, so there is no interface to fail and no gap between two systems for losses to hide in. An auditor from a separate-POS retailer will plan a week for it. That week is available for better work.</p>

<p><b>Undetectable master data changes.</b> Field-level version history means a price change or a bank detail change is reconstructable with old and new values. In many systems this is simply unavailable.</p>

<p><b>Silent deletion of history.</b> Submitted documents are cancelled and amended rather than edited, leaving a trail rather than a hole.</p>

<p><b>Manual consolidation across branches.</b> One database means branch comparison is a query rather than a collection exercise, which is what makes module 8's composite possible at all.</p>

<p><b>What it adds.</b></p>

<p><b>Concentration of privilege.</b> One system holding everything means an administrator holds everything. Module 7's point, and it is sharper here than across separate systems where no single person spans them.</p>

<p><b>Configuration as a single point of failure.</b> A setting changed once alters behaviour everywhere. Module 3's argument, and the reason the configuration baseline matters.</p>

<p><b>The API path.</b> Users can act without an interactive session, which defeats login-based review unless you know to look.</p>

<p><b>Dependence on the record.</b> When the system is the only evidence, anything not recorded is invisible — verbal authorisations, emailed quotes, informal arrangements. Module 4's caution applies generally: the system tells you what was recorded, not what was agreed.</p>

<p><b>And the honest summary.</b> The architecture makes detection dramatically easier and makes prevention depend on configuration and access. That is a good trade for an auditor, provided you spend the time it frees on the risks it creates rather than on the ones it removed.</p>

<blockquote>IMPLEMENTATION TIP: Write your own version of this list for your business. It is the fastest way to explain to a new auditor, or to an external one, why your programme is shaped the way it is — and it prevents a year being spent on a reconciliation that cannot fail.</blockquote>

<p><b>Revisit the list after any significant change.</b> A new integration, a second system for a new business line, an acquisition running its own ERP — each reintroduces exactly the risks this architecture removed. The moment a second system exists, interface and reconciliation risk return, and a programme built on the assumption of a single source of truth is quietly out of date. That is worth knowing before the integration goes live rather than after.</p>"""
, [
 C("An auditor joining from a separate-POS retailer plans a week for the POS-to-ledger reconciliation. You should tell them:",
   ["To proceed as planned", "There is no interface to fail — the week is available for better work",
    "To sample it instead", "To automate it"], 1,
   "The till writes the same backend, so there is no gap between two systems."),
 C("What the architecture adds to the risk register includes:",
   ["Interface failure", "Concentration of privilege in whoever administers it",
    "Reconciliation risk", "Data fragmentation"], 1,
   "One system holding everything means an administrator holds everything."),
 C("The architecture makes detection easier and makes prevention depend on:",
   ["Supervision", "Configuration and access",
    "Staff training", "Physical controls"], 1,
   "Which is why modules 3 and 7 carry more weight here than in a fragmented landscape.")]),

("Credibility, and how it is lost", 12, """<p>An internal audit function has one asset. Everything it achieves depends on people believing that what it says is accurate, proportionate and disinterested. That asset takes years to build and can be spent in a single meeting.</p>

<p><b>The five ways it goes, in rough order of frequency.</b></p>

<p><b>Overstating a finding.</b> Describing a possibility as a certainty, implying intent the data cannot show, or presenting a ranked list as though position implied wrongdoing. One overstatement that is publicly corrected will be remembered for years, and every subsequent finding will be discounted against it.</p>

<p><b>Being wrong on a fact.</b> A number that does not reconcile, a population that turns out to be partial, a document you did not know existed. Most of these are preventable by the disciplines in module 2 — define the population, reconcile it, retain the extract, ask for the file before concluding.</p>

<p><b>Reporting the trivial with the same weight as the serious.</b> A report where a naming inconsistency sits beside a ₦40m exposure teaches the reader that the function cannot distinguish, and they will then apply their own filter to everything you produce.</p>

<p><b>Losing independence quietly.</b> Becoming helpful, sitting on projects, owning remediation. Nobody objects at the time, and then a finding is dismissed because you designed the thing.</p>

<p><b>Being invisible.</b> A function nobody hears from between annual reports is one nobody consults, and it will find out about the acquisition, the new system and the branch closure after they have happened.</p>

<p><b>How it is built.</b> Slowly and unglamorously. Findings that are right. Numbers that reconcile. Recommendations that can actually be implemented by the person named. Withdrawing cleanly when wrong — module 6 made this point and it bears repeating, because an auditor who withdraws a concern cleanly loses very little while one who defends a position after the explanation arrives loses the ability to raise the next one.</p>

<p><b>And usefulness before criticism.</b> The recoverable duplicate payment, the unclaimed rebate, the price variance worth ₦18m — module 4's argument. These are welcomed, they demonstrate that the function pays for itself, and they buy the standing that a fraud finding will require. A function whose first year consists entirely of control weaknesses has spent that year building resistance.</p>

<blockquote>WATCH-OUT: The finding most likely to damage you is the one you are most certain about, because certainty is what makes an auditor stop checking. Test the strongest finding hardest, and ask somebody who was not involved to argue the other side before it goes out.</blockquote>

<p><b>How credibility looks from the other side of the table.</b> Managers judge the function on whether its findings turn out to be right, whether the recommendations are possible, and whether it treats people fairly when it has power over them. None of that is about technical skill, and all of it determines whether the next finding is acted on. A technically excellent function that is regarded as unfair will find things and change nothing.</p>"""
, [
 C("Which failure will be remembered longest and discount every later finding?",
   ["A missed deadline", "One overstated finding that is publicly corrected",
    "A minor arithmetic error", "An unimplemented recommendation"], 1,
   "Every subsequent finding is discounted against it."),
 C("Reporting a naming inconsistency beside a ₦40m exposure teaches the reader that:",
   ["The function is thorough", "It cannot distinguish, so they will apply their own filter to everything",
    "All findings matter", "Coverage is comprehensive"], 1,
   "They will apply their own filter to everything you produce, and proportion is part of what a report communicates."),
 C("You have one finding you regard as beyond dispute. That is the one to:",
   ["Report first, since it is strongest", "Test hardest, and have somebody argue the other side",
    "Escalate immediately", "Present without qualification"], 1,
   "Certainty is what makes an auditor stop checking.")]),

("Working with the people you examine", 12, """<p>Everything in this track produces conversations with people who did not ask to be examined and cannot refuse. How those go determines whether the work changes anything.</p>

<p><b>Start from what is true about their position.</b> They are busy, they did not design the controls, most of what you find is not their fault, and they have limited ability to fix the process even when they agree with you. An approach that ignores all of that produces defensiveness that is entirely rational.</p>

<p><b>Lead with data, then ask.</b> Module 7 made this point about access reviews and it generalises. Arriving with questions gets you a description of how things are meant to work. Arriving with the position and asking which of it is intended gets you an explanation of how they actually work, and the gap between those two is usually the finding.</p>

<p><b>Ask for the file before you conclude.</b> If a contract, a quote or an approval might exist outside the system, request it early, in writing, from somebody who is not the subject. Either it arrives and your finding improves or dissolves privately, or it does not and its absence is part of the finding. Both beat being shown it in the meeting.</p>

<p><b>Separate the process from the person.</b> "No approval is required for adjustments" is about design. "You made forty adjustments" is about a person. The first gets engagement; the second gets a defence, and most of the time the first is the finding anyway.</p>

<p><b>Agree the facts before the conclusions.</b> Take the numbers to the manager, confirm the data is right, and only then discuss what it means. A meeting where the facts and the interpretation are contested simultaneously produces an argument about arithmetic, and the interpretation never gets discussed.</p>

<p><b>Give people the chance to be right.</b> Where an explanation exists, you want it before publication, not after. This is not softness; a finding that survives the manager's best explanation is a much stronger finding than one that never met it.</p>

<p><b>Where it must be adversarial.</b> Suspected fraud, and module 9 sets those rules — do not tip off, do not interview early, tell the person the charter names. That mode is the exception and it should be entered deliberately rather than drifted into, because it cannot be reversed once entered.</p>

<p><b>And a word about being the person who finds things.</b> The role attracts a certain isolation. You will know things you cannot discuss, and people will be careful around you. That is a real cost of the job and it is worth knowing in advance, because auditors who try to be liked by the people they examine end up unable to do either thing well.</p>

<p><b>The relationship to aim for is respect rather than warmth.</b> Managers should find you useful, straight and predictable — they should know exactly what you will do with what they tell you, and that you will not surprise them in a meeting with something you could have raised privately. That is achievable and durable. Trying to be liked is neither, and it usually costs the finding that mattered.</p>

<blockquote>IMPLEMENTATION TIP: Confirm the numbers with the manager before writing any conclusion. It costs one conversation, it removes the arithmetic argument from the reporting meeting entirely, and it makes the manager a participant in a finding rather than its recipient.</blockquote>"""
, [
 C("Arriving at a review with questions rather than data gets you:",
   ["Faster cooperation", "A description of how things are meant to work",
    "The manager's confidence", "A shorter meeting"], 1,
   "The gap between the design and the reality is usually the finding."),
 C("You are about to draft conclusions from figures the manager has not seen. Confirming them first is:",
   ["Unnecessary if the query is sound", "Worth one conversation — it removes the arithmetic argument from the reporting meeting",
    "Best done at the exit meeting", "Only needed where you expect a dispute"], 1,
   "Otherwise the meeting becomes an argument about arithmetic and the interpretation is never discussed."),
 C("Giving a manager the chance to explain before publication is:",
   ["A courtesy that weakens the finding", "What makes a surviving finding much stronger",
    "Required by standards", "A delay to avoid"], 1,
   "A finding that has met the best explanation and survived is worth far more than one that has not.")]),

("What a good year looks like", 12, """<p>This is the chapter to keep. Seven modules of technique, and this is what a year using them should actually produce.</p>

<p><b>By the end of the first quarter.</b> A charter, or at least its escalation clause, approved. A configuration baseline recorded. An access position extracted and reconciled to HR. The integrity report set run and clean, or its problems raised. Six to ten tests built, tuned in silence, and running. You will have found things already — dormant accounts, a supplier with no controls around its bank details, an approval mechanism that does not exist.</p>

<p><b>By mid-year.</b> The programme running on its cadence: weekly payment watch, monthly behavioural analytics, quarterly structural review. A composite branch ranking with three months of history, so the recurring names have emerged. Fieldwork directed by that ranking rather than by a rota. And a handful of findings closed rather than merely raised.</p>

<p><b>By the year end.</b> A trend on the measures that matter — conflicts without compensating controls, enabled accounts for leavers, the proportion of hits that were genuine, the proportion of findings implemented. A programme reviewed once and pruned. And an annual report that says specific things about specific populations rather than offering general assurance.</p>

<p><b>What success is not.</b> The number of findings raised, which rewards noise and can be increased indefinitely by lowering thresholds. The number of tests built, which rewards accumulation. Or the size of the largest fraud discovered, which is largely luck and, in a well-controlled year, should be zero.</p>

<p><b>What it is.</b> Two things. <b>Losses that did not happen</b>, which are invisible and which you will get no credit for — the payment stopped because the bank change was caught, the split order that never went through because the buyer knew the test existed. And <b>controls that now exist</b> where none did, which is the durable output of everything in this track.</p>

<p><b>The uncomfortable part of that.</b> Both are hard to demonstrate. An audit function that works produces an absence, and absences do not appear in reports. So track the leading measures rather than the dramatic ones, report the clean runs as assurance, and accept that the best year the function ever has will be one where very little appears to happen.</p>

<p><b>And the sentence worth carrying out of the whole track.</b> In a manual environment you rely on people behaving well. In a system environment you rely on the record of what they did — so your job is to know what the record makes impossible to hide, and to say clearly which risks it does not cover.</p>

<p><b>One last note about this track.</b> It has given you techniques, tests and a method, and none of it substitutes for knowing your own business — which categories move, which branches struggle, who has been there twenty years, where the pressure sits. The data tells you where to look; that knowledge tells you what you are looking at. Auditors with one and not the other produce either rankings nobody can interpret or opinions nobody can evidence.</p>

<blockquote>IMPLEMENTATION TIP: Pick two things from the first-quarter list and do them properly rather than starting all five. The charter's escalation clause and the access reconciliation are the two with the highest return for the least effort, and both can be finished in a fortnight.</blockquote>"""
, [
 C("Which is NOT a valid measure of a successful audit year?",
   ["Findings implemented", "The number of findings raised",
    "Conflicts without compensating controls", "The proportion of hits that were genuine"], 1,
   "It rewards noise and can be increased indefinitely by lowering thresholds."),
 C("The two real outputs of a functioning audit programme are:",
   ["Findings and recommendations", "Losses that did not happen, and controls that now exist",
    "Reports and visits", "Tests and coverage"], 1,
   "Both are hard to demonstrate, which is why leading measures matter."),
 C("Of the first-quarter list, the two with the highest return for least effort are:",
   ["The full test programme and the risk map", "The charter's escalation clause and the access reconciliation",
    "The configuration baseline and the composite ranking", "Fieldwork and follow-up"], 1,
   "Both can be finished in a fortnight, and doing two properly beats starting five.")]),
]


QUESTIONS = [
 Q("Internal audit's classical methods were designed for:", ["Small businesses", "Paper records in locations you had to travel to", "Manufacturing", "Regulated industries"], 1,
   "Sampling, vouching and the annual visit are sensible responses to that world.", "Ch1 §1", "What changes"),
 Q("The most common failure in adapting is:", ["Resistance", "Partial adoption — the same rota plus a few reports", "Over-automation", "Excessive testing"], 1,
   "It produces the cost of both approaches and the benefit of neither.", "Ch1 §9", "What changes"),
 Q("What the system does not supply is:", ["Attribution", "Judgement about what evidence means", "Completeness", "Timestamps"], 1,
   "An auditor who becomes a query-writer has traded the valuable half of the job.", "Ch1 §8", "What changes"),
 Q("Control existence became testable in minutes because controls are now:", ["Automated", "Configuration rather than behaviour", "Documented", "Certified"], 1,
   "Previously it required observing people over time.", "Ch1 §7", "What changes"),
 Q("A clean population test establishes that:", ["The control operated effectively", "The tested condition did not occur in the records", "The risk did not materialise", "Assertions are correct"], 1,
   "It does not cover routes your test cannot observe.", "Ch2 §4", "What you can say"),
 Q("Which is the honest form of an audit conclusion?", ["A general assurance the reader must accept", "Specific assurances naming the population, test and result", "A rating", "A control opinion"], 1,
   "Three things a reader can weigh, rather than one they must take on trust.", "Ch2 §5", "What you can say"),
 Q("Stating what proportion of the risk map has tests converts an opinion into:", ["A rating", "A map", "A schedule", "An assurance"], 1,
   "And it puts untested risks in front of people who can accept them.", "Ch2 §6", "What you can say"),
 Q("Functions reporting only exceptions create the impression that they:", ["Are efficient", "Find nothing when things work", "Have narrow scope", "Are well targeted"], 1,
   "A clean nil-expected run is evidence and should be reported.", "Ch2 §7", "What you can say"),
 Q("Every statement made should be traceable to:", ["A management assertion", "A defined population, a stated test and a retained result", "A control framework", "A prior finding"], 1,
   "The answer to 'how do you know' should take thirty seconds.", "Ch2 §8", "What you can say"),
 Q("Independence requires that you do not audit:", ["Senior management", "What you operate", "Related parties", "New systems"], 1,
   "An auditor drawn into fixing a problem has become part of what they examine.", "Ch3 §3", "Independence"),
 Q("The most common structural failure in mid-sized functions is:", ["Insufficient resources", "Reporting to the person they examine", "Lack of qualifications", "No charter"], 1,
   "Which makes the function advisory at best.", "Ch3 §5", "Independence"),
 Q("Since an auditor cannot instruct anybody, the operative skill is:", ["Escalation", "Influence", "Persistence", "Documentation"], 1,
   "Built through being right, useful and predictable.", "Ch3 §8", "Independence"),
 Q("The most common erosion of independence is:", ["Social closeness", "Being drawn into remediation", "Scope limitation", "Budget pressure"], 1,
   "Advise freely; own nothing.", "Ch3 §10", "Independence"),
 Q("Which charter clause should be written first if none exists?", ["Scope", "The escalation route for suspected fraud", "Resourcing", "Access rights"], 1,
   "Its absence causes irreversible damage.", "Ch4 §9", "The charter"),
 Q("Charter clauses should be agreed:", ["When first needed", "While the business is calm", "Annually", "By the executive"], 1,
   "Agreeing escalation at the moment you must escalate is a negotiation with an interested party.", "Ch4 §7", "The charter"),
 Q("Access rights in a charter should be:", ["Subject to notice", "Unrestricted and without prior notice", "Agreed per engagement", "Limited to finance systems"], 1,
   "Vague access becomes a negotiation exactly when negotiation is fatal.", "Ch4 §5", "The charter"),
 Q("A charter should be approved by:", ["The finance director", "The audit committee, board or owner", "The chief executive alone", "Internal audit itself"], 1,
   "Approval by an executive the function may examine defeats the purpose.", "Ch4 §8", "The charter"),
 Q("A plan built from last year's plan finds:", ["The most material risks", "What somebody thought to look for years ago", "Recurring issues", "Comparable results"], 1,
   "Build from the risk map and composite ranking instead.", "Ch5 §2", "Risk-based planning"),
 Q("How much of the annual plan should be left unallocated?", ["None", "Twenty to thirty per cent", "Half", "Ten per cent"], 1,
   "For the investigation that arrives and the thing you find in March.", "Ch5 §6", "Risk-based planning"),
 Q("Which plan element is most often under-allocated?", ["Fieldwork", "Follow-up on prior findings", "Test building", "Reporting"], 1,
   "It is where most value is lost.", "Ch5 §7", "Risk-based planning"),
 Q("Presenting the risk map alongside the plan means untested risks are:", ["Hidden", "Accepted by somebody with authority to accept them", "Deferred", "Out of scope"], 1,
   "It converts the plan into endorsed choices.", "Ch5 §8", "Risk-based planning"),
 Q("Fieldwork across an estate should be directed by:", ["A visit rota", "The composite ranking, especially recurring names", "Branch size", "Manager tenure"], 1,
   "Defensible, and visibly not arbitrary when a manager asks why you are there.", "Ch5 §5", "Risk-based planning"),
 Q("Which risk does this architecture remove?", ["Privilege concentration", "POS-to-ledger reconciliation failure", "Configuration single points of failure", "API access"], 1,
   "The till writes the same backend.", "Ch6 §3", "Architecture risk profile"),
 Q("Which risk does it add?", ["Interface failure", "Concentration of privilege", "Data fragmentation", "Manual consolidation"], 1,
   "One system holding everything means an administrator holds everything.", "Ch6 §7", "Architecture risk profile"),
 Q("Cancel-and-amend rather than editing in place removes the risk of:", ["Duplicate documents", "Silent deletion of history", "Approval bypass", "Backdating"], 1,
   "It leaves a trail rather than a hole.", "Ch6 §5", "Architecture risk profile"),
 Q("The architecture makes detection easier and prevention dependent on:", ["Supervision", "Configuration and access", "Training", "Physical controls"], 1,
   "Which is why modules 3 and 7 carry more weight here.", "Ch6 §10", "Architecture risk profile"),
 Q("When the system is the only evidence, what becomes invisible?", ["Cancelled documents", "Verbal authorisations and emailed quotes", "Master data changes", "Login activity"], 1,
   "The system records what was entered, not what was agreed.", "Ch6 §9", "Architecture risk profile"),
 Q("Which failure discounts every subsequent finding?", ["A missed deadline", "One publicly corrected overstatement", "An arithmetic slip", "An unimplemented recommendation"], 1,
   "Credibility takes years to build and can be spent in one meeting.", "Ch7 §3", "Credibility"),
 Q("Reporting trivial and serious findings with equal weight teaches readers to:", ["Read everything", "Apply their own filter to everything you produce", "Prioritise by value", "Trust the ranking"], 1,
   "Proportion is part of the message.", "Ch7 §5", "Credibility"),
 Q("An auditor who defends a position after an innocent explanation arrives:", ["Shows conviction", "Loses the ability to raise the next finding", "Protects the finding", "Demonstrates rigour"], 1,
   "Withdrawing cleanly costs very little.", "Ch7 §8", "Credibility"),
 Q("A first year consisting entirely of control weaknesses has:", ["Established rigour", "Built resistance", "Covered the risks", "Set expectations"], 1,
   "Usefulness before criticism buys the standing harder findings require.", "Ch7 §9", "Credibility"),
 Q("The finding most likely to damage you is:", ["The least certain", "The one you are most certain about", "The largest", "The oldest"], 1,
   "Certainty is what makes an auditor stop checking.", "Ch7 §10", "Credibility"),
 Q("Leading with data rather than questions produces:", ["Faster meetings", "An explanation of how things actually work", "Better cooperation", "Fewer disputes"], 1,
   "Questions get you the design; data gets you the reality.", "Ch8 §3", "Working with people"),
 Q("Facts should be agreed with the manager:", ["After conclusions are drafted", "Before discussing what they mean", "At the exit meeting", "Only if disputed"], 1,
   "Otherwise the meeting becomes an argument about arithmetic.", "Ch8 §6", "Working with people"),
 Q("'No approval is required for adjustments' rather than 'you made forty adjustments':", ["Softens the finding", "Separates process from person, and is usually the finding anyway", "Avoids the issue", "Delays resolution"], 1,
   "The first gets engagement; the second gets a defence.", "Ch8 §5", "Working with people"),
 Q("A finding that has survived the manager's best explanation is:", ["Weakened by the delay", "Much stronger than one that never met it", "Unchanged", "Compromised"], 1,
   "Which is why you want the explanation before publication.", "Ch8 §7", "Working with people"),
 Q("Adversarial mode should be:", ["The default for fraud-prone areas", "Entered deliberately, because it cannot be reversed", "Avoided entirely", "Decided by management"], 1,
   "Module 9 sets those rules and they apply from the moment you enter it.", "Ch8 §8", "Working with people"),
 Q("Which is NOT a valid measure of a successful year?", ["Findings implemented", "Findings raised", "Conflicts without compensating controls", "Genuine-hit proportion"], 1,
   "It rewards noise and rises whenever thresholds fall.", "Ch9 §5", "What a good year looks like"),
 Q("The two real outputs of a working programme are:", ["Reports and visits", "Losses that did not happen, and controls that now exist", "Tests and coverage", "Findings and recommendations"], 1,
   "Both are hard to demonstrate, which is why leading measures matter.", "Ch9 §6", "What a good year looks like"),
 Q("The best year an audit function has is one where:", ["Many frauds are found", "Very little appears to happen", "Findings peak", "Coverage is complete"], 1,
   "A function that works produces an absence, and absences do not appear in reports.", "Ch9 §7", "What a good year looks like"),
 Q("The two first-quarter items with the highest return are:", ["The full programme and risk map", "The charter's escalation clause and the access reconciliation", "The baseline and composite", "Fieldwork and follow-up"], 1,
   "Both can be finished in a fortnight.", "Ch9 §9", "What a good year looks like"),
 Q("The sentence to carry out of the track is that in a system environment you rely on:", ["Well-designed controls", "The record of what people did", "Management assertions", "Continuous supervision"], 1,
   "So the job is knowing what the record makes impossible to hide, and saying which risks it does not cover.", "Ch9 §8", "What a good year looks like"),
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
    rebalance(QUESTIONS, "control:auditor_role:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:auditor_role:checks")

    mod = {
        "title": "The Auditor in a System Environment",
        "desc": ("What changes when the record is complete, and what does not. The "
                 "assurance you are now entitled to state, independence and authority "
                 "without line power, the charter clause to write first, building a plan "
                 "from evidence rather than last year's plan, what this architecture "
                 "removes and adds, and what a good year actually looks like."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    path = "academy_control_data.json"
    data = {}
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
    data[KEY] = mod
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("questions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("topics:", dict(collections.Counter(q["topic"] for q in QUESTIONS)))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
