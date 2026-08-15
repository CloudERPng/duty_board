#!/usr/bin/env python3
"""Build 'At the Counter: How ZhiftPOS Works' into academy_pos_pro_data.json.

The orientation module for the Certified ZhiftPOS Operator track.

Module 1 as it exists (counter_system) is written for consultants: it certifies
somebody who will configure a counter, and it spends its length on the four
architectural parts, the five roles, the selling modes and the profile as a
record to be built. A cashier will configure nothing. They need to know why the
till behaves as it does, what their own account means, what a completed sale
creates, and which of these things protect them personally.

Every fact here is derived from counter_system, which was written by somebody
who knows the product. Nothing asserts behaviour that module does not state.
Where the consultant module explains how to set something, this one explains
what it means at the counter.

Run from the app package directory:  python3 build_pos_operator_intro.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "counter_basics"
DATA = "academy_pos_pro_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, topic: {"q": q, "opts": opts, "ans": ans,
                                      "why": why, "topic": topic}


LESSONS = [
("Chapter 1 — What this certificate says about you", 10, """<p>This track certifies that you can run a ZhiftPOS counter properly: open a shift, build and complete a sale, handle the things that go wrong, work the extended counters, and close with a count that means something.</p>

<p><b>What it is not.</b> It does not certify you to configure a counter. Deciding what a cashier may do — whether discounts are allowed, whether refunds can be paid in cash, which payment methods appear — is done in the back office on a record called the Point of Sale Profile. That work belongs to an administrator, and there is a separate track for it. Knowing the profile exists matters to you; building one does not.</p>

<p><b>The one idea that explains almost everything.</b> ZhiftPOS is <b>governed centrally and trades locally.</b></p>

<p><i>Governed centrally</i> means the rules for your counter are set in the back office rather than at the till or by habit. What you can do is decided before your shift starts, and it is the same on Monday afternoon as at nine on a Saturday night.</p>

<p><i>Trades locally</i> means the till holds its own copy of the catalogue, prices and stock. Scanning is instant because nothing has to travel to a server first, and selling carries on when the internet drops.</p>

<p><b>Why a counter needs this much care.</b> The counter is where the business meets its money. Everything that arrives — the goods, the stock records, the prices somebody negotiated — passes through the few seconds in which you scan and take payment. A shop can buy well, price well and still lose the margin at the till, which is why the till is the part with the most rules attached.</p>

<p><b>What that means for the way this track reads.</b> You will meet controls that stop you doing things: greyed-out buttons, required reasons, approvals from somebody else. None of them exists because a cashier is not trusted. They exist because the counter handles money and goods at speed, and a rule enforced by software works at the end of a long Saturday in a way a rule remembered by a tired person does not.</p>

<p><b>And a promise about the rest of it.</b> Every rule in this track has a reason, and the reason is given. Where something seems awkward — a required explanation, a customer that must be attached, an approval you have to wait for — the chapter says what it prevents. You are entitled to know why, and a rule you understand is one you apply properly when nobody is watching.</p>

<blockquote>IMPLEMENTATION TIP: If any part of this track is printed and kept at the counter, make it the shift module — opening, the cart, payment and closing. This first module is the background; that one is the day.</blockquote>

<p><b>How the assessment works, so there are no surprises.</b> Each chapter ends with a few questions to check yourself as you go; they are not the exam and getting one wrong costs nothing. The exam comes at the end of each module, draws from a larger bank than you will see, and has a pass mark. If you fail, you can sit it again after a wait — the wait exists so that a retake is a second attempt at understanding rather than a second guess at the same questions.</p>"""
, [
 C("This certificate says you can run a counter. It does not say you can:",
   ["Handle returns", "Configure a counter — that is an administrator's work on the profile",
    "Close a shift", "Work the extended counters"], 1,
   "Knowing the profile exists matters to you; building one belongs to a separate track."),
 C("Scanning is instant even on a slow connection because the till:",
   ["Sends only the barcode", "Holds its own copy of the catalogue, prices and stock",
    "Caches the last hour", "Queues the scan"], 1,
   "Trades locally — nothing has to travel to a server before the item appears."),
 C("The controls that stop a cashier doing things exist because:",
   ["Cashiers are not trusted", "The counter handles money and goods at speed, and software rules hold at the end of a long Saturday",
    "Auditors require them", "They reduce training"], 1,
   "A rule remembered by a tired person is not the same as one enforced by the system.")]),

("Chapter 2 — The parts you actually deal with", 10, """<p>ZhiftPOS has four parts. Two of them you will use every day; the other two decide what you see, and knowing they exist saves you from calling for help you do not need.</p>

<p><b>The till application.</b> The program on your counter terminal — the Sales Console and the other counter screens. It is an installed application rather than a web page, and that is the reason it keeps working when the network cannot reach the server.</p>

<p><b>The background sync service.</b> Installed alongside it, started with the terminal, and running whether or not anybody is signed in. It keeps the local copies fresh and holds completed sales in a queue until they can post. You never operate it — but two of its behaviours matter to you: it catches up on its own, and it does not need anybody logged in to do so.</p>

<p><b>The back office.</b> The central system where items, prices, stock, customers and accounts live, and where profiles, promotions and vouchers are configured. Prices and policy come down from it; your completed sales go up to it.</p>

<p><b>The terminal management service.</b> Fleet monitoring — how the business sees the state of every terminal.</p>

<p><b>The rule that follows from all of this: never restart a terminal to force a sync.</b> The service catches up by itself, and a restart interrupts it mid-way rather than helping. If figures look stale, that is the local copy waiting to refresh, and it will.</p>

<p><b>Why 'installed application' is not a technical detail.</b> A web page needs the server for every action; an installed application with its own data does not. That single difference is what lets a queue of customers keep moving through a network outage, and it is why the offline chapters later in this track describe a normal way of working rather than an emergency.</p>

<p><b>What to do when the till behaves oddly.</b> Check the top bar first — it reports online or offline status, queued sales, and whether anything failed. Most of what looks like a fault is a state the top bar is already telling you about, and reading it takes two seconds.</p>

<p><b>What the top bar reports, in plain terms.</b> Whether you are online or offline. Whether any sales are queued — which is a safe state, not a problem. Whether anything has failed, which is the one that needs somebody. Whether stock or price figures are waiting to refresh. Plus your shift status and the lock. None of it requires interpretation, and glancing at it before you start a shift tells you what kind of day the terminal is having.</p><p><b>The one indicator that needs action rather than patience.</b> Where a cashier's queued sales cannot post until that person signs in online again, the bar says so. Queued alone resolves itself; that one does not, and it is the difference between waiting and doing something.</p>

<blockquote>WATCH-OUT: A restart is almost never the answer on a ZhiftPOS terminal, and it can make a sync worse. If something looks wrong, read the top bar, then ask — do not reach for the power button.</blockquote>"""
, [
 C("Figures on the till look stale. The correct response is:",
   ["Restart the terminal to force a sync", "Leave it — the sync service catches up on its own",
    "Sign out and back in", "Switch to another terminal"], 1,
   "A restart interrupts the service mid-way rather than helping it."),
 C("The sync service keeps running:",
   ["Only while a cashier is signed in", "Whether or not anybody is signed in",
    "Only when the terminal is online", "Only during shift hours"], 1,
   "It starts with the terminal and holds completed sales in a queue until they can post."),
 C("The till is an installed application rather than a web page, which is why:",
   ["It looks different", "A queue of customers keeps moving through a network outage",
    "It needs updating", "Scanning requires a driver"], 1,
   "A web page needs the server for every action; an installed application with local data does not.")]),

("Chapter 3 — Why your till behaves the way it does", 10, """<p>Two cashiers at two branches can sit in front of the same software and have different powers. That is not inconsistency — it is the Point of Sale Profile doing its job.</p>

<p><b>What the profile decides.</b> One profile governs one counter's entire behaviour, and almost every question about what a cashier can or cannot do is answered by a field on it:</p>

<p>Whether a discount can be given at all, and under which of three modes. Whether a refund can be paid in cash or only as store credit. Whether a shift must be opened before anything can be sold. Which payment methods appear, and in what order. Whether the counter sells vouchers, takes lay-bys, allows staff purchases, or checks customer credit limits. And who may approve the things a cashier cannot do alone.</p>

<p><b>Policy enforced by the system rather than by supervision.</b> In a shop without this, rules like these live in people's heads — and a rule in somebody's head is applied differently by different people, and differently by the same person at different hours. Here the rule is the same at every hour, for everybody on that profile, whether or not a supervisor is standing nearby.</p>

<p><b>The first troubleshooting rule, and it will save you calls.</b> A menu item you expected is missing, or a button is greyed out. That is almost never a fault. It is the profile, or your row on it, and the software is behaving exactly as configured.</p>

<p><b>Greyed controls give their reason.</b> Hover over a disabled control and it tells you why it is unavailable. Read it before asking — the answer is usually there, and it is usually specific.</p>

<p><b>What to do when a rule genuinely blocks a customer.</b> Not a workaround. Complete what you can, tell the customer plainly what is possible, and raise the rule afterwards with whoever owns the profile. Rules can be changed by the people who set them, and every workaround invented at a counter is a control the business thinks it has and does not.</p>

<p><b>How many profiles a business has.</b> As many as it has genuinely different counters. Two branches operating identically can share one; a pharmacy counter and a general counter cannot, because what they need to permit differs.</p>

<p><b>Why this is worth understanding rather than simply accepting.</b> A cashier who knows that powers come from a profile stops experiencing restrictions as personal. The colleague at the next branch who can process a cash refund is not more trusted than you — their counter is configured differently, probably for a reason somebody could explain. That distinction matters because the alternative reading, that some people are trusted more than others, is corrosive and almost always wrong.</p>

<blockquote>IMPLEMENTATION TIP: When something is missing or greyed out, hover for the reason, then check whether a colleague on the same counter has it too. Those two steps identify almost every case correctly before anybody is called.</blockquote>"""
, [
 C("A menu item you expected is not on your till. Most likely this is:",
   ["A software fault", "The profile, or your row on it, behaving as configured",
    "A network problem", "An expired session"], 1,
   "The first troubleshooting rule, and it saves a great many unnecessary calls."),
 C("A control is greyed out and you do not know why. You should:",
   ["Ask a supervisor immediately", "Hover over it — a disabled control gives its reason",
    "Restart the till", "Use another terminal"], 1,
   "The answer is usually there and usually specific."),
 C("A profile rule genuinely prevents you serving a customer as they want. The right response is:",
   ["Find a workaround at the till", "Do what is possible, say so plainly, and raise the rule afterwards",
    "Ask another cashier to try", "Complete it and correct it later"], 1,
   "Every workaround invented at a counter is a control the business thinks it has and does not.")]),

("Chapter 4 — Your account, and why it is only yours", 10, """<p>ZhiftPOS access runs on five roles. Yours is almost certainly <b>Cashier</b>: open a shift, sell, take payment, handle returns where permitted, close the shift, and reach the consoles your profile grants.</p>

<p><b>The other four, briefly.</b> The <b>Point of Sale Administrator</b> sets up and maintains the system. The <b>Sales Manager</b> supervises trading, approves overrides and reconciles shifts. Beyond these sit the roles that handle stock and back-office work. One person can hold more than one role, which is common in smaller businesses.</p>

<p><b>The rule that comes before every other rule in this track: one person, one account.</b></p>

<p><b>Why it matters more than it sounds.</b> When four cashiers share a login, every sale, every override and every variance carries the same name. Nothing can be attributed to anybody — and that single fact disables almost every control in the system. The discount report cannot tell you who discounted. The void pattern belongs to nobody. The shift variance is four people's work in one figure.</p>

<p><b>And the part that concerns you personally.</b> Attribution protects you as much as it exposes you. On your own account, a shortage on somebody else's shift is not yours and can be shown not to be. On a shared account, you cannot be blamed and you cannot be cleared either — and being unable to prove your own innocence is a real cost, paid by the honest cashier rather than the other kind.</p>

<p><b>How the till makes this practical on a shared terminal.</b> The lock button on the top bar lets one cashier lock the till and the next unlock it with their own credentials in seconds. Sharing a terminal is normal; sharing an account is not, and the lock is what makes the difference workable at speed.</p>

<p><b>What to do if you are asked to use somebody else's login.</b> It happens, and usually for an innocent reason — a new starter without an account yet, a forgotten password, a queue building. Say that the sales will be recorded against them and ask for the proper route: an account created, a password reset, or a manager sign-in, which is designed for exactly this and is tagged so everybody knows.</p>

<p><b>Passwords, briefly and practically.</b> Your account is your name on every sale of the day, so the password protects your record rather than the company's. Do not write it where the terminal is, do not tell a colleague in a hurry, and change it if you think somebody has seen it. A password shared once tends to stay shared, and the sales it produces are still recorded as yours.</p><p><b>And if you suspect somebody has used your account.</b> Say so promptly, to a supervisor, in writing if you can. Reporting it while it is a suspicion is straightforward; explaining it after a variance has been found is a much harder conversation, and the record will show your account either way.</p>

<blockquote>WATCH-OUT: Never leave a till unlocked and unattended. An unlocked till trades under your name — its sales, its overrides and its variances all become yours, and the lock takes one keystroke.</blockquote>"""
, [
 C("Four cashiers share one login. The effect on the system's controls is that:",
   ["Reports become slower", "Almost every control is disabled, because nothing can be attributed",
    "Only the variance report suffers", "Overrides stop working"], 1,
   "The discount report cannot say who discounted; the shift variance is four people's work in one figure."),
 C("A shared account harms an honest cashier specifically because:",
   ["Their sales count for less", "They cannot be cleared of somebody else's shortage",
    "Their permissions are reduced", "Their shift takes longer to close"], 1,
   "Being unable to prove your own innocence is a real cost, paid by the honest one."),
 C("Two cashiers work the same terminal across a busy afternoon. The workable arrangement is:",
   ["One signs in for the shift and both use it", "Each locks the till and the other unlocks it with their own credentials",
    "They open a joint shift", "They sign out fully after every customer"], 1,
   "Sharing a terminal is normal; sharing an account is not, and the lock makes the difference practical at speed.")]),

("Chapter 5 — Which counter you are working", 10, """<p>Every profile is set to one selling mode, and the mode decides which consoles appear and how a sale travels from basket to payment. Knowing which one you are on explains the shape of your day.</p>

<p><b>Standard.</b> One person builds the basket and takes the payment, on the Sales Console. The ordinary shop counter, and what most of this track assumes.</p>

<p><b>Pharmacy.</b> A two-stage flow for counters where the person who assembles the order and the person who takes the money are different. An <b>Order Console</b> where the order is built and handed off, then a <b>Checkout Console</b> where a second person collects payment.</p>

<p>It is standard practice in pharmacies, where a dispenser prepares medicines and a cashier handles money — and it is useful anywhere the goods and the money should pass through different hands. <b>The person who picked the items never touches the payment, and the person who takes the payment did not pick the items.</b> That separation is a control, not an inconvenience, and it is worth understanding if you work such a counter: the handoff is the point of the design rather than a step to be shortcut when it is busy.</p>

<p><b>What this means practically.</b> If your console list looks different from a colleague's at another branch, the mode is usually why. It is set on the profile, so it does not change during a shift and it is not something a cashier selects.</p>

<p><b>Where you work more than one counter.</b> Some staff cover a general counter on some days and a specialist one on others. The flow differs and the habits differ with it — checking which console has opened before starting is worth the two seconds, particularly at the start of a shift on a counter you do not work often.</p>

<p><b>A note for anyone moving between branches.</b> Cover shifts are where mode differences catch people out, because the habits of your usual counter arrive with you. Two seconds spent reading the console names, and one question to whoever is already there about how the handoff works, prevents the awkward version — completing a stage that was not yours to complete, in front of a customer, on a counter where somebody else was waiting to do it.</p>

<p><b>What does not change with the mode.</b> The rules from the rest of this track apply on every counter: the shift is opened and closed with a count, the record of every sale is an invoice, discounts and returns carry reasons and approvers, and your account is yours. The mode changes the shape of the sale, not the discipline around it — so nothing you learn in the later modules becomes optional because your counter works in two stages.</p>

<blockquote>IMPLEMENTATION TIP: On a two-stage counter, resist the temptation to complete both stages yourself when the other person steps away. The separation is the control, and the queue moving slightly slower is the price of it.</blockquote>"""
, [
 C("On a two-stage pharmacy counter, the colleague who takes payment steps away and a queue builds. You should:",
   ["Complete both stages yourself to keep the queue moving", "Wait — the separation of picking from payment is the control",
    "Switch the counter to standard mode", "Take payment and record it later"], 1,
   "The handoff is the point of the design rather than a step to shortcut when busy."),
 C("Your console list differs from a colleague's at another branch. The usual reason is:",
   ["A permissions error", "A different selling mode on that counter's profile",
    "A software version difference", "Their role"], 1,
   "The mode is set on the profile and is not something a cashier selects."),
 C("In pharmacy mode, the sale is built on the:",
   ["Sales Console", "Order Console, then handed to a Checkout Console",
    "Checkout Console only", "Return console"], 1,
   "Two stages and two people, so the person who picked the goods never touches the payment.")]),

("Chapter 6 — What happens when you press complete", 10, """<p>Knowing what a completed sale creates is what lets you answer a customer's question without calling anybody, and what lets you tell whether something has actually gone wrong.</p>

<p><b>An invoice is created.</b> Every completed sale becomes a sales invoice with a reference number, its item lines and its payments. <b>There is no such thing as an off-record sale on ZhiftPOS</b> — if it went through the till, there is an invoice.</p>

<p><b>A receipt is printed</b>, carrying the sale's reference and a barcode. Receipts can be reprinted later from the Recent Receipts panel or from Sales History, so a customer who has lost theirs is not a dead end.</p>

<p><b>The sale posts, or it queues.</b> Online, it reaches the back office within moments. Offline, it joins the queue and posts when the connection returns.</p>

<p><b>The two references, which is the part customers ask about.</b> A sale completed offline prints with a <i>local reference</i>. When it posts, it also receives a <i>back-office invoice number</i>. Both point to the same sale, and a return can be found using either one.</p>

<p>So an offline receipt is a fully valid document. Say so with confidence — a customer who sees an unfamiliar reference and asks whether their receipt is real deserves a plain yes rather than hesitation.</p>

<p><b>What this means when the network is down.</b> Nothing about the sale is provisional. The goods are sold, the receipt is valid, the record exists, and the posting is a background matter that resolves itself. Queued is a safe state, and the top bar tells you when anything is queued.</p>

<p><b>And what it means for stock.</b> Because every sale creates an invoice with its lines, stock reduces on the strength of what you actually scanned. That is the link between the counter and the stock figures the business relies on — and the reason a quantity typed carelessly is not just a pricing error but a stock one.</p>

<p><b>What the customer gets, and what the business gets.</b> The customer gets goods and a receipt they can return against. The business gets a priced record of what left the shelf, a reduction in the stock figure, and a payment recorded against a method. All three arrive from one action, which is why completing a sale properly matters more than any single step within it — an error at completion propagates into the stock position, the day's takings and the customer's ability to come back.</p>

<blockquote>IMPLEMENTATION TIP: When a customer questions an offline receipt, answer the question they are really asking: yes, this is a valid record of your purchase, and yes, we can find it for a return. Both are true, and hesitating about it invites a doubt that is not warranted.</blockquote>"""
, [
 C("A customer asks whether their offline receipt with an unfamiliar reference is a real receipt. The correct answer is:",
   ["It is provisional until the sale posts", "Yes — it is a fully valid document, and the sale can be found for a return",
    "It must be exchanged for a proper one", "Only if it is reprinted later"], 1,
   "Both the local reference and the later back-office number point to the same sale."),
 C("'There is no such thing as an off-record sale' means:",
   ["Sales cannot be cancelled", "If it went through the till, there is an invoice",
    "Receipts cannot be reprinted", "Offline sales are excluded"], 1,
   "Every completed sale becomes an invoice with its lines and payments."),
 C("A carelessly typed quantity is not only a pricing error because:",
   ["It affects the receipt", "Stock reduces on the strength of what was scanned",
    "It changes the tax", "It delays posting"], 1,
   "The invoice lines are the link between the counter and the business's stock figures.")]),

("Chapter 7 — What the system is protecting against", 10, """<p>Every major feature exists because of a specific and common problem at retail counters. Knowing the problems makes the rules make sense, and makes them much easier to apply properly when it is busy.</p>

<p><b>The exercise book.</b> Sales in a notebook, prices from memory, the day's total whatever the book says. No line-level record, stock never reduced, and any dispute settled by a pencil line against a customer's word. The invoice answers it: every sale recorded line by line, stock reduced automatically, every receipt reprintable.</p>

<p><b>The shared login.</b> One account for four people, so every sale, override and variance carries the same name. This single problem disables almost every control in the system, which is why one person one account comes before everything else — and why the lock button exists to make individual accounts practical on a shared terminal.</p>

<p><b>The memory price.</b> Prices held in people's heads means the same item sells at different prices in different shops, and nobody can say which was right. The price list answers it, and the rate-override marker is what makes a departure from it visible.</p>

<p><b>The uncounted drawer.</b> Totals that disagree with the cash by amounts nobody can break down, until <i>about right</i> becomes the accepted standard. The counted open and counted close answer it, which is why the shift module treats both as non-negotiable.</p>

<p><b>The phantom return.</b> A refund given against no original sale. The Return console answers it with a wall: no invoice, no return, and there is no path through that console starting from nothing.</p>

<p><b>What all of these have in common.</b> Each was, at some point, somebody being helpful or somebody being quick. None began as a decision to defraud. That is exactly why the answers are built into the software rather than left to intention — the system does not assume dishonesty, it removes the need to rely on memory, attention and goodwill at the end of a long day.</p>

<p><b>And the one worth carrying to the counter.</b> Every control in this track has a name and a story behind it. When one gets in your way, it is worth knowing which problem it was built to stop, because that is usually also the answer to how to work with it rather than around it.</p>

<blockquote>WATCH-OUT: The problems above are the common ones, and they are common because they are easy. Each begins with a reasonable shortcut on a busy day, which is precisely why the answer is a rule the system holds rather than a rule a person remembers.</blockquote>

<p><b>One that is worth naming separately: the cleared basket.</b> Building a basket, taking the customer's cash, then clearing the screen leaves no sale and no record, and the money goes into a pocket rather than a drawer. It is a known pattern rather than a hypothetical one, which is why cleared carts are recorded and reviewed, and why the habit taught in the shift module is to hold rather than clear. Knowing the reason makes the habit easy to keep.</p>"""
, [
 C("A refund is requested with no receipt and no reference of any kind. The Return console:",
   ["Allows it with a manager override", "Offers no path — no invoice, no return",
    "Searches by customer name", "Records it as goodwill"], 1,
   "That wall is what answers the phantom-return problem."),
 C("What do the exercise book, the shared login and the uncounted drawer have in common?",
   ["All are deliberate fraud", "Each began as somebody being helpful or quick, not dishonest",
    "All are rare", "All require system changes"], 1,
   "Which is why the answers are built into the software rather than left to intention."),
 C("The rate-override marker exists to answer:",
   ["The uncounted drawer", "The memory price — it makes a departure from the price list visible",
    "The phantom return", "The shared login"], 1,
   "Prices in people's heads mean the same item sells at different prices and nobody can say which was right.")]),

("Chapter 8 — Okelewo Stores, before", 10, """<p>This track follows one retailer, and it is worth knowing where they started, because the rules in the later modules were written against these facts rather than in the abstract.</p>

<p><b>The business.</b> Three branches — the flagship on Okelewo Lalubu Road in Abeokuta, a second smaller Abeokuta shop, and one in Lagos. Eleven counter staff across the three. The founder has run it for nine years, largely by personal presence and long hours.</p>

<p><b>The counters, before ZhiftPOS.</b> The two smaller branches ran on exercise books. The flagship had an old standalone till, and all four of its cashiers shared one login.</p>

<p><b>Prices lived in memory</b>, so they differed between branches. In one recorded week the same item sold at three different prices across the three shops — not through dishonesty, but because three people remembered three things.</p>

<p><b>Drawers were counted irregularly.</b> Day totals disagreed with the cash by amounts nobody could break down, and <i>about right</i> had become the accepted standard four days out of five.</p>

<p><b>Two incidents from the last month before rollout.</b> A refund was given twice against no receipt. And the shared login meant that when a shortage appeared, four people were equally implicated and none could be cleared.</p>

<p><b>What is worth noticing about this list.</b> Nobody in it is a villain. Eleven people were working hard in a business that had outgrown the way it was being run, and every one of the failures came from a system that asked people to hold prices, totals and rules in their heads while serving customers.</p>

<p><b>Why the example is used throughout.</b> Each later module returns to Okelewo at the point where the relevant rule first mattered — the first counted close, the first discount with a reason attached, the first lay-by that went overdue. Rules explained in the abstract are forgettable; the same rule attached to a shop that had the problem tends to stay.</p>

<p><b>And the fair thing to say about the before.</b> Most retailers in this market look something like this before they change, and recognising your own counter in the description is not an embarrassment. It is the reason the system exists, and the reason the rules in this track are worth learning properly rather than working around.</p>

<p><b>What changed afterwards, briefly.</b> The later modules follow Okelewo through the change — the first month of counted closes, the first discounts with reasons attached, the first lay-by that went overdue and was terminated by the book. None of it went perfectly, and the examples say so. A worked example where everything succeeds teaches nothing about what to do when something does not.</p>

<blockquote>IMPLEMENTATION TIP: When a rule in a later module seems heavy-handed, look at which Okelewo problem it answers. Almost every one of them traces back to something on this page, and seeing the connection is what turns a rule you comply with into one you would keep if it were optional.</blockquote>"""
, [
 C("The same item sold at three different prices across three branches in one week because:",
   ["Staff were dishonest", "Prices lived in memory and three people remembered three things",
    "The branches had different costs", "Promotions overlapped"], 1,
   "Three people remembered three prices, which is exactly what a central price list exists to end."),
 C("When a shortage appeared at the flagship, four cashiers were:",
   ["Individually accountable", "Equally implicated, and none could be cleared",
    "Cleared by the till record", "Identified by the shift log"], 1,
   "Which is the personal cost of a shared login, paid by the honest cashier."),
 C("Recognising your own counter in the description of Okelewo before is:",
   ["An embarrassment", "The reason the system exists and the rules are worth learning",
    "Unusual in this market", "A sign of poor management"], 1,
   "Most retailers look something like this before they change.")]),

("Chapter 9 — Review, and what comes next", 10, """<p>Check yourself against each section before the assessment. If any feels unclear, re-read its chapter — everything after this module builds on all of them.</p>

<p><b>What this certifies (Chapter 1).</b> Running a counter, not configuring one. Governed centrally and trades locally: rules set in the back office, selling done on a terminal holding its own catalogue, prices and stock. Every control exists because the counter handles money and goods at speed.</p>

<p><b>The parts (Chapter 2).</b> Till application — an installed program, which is why it survives an outage. Sync service — runs whether anybody is signed in or not, holds queued sales, catches up by itself. Back office — where policy and the books live. Terminal management — fleet monitoring. <b>Never restart to force a sync.</b> Read the top bar first.</p>

<p><b>The profile (Chapter 3).</b> One profile governs one counter. A missing menu item or greyed control is the profile, not a fault; hover for the reason. Raise a blocking rule afterwards rather than working around it.</p>

<p><b>Your account (Chapter 4).</b> One person, one account, before every other rule. A shared login disables almost every control and leaves an honest cashier unable to be cleared. Lock the till between users; never leave it unlocked and unattended.</p>

<p><b>The mode (Chapter 5).</b> Standard: one person builds and takes payment. Pharmacy: Order Console then Checkout Console, two people, deliberately separated. The mode is on the profile and explains why your consoles differ from a colleague's.</p>

<p><b>A completed sale (Chapter 6).</b> An invoice with lines and payments — no off-record sales. A receipt, reprintable. Posts online, queues offline. An offline sale has a local reference and later a back-office number; both find the same sale, and the offline receipt is fully valid.</p>

<p><b>The problems (Chapter 7).</b> Exercise book, shared login, memory price, uncounted drawer, phantom return. Each began as somebody being quick rather than dishonest, which is why the answers are built into the software.</p>

<p><b>Okelewo before (Chapter 8).</b> Three branches, eleven staff, one shared login, prices from memory, <i>about right</i> as the standard, and two incidents in the final month.</p>

<p><b>What comes next.</b> The shift module is the day itself — sign-in, opening count, building a sale, payment, closing count. It is the module to keep at the counter. After it come the exceptions: discounts and returns, the extended counters, and the voucher programme.</p>

<blockquote>IMPLEMENTATION TIP: Before moving on, answer one question out loud: what would you say to a colleague who asks to use your login because theirs is not ready? If the answer comes easily, this module has done its work.</blockquote>

<p><b>A last word about the certificate itself.</b> It says that you can run a counter to a standard the business can rely on — that the money you take is recorded, the stock you sell is accounted for, and the exceptions you handle leave a trail somebody can follow. That is worth having on your own account, and it is worth more to you than to anybody else: it is the evidence that a shortage on somebody else's shift is not yours, and that the day you handled properly can be shown to have been handled properly.</p>"""
, [
 C("A colleague asks to use your login because their account is not ready. The right answer is:",
   ["Allow it and tell a supervisor afterwards", "Explain the sales will record against you, and ask for an account, a reset or a manager sign-in",
    "Allow it for one sale only", "Refuse without explanation"], 1,
   "Manager sign-in is designed for exactly this and is tagged so everybody knows."),
 C("Which module should be kept at the counter?",
   ["This one", "The shift module — sign-in, opening, the cart, payment, closing",
    "The voucher module", "The returns module"], 1,
   "This one is the background; that one is the day."),
 C("The single rule that comes before every other rule in this track is:",
   ["Count the drawer at close", "One person, one account",
    "No invoice, no return", "Never restart to force a sync"], 1,
   "A shared login disables almost every control that follows.")]),
]


QUESTIONS = [
 Q("This track certifies you to:", ["Configure a POS Profile", "Run a counter", "Administer terminals", "Manage the back office"], 1,
   "Configuring a counter is an administrator's work and belongs to a separate track.", "What this certifies"),
 Q("ZhiftPOS's design principle is:", ["Everything in the cloud", "Governed centrally, trades locally", "Each till sets its own rules", "The server does all the work"], 1,
   "Rules set in the back office; selling done on a terminal with its own local copy.", "What this certifies"),
 Q("Scanning is instant because the till holds a local copy of:", ["Only prices", "The catalogue, prices and stock", "The customer list", "Recent receipts"], 1,
   "Nothing has to travel to a server before the item appears.", "What this certifies"),
 Q("Controls that restrict a cashier exist because:", ["Cashiers are not trusted", "A rule enforced by software holds at the end of a long Saturday", "Auditors require them", "They speed up training"], 1,
   "A rule remembered by a tired person is not the same thing.", "What this certifies"),
 Q("Which two parts does a cashier deal with daily?", ["Back office and till", "Till application and, indirectly, the sync service", "Terminal management and back office", "Sync service and back office"], 1,
   "The other two decide what you see.", "The parts"),
 Q("The sync service runs:", ["Only while signed in", "Whether or not anybody is signed in", "Only when online", "Only during a shift"], 1,
   "It starts with the terminal and holds queued sales.", "The parts"),
 Q("To force a sync you should:", ["Restart the terminal", "Do nothing — it catches up on its own", "Sign out and in", "Clear the local cache"], 1,
   "A restart interrupts it mid-way.", "The parts"),
 Q("The till is an installed application rather than a web page because:", ["It looks better", "It can keep working with local data when the network fails", "It is faster to update", "It supports scanners"], 1,
   "Which is why the offline chapters describe a normal way of working.", "The parts"),
 Q("When something looks wrong on the till, read first:", ["The receipt", "The top bar", "The sales history", "The profile"], 1,
   "It reports online status, queued sales and failures.", "The parts"),
 Q("One profile governs:", ["One cashier", "One counter", "One branch", "One company"], 1,
   "Almost every question about what a cashier can do is answered by a field on it.", "The profile"),
 Q("Which is NOT decided by the profile?", ["Whether refunds can be cash", "Whether a shift must be opened", "The price of an item", "Which payment methods appear"], 2,
   "Prices come from the back office price list rather than the counter's profile.", "The profile"),
 Q("A missing menu item usually indicates:", ["A software fault", "The profile or your row on it", "A network failure", "An expired login"], 1,
   "The first troubleshooting rule.", "The profile"),
 Q("A greyed-out control:", ["Means the till is faulty", "Gives its reason on hover", "Requires a restart", "Means you lack a licence"], 1,
   "Read it before asking — the answer is usually specific.", "The profile"),
 Q("A profile rule blocks a customer request. You should:", ["Find a workaround", "Do what is possible, explain, and raise the rule afterwards", "Ask another cashier to try", "Complete and correct later"], 1,
   "Every workaround is a control the business thinks it has and does not.", "The profile"),
 Q("How many profiles does a business need?", ["One per branch", "As many as it has genuinely different counters", "One per cashier", "One per company"], 1,
   "A pharmacy counter and a general counter cannot share one.", "The profile"),
 Q("A cashier's role permits:", ["Editing the profile", "Opening a shift, selling, taking payment, closing", "Commissioning terminals", "Setting discount policy"], 1,
   "Plus returns where the profile permits and the consoles it grants.", "Your account"),
 Q("Can one person hold more than one role?", ["No", "Yes — common in smaller businesses", "Only administrators", "Only with approval"], 1,
   "Roles are assigned to accounts in the back office.", "Your account"),
 Q("A shared login disables almost every control because:", ["It slows the system", "Nothing can be attributed to anybody", "Permissions merge", "Sessions conflict"], 1,
   "Every sale, override and variance carries the same name.", "Your account"),
 Q("A shared account harms an honest cashier because they:", ["Lose commission", "Cannot be cleared of somebody else's shortage", "Get fewer permissions", "Cannot open a shift"], 1,
   "Being unable to prove your own innocence is a real cost.", "Your account"),
 Q("Sharing a terminal between cashiers is handled by:", ["Sharing the login", "The lock button", "A joint shift", "Signing out fully"], 1,
   "One locks, the next unlocks with their own credentials in seconds.", "Your account"),
 Q("An unattended unlocked till:", ["Locks itself after a sale", "Trades under your name — its sales, overrides and variances", "Is disabled automatically", "Prompts for a password"], 1,
   "The lock takes one keystroke.", "Your account"),
 Q("Asked to use somebody else's login, the proper routes are an account, a password reset, or:", ["A supervisor watching", "A manager sign-in, which is tagged", "A shared shift", "A written note"], 1,
   "It is designed for exactly this situation and everybody is told.", "Your account"),
 Q("In standard mode:", ["Two people handle the sale", "One person builds the basket and takes payment", "Payment is taken first", "The order is prepared elsewhere"], 1,
   "The ordinary shop counter.", "Selling modes"),
 Q("Pharmacy mode separates:", ["Branches", "The person who picks the goods from the person who takes the money", "Cash from card", "Sales from returns"], 1,
   "Order Console, then Checkout Console.", "Selling modes"),
 Q("The pharmacy handoff should be treated as:", ["A step to shortcut when busy", "The control the mode exists for", "An optional workflow", "A training exercise"], 1,
   "The queue moving slightly slower is the price of the separation.", "Selling modes"),
 Q("Your consoles differ from a colleague's at another branch because of:", ["Your role", "The selling mode on that counter's profile", "The software version", "Their permissions"], 1,
   "The mode is set on the profile and is not selected by a cashier.", "Selling modes"),
 Q("Every completed sale creates:", ["A receipt only", "An invoice with its lines and payments", "A ledger entry only", "A shift record"], 1,
   "There is no such thing as an off-record sale.", "A completed sale"),
 Q("A customer who has lost their receipt:", ["Cannot be helped", "Can have it reprinted from Recent Receipts or Sales History", "Must return with the card used", "Needs a manager"], 1,
   "A lost receipt is not a dead end.", "A completed sale"),
 Q("An offline sale prints with a local reference and later receives:", ["A replacement receipt", "A back-office invoice number", "A void marker", "A queue position"], 1,
   "Both references point to the same sale.", "A completed sale"),
 Q("An offline receipt is:", ["Provisional until posting", "A fully valid document", "Valid only for exchange", "Reissued when online"], 1,
   "Say so with confidence when a customer asks.", "A completed sale"),
 Q("A queued sale is:", ["At risk until it posts", "In a safe state, posting when the connection returns", "Lost if the terminal restarts", "Void after 24 hours"], 1,
   "The top bar tells you when anything is queued.", "A completed sale"),
 Q("Stock reduces on the strength of:", ["The shift total", "The invoice lines — what was actually scanned", "The payment amount", "The end-of-day count"], 1,
   "Which is why a carelessly typed quantity is a stock error too.", "A completed sale"),
 Q("The exercise book problem is answered by:", ["The lock button", "The invoice — line by line, stock reduced, receipts reprintable", "The price list", "The counted close"], 1,
   "No line-level record was the core of it.", "What it prevents"),
 Q("The memory price problem is answered by the price list and made visible by:", ["The receipt", "The rate-override marker", "The shift report", "The customer discount marker"], 1,
   "A departure from the list is marked and stays visible on review.", "What it prevents"),
 Q("The phantom return is answered by:", ["Manager approval", "No invoice, no return", "A returns register", "A refund limit"], 1,
   "There is no path through the console that starts from nothing.", "What it prevents"),
 Q("What the common counter problems share is that each began as:", ["Deliberate fraud", "Somebody being helpful or quick", "A system failure", "A training gap"], 1,
   "Which is why the answers are built into the software rather than left to intention.", "What it prevents"),
 Q("Okelewo's flagship had how many cashiers on one shared login?", ["Two", "Four", "Six", "Eleven"], 1,
   "When a shortage appeared, all four were implicated and none could be cleared.", "Okelewo before"),
 Q("At Okelewo, 'about right' had become the accepted standard:", ["Once a week", "Four days out of five", "At month end", "On busy days only"], 1,
   "Day totals disagreed with the cash by amounts nobody could break down.", "Okelewo before"),
 Q("The Okelewo example is used throughout the track because:", ["It is a real client", "A rule attached to a shop that had the problem tends to stay", "It simplifies the content", "It avoids naming others"], 1,
   "Rules explained in the abstract are forgettable.", "Okelewo before"),
 Q("The rule that comes before every other rule is:", ["Count at close", "One person, one account", "No invoice, no return", "Never restart to sync"], 1,
   "A shared login disables almost every control that follows.", "Review"),

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
    rebalance(QUESTIONS, "pos:counter_basics:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "pos:counter_basics:checks")

    data = json.load(io.open(DATA, encoding="utf-8"))

    # every check must differ from this module's own exam bank
    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    for _t, _e, _h, ch in LESSONS:
        for c in ch:
            if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank:
                raise SystemExit("ABORT: check duplicates exam question: %s" % c["q"][:60])

    data[KEY] = {
        "title": "POS 0 — At the Counter: How ZhiftPOS Works",
        "desc": ("The operator's orientation. What the certificate covers and what it does "
                 "not, why the till behaves as it does, what your own account means and "
                 "why it is only yours, which counter you are working, what pressing "
                 "complete actually creates, and the problems every rule in this track "
                 "was built to prevent."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in data[KEY]["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("questions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("checks: %d" % sum(len(l["checks"]) for l in data[KEY]["lessons"]))


if __name__ == "__main__":
    main()
