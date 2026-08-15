#!/usr/bin/env python3
"""Build 'Findings, Evidence and the Report' into academy_control_data.json.

Module 9, and the last of the track. Every technique in the preceding eight
produces nothing unless somebody acts on it, and most internal audit functions
in this market can find things and cannot get them fixed.

Chapter 9 is the one insisted on at blueprint stage: the first hour of a
suspected fraud. Auditors destroy their own cases routinely and it is covered
almost nowhere.

Run from the app package directory:  python3 build_control_m9.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "findings"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Why findings fail", 12, """<p>Most internal audit functions can find things. Far fewer can get them fixed, and the gap between those two is where the value of everything in this track is won or lost.</p>

<p><b>The six ways a correct finding produces nothing.</b></p>

<p><b>It was not believed.</b> The number did not reconcile, the population turned out to be partial, or a document existed that you had not seen. Module 2's disciplines exist for this, and the remedy is almost entirely preventive.</p>

<p><b>It was believed and dismissed as immaterial.</b> Frequently because the exposure was never quantified — "controls over adjustments are weak" invites a shrug where "any of nine storekeepers can write off any quantity, and ₦31m was written off last year with no second signature" does not.</p>

<p><b>It had no owner.</b> A recommendation addressed to a department is addressed to nobody. Without a named person and a date it will be agreed and forgotten, and the agreement will be sincere.</p>

<p><b>It could not be implemented.</b> A recommendation requiring headcount that does not exist, a system change nobody has budget for, or a process the business cannot actually run. Agreed politely, never attempted.</p>

<p><b>It was implemented and drifted back.</b> Access removals, in particular. The position was corrected and the mechanism that produced it was not.</p>

<p><b>Nobody followed up.</b> The single largest cause. Findings are raised, agreed, and never revisited, and the function reports the same weaknesses year after year without noticing that it has become a chronicler rather than a control.</p>

<p><b>What this chapter changes about how you work.</b> If a finding will fail for one of those six reasons, that is knowable when you write it rather than a year later. Quantify the exposure, name an owner, propose something implementable, address the mechanism rather than the instance, and put follow-up in the plan.</p>

<p><b>And the harder point about volume.</b> A report with twenty findings will produce fewer implemented changes than one with five, because attention is finite and a long list invites triage by whoever receives it — and their triage will not match yours. <b>Report fewer things and pursue them harder.</b> That is a discipline, not a compromise, and functions that adopt it change more than functions that do not.</p>

<blockquote>WATCH-OUT: The finding you are proudest of is often the one that fails, because effort spent on the analysis is frequently effort not spent on the reporting. A brilliant piece of work that produces no change is worth less than an obvious one that does.</blockquote>

<p><b>One more failure worth naming, because it is invisible from inside.</b> A finding that arrives too late. A control weakness reported eleven months after it was detectable is a weakness the business carried for eleven months, and the reader will reasonably ask why. Where a standing test surfaced something in March, the finding is a March finding, and reporting it in the annual cycle rather than when it appeared wastes most of the value continuous monitoring was built to create.</p>"""
, [
 C("A recommendation is addressed to 'the Finance Department'. It will be:",
   ["Actioned by the department head", "Agreed and forgotten, sincerely",
    "Escalated automatically", "Owned collectively"], 1,
   "Without a named person and a date, agreement costs nothing."),
 C("A report with twenty findings compared with one containing five will produce:",
   ["More implemented changes", "Fewer, because a long list invites triage that will not match yours",
    "The same outcome", "Broader coverage"], 1,
   "Report fewer things and pursue them harder — a discipline rather than a compromise."),
 C("The single largest cause of findings producing nothing is:",
   ["Disbelief", "Nobody following up",
    "Poor writing", "Insufficient evidence"], 1,
   "The function becomes a chronicler rather than a control without noticing.")]),

("The anatomy of a finding", 12, """<p>A finding has five parts, and each answers a question the reader will otherwise ask. Omitting any one is where most poor findings go wrong, and the missing part is usually the same one.</p>

<p><b>Condition — what is.</b> The fact, stated plainly and quantified. "Between January and November, 412 stock adjustments totalling ₦31.4m were posted at four branches without any secondary approval, because no approval mechanism is configured on Stock Entry."</p>

<p><b>Criteria — what should be.</b> The standard you are measuring against, and it must be stated or the reader supplies their own. Company policy, a control principle, a regulatory requirement, or simply what the business believes is happening. <b>Where no policy exists, say so</b> — the absence of a standard is frequently the more important finding.</p>

<p><b>Cause — why.</b> Not who. The mechanism: no approval was configured, the role was granted for leave cover and never removed, the price list was never loaded so the system had nothing to compare against. Cause is what the recommendation must address, and a finding without one produces a recommendation aimed at symptoms.</p>

<p><b>Effect — so what.</b> The exposure, in money where possible. Not "risk of loss" but what could be lost, how, and how much. This is the part that determines whether anybody acts, and it is the part most often written as a generality.</p>

<p><b>Recommendation — what should happen.</b> Specific, implementable, with an owner and a date. Its own chapter follows.</p>

<p><b>The part most often missing is cause</b>, and its absence is diagnostic. A finding that jumps from condition to recommendation usually means the analysis stopped at the symptom. "Adjustments lack approval, therefore introduce approval" skips the question of why none exists — which might be that the business tried it and the delay stopped branches trading, in which case your recommendation is about to be rejected for a reason you could have known.</p>

<p><b>Length.</b> A finding should fit on one page including all five parts. If it needs more, it is either several findings or it contains detail that belongs in an appendix. Readers who must work to extract the point will extract a different one.</p>

<p><b>And write the effect before the recommendation.</b> Sizing the exposure first tells you how much remediation the finding can justify. A ₦400,000 annual exposure does not warrant a control costing ₦2m a year to operate, and proposing one anyway is how a function acquires a reputation for being disconnected from the business.</p>

<blockquote>IMPLEMENTATION TIP: Write the five parts as five separate sentences before drafting anything. If you cannot complete the cause sentence, the work is not finished — you have observed something rather than understood it.</blockquote>

<p><b>Where several findings share a cause, say so.</b> Four separate weaknesses that all stem from nobody owning master data are one finding with four symptoms, and reporting them separately produces four small recommendations instead of one that would fix all of them. Look across your findings before writing them up and ask whether any collapse into a common cause — the consolidated version is both shorter and more likely to be acted on.</p>"""
, [
 C("You cannot complete the 'cause' sentence for a finding. This means:",
   ["The finding is still valid", "The work is not finished — you have observed something rather than understood it",
    "The cause is management's to determine", "It should be graded lower"], 1,
   "A finding without a cause produces a recommendation aimed at symptoms."),
 C("Where no company policy exists to serve as criteria, you should:",
   ["Use an international standard", "Say so — the absence of a standard is often the more important finding",
    "Omit the criteria", "Use management's expectation"], 1,
   "Otherwise the reader supplies their own standard."),
 C("The effect should be written before the recommendation because:",
   ["It reads better", "Sizing the exposure tells you how much remediation the finding can justify",
    "It is more persuasive", "Readers expect that order"], 1,
   "A ₦400,000 exposure does not warrant a control costing ₦2m a year to operate.")]),

("Grading", 12, """<p>A grade tells the reader how to allocate their attention. Get it wrong consistently and they stop reading the grades, then the findings.</p>

<p><b>Grade on exposure and likelihood, not on how the finding was discovered.</b> A finding that took three weeks of clever analysis is not more serious for that reason, and one noticed in passing is not less. This sounds obvious and is routinely violated, because effort feels like significance.</p>

<p><b>A workable three-level scheme.</b></p>

<p><b>High</b> — material loss has occurred or could occur without further failure. The control does not exist, or exists and does not operate. Requires action within weeks and belongs in front of the audit committee.</p>

<p><b>Medium</b> — a control weakness where loss requires an additional failure or where the exposure is bounded. Action within the quarter.</p>

<p><b>Low</b> — a weakness worth correcting whose exposure is small. Include, but be prepared to drop it: a page of low findings dilutes the high ones and teaches the reader that most of what you report does not matter.</p>

<p><b>Grade the finding, not the department.</b> Aggregating into an overall rating for a branch or a function produces an argument about the rating and no discussion of the findings. Where a rating is demanded, tie it explicitly to defined criteria and expect it to be contested anyway.</p>

<p><b>The consistency requirement.</b> The same condition should carry the same grade wherever it appears. Auditors under pressure grade the same weakness High at a branch whose manager will not object and Medium at one who will, and everybody notices eventually. Write the grading criteria down and apply them mechanically where you can.</p>

<p><b>Distinguish a control weakness from a loss.</b> "No approval is required" and "₦4m was written off improperly" are different findings even where the first enabled the second. The first is a design finding with a permanent remedy; the second is an incident requiring recovery and possibly discipline. <b>Merging them means the design fix gets lost in the incident response</b>, which is exactly backwards, because the design fix is what prevents the next one.</p>

<p><b>And the grade you will be pressed on.</b> Management will argue High down to Medium, and sometimes they will be right. Change a grade when the argument is about facts you did not have; do not change it because the conversation is uncomfortable. A grade that moves under pressure is not a grade, and the next one will be argued harder.</p>

<blockquote>WATCH-OUT: A report where most findings are High has no High findings. The grade only carries information if it discriminates, and a function that grades everything seriously is telling the reader to decide for themselves — which they will, using criteria you cannot see.</blockquote>

<p><b>Grade for the reader you have.</b> An audit committee with quarterly meetings needs High to mean 'this cannot wait for the next meeting'. An owner-manager who reads everything may want finer discrimination. The scheme matters less than that it is written down, applied consistently, and understood the same way by you and by whoever receives it — a grade means nothing if the reader's interpretation differs from yours.</p>"""
, [
 C("A finding that took three weeks of analysis and one noticed in passing carry:",
   ["Grades reflecting the effort", "Grades reflecting exposure and likelihood only",
    "The same grade by default", "Grades set by management"], 1,
   "Effort feels like significance, which is why this is routinely violated."),
 C("'No approval is required' and '₦4m was written off improperly' should be:",
   ["Merged into one finding", "Reported separately — a design finding and an incident",
    "Graded identically", "Reported only as the loss"], 1,
   "Merging them means the design fix gets lost in the incident response."),
 C("A report where most findings are graded High:",
   ["Reflects a poorly controlled business", "Has no High findings",
    "Is appropriately urgent", "Requires escalation"], 1,
   "The grade only carries information if it discriminates.")]),

("Evidence that survives challenge", 12, """<p>A finding will be tested by somebody with an interest in its being wrong. Evidence is what makes it survive, and the standard is not what convinces you — it is what convinces a sceptical reader who was not there.</p>

<p><b>What the file must contain</b>, and module 2 set most of this as a working-paper standard. Here it is a defensive one.</p>

<p><b>The population and its definition.</b> Doctype, date field, date range, docstatus, scope, exclusions with reasons. The commonest successful challenge is not that the analysis was wrong but that the population was, and a population you cannot define precisely is a finding you cannot defend.</p>

<p><b>The extract as it stood.</b> Retained, not re-runnable. Underlying documents may be amended, cancelled or corrected between your work and the challenge, and re-running produces a different answer that undermines rather than supports you.</p>

<p><b>The test and its parameters.</b> The query or the saved report, with the threshold as it was applied.</p>

<p><b>The reasoning, including what you eliminated.</b> Hits examined and found innocent belong in the file. A file recording only what you pursued hides the judgement you exercised, and the judgement is the professional part — it also demonstrates that you looked for the innocent explanation rather than only for the guilty one.</p>

<p><b>Corroboration.</b> Where the finding rests on a pattern, the second and third measures that support it.</p>

<p><b>What is not evidence.</b> A ranking, on its own. A single anomalous transaction. Something somebody told you that you did not verify. A pattern with no quantification. Each of these is a reason to investigate and none survives being called into question.</p>

<p><b>The document you have not seen.</b> Module 4's caution generalises: the system records what was entered, not what was agreed. Contracts, quotes, approvals and correspondence may exist outside it. Ask for them early, in writing, from somebody who is not the subject — either the document arrives and your finding improves or dissolves privately, or it does not and its absence is part of the finding.</p>

<p><b>Retention.</b> Working papers should outlive the follow-up cycle, and in practice longer, because a recurring finding is only demonstrable if the earlier files exist. Keep them where the audit function controls them. A file on one auditor's laptop is not a record of the function's work.</p>

<blockquote>WATCH-OUT: Retain the extract at the moment you take it. Once anybody knows they are being examined, documents can be amended and explanations constructed. Version history will record the amendment — but you want the position as it was, held by you, before that becomes necessary.</blockquote>

<p><b>Evidence for a finding about an absence.</b> Where the finding is that no control exists, the evidence is configuration rather than transactions: a screenshot or extract showing no workflow attached, no authorisation rule, no approver role. These are easy to capture and easy to forget, because there is no exception list to point at. Capture them at the time — configuration changes, and a finding that a control was missing is much harder to make six months after somebody added one.</p>"""
, [
 C("The commonest successful challenge to a finding is that:",
   ["The analysis was wrong", "The population was wrong",
    "The grade was too high", "The recommendation was impractical"], 1,
   "A population you cannot define precisely is a finding you cannot defend."),
 C("Hits you examined and found innocent belong in the file because they:",
   ["Support the sample size", "Show the judgement you exercised and that you looked for innocent explanations",
    "Satisfy retention policy", "Reduce review time"], 1,
   "A file recording only what you pursued hides the professional part of the work."),
 C("Your finding rests on a branch ranking and nothing else. Challenged, it will:",
   ["Hold, since the ranking is objective", "Not survive — a ranking is a reason to investigate rather than a finding",
    "Depend on the grade", "Require only the population definition"], 1,
   "It needs the quantified population test and the corroborating measures behind it.")]),

("The recommendation somebody can implement", 12, """<p>A recommendation is the only part of a finding that changes anything. Most are written as the last line after the real work is done, and it shows.</p>

<p><b>Four properties, and a recommendation missing any one will not be implemented.</b></p>

<p><b>Specific.</b> "Strengthen controls over adjustments" is a sentiment. "Configure an Authorization Rule requiring approval by a regional manager for any Stock Entry above ₦250,000" is an instruction somebody can carry out.</p>

<p><b>Implementable by the person named.</b> A recommendation requiring budget from somebody who has none, or a system change the owner cannot commission, will be agreed and not attempted. Check that the owner can actually do it before naming them.</p>

<p><b>Proportionate.</b> The cost of the control against the exposure it addresses. A daily reconciliation to prevent a ₦300,000 annual loss consumes more than it saves, and proposing it damages your standing on the recommendations that are proportionate.</p>

<p><b>Aimed at cause rather than instance.</b> Removing the four conflicting role assignments fixes today. A quarterly access confirmation by department heads fixes it permanently. <b>Module 7's point about mechanism over position applies to almost every finding in this track</b>, and it is what distinguishes a recommendation that holds from one you will raise again next year.</p>

<p><b>Offer the choice where one exists.</b> Prevention through configuration, detection through an exception test, or acceptance with monitoring. Presenting alternatives with their costs makes you a participant in a decision rather than the source of an obligation, and management is far more likely to implement something they chose between than something they were told.</p>

<p><b>Accept a different remedy that achieves the objective.</b> If a manager proposes something other than your recommendation and it addresses the cause, take it — they will implement their own idea and resist yours. Your objective is the control existing, not your wording surviving.</p>

<p><b>And the recommendation you should be willing to make.</b> "Accept this risk explicitly, recorded, with a named owner." Where remediation genuinely costs more than the exposure, acceptance is the correct answer, and forcing every finding toward a fix produces dishonest closure. A recorded acceptance is a real outcome and it is honest.</p>

<blockquote>IMPLEMENTATION TIP: Before writing any recommendation, ask what specifically will be different on the day it is implemented, and who will do it. If you cannot answer both in a sentence, the recommendation is a sentiment and will be treated as one.</blockquote>

<p><b>Sequence the recommendations where there are several.</b> Some must happen before others are possible — a role mapping before an access review, a policy before compliance with it can be tested. Presenting six recommendations as a flat list invites the easiest to be done first, which is often the least useful. Number them in the order they must occur and say which are prerequisites.</p>"""
, [
 C("A manager rejects your proposed workflow and offers a daily exception report instead, which addresses the same cause. You should:",
   ["Insist on the workflow", "Accept it — an implemented remedy of their choosing beats a resisted one of yours",
    "Report the disagreement", "Grade the finding higher"], 1,
   "Your objective is the control existing, not your wording surviving."),
 C("A daily reconciliation proposed to prevent a ₦300,000 annual loss is:",
   ["Appropriately rigorous", "Disproportionate, and it damages your standing on the recommendations that are not",
    "A reasonable starting position", "A matter for management"], 1,
   "Cost of control against exposure addressed."),
 C("Where remediation genuinely costs more than the exposure, the correct recommendation is:",
   ["A reduced version of the control", "Explicit recorded acceptance with a named owner",
    "Deferral to next year", "Omitting the finding"], 1,
   "Forcing every finding toward a fix produces dishonest closure.")]),

("The conversation before publication", 12, """<p>What happens between finishing the analysis and issuing the report determines whether the finding lands. Most of the outcome is decided there.</p>

<p><b>Confirm the facts first, and separately.</b> Take the numbers to the manager before you write conclusions. Ask whether the data is right, not whether the conclusion is fair. A meeting where facts and interpretation are contested simultaneously becomes an argument about arithmetic, and the interpretation is never reached.</p>

<p><b>Ask for the explanation you have not thought of.</b> Genuinely, and early. If one exists, you want it now rather than in the committee meeting. A finding that has met the manager's best explanation and survived is worth several that have not.</p>

<p><b>Separate process from person.</b> "No approval is configured" invites engagement. "You approved forty adjustments" invites a defence. Most of the time the process statement is the finding anyway, and where an individual's conduct genuinely is the finding, that is a different conversation with different rules — chapter nine.</p>

<p><b>Agree the recommendation with the person who must implement it</b>, before publication. A recommendation agreed in draft is one they have already accepted; one that appears in a final report is one done to them. This costs one conversation and materially changes implementation rates.</p>

<p><b>No surprises.</b> Nobody should read something about their area in a committee paper that they have not seen. This is not softness — it is the single strongest predictor of whether a manager cooperates with the function next time, and a manager ambushed once will manage information carefully thereafter, which costs you far more than the surprise was worth.</p>

<p><b>Record disagreement rather than resolving it.</b> Where management does not accept a finding, publish it with their position stated fairly alongside yours. That is more credible than a report where everything is agreed, and it puts the disagreement in front of the people whose job is to weigh it. A function that only reports what management accepts is reporting management's view.</p>

<p><b>And where you turn out to be wrong.</b> Say so, in writing, to everyone who received the concern, and record what the explanation was so the test can be tuned. Withdrawing cleanly costs very little. Defending a position after the explanation arrives costs the ability to raise the next finding — and that is a much larger price than any single finding is worth.</p>

<blockquote>IMPLEMENTATION TIP: Send the draft finding to the manager with a specific question: is anything here factually wrong, and is there an explanation I have missed. Two questions, a short deadline, and it removes almost every dispute that would otherwise happen in public.</blockquote>

<p><b>Keep the exchange in writing.</b> Verbal agreement to a finding evaporates, honestly, as people reconstruct conversations differently. A short email confirming what was agreed — the facts, the action, the owner, the date — costs two minutes and prevents the version of events where nobody quite recalls committing to anything. It also gives the owner something to act from.</p>"""
, [
 C("A manager reads a finding about their area for the first time in a committee paper. The lasting cost is:",
   ["A difficult meeting", "They will manage information carefully thereafter",
    "A disputed grade", "A delayed response"], 1,
   "No surprises is the single strongest predictor of future cooperation."),
 C("Management does not accept your finding. You should:",
   ["Withdraw it", "Publish it with their position stated fairly alongside yours",
    "Escalate before publishing", "Downgrade it"], 1,
   "A function that only reports what management accepts is reporting management's view."),
 C("Agreeing the recommendation with its implementer before publication:",
   ["Compromises independence", "Materially changes implementation rates, at the cost of one conversation",
    "Delays the report", "Weakens the finding"], 1,
   "A recommendation agreed in draft is one they have accepted; one in a final report is done to them.")]),

("Follow-up, and the recurring finding", 12, """<p>Follow-up is the least glamorous work in internal audit and the point at which most functions leak all their value. A finding raised and never revisited is a finding that did not happen.</p>

<p><b>Track four things per finding.</b> The agreed action, the named owner, the due date, and the current status. That is a small table and most functions do not maintain it, which means at any moment nobody can say how many findings are outstanding or how old they are.</p>

<p><b>Verify rather than accept.</b> "Implemented" reported by the owner is a claim. Test it: is the Authorization Rule actually configured, are the roles actually removed, does the exception report actually run. Verification takes minutes for most findings because they are configuration, and it is the difference between a closure and an assertion.</p>

<p><b>Report the ageing, not just the count.</b> Twelve open findings means little. Twelve open, of which four are more than a year old and two have been agreed twice, is a statement about the business — and it is the statement most likely to produce action from an audit committee, because it is about the process for handling findings rather than about any individual finding.</p>

<p><b>The recurring finding deserves special treatment.</b> Where the same weakness appears a second time, the finding is no longer the weakness. It is that the business agreed to fix something and did not, which is a different and more serious matter, and it should be reported that way — with the original date, the agreement, and the fact that nothing happened.</p>

<p>This is the most powerful thing an audit function can put in front of a board, and it requires only that earlier files were kept.</p>

<p><b>Distinguish not-done from drifted-back.</b> A recommendation never implemented is a follow-up failure. One implemented and reversed is a mechanism failure, and the remedy differs: the first needs pressure, the second needs a control over the control — which is usually a periodic review rather than a stronger initial fix.</p>

<p><b>Closing findings honestly.</b> Three legitimate closures: implemented and verified, superseded by something better, or accepted as a risk with a named owner. <b>Everything else is open</b>, however long it has been there and however tired everybody is of seeing it. Functions that close findings to keep the list tidy have removed the only pressure that existed.</p>

<p><b>And put follow-up in the plan.</b> It is the first thing dropped when the year gets busy, and it is where the return on everything else is realised. A function that raises fifty findings and follows up none has done less than one that raises ten and closes eight.</p>

<blockquote>WATCH-OUT: Never close a finding because it has been open a long time and nobody is acting on it. That is precisely the finding that should be escalated, and closing it converts a governance problem into a tidy report.</blockquote>

<p><b>Report closures as well as openings.</b> A function that reports only what remains open looks like a source of unending problems. Reporting what was closed, verified, and what improved as a result gives the committee evidence that the process works and gives the managers who did the work some visible credit — which materially affects how the next recommendation is received. It costs a line in the report.</p>"""
, [
 C("An owner reports a finding as implemented. You should:",
   ["Close it", "Verify it — configuration takes minutes to check",
    "Close it and re-test next year", "Request written confirmation"], 1,
   "Reported implementation is a claim; verification is the difference between a closure and an assertion."),
 C("The same weakness appears for a second year. The finding is now:",
   ["The weakness, restated", "That the business agreed to fix something and did not",
    "A resourcing constraint", "An accepted risk"], 1,
   "A different and more serious matter, and the most powerful thing to put before a board."),
 C("A finding open for two years with nobody acting should be:",
   ["Closed to keep the list current", "Escalated — closing it converts a governance problem into a tidy report",
    "Downgraded", "Reissued as new"], 1,
   "Closing findings for tidiness removes the only pressure that existed.")]),

("Reporting upward", 12, """<p>The audit committee or the owner receives what the function produces and decides what happens next. Reporting to them well is a distinct skill from finding things, and it is the one auditors are least often taught.</p>

<p><b>What they need, and it is less than most reports contain.</b> Whether anything requires their intervention. Whether the control position is improving or deteriorating. Whether the audit function can do its job. Three questions, and a report that answers them in two pages will be read.</p>

<p><b>Lead with what requires a decision.</b> Not a summary of work performed. A committee reading four pages of activity before reaching the point has already allocated its attention elsewhere, and the important finding on page five arrives to a room that has stopped concentrating.</p>

<p><b>Trend beats snapshot.</b> Findings open and their ageing, conflicts without compensating controls, enabled accounts for leavers, the proportion of findings implemented. These say whether the control environment is getting better or worse, which is the question a committee actually has and which a list of this quarter's findings cannot answer.</p>

<p><b>Report clean results as assurance.</b> A nil-expected test returning nothing for six months is evidence and belongs in the report. Functions that report only exceptions give the impression of finding nothing when things work, which undersells the programme and makes the exception quarters look worse than they are.</p>

<p><b>Say what you did not cover.</b> The risk map with tests against it, including the gaps and why. This converts untested risks into decisions the committee has made rather than omissions you are responsible for, and it is the clearest way to raise resourcing without asking for it directly.</p>

<p><b>Raise limitations on the function itself.</b> Access you were refused, information not provided, scope restricted, a reporting line that compromises independence. These belong in the report to the committee and nowhere else, and a function that never raises them is either exceptionally well supported or not reporting fully.</p>

<p><b>Private session.</b> Where the committee will allow it, time without executives present. It is where anything concerning senior management can be raised, and its existence matters even in the quarters where nothing needs saying — because a private session that only happens when something is wrong announces that something is wrong.</p>

<blockquote>IMPLEMENTATION TIP: Structure every committee report the same way: decisions required, trend on the standing measures, significant findings, coverage and gaps, limitations. Consistency lets a reader find what they need, and a report they can navigate is one they read.</blockquote>

<p><b>And write for somebody who was not in any of the meetings.</b> Committee members read the paper days later, out of context, among other papers. Every finding must stand alone: what happened, why it matters, what is being done, by whom, by when. Internal shorthand, references to earlier discussions and assumed background all fail at that distance, and the finding that cannot be understood cold is the finding that gets deferred.</p>"""
, [
 C("A committee report opening with four pages of work performed means:",
   ["Thorough documentation", "The important finding on page five arrives to a room that has stopped concentrating",
    "Appropriate context", "Better accountability"], 1,
   "A committee that has already allocated its attention elsewhere will not recover it for page five — lead with what requires a decision."),
 C("Stating the risks you did not cover converts them into:",
   ["Audit omissions", "Decisions the committee has made",
    "Next year's plan", "Resourcing requests"], 1,
   "And it is the clearest way to raise resourcing without asking directly."),
 C("A private session that happens only when something is wrong:",
   ["Is efficient use of time", "Announces that something is wrong",
    "Is standard practice", "Protects management"], 1,
   "Its existence as a routine matters even in quarters where nothing needs saying.")]),

("The first hour", 12, """<p>The last chapter of the track, and the one most likely to matter on the day it does. When a pattern stops looking like error and starts looking deliberate, what you do in the first hour determines whether anything can be established at all.</p>

<p><b>Four rules, and each is broken routinely by capable people acting from good motives.</b></p>

<p><b>Do not tip off.</b> Not a casual question at the branch. Not a request for an explanation. Not an unusual data request routed through the department concerned. Not a supplier call. Every one of these is natural, and each has ended investigations that were otherwise sound.</p>

<p><b>Do not interview early.</b> An interview before the evidence is complete converts a strong position into a denial and a warning. You get one first conversation with the person concerned, and it is worth vastly more after the facts are established than before.</p>

<p><b>Preserve immediately.</b> Extract and retain everything: the documents, the version histories, the surrounding transactions, the access position. Do it before anybody knows, because documents can be amended, roles can be changed and explanations can be constructed — and because the person concerned may hold rights that let them alter what you are relying on.</p>

<p><b>Tell one person, the one your charter names.</b> Typically the audit committee chair or the chief executive. Specifically not the line manager of the person concerned, who may be involved and will certainly be conflicted. Module 1 argued for agreeing this in advance precisely so that this hour does not require a decision about who to trust.</p>

<p><b>What you are establishing, and its limit.</b> The data can show that goods left without a sale, that a bank account was changed before a payment, that one person had access and opportunity. <b>It cannot show intent.</b> A report implying it has overstepped, and it will be attacked on exactly that point by somebody who is right to attack it there.</p>

<p><b>Where your role ends.</b> You establish what the data shows. You do not conduct disciplinary proceedings, decide consequences, or accuse. Auditors step past this line from a sense of responsibility rather than ambition, which makes it harder to resist and no less damaging — and once past it, the independence that made the work credible is gone.</p>

<p><b>Handing over.</b> At some point this becomes somebody else's process — HR, legal, an external investigator, occasionally the police. Your contribution is a defensible factual position: what happened, when, how much, what the data establishes and what it does not. Prepared properly, that is enormously valuable. Prepared as an accusation, it is a liability to whoever inherits it.</p>

<p><b>And a closing word on the whole track.</b> Eight modules of technique, and their purpose was never to catch people. It was to make the record tell the truth about what happened — so that losses are visible while they are small, honest staff cannot be suspected without evidence, and the business knows what it is standing on. The catching is rare. The knowing is the job.</p>

<p><b>One practical note for the day it happens.</b> Write a contemporaneous record as you go — what you found, when, what you did, who you told, and at what time. Not a report; a log. Investigations become contested months later and memory is not evidence. A dated log written on the day carries far more weight than a reconstruction, and it takes minutes while everything is fresh.</p>

<blockquote>WATCH-OUT: The single most common way an investigation is lost is a natural question asked at the branch during the exploratory phase. If you are unsure whether you have crossed from analysis into investigation, assume you have and apply these rules — the cost of applying them unnecessarily is nil.</blockquote>"""
, [
 C("You are unsure whether the work has become an investigation. You should:",
   ["Continue as before until certain", "Assume it has — the cost of applying the rules unnecessarily is nil",
    "Ask the manager", "Seek approval first"], 1,
   "The most common loss is a natural question asked at the branch during the exploratory phase."),
 C("The data establishes access, opportunity and a sequence of events. What it cannot establish is:",
   ["Timing", "Intent", "Value", "Attribution"], 1,
   "A report implying it has overstepped and will be attacked on exactly that point."),
 C("Evidence should be preserved before anybody knows because:",
   ["Retention policy requires it", "Documents can be amended, roles changed and explanations constructed",
    "Queries become slower", "The data may be purged"], 1,
   "And the person concerned may hold rights that let them alter what you are relying on.")]),
]


QUESTIONS = [
 Q("The largest single cause of findings producing nothing is:", ["Poor evidence", "Nobody following up", "Weak writing", "Disbelief"], 1,
   "The function becomes a chronicler rather than a control.", "Ch1 §8", "Why findings fail"),
 Q("A recommendation addressed to a department rather than a person is:", ["Collectively owned", "Addressed to nobody", "Escalated by default", "Standard practice"], 1,
   "It will be agreed and forgotten, and the agreement will be sincere.", "Ch1 §5", "Why findings fail"),
 Q("A report with twenty findings will produce:", ["More change than one with five", "Fewer implemented changes", "Broader coverage", "Better prioritisation"], 1,
   "Attention is finite and a long list invites triage that will not match yours.", "Ch1 §10", "Why findings fail"),
 Q("A finding implemented and then reversed indicates:", ["A follow-up failure", "A mechanism failure", "Poor evidence", "An unclear recommendation"], 1,
   "The position was corrected and the mechanism that produced it was not.", "Ch1 §7", "Why findings fail"),
 Q("The five parts of a finding are condition, criteria, cause, effect and:", ["Conclusion", "Recommendation", "Grade", "Owner"], 1,
   "Each answers a question the reader will otherwise ask.", "Ch2 §1", "Anatomy of a finding"),
 Q("The part most often missing is:", ["Condition", "Cause", "Effect", "Criteria"], 1,
   "Its absence means the analysis stopped at the symptom.", "Ch2 §7", "Anatomy of a finding"),
 Q("Where no policy exists to serve as criteria, you should:", ["Apply a standard framework", "State that no standard exists", "Omit criteria", "Use management expectation"], 1,
   "The absence of a standard is frequently the more important finding.", "Ch2 §4", "Anatomy of a finding"),
 Q("A finding should fit:", ["Three pages", "One page including all five parts", "A paragraph", "Whatever the evidence requires"], 1,
   "Readers who must work to extract the point will extract a different one.", "Ch2 §8", "Anatomy of a finding"),
 Q("Writing the effect before the recommendation tells you:", ["How to grade it", "How much remediation the finding can justify", "Who should own it", "When it is due"], 1,
   "A ₦400,000 exposure does not warrant a ₦2m control.", "Ch2 §9", "Anatomy of a finding"),
 Q("Findings should be graded on:", ["Effort and discovery method", "Exposure and likelihood", "Management response", "Value at the branch"], 1,
   "Effort feels like significance, which is why this is routinely violated.", "Ch3 §2", "Grading"),
 Q("A High grade means loss has occurred or could occur:", ["With several further failures", "Without further failure", "Only in exceptional cases", "Over several years"], 1,
   "It requires action within weeks and belongs before the audit committee.", "Ch3 §4", "Grading"),
 Q("Aggregating findings into a departmental rating produces:", ["Clear accountability", "An argument about the rating and no discussion of the findings", "Better prioritisation", "Management engagement"], 1,
   "Grade the finding, not the department.", "Ch3 §7", "Grading"),
 Q("A control weakness and an actual loss should be:", ["Merged", "Reported as separate findings", "Graded together", "Reported only as the loss"], 1,
   "Merging them means the design fix gets lost in the incident response.", "Ch3 §9", "Grading"),
 Q("A grade should be changed when:", ["The conversation is difficult", "The argument concerns facts you did not have", "Management objects formally", "The owner requests it"], 1,
   "A grade that moves under pressure is not a grade.", "Ch3 §10", "Grading"),
 Q("A report where most findings are High:", ["Reflects poor control", "Has no High findings", "Is appropriately urgent", "Needs escalation"], 1,
   "The grade only carries information if it discriminates.", "Ch3 §11", "Grading"),
 Q("The commonest successful challenge to a finding concerns:", ["The analysis", "The population", "The grade", "The recommendation"], 1,
   "A population you cannot define precisely is a finding you cannot defend.", "Ch4 §3", "Evidence"),
 Q("The extract must be retained rather than re-runnable because:", ["Queries are slow", "Underlying documents may be amended before the challenge", "Storage is required", "It proves the date"], 1,
   "Re-running produces a different answer that undermines rather than supports you.", "Ch4 §4", "Evidence"),
 Q("Hits found innocent belong in the file because they show:", ["Sample adequacy", "That you looked for the innocent explanation", "Compliance with standards", "Time spent"], 1,
   "The judgement is the professional part of the work.", "Ch4 §6", "Evidence"),
 Q("Which is NOT evidence on its own?", ["A defined population test", "A ranking", "A retained extract", "Corroborated measures"], 1,
   "It is a reason to investigate, not a finding.", "Ch4 §7", "Evidence"),
 Q("Documents existing outside the system should be requested:", ["After the finding is drafted", "Early, in writing, from somebody who is not the subject", "At the exit meeting", "Only if disputed"], 1,
   "Either your finding improves or dissolves privately, or its absence is part of the finding.", "Ch4 §8", "Evidence"),
 Q("Working papers should be retained:", ["One year", "Beyond the follow-up cycle, since recurrence needs the earlier files", "Until the report is issued", "Per the IT policy"], 1,
   "And somewhere the audit function controls.", "Ch4 §9", "Evidence"),
 Q("'Strengthen controls over adjustments' fails because it is:", ["Too ambitious", "A sentiment rather than an instruction", "Incorrectly graded", "Unowned"], 1,
   "Name the mechanism, the threshold and the approver.", "Ch5 §3", "Recommendations"),
 Q("A recommendation should address:", ["The instance", "The cause", "The person", "The report"], 1,
   "Mechanism over position, which is what makes a recommendation hold.", "Ch5 §6", "Recommendations"),
 Q("A manager proposes a different remedy that addresses the cause. You should:", ["Hold your version", "Accept it", "Report both", "Escalate"], 1,
   "Your objective is the control existing, not your wording surviving.", "Ch5 §8", "Recommendations"),
 Q("Where remediation costs more than the exposure, recommend:", ["A partial control", "Explicit recorded acceptance with a named owner", "Deferral", "Omission"], 1,
   "Forcing every finding toward a fix produces dishonest closure.", "Ch5 §9", "Recommendations"),
 Q("Offering prevention, detection or acceptance as alternatives makes you:", ["Indecisive", "A participant in a decision rather than the source of an obligation", "Less authoritative", "Slower"], 1,
   "Management implements what it chose between.", "Ch5 §7", "Recommendations"),
 Q("Facts should be confirmed with the manager:", ["After conclusions are drafted", "Before conclusions are written", "At the exit meeting", "Only where disputed"], 1,
   "Otherwise the meeting becomes an argument about arithmetic.", "Ch6 §2", "Before publication"),
 Q("A manager first reading a finding in a committee paper will:", ["Respond promptly", "Manage information carefully thereafter", "Accept the finding", "Request a meeting"], 1,
   "No surprises is the strongest predictor of future cooperation.", "Ch6 §6", "Before publication"),
 Q("Where management rejects a finding you should:", ["Withdraw it", "Publish it with their position stated fairly", "Escalate before publishing", "Downgrade it"], 1,
   "A function reporting only what management accepts is reporting management's view.", "Ch6 §7", "Before publication"),
 Q("Withdrawing a finding cleanly when wrong costs:", ["The function's credibility", "Very little", "The relationship", "The year's work"], 1,
   "Defending it after the explanation arrives costs the ability to raise the next one.", "Ch6 §8", "Before publication"),
 Q("Which four things must be tracked per finding?", ["Grade, cause, effect, owner", "Action, owner, due date, status", "Risk, control, test, result", "Date, department, grade, cost"], 1,
   "Most functions cannot say how many findings are outstanding or how old they are.", "Ch7 §2", "Follow-up"),
 Q("An owner reporting a finding as implemented should be:", ["Accepted", "Verified", "Asked to confirm in writing", "Re-tested next year"], 1,
   "Reported implementation is a claim, and configuration takes minutes to check.", "Ch7 §3", "Follow-up"),
 Q("A weakness appearing for the second year is now a finding about:", ["The weakness", "The business agreeing to fix something and not doing it", "Resourcing", "Risk appetite"], 1,
   "The most powerful thing an audit function can put before a board.", "Ch7 §5", "Follow-up"),
 Q("Which is NOT a legitimate closure?", ["Implemented and verified", "Closed because it has been open a long time", "Superseded by a better control", "Accepted as a risk with an owner"], 1,
   "That is precisely the finding that should be escalated.", "Ch7 §8", "Follow-up"),
 Q("Reporting ageing rather than count matters because it is a statement about:", ["The auditor's workload", "The process for handling findings", "Individual managers", "Risk levels"], 1,
   "Which is what produces action from an audit committee.", "Ch7 §4", "Follow-up"),
 Q("A committee report should lead with:", ["Work performed", "What requires a decision", "The methodology", "Coverage statistics"], 1,
   "Otherwise the important finding arrives to a room that has stopped concentrating.", "Ch8 §3", "Reporting upward"),
 Q("Trend measures answer the question a committee actually has, which is whether:", ["Findings are material", "The control environment is improving or deteriorating", "The plan was completed", "Costs are controlled"], 1,
   "A list of this quarter's findings cannot answer it.", "Ch8 §4", "Reporting upward"),
 Q("Stating what you did not cover converts untested risks into:", ["Audit omissions", "Decisions the committee has made", "Next year's plan", "Scope limitations"], 1,
   "And it raises resourcing without asking directly.", "Ch8 §6", "Reporting upward"),
 Q("Limitations on the audit function itself belong:", ["In the annual report", "In the report to the committee", "In a memo to the executive", "Nowhere formally"], 1,
   "A function that never raises them is either exceptionally supported or not reporting fully.", "Ch8 §7", "Reporting upward"),
 Q("Which is the first rule of the first hour?", ["Preserve the evidence", "Do not tip off", "Tell the charter's named person", "Do not interview"], 1,
   "Not a casual question, a request for explanation, or a supplier call.", "Ch9 §2", "The first hour"),
 Q("An early interview converts a strong position into:", ["A confession", "A denial and a warning", "A negotiation", "A dispute"], 1,
   "You get one first conversation and it is worth far more after the facts are established.", "Ch9 §3", "The first hour"),
 Q("Who should NOT be told first?", ["The audit committee chair", "The line manager of the person concerned", "The chief executive", "Whoever the charter names"], 1,
   "They may be involved and will certainly be conflicted.", "Ch9 §5", "The first hour"),
 Q("The data cannot establish:", ["Access", "Intent", "Sequence", "Value"], 1,
   "A report implying it has overstepped and will be attacked there.", "Ch9 §6", "The first hour"),
 Q("If unsure whether analysis has become investigation:", ["Continue until certain", "Assume it has", "Ask management", "Seek approval"], 1,
   "The cost of applying the rules unnecessarily is nil.", "Ch9 §10", "The first hour"),
 Q("The purpose of the whole track is best described as:", ["Catching dishonest staff", "Making the record tell the truth about what happened", "Satisfying governance requirements", "Reducing stock losses"], 1,
   "The catching is rare; the knowing is the job.", "Ch9 §9", "The first hour"),
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
    rebalance(QUESTIONS, "control:findings:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:findings:checks")

    mod = {
        "title": "Findings, Evidence and the Report",
        "desc": ("The module that decides whether any of the others change anything. Why "
                 "correct findings produce nothing, the five parts of a finding, grading "
                 "that discriminates, evidence that survives challenge, recommendations "
                 "somebody can implement, follow-up and the recurring finding, reporting "
                 "upward, and the first hour of a suspected fraud."),
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
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
