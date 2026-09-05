#!/usr/bin/env python3
"""Build 'Stock, Dates and Damage' into academy_shopfloor_data.json.

Module 4 of Retail Foundations.

Module 3 was the shelf being full. This is everything on it being fit to sell:
where stock comes from, why rotation is the single highest-return habit at this
level, dates and what to do about them, damage, and the receiving moment.

Three positions the module takes:

  ROTATION IS THE WHOLE MODULE. Everything else here is supporting material.
  It costs no extra time when done while filling, it is skipped constantly, and
  skipping it is the direct cause of most waste in a branch. The module keeps
  returning to it rather than treating it as one topic among several.

  DATES ARE A SAFETY MATTER BEFORE THEY ARE A MONEY MATTER. In a pharmacy or a
  food business somebody can be harmed. The track is written for a market where
  many learners work in exactly those trades, so the expiry material states the
  safety framing first and the waste framing second, and it never suggests
  judgement about whether something 'looks fine'.

  RECEIVING IS WHERE ERRORS ARE CHEAP. A short delivery caught at the vehicle
  is a conversation; caught at the count six weeks later it is unresolvable.
  Most learners will not sign for deliveries early on, but they will be present
  at them, and knowing what good looks like is what makes them useful when they
  are eventually trusted with it.

Deliberately NOT covered: stocktaking and counting procedure, which belongs to
a supervisor's job and to the Inventory track, and the accounting treatment of
write-offs, which nobody at this level needs.

Run from the app package directory:  python3 build_shopfloor_m4.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "stock_dates"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Where the stock comes from", 10, """<p>Most people work in a shop for months without knowing how the goods got there. It is worth ten minutes, because it explains why some things can be fixed quickly and others cannot.</p>

<p><b>The chain, simply.</b> Somebody decides what the shop should sell and at what price — usually not at your branch. Somebody orders it, either a person or a system reacting to what has sold. A supplier sends it. It arrives at your door, gets checked, gets put away, gets put out, gets sold. Then the cycle repeats, usually driven by what the sale recorded.</p>

<p><b>The two things worth taking from that.</b> First, the order for what you are filling today was placed days or weeks ago, by somebody working from figures rather than from standing in your aisle. That is why the ordering is sometimes wrong and why your information about what customers actually asked for is worth having.</p>

<p><b>Second, and more useful: the system only knows what it was told.</b> If a sale was rung up as the wrong item, the system believes it still has one of the right one and one fewer of the wrong. If a damaged item is binned without being recorded, the system believes it is still on the shelf and will not reorder. Every gap between what the records say and what is physically there was created by somebody, usually with no bad intent and usually in a hurry.</p>

<p><b>Which is the point of the whole module.</b> Your handling of stock is not separate from the shop's records; it is what creates them. A branch whose records are right can order properly, and a branch whose records have drifted cannot — it will be simultaneously out of things it thinks it has and overstocked with things it thinks it needs.</p>

<p><b>Lead time, in one line.</b> The gap between somebody ordering and the goods being sellable. It might be a day for a local supplier and several weeks for an import, which is why "just order more" is not the answer to a gap and why noticing a line running low is more valuable than noticing it has run out.</p>

<blockquote>WORTH KNOWING: Ask what the lead time is on the lines in your section. If it is three days, a gap you report today is fixable this week. If it is six weeks, the only useful moment to have noticed was a month ago — which changes how early you start paying attention.</blockquote>

<p><b>The one number worth asking about your own section.</b> How often does it get delivered? A line delivered daily forgives almost any mistake — run out this morning and it is back tomorrow. A line delivered monthly forgives nothing, and a gap on it is a gap for weeks. Same shop, same shelf, completely different consequences for the same lapse, and knowing which is which tells you where to be careful.</p>

<p><b>And why the system reordering automatically does not remove your job.</b> Where a branch reorders from what the tills recorded, the arithmetic only works if the records are true. A line whose stock has been over-recorded because damage went unlogged will not reorder even as the shelf empties, and the system will be confidently wrong for weeks. Automatic ordering does not replace accurate handling; it makes accurate handling matter more, because nobody is looking at the shelf before the order goes.</p>"""
, [
 C("A damaged item binned without being recorded means the system believes:",
   ["Nothing changed", "It is still on the shelf, so it will not reorder",
    "It was sold", "Stock is short"], 1,
   "Every gap between the records and the shelf was created by somebody, usually in a hurry."),
 C("The order for what you are filling today was placed:",
   ["This morning", "Days or weeks ago, by somebody working from figures",
    "Automatically overnight", "By your supervisor"], 1,
   "Which is why your information about what customers actually asked for is worth having."),
 C("Where lead time is six weeks, noticing a line is low:",
   ["Makes no difference", "Has to happen far earlier than the shelf running out",
    "Is the buyer's job", "Only matters seasonally"], 1,
   "'Just order more' is not the answer to a gap.")]),

("Rotation: the habit that pays most", 10, """<p>If you take one thing from this entire track, take this. It costs no extra time, almost everybody skips it, and skipping it is the direct cause of most of what a branch throws away.</p>

<p><b>The rule.</b> New stock goes behind. Old stock comes forward. Every time, on everything, whether or not the item has a date on it.</p>

<p><b>Why it is skipped.</b> Because putting new stock in front is faster in the moment. The shelf has space at the front where things have sold, the new case is in your hand, and pushing it in takes seconds while pulling the old forward and loading behind takes half a minute. Multiply that by twenty lines and it feels like real time. It is not — it is about ten minutes across a whole fill, and it is the difference between selling stock and skipping it.</p>

<p><b>What actually happens when you do not.</b> The old stock migrates to the back and stays there. Customers take from the front, which is always the newest. The units at the back get older and older until they expire, and then somebody throws away goods the shop paid for — goods that were sellable for months and simply never came within reach of a customer.</p>

<p><b>Which is worth stating in money.</b> Module 1's arithmetic: an expired item costs what the shop paid for it, and recovering that takes two or three more sales. A shelf that is never rotated does not produce one write-off; it produces a steady monthly trickle from every line on it.</p>

<p><b>It applies to things without dates too.</b> Packaging fades, boxes get scuffed, and the unit that has been at the back for a year looks it. Customers reach past shabby stock for the fresh-looking one behind, which produces the same outcome by a slower route.</p>

<p><b>The technique, which takes practice and then none.</b> Take the existing stock off the front, put the new stock in at the back, put the old stock back on the front. It feels clumsy for about a week. After that it is one movement and you will do it without thinking — and that is genuinely the whole skill.</p>

<blockquote>WATCH-OUT: The temptation is worst when you are behind and the shop is busy. That is exactly when rotation is most valuable, because a rushed fill that runs for three weeks builds a back row of stock nobody will ever reach.</blockquote>

<p><b>Where rotation matters even more than on the shelf.</b> In the stockroom. Cases stacked with the newest in front produce exactly the same result at a larger scale — a pallet of something at the back of the room, bought and paid for, quietly ageing while newer cases get used. Stockroom rotation is less visible, harder to fix once it has gone wrong, and worth the same thirty seconds when a delivery is put away.</p>

<p><b>The one exception, and it is worth knowing.</b> Occasionally a delivery arrives with a shorter date than stock already on the shelf — it happens with slow lines and with suppliers clearing their own stock. Rotating by arrival then puts the shorter date at the back, which is exactly wrong. Rotate by date rather than by arrival where the dates are visible; the rule is oldest-sells-first, and new-behind is simply the usual way of achieving it.</p>"""
, [
 C("Rotation applies to:",
   ["Dated items only", "Everything, dated or not",
    "Food and medicine only", "Slow-moving lines"], 1,
   "Packaging fades and scuffs, and customers reach past shabby stock for the fresh-looking one behind."),
 C("A shelf that is never rotated produces:",
   ["One large write-off", "A steady monthly trickle from every line on it",
    "No measurable loss", "Occasional damage"], 1,
   "The old stock migrates to the back and stays there until it expires."),
 C("Doing rotation properly across a whole fill costs about:",
   ["An extra hour", "About ten minutes",
    "No extra time at all", "Half the shift"], 1,
   "It feels like real time and it is not, which is why the shortcut is so tempting.")]),

("Reading dates", 10, """<p>Dates are the one area of this track where getting it wrong can hurt somebody. That framing comes first and everything else follows from it.</p>

<p><b>The kinds you will meet.</b> Most goods carry a date about safety — after it, the item should not be sold or used, and this is absolute. Some carry a date about quality instead, meaning the product is still safe afterwards but no longer at its best. The wording differs by product and country, and which is which is not something to work out from the label yourself.</p>

<p><b>Which is the important instruction in this chapter.</b> Learn from your branch which dates on your products are safety dates and which are quality dates, and treat every one as a safety date until you have been told otherwise. Guessing in the safe direction costs the shop a little; guessing the other way can cost somebody a great deal.</p>

<p><b>What you never do.</b> Sell anything past a safety date, however slightly. Decide something is fine because it looks and smells fine — the whole point of a date is that some risks are invisible. Cover, alter or obscure a date. And never make the decision yourself about whether something borderline can be sold: that is somebody's named responsibility, and it is not the person filling the shelf.</p>

<p><b>How to check without it taking all day.</b> Check as you fill, not as a separate task. The stock is already in your hand and it costs nothing. Check the front and the back of the facing, because the back is where the old stock is. And know your section's fast-expiring lines — dairy, bread, fresh, and in a pharmacy the short-dated lines your branch will tell you about — because those are the ones worth a deliberate look daily rather than incidentally.</p>

<p><b>What to do when you find one.</b> Take it off the shelf immediately rather than finishing what you were doing. Put it wherever your branch says damaged and expired goods go — not back in the stockroom where somebody will put it out again. Tell somebody. And check the rest of that line, because a single expired unit almost never travels alone.</p>

<blockquote>WATCH-OUT: The most dangerous moment is finding something expired while serving a customer who wants it. The pressure to sell it is real and the answer is not negotiable: it comes off the shelf, and the customer gets an apology and an alternative.</blockquote>

<p><b>What to do about the date you cannot read.</b> Rubbed off, printed badly, in a format you do not recognise, or on part of the packaging that has been removed. Do not guess and do not put it out. An unreadable date is the same as an expired one for practical purposes — nobody can prove it is safe — and it is a question for whoever your branch says rather than a judgement to make while holding a case.</p>

<p><b>Two date habits worth building early.</b> Learn where the date is printed on your fastest lines — they are in different places on different packaging and hunting for it is most of what makes checking feel slow. And when a line has several dates on the shelf at once, know the shortest one on it, because that is the one that decides when the shelf needs attention. Both take a fortnight to acquire and then cost nothing forever.</p>"""
, [
 C("Until told otherwise, every date on a product should be treated as:",
   ["A quality date", "A safety date",
    "Guidance only", "The supplier's estimate"], 1,
   "Guessing in the safe direction costs the shop a little; guessing the other way can cost somebody a great deal."),
 C("Deciding something past its date is fine because it looks and smells fine is wrong because:",
   ["Policy forbids it", "The whole point of a date is that some risks are invisible",
    "Customers may complain", "The supervisor decides"], 1,
   "Judgement about borderline stock is somebody's named responsibility and not the person filling the shelf."),
 C("On finding one expired unit you should also:",
   ["Note it for the count", "Check the rest of that line",
    "Report it weekly", "Move the facing forward"], 1,
   "A single expired unit almost never travels alone.")]),

("Before it expires: the lanes", 10, """<p>Stock that expires has been mismanaged, not unlucky. There is almost always a window between noticing something will not sell in time and having to throw it away, and what happens in that window is the difference between recovering most of the value and recovering none.</p>

<p><b>Why it is a window rather than a moment.</b> A line with three weeks left and forty units, selling five a week, is not going to sell out. That is knowable three weeks early, and every day of delay narrows what can be done about it.</p>

<p><b>What can be done, in the order the shop prefers.</b></p>

<p><b>Move it where it will sell.</b> To a better position, an end, a busier branch. Full price, nothing lost — which is why it is first.</p>

<p><b>Mark it down.</b> Some margin recovered rather than none. Most shops have rules about when and by how much, and those rules exist because a markdown taken three weeks early recovers far more than one taken on the last day.</p>

<p><b>Return it to the supplier</b>, where the arrangement allows it, which is not always.</p>

<p><b>Write it off.</b> The last option and the only one that recovers nothing.</p>

<p><b>What you can actually do at your level.</b> Not the decision — the noticing. A line with a short date and too much stock is exactly the thing to report, and it is the report with the most money attached in this whole track, because it is the one where somebody can still act. Nobody can do anything about a case of expired goods; almost anybody can do something about a case that expires in a fortnight.</p>

<p><b>And the thing to watch for at receiving.</b> Stock that arrives already short-dated. It happens, sometimes routinely from certain suppliers, and it is the beginning of a write-off that will be blamed on the branch three weeks later. Anyone can notice it; almost nobody reports it.</p>

<blockquote>IMPLEMENTATION TIP: Once a week, look at your section's dated lines and ask which will not sell through in time. Two minutes, and the answer is usually one or two lines — which is a report worth far more than the effort it took to produce.</blockquote>

<p><b>Why the shop would rather mark down than write off, in numbers.</b> An item costing ₦700 and selling at ₦1,000 makes ₦300. Sold at half price it makes nothing but recovers the ₦700 — the shop breaks even instead of losing. Written off it loses the whole ₦700, which module 1's arithmetic says needs two or three full-price sales to replace. That is why a markdown that feels like giving stock away is almost always the better outcome, and why nobody thanks you for protecting the margin on something that then expires.</p>

<p><b>Why markdowns are usually rule-bound rather than left to judgement.</b> Because the temptation runs both ways: too early gives away margin on stock that would have sold, and too late recovers nothing. Most shops settle it with a written rule — so many days before the date, so much off — precisely so that nobody has to make the call under pressure on the day. If your branch has such a rule, knowing it is what lets you flag a line at the right moment rather than at the obvious one.</p>"""
, [
 C("The preferred first response to stock that will not sell in time is:",
   ["Mark it down", "Move it where it will sell",
    "Return it", "Write it off"], 1,
   "Full price, nothing lost, which is why it comes before markdown."),
 C("A markdown taken three weeks early rather than on the last day:",
   ["Costs the shop more", "Recovers far more",
    "Is against policy", "Makes no difference"], 1,
   "Which is why the shop's markdown rules exist at all."),
 C("Stock arriving already short-dated is:",
   ["Normal and unremarkable", "The beginning of a write-off that will be blamed on the branch later",
    "The supplier's loss", "Checked by the system"], 1,
   "Anyone can notice it; almost nobody reports it.")]),

("Damage, and the honest handling of it", 10, """<p>Things get dropped, crushed, leaked and torn. What matters is not that it happens but what happens next, and this chapter is mostly about one thing: the pressure not to say.</p>

<p><b>The rule, stated plainly.</b> Damage is recorded, not hidden. Every branch has a way of doing it — a bin, a book, a form, a person to tell. Use it every time, including when you did it, including when it was small, including when nobody saw.</p>

<p><b>Why hiding it is worse than the damage.</b> The item is lost either way; that money is gone the moment it hit the floor. What hiding adds is a record that no longer matches reality, which means the system will not reorder, the count will show a shortage nobody can explain, and — this is the part that matters to you — an unexplained shortage is a suspicion looking for somewhere to land. A recorded breakage is an accident. An unrecorded one becomes, months later, part of a number somebody is investigating.</p>

<p><b>What good branches do about it.</b> They make reporting damage easy and unpunished, because they would rather know. If yours does not, report it anyway and in writing where you can — the protection is worth more to you than the awkwardness costs.</p>

<p><b>The judgement about damaged-but-sellable.</b> A dented tin, a torn outer on something sealed inside, a scuffed box. Sometimes these can still be sold, often at a reduction, and sometimes they cannot. That is not your call — it depends on the product, the trade and the rules, and in food and pharmacy it is frequently a firm no. Set it aside and ask.</p>

<p><b>Damage found rather than caused.</b> Same treatment. A leaking bottle discovered on a shelf is not an accusation of anybody; it needs removing, recording and — the part people miss — cleaning up properly, because the next thing to happen otherwise is somebody slipping.</p>

<p><b>And the small stuff.</b> One broken egg, a split bag of rice. It feels too minor to record and the branch's whole waste figure is built from exactly these. If it is not sellable, it is a loss, and a loss the records do not know about is worse than the loss itself.</p>

<blockquote>WORTH KNOWING: The best thing about working somewhere that records damage properly is that it stops being frightening. In a branch where breakages are logged as a matter of routine, dropping something is an inconvenience. In one where they are hidden, it is a secret — and secrets are how honest people end up in trouble.</blockquote>

<p><b>Damage caused by a customer.</b> A dropped bottle in an aisle, a child pulling a display over. Nobody is in trouble and the handling is the same: make it safe first, clean it, record it. What matters is that customers are not made to feel accused — most are already embarrassed, and a shop that handles it easily keeps them while a shop that makes a scene loses somebody worth half a million naira over an item worth eight hundred.</p>"""
, [
 C("Hiding a breakage is worse than the breakage because:",
   ["It is dishonest", "It creates a shortage nobody can explain",
    "The item costs more", "Someone else gets blamed"], 1,
   "An unexplained shortage is a suspicion looking for somewhere to land."),
 C("Whether damaged-but-sealed stock can still be sold is:",
   ["Your judgement", "Not your call — set it aside and ask",
    "Always yes at a reduction", "Always no"], 1,
   "It depends on the product, the trade and the rules, and in food and pharmacy it is frequently a firm no."),
 C("A leaking bottle found on a shelf needs removing, recording and:",
   ["Reporting to the supplier", "Cleaning up properly",
    "Replacing from stock", "Marking on the facing"], 1,
   "The next thing to happen otherwise is somebody slipping.")]),

("The delivery arriving", 10, """<p>You may not sign for deliveries yet. You will be standing near one, and knowing what should happen is what makes you useful when you eventually are trusted with it.</p>

<p><b>Why this moment matters more than any other.</b> It is the last point at which a problem is cheap. A short delivery caught at the vehicle is a conversation with the driver. The same shortage found at a count six weeks later is unresolvable — nobody can prove what arrived, the supplier will not accept it, and the branch absorbs it.</p>

<p><b>What good receiving looks like.</b> Count what physically arrived against the paperwork, before the vehicle leaves. Check the condition of what you are accepting rather than assuming the outside of a pallet represents the inside. Check dates on anything dated, at the door, because that is the only moment a short-dated delivery can be refused. And note anything wrong on the paperwork before signing, not afterwards.</p>

<p><b>The pressure, which is real and worth naming.</b> The driver is in a hurry and has other drops. The shop is busy. Signing quickly is the path of least resistance and everybody knows it. This is precisely why a good branch treats the count as non-negotiable — because the pressure is constant, and a rule that bends under pressure is not a rule.</p>

<p><b>What to do with cold and frozen goods, which is different.</b> They come first, always, before anything else is checked or moved. Chilled stock standing in a warm receiving area is losing shelf life every minute and may become unsellable entirely. If you do one thing at a delivery, get the cold goods into the cold.</p>

<p><b>And then the part that decides everything downstream.</b> Getting it out. A delivery counted correctly, put away neatly, and left in the stockroom for two days is module 3's cause three — the biggest cause of empty shelves. Receiving is not finished when the vehicle leaves; it is finished when the goods are where customers can buy them.</p>

<blockquote>WATCH-OUT: Never sign for goods you have not counted, even when you are certain, even when the driver is waiting, even when it is always been right before. Your signature is the shop's evidence, and it is the only one it has.</blockquote>

<p><b>What to do when you spot a problem and you are not the one signing.</b> Say it out loud, before the vehicle leaves, to whoever is signing. That is the entire contribution and it is genuinely valuable: the person checking paperwork is looking at paperwork, and the person standing beside the pallet can see that a case is crushed or that two are missing from a stack. Saying it afterwards helps nobody, and saying it while the driver is present costs nothing.</p>"""
, [
 C("A shortage found at a count six weeks after delivery is:",
   ["Recoverable from the supplier", "Unresolvable",
    "Covered by insurance", "The driver's responsibility"], 1,
   "Nobody can prove what arrived, so the branch absorbs it."),
 C("At a delivery, cold and frozen goods:",
   ["Are checked last", "Come first, before anything else",
    "Follow the paperwork order", "Wait until the count finishes"], 1,
   "Chilled stock in a warm receiving area is losing shelf life every minute."),
 C("Receiving is finished when:",
   ["The vehicle leaves", "The goods are where customers can buy them",
    "The paperwork is signed", "The stockroom is tidy"], 1,
   "A delivery left in the stockroom for two days is the biggest cause of empty shelves.")]),

("Cold, heat and the things that spoil", 10, """<p>Some stock is fine wherever it sits and some is not, and the difference is invisible until it is expensive.</p>

<p><b>The chilled and frozen rule.</b> These goods have a temperature range they must stay inside, from the supplier to the customer. Every minute outside it uses up shelf life that does not come back. That is why chilled deliveries are put away first, why a fridge door left ajar matters, and why a case of yoghurt left on a trolley through a lunch break is a genuine loss rather than a small lapse.</p>

<p><b>What to actually watch.</b> Fridge and freezer doors properly closed. Nothing stacked above the load line inside a chiller, because the cold air stops circulating. Stock not left out during a fill — take out what you will put away in a few minutes rather than the whole case. And if a unit sounds wrong, feels warm, or has water where water should not be, tell somebody immediately; refrigeration failures are one of the few things in a shop that can go from a nuisance to thousands of naira overnight.</p>

<p><b>Heat, which matters more in this market than most guidance admits.</b> Chocolate, some cosmetics, and a range of medicines degrade in ordinary Nigerian afternoon heat without any obvious sign. Direct sun through a window onto a display is enough. If your branch has a pharmacy, some of its stock has storage conditions that are a regulatory matter rather than a preference, and those are worth knowing precisely rather than approximately.</p>

<p><b>Power, said plainly.</b> Where supply is unreliable, know what your branch does when it goes and what your part in it is — which fridges are on the generator, what is checked when power returns, and who decides whether stock is still sellable. That last decision is never yours, and knowing that in advance is what stops somebody making it under pressure at seven in the morning.</p>

<p><b>The habit underneath all of it.</b> Notice temperature the way you notice gaps. A warm chiller and an empty shelf are both invisible to somebody not looking and obvious to somebody who is.</p>

<p><b>The chilled fill order, which is not obvious.</b> Do the most temperature-sensitive lines first — dairy and fresh before drinks. And close the door between loads rather than propping it open for the duration of the fill, which is the commonest habit in every shop and the one that undoes the rest. A door held open for fifteen minutes warms everything in the unit, not just the shelf you are working on.</p>

<blockquote>WORTH KNOWING: A chiller full to above the load line looks well-stocked and is failing — the cold air cannot circulate and everything in it warms. It is one of the few cases in retail where a fuller shelf is genuinely worse.</blockquote>"""
, [
 C("Stock stacked above the load line in a chiller:",
   ["Maximises the display", "Stops the cold air circulating, so everything warms",
    "Is standard practice", "Only matters when busy"], 1,
   "One of the few cases in retail where a fuller shelf is genuinely worse."),
 C("Deciding whether stock is still sellable after a power failure is:",
   ["Yours if you were present", "Never yours",
    "The supervisor's on the day", "Decided by appearance"], 1,
   "Knowing that in advance stops somebody making it under pressure at seven in the morning."),
 C("During a fill of chilled goods you should take out:",
   ["The whole case", "What you will put away in a few minutes",
    "Two cases at once", "Whatever fits the trolley"], 1,
   "Every minute outside the temperature range uses up shelf life that does not come back.")]),

("Okelewo Stores: the month Ada stopped the waste", 10, """<p>Seven months in. The Ibadan branch was throwing away a noticeable amount of dairy every week and nobody had worked out why, because everybody assumed it was ordering.</p>

<p><b>What she noticed.</b> Filling the chiller one morning, Ada pulled a yoghurt from the back of a facing and found it three days past date. The front row was fresh. She checked the rest of the shelf and found eleven units past date behind fresh stock, across four lines — all of it hidden by exactly the pattern module 2 of this module describes.</p>

<p><b>What was actually happening.</b> The chiller was being filled in the morning rush, quickly, new stock pushed in at the front because it was faster. Nobody was doing it wrongly on purpose; the fill was being done by whoever had ten minutes, and rotating properly takes practice nobody had been given.</p>

<p><b>What she did, in order.</b> Pulled everything past date, told the supervisor rather than quietly binning it, and — this is the part that mattered — showed her the pattern rather than just the units. Eleven expired items is a bad morning. Eleven expired items sitting behind fresh stock is a cause.</p>

<p><b>What changed.</b> The supervisor showed the whole team the take-off-put-behind-put-back movement, once, taking about five minutes. Ada took the chilled fill herself for two weeks so it was done the same way every morning. After that anybody could do it, because they had seen it done properly rather than been told about it.</p>

<p><b>What it was worth.</b> The branch's dairy waste fell substantially over the following two months. Nobody produced an exact figure, and the honest reason is that nobody had measured it precisely before either — which is worth admitting rather than inventing a number, and it is also the reason it had run for so long unnoticed.</p>

<p><b>The part worth copying.</b> She reported the cause, not the incident. Anybody could have found eleven expired yoghurts; most people would have binned them, mentioned it, and found eleven more the following month. The difference between a person who fixes today and a person who fixes the pattern is one sentence at the moment of reporting.</p>

<p><b>What the supervisor did that made it work.</b> She showed the movement rather than issuing an instruction. A note on a board saying rotate stock had been up for a year and had changed nothing, because rotation is a physical skill and nobody had ever watched somebody do it. Five minutes of demonstration achieved what twelve months of a written reminder had not — which is worth knowing if you are ever the person trying to change how something is done.</p>

<blockquote>IMPLEMENTATION TIP: The next time you find something wrong, spend thirty seconds working out whether it is an incident or a pattern before you report it. If four of the same thing are wrong in the same way, it is a pattern — and saying so is what makes the report worth acting on.</blockquote>"""
, [
 C("The eleven expired units were hidden by:",
   ["Poor lighting", "Fresh stock in front of them",
    "The stockroom layout", "A labelling error"], 1,
   "New stock pushed in at the front because it was faster, so the old migrated backward."),
 C("What made Ada's report worth acting on was that she showed:",
   ["The units she had found", "The pattern rather than just the units",
    "The waste figure", "The supplier's delivery notes"], 1,
   "Eleven expired items is a bad morning; eleven sitting behind fresh stock is a cause."),
 C("The fix that changed things was:",
   ["A new ordering cycle", "Five minutes showing the whole team the rotation movement",
    "Daily date checks", "A written procedure"], 1,
   "They had seen it done properly rather than been told about it.")]),

("Review, and the three habits", 10, """<p>The module in short, then what to do with it.</p>

<p><b>Your handling of stock creates the records.</b> A damaged item binned unrecorded means the system thinks it is on the shelf and will not reorder. Records that have drifted make a branch simultaneously out of things it thinks it has and overstocked with things it thinks it needs.</p>

<p><b>Rotation is the habit that pays most.</b> New behind, old forward, every time, on everything, dated or not. It costs about ten minutes across a whole fill and skipping it produces a steady monthly trickle of waste from every line on the shelf.</p>

<p><b>Dates are a safety matter first.</b> Treat every date as a safety date until told otherwise. Never sell past one, never decide something is fine because it looks fine, and never make the borderline judgement yourself. Check as you fill, check the back as well as the front, and when you find one, check the rest of the line.</p>

<p><b>There is a window before expiry.</b> Move it, mark it down, return it, write it off — in that order, and the earlier the better. Your part is the noticing: a short-dated line with too much stock is the report with the most money attached in this whole track.</p>

<p><b>Damage is recorded, not hidden.</b> The item is lost either way; hiding it adds an unexplained shortage, and unexplained shortages are suspicions looking for somewhere to land.</p>

<p><b>Receiving is where errors are cheap.</b> Count before signing, cold goods first, and the delivery is not finished until the goods are where customers can buy them.</p>

<p><b>Temperature is invisible until it is expensive.</b> Doors closed, nothing above the load line, small amounts out at a time, and the sellability decision after a power failure is never yours.</p>

<p><b>The three habits.</b> First: rotate on every fill, until it stops being a separate action. Second: check dates as you fill rather than as a task — front and back. Third: record every breakage, including your own, including the small ones.</p>

<blockquote>IMPLEMENTATION TIP: Give rotation a fortnight before judging whether you have it. It is genuinely awkward for about a week and then becomes a single movement you stop noticing — and it is the point at which most of this module starts working on its own.</blockquote>

<p><b>Where this module meets the last one.</b> Module 3 said the shelf should be full; this one says everything on it should be fit to sell. The two fail together and in the same way — a rushed fill produces gaps at the front and expired stock at the back, from one decision to save thirty seconds. Doing both properly is not two habits stacked on each other; it is one habit, and it is the one that separates somebody working a section from somebody merely covering it.</p>

<p><b>One last thing about all three habits.</b> Every one of them is invisible when done and expensive when not. Nobody sees a rotation that happened, a date checked, or a breakage recorded — they see the write-off, the complaint and the unexplained shortage that follow when those things did not happen. That is a genuinely unsatisfying feature of the work, and it is worth naming rather than pretending otherwise: you are being asked to do three things well that will never once be noticed individually, on the strength of what they prevent.</p>"""
, [
 C("The three habits from this module are rotation, checking dates as you fill, and:",
   ["Reporting short dates", "Recording every breakage",
    "Checking deliveries", "Watching temperature"], 1,
   "Including your own, including the small ones."),
 C("Rotation is described as becoming automatic after about:",
   ["A day", "A fortnight",
    "Three months", "A year"], 1,
   "It is genuinely awkward for about a week and then becomes a single movement you stop noticing."),
 C("Records that have drifted make a branch:",
   ["Simply overstocked", "Out of things it thinks it has and overstocked with things it thinks it needs",
    "Unable to trade", "Reliant on manual counts"], 1,
   "Which is why stock handling and the records are the same subject.")]),
]


QUESTIONS = [
 Q("A sale rung up as the wrong item leaves the system believing it has:", ["The correct balance", "One of the right item and one fewer of the wrong", "Nothing recorded", "A shortage"], 1,
   "The system only knows what it was told.", "Ch1 §4", "Where stock comes from"),
 Q("The lead time is the gap between ordering and:", ["Delivery arriving", "The goods being sellable", "Payment", "The next order"], 1,
   "Which includes receiving and putting out, not just transport.", "Ch1 §6", "Where stock comes from"),
 Q("A branch whose records have drifted will be:", ["Consistently overstocked", "Out of things it thinks it has and overstocked with things it thinks it needs", "Unable to order", "Short on fast lines only"], 1,
   "Ordering computes from records rather than from the shelf.", "Ch1 §5", "Where stock comes from"),
 Q("Your handling of stock is:", ["Separate from the records", "What creates the records", "Checked against them", "Reconciled monthly"], 1,
   "Which is the point of the whole module.", "Ch1 §5", "Where stock comes from"),
 Q("The rotation rule is:", ["Fill from the front", "New behind, old forward", "Newest at eye level", "Oldest to the stockroom"], 1,
   "Every time, on everything, dated or not.", "Ch2 §2", "Rotation"),
 Q("Rotation gets skipped because putting new stock in front is:", ["Tidier", "Faster in the moment", "Required when busy", "Better for display"], 1,
   "About ten minutes across a whole fill, which feels like real time and is not.", "Ch2 §3", "Rotation"),
 Q("Without rotation, the units at the back:", ["Sell eventually", "Get older until they expire", "Are found at the count", "Move forward naturally"], 1,
   "Goods that were sellable for months and never came within reach of a customer.", "Ch2 §4", "Rotation"),
 Q("On undated goods, failing to rotate produces the same outcome because:", ["Dates are hidden", "Packaging fades and customers reach past shabby stock", "Stock is miscounted", "Prices change"], 1,
   "The same result by a slower route.", "Ch2 §6", "Rotation"),
 Q("The rotation technique is awkward for about:", ["A day", "A week", "A month", "A quarter"], 1,
   "After that it is one movement done without thinking.", "Ch2 §7", "Rotation"),
 Q("Until told otherwise, a date should be treated as:", ["Quality guidance", "A safety date", "The supplier's estimate", "Advisory"], 1,
   "Guessing in the safe direction costs the shop a little; the other way can cost somebody a great deal.", "Ch3 §3", "Dates"),
 Q("Judging that something past its date is fine because it looks fine is wrong because:", ["It breaches policy", "Some risks are invisible", "Customers may notice", "Records disagree"], 1,
   "Which is the whole point of having a date at all.", "Ch3 §4", "Dates"),
 Q("Dates should be checked:", ["As a weekly task", "As you fill", "At the count", "On delivery only"], 1,
   "The stock is already in your hand and it costs nothing.", "Ch3 §5", "Dates"),
 Q("When checking a facing for dates you check the front and:", ["The label", "The back", "The shelf below", "The stockroom"], 1,
   "The back is where the old stock is.", "Ch3 §5", "Dates"),
 Q("Expired stock removed from the shelf should go:", ["Back to the stockroom", "Wherever the branch says expired goods go", "In the general bin", "To the supplier"], 1,
   "Not somewhere it can be put out again by somebody else.", "Ch3 §6", "Dates"),
 Q("Finding something expired while a customer wants it means:", ["Selling it with a warning", "It comes off the shelf, with an apology and an alternative", "Asking a supervisor to decide", "Marking it down"], 1,
   "The pressure is real and the answer is not negotiable.", "Ch3 §7", "Dates"),
 Q("Stock that expires has been:", ["Unlucky", "Mismanaged", "Over-ordered", "Poorly displayed"], 1,
   "There is almost always a window between noticing and having to throw it away.", "Ch4 §1", "The lanes"),
 Q("The four lanes in order are move it, mark it down, return it and:", ["Donate it", "Write it off", "Repack it", "Sell it as damaged"], 1,
   "The last option and the only one that recovers nothing.", "Ch4 §7", "The lanes"),
 Q("At floor level, your part in the lanes is:", ["The markdown decision", "The noticing", "The write-off", "The return"], 1,
   "Nobody can act on expired goods; almost anybody can act on goods expiring in a fortnight.", "Ch4 §8", "The lanes"),
 Q("Forty units with three weeks left, selling five a week, is knowable:", ["On the last day", "Three weeks early", "At the count", "Only from the system"], 1,
   "Every day of delay narrows what can be done about it.", "Ch4 §3", "The lanes"),
 Q("Damage should be recorded:", ["When significant", "Every time, including your own and the small ones", "At the weekly count", "If somebody saw"], 1,
   "The branch's whole waste figure is built from exactly these.", "Ch5 §2", "Damage"),
 Q("Hiding a breakage adds, to the loss itself:", ["A policy breach", "An unexplained shortage", "A supplier claim", "A count error only"], 1,
   "Which is a suspicion looking for somewhere to land.", "Ch5 §3", "Damage"),
 Q("A recorded breakage is an accident; an unrecorded one becomes:", ["A write-off", "Part of a number somebody is investigating", "A training issue", "A supplier claim"], 1,
   "Which is why the protection matters more to you than the awkwardness costs.", "Ch5 §3", "Damage"),
 Q("Good branches make reporting damage easy and unpunished because:", ["Policy requires it", "They would rather know", "It reduces waste", "Auditors expect it"], 1,
   "And where yours does not, report it anyway and in writing where you can.", "Ch5 §4", "Damage"),
 Q("A leaking bottle found on the shelf also needs:", ["A supplier report", "Cleaning up properly", "A price adjustment", "A note on the facing"], 1,
   "The next thing to happen otherwise is somebody slipping.", "Ch5 §6", "Damage"),
 Q("A shortage caught at the vehicle is a conversation; the same shortage at a count six weeks later is:", ["A claim", "Unresolvable", "A supplier debit", "A branch adjustment"], 1,
   "Nobody can prove what arrived.", "Ch6 §2", "Receiving"),
 Q("Anything wrong with a delivery is noted:", ["After checking properly", "On the paperwork before signing", "In the stock book", "At the next count"], 1,
   "Your signature is the shop's evidence and the only one it has.", "Ch6 §3", "Receiving"),
 Q("The reason a good branch treats the delivery count as non-negotiable is that:", ["Suppliers are unreliable", "The pressure to skip it is constant", "The system requires it", "Drivers expect it"], 1,
   "A rule that bends under pressure is not a rule.", "Ch6 §4", "Receiving"),
 Q("Checking dates at the door matters because it is the only moment:", ["Staff are free", "A short-dated delivery can be refused", "The paperwork is available", "The driver is present"], 1,
   "After that the branch owns the problem.", "Ch6 §3", "Receiving"),
 Q("A correctly received delivery left in the stockroom for two days is:", ["Safely stored", "The biggest cause of empty shelves", "Ready for the count", "Acceptable when busy"], 1,
   "Receiving is finished when the goods are where customers can buy them.", "Ch6 §6", "Receiving"),
 Q("Every minute chilled stock spends outside its temperature range:", ["Is recoverable", "Uses up shelf life that does not come back", "Affects appearance only", "Is monitored automatically"], 1,
   "Which is why chilled deliveries are put away first.", "Ch7 §2", "Temperature"),
 Q("A chiller filled above the load line:", ["Displays more stock", "Fails, because the cold air cannot circulate", "Is more efficient", "Needs defrosting"], 1,
   "One of the few cases where a fuller shelf is genuinely worse.", "Ch7 §3", "Temperature"),
 Q("During a chilled fill you should bring out:", ["The whole case", "What you will put away in a few minutes", "A trolley load", "Two cases"], 1,
   "Stock left out during a fill is losing shelf life while you work.", "Ch7 §3", "Temperature"),
 Q("Heat damage to chocolate, cosmetics and some medicines:", ["Is visible immediately", "Happens without any obvious sign", "Only occurs above 40 degrees", "Affects packaging only"], 1,
   "Direct sun through a window onto a display is enough.", "Ch7 §4", "Temperature"),
 Q("After a power failure, deciding whether stock is still sellable is:", ["The first person's call", "Never yours", "Made by appearance", "Automatic"], 1,
   "Knowing that in advance stops somebody deciding under pressure.", "Ch7 §5", "Temperature"),
 Q("A refrigeration unit that sounds wrong or feels warm should be:", ["Monitored for a day", "Reported immediately", "Checked at close", "Emptied first"], 1,
   "One of the few things that can go from a nuisance to thousands of naira overnight.", "Ch7 §3", "Temperature"),
 Q("Ada found eleven expired units:", ["In the stockroom", "Behind fresh stock, across four lines", "On a delivery", "At the count"], 1,
   "Hidden by exactly the pattern the rotation chapter describes.", "Ch8 §2", "Ada and the waste"),
 Q("The cause of the dairy waste was:", ["Over-ordering", "The chiller being filled quickly with new stock at the front", "Supplier short dates", "A faulty unit"], 1,
   "Nobody was doing it wrongly on purpose.", "Ch8 §3", "Ada and the waste"),
 Q("Ada told the supervisor rather than:", ["Fixing it herself", "Quietly binning the expired stock", "Reporting it in writing", "Waiting for the count"], 1,
   "And showed her the pattern rather than just the units.", "Ch8 §4", "Ada and the waste"),
 Q("The fix took about:", ["A week of training", "Five minutes showing the team the movement", "A new procedure", "A month"], 1,
   "Then Ada took the chilled fill for two weeks so it was done the same way every morning.", "Ch8 §5", "Ada and the waste"),
 Q("No exact waste figure is given because:", ["It was commercially sensitive", "Nobody had measured it precisely before either", "The period was too short", "Records were lost"], 1,
   "Which is also the reason it had run so long unnoticed.", "Ch8 §6", "Ada and the waste"),
 Q("The difference between fixing today and fixing the pattern is:", ["Seniority", "One sentence at the moment of reporting", "A written report", "Supervisor involvement"], 1,
   "Most people would have binned them, mentioned it, and found eleven more next month.", "Ch8 §7", "Ada and the waste"),
 Q("Four of the same thing wrong in the same way indicates:", ["Bad luck", "A pattern", "A supplier fault", "A training gap only"], 1,
   "And saying so is what makes the report worth acting on.", "Ch8 §8", "Ada and the waste"),
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


BANNED = ["at the end of the day", "at the end of the day,"]


def main():
    if len(LESSONS) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(LESSONS))

    rebalance(QUESTIONS, "shopfloor:stock_dates:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:stock_dates:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    problems = []
    seen = set()
    for _t, _e, html, ch in LESSONS:
        flat = re.sub(r"<[^>]+>", " ", html).lower()
        for b in BANNED:
            if b in flat:
                problems.append("banned phrase %r" % b)
        if len(ch) != 3:
            problems.append("chapter has %d checks" % len(ch))
        for c in ch:
            norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
            if norm in bank:
                problems.append("duplicates exam question: %s" % c["q"][:58])
            if norm in seen:
                problems.append("duplicate check: %s" % c["q"][:58])
            seen.add(norm)
            if len(c.get("why") or "") < 40:
                problems.append("weak rationale: %s" % c["q"][:50])
            if len(c["opts"]) != 4:
                problems.append("not 4 options: %s" % c["q"][:50])
    if problems:
        raise SystemExit("ABORT — %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))

    mod = {
        "title": "RF 4 — Stock, Dates and Damage",
        "desc": ("Everything on the shelf being fit to sell. Where stock comes from and how "
                 "your handling creates the records, rotation as the habit that pays most, "
                 "reading dates as a safety matter, the window before something expires, "
                 "recording damage rather than hiding it, the delivery moment where errors "
                 "are still cheap, and the stock that spoils invisibly."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    data = {}
    if os.path.exists(DATA):
        with io.open(DATA, encoding="utf-8") as f:
            data = json.load(f)
    data[KEY] = mod
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("questions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))
    thin = [i + 1 for i, n in enumerate(lens) if n < 2500]
    print("thin chapters:", thin or "NONE")


if __name__ == "__main__":
    main()
