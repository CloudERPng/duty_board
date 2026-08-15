#!/usr/bin/env python3
"""Build 'Access and Segregation of Duties' into academy_control_data.json.

Module 7 of System-Based Internal Control in a Retail Environment.

Verified from Frappe v15 source: DocPerm carries role, permlevel, if_owner and
the read/write/create/delete/submit/cancel/amend flags; Role has disabled and
desk_access; Role Profile bundles roles; User Permission carries allow,
for_value, applicable_for and apply_to_all_doctypes; User carries enabled,
last_login, last_active, simultaneous_sessions, restrict_ip, api_key and
api_secret, and tracks changes.

The last two matter more than they look. simultaneous_sessions makes shared
logins testable rather than merely suspected, and api_access means a user can
act without ever appearing in a login record.

Run from the app package directory:  python3 build_control_m7.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "access"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The control behind every other control", 12, """<p>Every test in this track assumes that the person who created a document is the person the record names. Access control is what makes that assumption true, and where it fails, everything built on it fails silently.</p>

<p><b>Consider what a shared login does to your work.</b> Three cashiers using one account produce a void profile attributed to a person who may have been at home. An adjustment pattern belongs to nobody. A segregation conflict cannot be detected because there is only one identity. Every finding you produce is unattributable, and worse, you will not know it — the data looks entirely normal.</p>

<p>That is why access work comes before the analytical modules in importance even though it comes after them in this track: they were written first so you could see what depends on it.</p>

<p><b>What access control actually delivers, in three parts.</b></p>

<p><b>Identity</b> — that actions are attributable to a person. <b>Authority</b> — that people can do only what their role requires. <b>Segregation</b> — that no single person can complete a transaction end to end without another pair of eyes.</p>

<p>These fail differently. Identity failures make your evidence worthless. Authority failures create exposure. Segregation failures create opportunity. All three are testable from data and none appears in any operational report.</p>

<p><b>Why access drifts rather than being designed.</b> Permissions are set at implementation with reasonable intent, and then reality happens. Somebody covers a colleague's leave and keeps the role. A project needs temporary access that becomes permanent. A leaver's account stays enabled because disabling it broke a scheduled report. A role is widened to solve an urgent problem on a Friday.</p>

<p>Nobody decides that the finance clerk should also be able to create suppliers. It accumulates, one reasonable step at a time, and the resulting position is nobody's design and nobody's responsibility.</p>

<p><b>What this means for your findings.</b> Access findings almost never involve wrongdoing. Nobody misused the access; the point is that they could. That makes them easy to dismiss as theoretical — and it makes quantifying the exposure essential, exactly as with master data.</p>

<blockquote>WATCH-OUT: Test the access position before relying on any attributed finding. A void profile, an adjustment concentration or a discount pattern is only as good as the certainty that the named user was the person acting, and shared credentials are common enough in branch retail that the assumption must be checked rather than made.</blockquote>

<p><b>One reason access work is often neglected by internal audit specifically.</b> It looks like IT's job, and IT reasonably regards permissions as something they administer rather than something they design. So the technical function operates the mechanism and the business function owns the risk, and neither believes the appropriateness of access is theirs to judge. That gap is where the work sits, and an internal auditor is usually the only person positioned to see both sides of it.</p>"""
, [
 C("Three cashiers share one login. Your void profile for that account is:",
   ["Still valid in aggregate", "Unattributable, and the data will look entirely normal",
    "Overstated", "A segregation finding only"], 1,
   "Identity failures make evidence worthless without any sign that they have."),
 C("Access accumulates rather than being designed because:",
   ["Policies are weak", "Each widening was a reasonable step — leave cover, a project, an urgent Friday fix",
    "Systems default to open", "IT lacks a process"], 1,
   "Nobody decides the finance clerk should create suppliers; it accrues."),
 C("A manager responds that nobody has ever abused the access you have raised. The reply is that:",
   ["They are technical", "Nobody misused the access — the point is only that they could",
    "They belong to IT", "They cannot be quantified"], 1,
   "Which makes quantifying the exposure essential.")]),

("How permissions actually compose", 12, """<p>You cannot test access without understanding how it is assembled, and in Frappe it comes from several layers that combine. Auditors who examine only role names reach confident wrong conclusions.</p>

<p><b>Roles</b> are named bundles of capability — Accounts Manager, Stock User, Sales Manager. A user holds any number. A <b>Role Profile</b> bundles roles so that new staff can be set up consistently, which is good practice and also a way that access spreads faster than anybody notices: widen the profile and everybody who has it gains the capability.</p>

<p><b>DocPerm</b> is where the actual rights live. For a given doctype and role it carries separate flags for <code>read</code>, <code>write</code>, <code>create</code>, <code>delete</code>, <code>submit</code>, <code>cancel</code> and <code>amend</code>. Those last three are the ones that matter most in a retail control context: <b>cancel and amend are the rights that permit a void</b>, and they are frequently granted alongside write without anybody intending it.</p>

<p><b>permlevel</b> adds a second dimension. Fields can sit at a permission level above zero, so a role may read a document but not see or edit its sensitive fields. This is how a price or a credit limit can be visible to few while the document is visible to many. Where a business has never used permlevels, every field on a document is as accessible as the document itself.</p>

<p><b>if_owner</b> restricts a right to documents the user created. A role with write only <code>if_owner</code> is materially different from one with write generally, and the difference is invisible if you look only at the role name.</p>

<p><b>User Permission</b> restricts <i>which records</i> a user sees, rather than what they may do. Carrying <code>allow</code>, <code>for_value</code> and <code>applicable_for</code>, it is how a branch manager is confined to their own warehouse or company. <b>Note <code>apply_to_all_doctypes</code></b>: where it is not set, a restriction may apply to some doctypes and not others, which produces the situation where a manager cannot see another branch's stock but can see its invoices.</p>

<p><b>How to establish what somebody can actually do.</b> Roles held, from the user's role table. Rights those roles carry per doctype, from DocPerm. Record restrictions, from User Permission. And whether any of it is modified by permlevel or if_owner. Four queries, and the answer frequently surprises the person whose access it is.</p>

<blockquote>IMPLEMENTATION TIP: Test rights rather than role names. "Who holds the Stock Manager role" is a list; "who can cancel a submitted Stock Entry" is a control question, and the second list is usually longer and contains names nobody expected.</blockquote>

<p><b>A practical caution about inherited roles.</b> Some rights come from roles a user did not know they held — granted by a role profile, or by a default applied at creation. When you tell somebody they can cancel invoices, expect genuine surprise rather than evasion. Approach it as information rather than accusation, because the person holding unexpected access is usually as interested in removing it as you are in reporting it.</p>"""
, [
 C("Which DocPerm rights permit a void of a submitted document?",
   ["read and write", "cancel and amend", "create and delete", "submit and read"], 1,
   "They are frequently granted alongside write without anybody intending it."),
 C("A role granted write only if_owner is:",
   ["Equivalent to full write", "Materially different, and invisible if you look only at the role name",
    "A read-only role", "A permlevel restriction"], 1,
   "It confines the right to documents the user created."),
 C("A branch manager cannot see another branch's stock but can see its invoices. The likely cause is:",
   ["Two conflicting roles", "A User Permission without apply_to_all_doctypes set",
    "A permlevel setting", "A role profile error"], 1,
   "The restriction applies to some doctypes and not others.")]),

("The segregation matrix", 12, """<p>Segregation of duties says no single person should control a transaction end to end. In practice it reduces to a short list of combinations that must not sit with one individual, and the list is shorter than most policies suggest.</p>

<p><b>The four functions</b>, in the classical formulation and still the right one: <b>authorising</b> a transaction, <b>recording</b> it, holding <b>custody</b> of the asset, and <b>reconciling</b> the result. One person holding any two adjacent functions is where opportunity is created.</p>

<p><b>The combinations that matter in retail, and each is directly testable.</b></p>

<p><b>Create a supplier and release a payment.</b> Invent a payee and pay them. The highest-value conflict in the business, and module 4 established why.<br>
<b>Raise a purchase order and receive the goods.</b> Order what never arrives and confirm its arrival.<br>
<b>Hold stock and adjust it.</b> Take goods and write off the difference.<br>
<b>Take cash and reconcile the till.</b> Take money and agree the count to what remains.<br>
<b>Process a sale and authorise a refund.</b> Refund a sale that was never returned.<br>
<b>Change a price and sell at it.</b> Discount for a related party without any discount appearing.<br>
<b>Administer users and transact.</b> Grant yourself what you need, act, and remove it.</p>

<p><b>Building the matrix as data.</b> For each conflicting pair, express both sides as rights rather than roles — who can create a Supplier, who can submit a Payment Entry — then intersect the two lists. The result is the set of people holding the conflict. This is a query, not an interview, and it is the single most valuable access test there is.</p>

<p><b>Expect a long list first time, and expect it to be legitimate.</b> A small business cannot segregate everything; there may be four people in the finance function and seven conflicts. Reporting all of them as failures is unhelpful and will be ignored.</p>

<p><b>What to do instead: rank by exposure and ask about compensating controls.</b> Where segregation is impossible, something else must substitute — a review of all payments by somebody outside the process, a second signature on the bank, an exception report to a manager. <b>The finding is not the conflict but a conflict with no compensating control</b>, and that distinction is what makes an access report credible to a business that knows it is short-staffed.</p>

<p><b>The System Manager problem, which cuts across all of it.</b> Anybody holding full administrative rights holds every conflict simultaneously. That is examined in the next chapter, and it is why a segregation matrix that excludes administrators is describing a business that does not exist.</p>

<blockquote>IMPLEMENTATION TIP: Build the matrix once as a set of paired queries and re-run it quarterly. The list changes constantly as people move roles, and the value is entirely in noticing what has appeared since last time rather than in the first heroic exercise.</blockquote>

<p><b>How many conflicts to put in a report.</b> Not all of them. Rank by the value flowing through the conflicted process and report the top handful properly — exposure quantified, compensating control named or its absence stated, a specific remedy. A report listing sixty conflicts communicates that segregation is hopeless and invites the reader to give up. One that names four and shows what each permits gets four fixed.</p>"""
, [
 C("Your first segregation matrix returns forty conflicts in a finance team of five. You should:",
   ["Report all forty as failures", "Rank by exposure and identify which have no compensating control",
    "Recommend hiring", "Reduce the matrix scope"], 1,
   "A small business cannot segregate everything; reporting all of them will be ignored."),
 C("The highest-value segregation conflict in a retailer is between:",
   ["Ordering and receiving", "Creating a supplier and releasing a payment",
    "Selling and refunding", "Counting and adjusting"], 1,
   "Invent a payee and pay them — and module 4 established the rest."),
 C("A segregation matrix that excludes system administrators is:",
   ["Appropriately scoped", "Describing a business that does not exist",
    "Standard practice", "Sufficient for most purposes"], 1,
   "Anybody with full administrative rights holds every conflict simultaneously.")]),

("Privileged access", 12, """<p>Some people can do anything. That is unavoidable in any system, and the control is not to eliminate it but to make it small, visible and accountable.</p>

<p><b>Three questions about privileged access, and they are the whole chapter.</b> How many people hold it. What they do with it. And who would know if they did something they should not.</p>

<p><b>How many.</b> Count the holders of full administrative rights, and the holders of roles that approximate it. Most businesses discover the number is larger than they thought, because it accumulated: the implementation consultant, two people in IT, a finance manager who needed something once, a developer at a vendor, an account created for an integration. <b>Every one of those is a person who can do anything and can also cover their tracks</b>, which is the part that matters.</p>

<p><b>What they do.</b> Privileged users acting on operational documents — creating invoices, adjusting stock, changing prices — is the signal. Administration is legitimately about configuration and support; an administrator posting a stock adjustment at a branch is doing operational work with a tool that bypasses every control, and each instance should be explicable.</p>

<p><b>Who would know.</b> This is the uncomfortable one. If the person who administers the system is also the person who would detect misuse, there is no control. Detection must sit somewhere the administrator cannot reach — which for most retailers means the audit function, and it means your own access to the logs must not depend on their goodwill.</p>

<p><b>The API path, which auditors routinely miss.</b> A user with API credentials can act without a browser session. Actions are still attributed to that user and still recorded, but they will not appear in login-based reviews, and a user who never logs in can be transacting daily. Include API-enabled accounts in every access review, and treat an API credential on a human user's account — rather than a dedicated integration account — as a finding.</p>

<p><b>Integration and service accounts.</b> These typically hold broad rights, never log in interactively, and belong to nobody. They are attractive precisely for those reasons. Each should have a named human owner, a documented purpose, and rights no wider than that purpose requires — and an integration account whose password is known to three people is a shared login by another name.</p>

<p><b>The vendor question.</b> Where a supplier or consultant retains access, establish whether it is still needed, whether it is time-bounded, and whether their activity is visible to you. Long-dormant vendor accounts with full rights are common and are exactly the kind of thing that is nobody's job to review.</p>

<blockquote>WATCH-OUT: An administrator can disable change tracking, delete records, and alter permissions — including their own. This means your evidence depends on people you are examining. Where possible, extract and retain evidence promptly rather than assuming it will still be there, and treat any gap in a log as a finding rather than a technicality.</blockquote>

<p><b>The break-glass arrangement, where it exists.</b> Mature businesses keep an emergency administrative account, sealed, used only in a crisis, with its use alerting somebody independent. Where such an arrangement exists, test whether it was used and whether each use was reviewed. Where it does not, the practical alternative is that several people hold permanent administrative rights against the possibility of an emergency — which is a permanent exposure accepted to cover an occasional need, and worth naming as that trade rather than leaving unexamined.</p>"""
, [
 C("An administrator posts a stock adjustment at a branch. This is:",
   ["Normal support work", "Operational work with a tool that bypasses every control, and needs explaining",
    "Efficient escalation", "A configuration task"], 1,
   "Administration is legitimately about configuration and support."),
 C("A user with API credentials who never logs in interactively:",
   ["Cannot transact", "Can transact daily while never appearing in login-based reviews",
    "Is automatically restricted", "Appears in session logs"], 1,
   "Include API-enabled accounts in every access review."),
 C("If the person administering the system is also the person who would detect misuse:",
   ["Oversight is efficient", "There is no control",
    "A second reviewer is optional", "Logging compensates"], 1,
   "Detection must sit somewhere the administrator cannot reach.")]),

("Joiners, movers and leavers", 12, """<p>Access is granted attentively and removed carelessly. That asymmetry is where most access risk actually sits, and it is entirely testable.</p>

<p><b>Leavers.</b> The obvious one and still routinely wrong. Query users where <code>enabled</code> is set and <code>last_login</code> or <code>last_active</code> is older than a threshold, then compare against the current staff list. Expect to find accounts belonging to people who left months ago.</p>

<p>The reason is nearly always mundane: the leaver's account owned a scheduled report, or an integration used their credentials, or nobody told IT. That is worth stating in the finding, because it points at the fix — a leavers process that includes system access with a named owner — rather than at anybody's negligence.</p>

<p><b>Movers, which are worse and are almost never tested.</b> Somebody transfers from stores to finance. Their new role is added. Their old one is not removed, because removing it might break something and nobody is sure what depends on it. Now they hold both, and the segregation conflicts they hold are ones no policy contemplated.</p>

<p><b>Movers are the single largest source of segregation conflicts in a stable business</b>, and the test is straightforward: compare current role assignments against the role expected for a person's current position. Where no such mapping exists — where nobody has ever written down which roles a branch manager should hold — that absence is the finding, and it is the prerequisite for every other access test.</p>

<p><b>Joiners.</b> Test how new accounts are provisioned. Where a role profile exists, the question is whether the profile is appropriate. Where accounts are created by copying an existing user's access — which is common and convenient — the copy inherits everything the original accumulated, and access spreads by replication. A new clerk given the same rights as a fifteen-year veteran is how a business ends up with everybody able to do everything.</p>

<p><b>Temporary access.</b> Leave cover, a project, a month-end crunch. Test whether any mechanism exists to remove it, and if not, test how much of it is still in place. Temporary access with no expiry is permanent access with an optimistic name.</p>

<p><b>Contractors and third parties deserve a line of their own.</b> Implementation consultants, support vendors and temporary specialists are frequently granted broad access quickly and removed slowly, because nobody is certain the engagement is over. Test third-party accounts specifically: who they belong to, whether the engagement is current, when they last acted, and whether their rights match what the work required. This is one of the more reliably productive tests in the module.</p>

<p><b>The version history helps here.</b> User records track changes, so role additions and removals are queryable with dates and actors. "Who granted this role, when, and who asked for it" is answerable, and asking it occasionally changes how casually roles are granted.</p>

<blockquote>IMPLEMENTATION TIP: Reconcile the enabled user list against the payroll or HR staff list quarterly. It is one comparison, it requires no system knowledge, and it reliably finds accounts that should not exist — which makes it the best first access test for a function that has never done one.</blockquote>"""
, [
 C("Headcount has been stable for three years yet conflicts keep appearing. The likeliest source is:",
   ["New joiners", "Movers who keep old roles when they gain new ones",
    "Leavers", "Temporary access"], 1,
   "Removing the old role might break something and nobody is sure what depends on it."),
 C("New accounts are created by copying an existing user's access. The consequence is:",
   ["Consistent provisioning", "Access spreads by replication, inheriting everything the original accumulated",
    "Faster onboarding only", "A role profile requirement"], 1,
   "A new clerk with a fifteen-year veteran's rights is how everybody ends up able to do everything."),
 C("No mapping exists of which roles each position should hold. This is:",
   ["A documentation gap", "The finding, and the prerequisite for every other access test",
    "An HR matter", "Acceptable in a small business"], 1,
   "Without it you cannot test whether anybody's access is appropriate.")]),

("Identity, and shared logins", 12, """<p>Everything attributable rests on one person, one account. In branch retail that assumption fails often enough that it must be tested rather than believed.</p>

<p><b>Why sharing happens.</b> A queue, a forgotten password, a supervisor override needed while the supervisor is on break, a new starter whose account has not been created, a till that must keep working. Every reason is operational and immediate, and none involves any intent to conceal. That is precisely why it is common and why lecturing about policy does not fix it.</p>

<p><b>What it destroys.</b> Attribution, and therefore every profiling test in modules 5 and 6. Segregation, because one credential may hold rights that were never meant to combine in one person. And accountability, because nobody can be held to an action and nobody can be cleared of one either — which is worth saying to staff, since being unable to prove your own innocence is a real cost to them.</p>

<p><b>Testing it with data.</b> Frappe's User record carries <code>simultaneous_sessions</code>, which caps concurrent sessions and where set low makes sharing harder. It also carries <code>restrict_ip</code>. Between configuration and activity data, several tests are available:</p>

<p><b>Improbable movement.</b> The same account acting at two branches within a period nobody could travel. This is the strongest single indicator and it needs only transactions with timestamps and a branch or warehouse.<br>
<b>Sessions beyond a plausible shift.</b> An account active for sixteen continuous hours is more than one person or a session nobody logged out of, and both are worth knowing.<br>
<b>Activity while the named user is on leave.</b> A comparison against the leave record, and one of the few tests where a single hit is close to conclusive.<br>
<b>Volume beyond a person.</b> Transaction counts materially above what one operator could physically perform in the hours available.</p>

<p><b>The configuration side.</b> Whether <code>simultaneous_sessions</code> is set to 1 for operational users, whether passwords expire, whether accounts lock after failed attempts. These are cheap to check and each is a recommendation that costs nothing to implement.</p>

<p><b>How to report it.</b> Not as misconduct. The finding is that the business cannot attribute actions to individuals at named branches, with the consequence spelled out — that no cashier can be cleared of a difference, and no profiling test is reliable there. Framed that way it is usually accepted quickly, because branch managers understand the risk to their own people.</p>

<blockquote>WATCH-OUT: If shared logins are found, every attributed finding from that branch must be qualified. Do not report a cashier profile from a branch where credentials are shared as though it identified individuals — it identifies a credential, and presenting it otherwise is the fastest way to have an entire report dismissed.</blockquote>

<p><b>What to recommend rather than a policy statement.</b> Sharing is usually a symptom: too few accounts, slow provisioning, a supervisor override needed more often than a supervisor is available. Recommending that staff stop sharing addresses none of that and will not work. Recommending that new starters get accounts on day one, that override authority sits with somebody present on every shift, and that concurrent sessions be capped — those change the conditions that produced the sharing.</p>"""
, [
 C("Which test most strongly indicates a shared credential?",
   ["High transaction volume", "The same account acting at two branches within a period nobody could travel",
    "Long sessions", "Frequent password resets"], 1,
   "It needs only transactions with timestamps and a branch."),
 C("Shared logins should be reported as:",
   ["Staff misconduct", "The business being unable to attribute actions, so nobody can be cleared either",
    "An IT configuration issue", "A training failure"], 1,
   "Branch managers accept it quickly when the risk to their own people is spelled out."),
 C("You find shared credentials at Branch 6. A cashier profile you already produced for that branch:",
   ["Remains valid", "Must be qualified — it identifies a credential, not individuals",
    "Should be withdrawn entirely", "Is unaffected"], 1,
   "Presenting it as identifying individuals is the fastest way to have a report dismissed.")]),

("Audit trail integrity", 12, """<p>Your evidence lives in the same system as the activity you are examining, and some people can alter it. That is not a reason for despair; it is a reason to know precisely who, and to extract promptly.</p>

<p><b>What can be altered, and by whom.</b> Change tracking can be switched off per doctype, after which no version records are created — and the earlier ones remain, so a gap in version history for a doctype that previously had them is itself a signal. Records can be deleted where the right is granted. Permissions can be changed, including by the person using them. And documents can be cancelled and amended, which is legitimate and leaves a trail.</p>

<p><b>The tests.</b></p>

<p><b>Who holds delete rights</b> on transactional doctypes. Deletion should be rare and confined; a delete right on Sales Invoice or Stock Entry held by operational users is a control weakness regardless of whether anything was deleted.</p>

<p><b>Tracking status against a baseline.</b> Module 3 argued for a configuration baseline. This is where it pays: comparing the current tracking configuration against the recorded one shows whether anything was disabled, and by whom.</p>

<p><b>Permission changes.</b> User records track changes, so role grants and removals are queryable. Self-granted roles — where the user who added a role is the user who received it — are worth flagging every time, and are not always improper: an administrator may legitimately grant themselves something to perform a task. The question is whether it was removed afterwards.</p>

<p><b>Gaps.</b> Where documents are numbered sequentially, missing numbers are detectable. Where they are not, module 3's point applies: you have lost a completeness test most auditors assume they have.</p>

<p><b>Your own position, which deserves plain statement.</b> An internal auditor's access should be read-only and broad — able to see everything, able to change nothing. Read-only is what protects your independence; broad is what makes the work possible. Where your access is granted and can be revoked by somebody you may need to examine, that is a structural weakness in the audit function itself, and it belongs in a report to whoever your charter names rather than in a conversation with the person who controls it.</p>

<p><b>And the practical habit.</b> Extract and retain evidence when you find it, not when you write the report. Module 2 made this a working-paper standard; here it is a defensive one. Data can change, tracking can be disabled, and a snapshot held by you is the only version nobody else can alter.</p>

<blockquote>IMPLEMENTATION TIP: Check who holds delete rights on your transactional doctypes this week. It is one query, deletion should be almost nobody, and the answer in most businesses is a longer list than anybody expects.</blockquote>

<p><b>Where the trail extends beyond the application.</b> Database access sits outside everything discussed here: somebody with direct access to the database can change data without any application record at all, including the version history itself. That is normally a very short list of people, and establishing who is on it — and whether database activity is logged anywhere you can see — is a legitimate question for an internal auditor to ask, even though the answer sits with IT.</p>"""
, [
 C("Version records exist for a doctype up to March and none after. This suggests:",
   ["Nothing changed after March", "Change tracking was disabled, and the gap is the signal",
    "A retention policy", "A migration boundary"], 1,
   "Earlier records remain, which is what makes the gap visible."),
 C("An administrator granted themselves a role to perform a task. The audit question is:",
   ["Whether it was permitted", "Whether it was removed afterwards",
    "Who approved it", "Whether it was documented"], 1,
   "Self-granted roles are not always improper; retention of them is the issue."),
 C("An internal auditor's own access should be:",
   ["Broad and able to correct errors", "Read-only and broad",
    "Limited to reports", "Equal to a manager's"], 1,
   "Read-only protects independence; broad makes the work possible.")]),

("Testing access with data", 12, """<p>Access is usually assessed by interview and document review, which produces a description of what people believe. Testing it as data produces what is true, and the two differ more often than not.</p>

<p><b>The four extractions that give you everything.</b></p>

<p><b>Users and their status.</b> Every user with <code>enabled</code>, <code>last_login</code>, <code>last_active</code>, whether API credentials exist, and their role list. This single extract answers dormancy, leavers and privileged counts.</p>

<p><b>Rights by role.</b> DocPerm for the doctypes that matter, showing which roles carry create, write, submit, cancel, amend and delete at which permlevel. This converts role names into capabilities.</p>

<p><b>Record restrictions.</b> User Permission entries, with attention to <code>apply_to_all_doctypes</code>, which determines whether a branch restriction is complete or partial.</p>

<p><b>Change history.</b> Version records on User, showing role grants and removals with dates and actors.</p>

<p><b>Then the analysis, which is joins rather than judgement.</b> Intersect capability lists to find segregation conflicts. Compare the enabled user list against HR to find leavers. Compare role assignments against an expected mapping to find movers. Rank privileged holders. Count users per role and roles per user — a user with fifteen roles has accumulated rather than been assigned, and a role held by one person may be a conflict or may simply be somebody's job.</p>

<p><b>What data cannot tell you</b>, and it is worth being clear so you do not overstate. It cannot tell you whether access is appropriate for a job, because that requires knowing the job. It cannot tell you whether a compensating control operates. And it cannot tell you whether a shared credential is being shared, only that the pattern is consistent with sharing.</p>

<p><b>So the method is data first, then conversation.</b> Produce the position from data, then take it to the people who know what the jobs involve and ask which of it is intended. That order matters: an auditor who opens with questions gets a description of the design, while one who opens with the position gets an explanation of the reality — and the gap between those two is frequently the most useful thing in the report.</p>

<p><b>Frequency.</b> Quarterly for the full extract, and immediately after any reorganisation, system upgrade or period of significant staff movement. Access changes continuously and an annual review describes a position that no longer exists by the time it is written.</p>

<blockquote>IMPLEMENTATION TIP: Do the four extractions once and keep the queries. Access review then costs an hour a quarter rather than a fortnight a year, and it becomes something you actually do rather than something that slips.</blockquote>

<p><b>Presenting the position to people who will find it uncomfortable.</b> An access review tells managers that their teams can do things they did not intend, which reads as criticism of their supervision. Lead with the fact that access accumulates through ordinary events rather than through anybody's failure, show the delta rather than the absolute position, and ask which of it is intended rather than asserting which of it is wrong. The same data, presented as a question, gets cooperation that the same data presented as a finding does not.</p>"""
, [
 C("An auditor who opens an access review with questions rather than data gets:",
   ["A faster answer", "A description of the design rather than an explanation of the reality",
    "Better cooperation", "The same result"], 1,
   "The gap between those two is frequently the most useful thing in the report."),
 C("Which cannot be established from access data alone?",
   ["Who holds a conflicting pair of rights", "Whether the access is appropriate for the person's job",
    "Which accounts are dormant", "Who granted a role and when"], 1,
   "That requires knowing the job, which is why data comes first and conversation second."),
 C("A user holding fifteen roles has most likely:",
   ["Been assigned them deliberately", "Accumulated them",
    "A senior position", "A role profile applied"], 1,
   "Roles per user is one of the fastest indicators of drift.")]),

("The access tests and the review routine", 12, """<p>The working programme, and how to make an access review something that happens rather than something that is intended.</p>

<p><b>Nil-expected tests.</b> Any row needs explaining.</p>

<p><b>Enabled accounts for people who have left.</b> <i>Innocent:</i> a leaver's account retained for a scheduled job or integration — which is a finding about the integration rather than the leaver.<br>
<b>Delete rights on transactional doctypes held by operational users.</b> <i>Innocent:</i> almost none.<br>
<b>Change tracking disabled since the baseline.</b> <i>Innocent:</i> a deliberate decision somebody can name.<br>
<b>Activity while the named user is on leave.</b> <i>Innocent:</i> a genuine remote login, checkable.<br>
<b>API credentials on a human user's account.</b> <i>Innocent:</i> a developer's own testing account, which should not exist in production.</p>

<p><b>Analytical tests.</b> The position is the question.</p>

<p><b>Segregation conflicts ranked by exposure</b>, with compensating controls noted. <b>Privileged holders</b> and their operational activity. <b>Roles per user and users per role.</b> <b>Dormant enabled accounts</b> by age. <b>Improbable movement</b> and session length, for identity.</p>

<p><b>Making the review routine.</b> The four extractions from the last chapter, quarterly, comparing against the previous quarter. What matters is the delta — who gained access, who lost it, which conflicts are new. A quarterly comparison takes an hour; the first full review takes days, and it only has to be done once.</p>

<p><b>Who should confirm what.</b> Access appropriateness is a management judgement, not an audit one. The workable arrangement is that you produce the position and department heads confirm that each person's access matches their job. That confirmation is itself evidence, it puts the judgement where the knowledge is, and it makes the manager an owner of the answer rather than a recipient of a finding.</p>

<p><b>Reporting access findings so they are acted on.</b> Quantify the exposure, exactly as with master data. Not "segregation of duties weaknesses exist" but "four people can both create a supplier and release a payment, covering ₦1.4bn of annual payments, with no secondary review". Name the compensating control that is absent rather than the principle that is breached.</p>

<p><b>And the recommendation that usually matters most.</b> Not the individual removals — those get done and then drift back. It is the process: a leavers checklist that includes system access, a role mapping per position, a quarterly confirmation by managers, and an owner for each. Fix the mechanism and the position stays fixed; fix the position and you will find it again next year, which is how most access findings recur indefinitely.</p>

<p><b>The measure worth reporting over time.</b> Not the number of conflicts, which moves with headcount and reorganisations. Report the number of conflicts <i>without a compensating control</i>, and the number of accounts enabled for people who have left. Those two track whether the process is working rather than whether the business is complicated, and a trend on them is a far better statement about control than any snapshot.</p>

<blockquote>WATCH-OUT: Access findings recur more than any other category, because removals are done once and grants continue daily. If your report says the same thing it said last year, report the recurrence itself and address the process rather than listing the individuals again.</blockquote>"""
, [
 C("A leaver's account is still enabled because a scheduled job uses it. The finding concerns:",
   ["The leavers process only", "The integration depending on a personal account",
    "The scheduler configuration", "Nothing, if the job is legitimate"], 1,
   "The innocent explanation relocates the finding rather than removing it."),
 C("Who should confirm that a person's access matches their job?",
   ["Internal audit", "The department head who knows the job",
    "IT", "The individual concerned"], 1,
   "It puts the judgement where the knowledge is and makes the manager an owner of the answer."),
 C("Access findings recur more than any other category because:",
   ["They are ignored", "Removals happen once while grants continue daily",
    "They are low priority", "IT lacks resources"], 1,
   "Fix the mechanism and the position stays fixed; fix the position and you will find it again next year.")]),
]


QUESTIONS = [
 Q("Access control delivers identity, authority and:", ["Confidentiality", "Segregation", "Availability", "Accountability alone"], 1,
   "That no single person can complete a transaction end to end.", "Ch1 §4", "Why access matters"),
 Q("An identity failure such as a shared login makes your analytical findings:", ["Overstated", "Unattributable, with no visible sign", "Understated", "Unaffected in aggregate"], 1,
   "The data looks entirely normal.", "Ch1 §2", "Why access matters"),
 Q("Access drifts because:", ["Policies are absent", "Each widening was individually reasonable", "Systems default to open", "Audits are infrequent"], 1,
   "Leave cover, a project, an urgent Friday fix.", "Ch1 §6", "Why access matters"),
 Q("Access findings are easy to dismiss because:", ["They are technical", "Nobody misused the access — the point is that they could", "They lack evidence", "They belong to IT"], 1,
   "Which makes quantifying the exposure essential.", "Ch1 §8", "Why access matters"),
 Q("Actual rights per doctype and role are held in:", ["Role", "DocPerm", "Role Profile", "User Permission"], 1,
   "With separate flags for read, write, create, delete, submit, cancel and amend.", "Ch2 §3", "How permissions compose"),
 Q("Which rights permit a void of a submitted document?", ["read and write", "cancel and amend", "create and submit", "delete and write"], 1,
   "Frequently granted alongside write without anybody intending it.", "Ch2 §3", "How permissions compose"),
 Q("permlevel allows:", ["Time-limited access", "Sensitive fields to be restricted while the document remains visible", "Branch restriction", "Owner-only editing"], 1,
   "Where permlevels are never used, every field is as accessible as the document.", "Ch2 §4", "How permissions compose"),
 Q("User Permission restricts:", ["What a user may do", "Which records a user sees", "Which fields are editable", "Session duration"], 1,
   "Carrying allow, for_value and applicable_for.", "Ch2 §6", "How permissions compose"),
 Q("Where apply_to_all_doctypes is not set, a branch restriction may:", ["Fail entirely", "Apply to some doctypes and not others", "Apply only to reports", "Require a role profile"], 1,
   "Which produces the manager who cannot see another branch's stock but can see its invoices.", "Ch2 §6", "How permissions compose"),
 Q("The four classical functions to segregate are authorising, recording, custody and:", ["Approving", "Reconciling", "Reporting", "Reviewing"], 1,
   "One person holding any two adjacent functions creates opportunity.", "Ch3 §2", "Segregation matrix"),
 Q("A segregation matrix should be built by:", ["Interviewing managers", "Intersecting rights-based lists as a query", "Reviewing role names", "Reading job descriptions"], 1,
   "It is the single most valuable access test there is.", "Ch3 §5", "Segregation matrix"),
 Q("Where segregation is impossible in a small team, the finding is:", ["The conflict itself", "A conflict with no compensating control", "The headcount", "The role design"], 1,
   "That distinction is what makes an access report credible.", "Ch3 §8", "Segregation matrix"),
 Q("A matrix excluding administrators:", ["Is appropriately scoped", "Describes a business that does not exist", "Is standard", "Reduces false positives"], 1,
   "Full administrative rights hold every conflict simultaneously.", "Ch3 §9", "Segregation matrix"),
 Q("The three questions about privileged access are how many, what they do, and:", ["What it costs", "Who would know if they misused it", "How it is granted", "When it was reviewed"], 1,
   "Detection must sit somewhere the administrator cannot reach.", "Ch4 §2", "Privileged access"),
 Q("An API-enabled account that never logs in interactively:", ["Cannot transact", "Can transact while absent from login-based reviews", "Is automatically dormant", "Requires a session"], 1,
   "Auditors routinely miss this path.", "Ch4 §6", "Privileged access"),
 Q("An integration account whose password is known to three people is:", ["Correctly shared", "A shared login by another name", "Adequately controlled", "A service account"], 1,
   "Each should have a named owner, a documented purpose and minimal rights.", "Ch4 §7", "Privileged access"),
 Q("An administrator posting a stock adjustment is:", ["Routine support", "Operational work with a tool that bypasses every control", "A configuration task", "Efficient escalation"], 1,
   "Each instance should be explicable.", "Ch4 §4", "Privileged access"),
 Q("The largest source of segregation conflicts in a stable business is:", ["Joiners", "Movers keeping old roles", "Leavers", "Contractors"], 1,
   "Removing the old role might break something nobody has mapped.", "Ch5 §4", "Joiners movers leavers"),
 Q("Creating new accounts by copying an existing user causes:", ["Consistency", "Access to spread by replication", "Faster onboarding only", "Role profile drift"], 1,
   "The copy inherits everything the original accumulated.", "Ch5 §6", "Joiners movers leavers"),
 Q("Where no mapping of roles to positions exists:", ["Test individual users", "That absence is the finding and the prerequisite for other access tests", "Use the role profiles", "Ask each manager"], 1,
   "Without it you cannot test whether access is appropriate.", "Ch5 §5", "Joiners movers leavers"),
 Q("Temporary access with no expiry mechanism is:", ["A minor risk", "Permanent access with an optimistic name", "Acceptable if logged", "A process gap only"], 1,
   "Test how much of it is still in place.", "Ch5 §7", "Joiners movers leavers"),
 Q("The best first access test for a function that has never done one is:", ["A segregation matrix", "Reconciling enabled users against the HR staff list", "A privileged access review", "Session analysis"], 1,
   "One comparison, no system knowledge, and it reliably finds accounts that should not exist.", "Ch5 §9", "Joiners movers leavers"),
 Q("Which field caps concurrent sessions for a user?", ["restrict_ip", "simultaneous_sessions", "api_access", "desk_access"], 1,
   "Set low, it makes credential sharing materially harder.", "Ch6 §4", "Identity and shared logins"),
 Q("The strongest single indicator of a shared credential is:", ["Long sessions", "The same account acting at two branches within an impossible interval", "High volume", "Password resets"], 1,
   "It needs only transactions with timestamps and a branch.", "Ch6 §5", "Identity and shared logins"),
 Q("Shared logins also harm staff because:", ["Performance is misjudged", "Nobody can be cleared of an action either", "Training suffers", "Access is slower"], 1,
   "Worth saying to staff, since being unable to prove innocence is a real cost.", "Ch6 §3", "Identity and shared logins"),
 Q("Where credentials are shared, an existing cashier profile must be:", ["Withdrawn entirely", "Qualified — it identifies a credential, not individuals", "Reported unchanged", "Recalculated"], 1,
   "Presenting it otherwise is the fastest way to have a report dismissed.", "Ch6 §8", "Identity and shared logins"),
 Q("Version records present until March and absent afterwards indicate:", ["No changes occurred", "Tracking was disabled, and the gap is the signal", "A purge", "A migration"], 1,
   "Earlier records remain, which is what makes it visible.", "Ch7 §2", "Audit trail integrity"),
 Q("Delete rights on Sales Invoice held by operational users are:", ["Acceptable with approval", "A control weakness regardless of whether anything was deleted", "Necessary for corrections", "Covered by version history"], 1,
   "Deletion should be rare and confined.", "Ch7 §3", "Audit trail integrity"),
 Q("A self-granted role is problematic mainly if:", ["It was not approved", "It was not removed afterwards", "It exceeded the job", "It was undocumented"], 1,
   "An administrator may legitimately grant themselves something to perform a task.", "Ch7 §5", "Audit trail integrity"),
 Q("An internal auditor's access should be:", ["Broad with correction rights", "Read-only and broad", "Report-only", "Equal to a manager's"], 1,
   "Read-only protects independence; broad makes the work possible.", "Ch7 §7", "Audit trail integrity"),
 Q("Evidence should be extracted:", ["When the report is written", "When it is found", "At quarter end", "After confirmation"], 1,
   "Data can change and tracking can be disabled; your snapshot is the version nobody else can alter.", "Ch7 §8", "Audit trail integrity"),
 Q("Which extraction answers dormancy, leavers and privileged counts at once?", ["DocPerm by role", "Users with status, activity dates and roles", "User Permission entries", "Version records"], 1,
   "One extract covering enabled, last_login, last_active, API credentials and role list.", "Ch8 §2", "Testing access with data"),
 Q("Access data cannot establish:", ["Who holds conflicting rights", "Whether access suits the person's job", "Which accounts are dormant", "Who granted a role"], 1,
   "Which is why data comes first and conversation second.", "Ch8 §6", "Testing access with data"),
 Q("Opening an access review with data rather than questions yields:", ["Faster cooperation", "An explanation of reality rather than a description of the design", "Fewer disputes", "A shorter report"], 1,
   "The gap between the two is frequently the most useful thing in the report.", "Ch8 §7", "Testing access with data"),
 Q("Access reviews should be run:", ["Annually", "Quarterly, and after any reorganisation or upgrade", "Monthly", "On request"], 1,
   "An annual review describes a position that no longer exists by the time it is written.", "Ch8 §8", "Testing access with data"),
 Q("A user holding fifteen roles has probably:", ["A senior position", "Accumulated them", "A role profile", "Temporary cover"], 1,
   "Roles per user is one of the fastest indicators of drift.", "Ch8 §5", "Testing access with data"),
 Q("Which is a nil-expected access test?", ["Roles per user", "API credentials on a human user's account", "Privileged activity levels", "Session length distribution"], 1,
   "The innocent explanation is a developer's testing account, which should not exist in production.", "Ch9 §3", "Access tests and routine"),
 Q("Access appropriateness should be confirmed by:", ["Internal audit", "Department heads", "IT", "The individual"], 1,
   "It puts the judgement where the knowledge is and makes the manager an owner.", "Ch9 §6", "Access tests and routine"),
 Q("The quarterly access review should focus on:", ["The full position", "The delta since last quarter", "Privileged users only", "New joiners"], 1,
   "The first full review takes days and only has to be done once.", "Ch9 §5", "Access tests and routine"),
 Q("Access findings recur because:", ["They are ignored", "Removals happen once while grants continue daily", "They are low priority", "Systems reset them"], 1,
   "Fix the mechanism rather than the position.", "Ch9 §9", "Access tests and routine"),
 Q("The recommendation that matters most is:", ["Removing the individual conflicts", "The process — leavers checklist, role mapping, quarterly confirmation, with owners", "More frequent review", "Tighter role design"], 1,
   "Fix the position and you will find it again next year.", "Ch9 §8", "Access tests and routine"),
 Q("An access finding should be expressed as:", ["The principle breached", "The exposure quantified and the missing compensating control named", "The policy reference", "The number of users affected"], 1,
   "Four people covering ₦1.4bn of payments with no secondary review.", "Ch9 §7", "Access tests and routine"),
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
    rebalance(QUESTIONS, "control:access:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:access:checks")

    mod = {
        "title": "Access and Segregation of Duties",
        "desc": ("The control every other control rests on. How Frappe permissions "
                 "actually compose, building a segregation matrix as a query rather than "
                 "an interview, privileged and API access, movers as the largest source of "
                 "conflict, testing shared logins with data, audit trail integrity, and "
                 "making the review a quarterly hour rather than an annual fortnight."),
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
    print("modules in file: %s" % ", ".join(sorted(data)))
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    for l, n in zip(mod["lessons"], lens):
        print("   %-54s %5d" % (l["title"][:54], n))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("\nquestions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("topics:", dict(collections.Counter(q["topic"] for q in QUESTIONS)))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
