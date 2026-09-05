#!/usr/bin/env python3
"""Build 'When It Goes Wrong' into academy_shopfloor_data.json.

Module 7 of Retail Foundations.

The safety-critical module, and the one where being wrong could genuinely hurt
somebody. Four rules governed the writing:

  IT NEVER TEACHES PROCEDURE BEYOND THE READER'S TRAINING. No first aid
  technique, no fire-fighting instruction, no restraint. What it teaches is
  what to do in the first thirty seconds, who to call, and where a shop
  assistant's responsibility genuinely ends. A track that made somebody feel
  competent to act beyond their training would be actively dangerous.

  IT DEFERS TO THE BRANCH ON SPECIFICS. Emergency numbers, assembly points,
  named first aiders and the panic procedure differ by business, state and
  premises. The module says repeatedly: find out yours, now, before you need
  it. Asserting a single number or a single procedure would be wrong somewhere
  and dangerous where it was wrong.

  PEOPLE BEFORE STOCK AND CASH IS STATED AS THE RULE ABOVE ALL OTHERS, and the
  robbery chapter says comply, plainly and without qualification. This mirrors
  the Retail Leadership track's rule from the other side; the difference is
  that here it is being said to the person who would be in the room.

  THE AFTERMATH IS TREATED AS PART OF THE EVENT. Being present at something
  frightening has effects for days, people are surprised by it, and a track
  that stops at 'incident resolved' leaves out the part that most affects
  whether somebody stays in the job.

Run from the app package directory:  python3 build_shopfloor_m7.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "hard_moments"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The rule above all the others", 10, """<p>Everything in this module comes back to one sentence, and it is worth reading before anything else: <b>people come before stock and before cash.</b></p>

<p><b>Why it needs saying out loud.</b> Because in the moment it does not feel obvious. Somebody is walking out with goods and the instinct is to stop them. A drawer is open and somebody reaches for it and the instinct is to close it. Those instincts are normal, they are about doing your job properly, and they are wrong — and they are strongest in people who care most about doing the job well.</p>

<p><b>The arithmetic, stated once so it does not need repeating.</b> Goods are insured. Cash is replaceable and usually insured. Neither is worth an injury to you, to a colleague, or to a customer. A shop can absorb the loss of a trolley of stock or the contents of a till. It cannot undo somebody being hurt, and no employer worth working for would want the trade.</p>

<p><b>What this module actually gives you.</b> Not training in how to handle emergencies — that is a different thing and some of it takes days to learn properly. What it gives you is the first thirty seconds: what to do immediately, who to call, and where your responsibility ends. In almost every situation in this module, doing the right thing in the first thirty seconds and then handing over to somebody qualified is the entire correct response.</p>

<p><b>The three questions to answer before you need them.</b> Every chapter here ends up at the same place, so find these out this week rather than during an incident. Who are the trained first aiders on your shifts? What are the emergency numbers your branch posts, and where are they written? And where is the assembly point if the building has to be emptied?</p>

<p><b>Why now rather than then.</b> Because nobody learns anything during an emergency. Whatever you know at the moment it starts is what you have, and ten minutes of asking this week is the entire preparation required for most of what follows.</p>

<p><b>Why freezing is normal and worth planning around.</b> Most people, in a genuine emergency, do nothing for several seconds — not from cowardice but because the brain is looking for a familiar pattern and not finding one. That is why every chapter here gives a first action rather than a principle: having one specific thing to do is what gets somebody moving, and once they are moving the rest follows. If you take nothing else from this module, take the first action from each chapter.</p>

<p><b>And why your branch's version wins over this one.</b> Emergency numbers, assembly points, alarm phrases and who holds keys differ by business, by premises and by state. Nothing here is meant to replace what your branch tells you — it is meant to make sure you have asked. Where the two agree, you know it twice. Where they differ, follow your branch, with the single exception named above.</p>

<blockquote>WATCH-OUT: If anything in this module conflicts with what your branch tells you, follow your branch — unless it asks you to put yourself at risk to protect goods or money. That instruction is wrong wherever it comes from, and it is worth raising.</blockquote>"""
, [
 C("The rule above all others in this module is:",
   ["Protect the stock", "People come before stock and before cash",
    "Follow the procedure", "Call the manager"], 1,
   "A shop can absorb the loss of a trolley of stock; it cannot undo somebody being hurt."),
 C("What this module teaches is:",
   ["How to handle emergencies fully", "The first thirty seconds, who to call, and where your responsibility ends",
    "First aid", "Security procedure"], 1,
   "Doing the right thing immediately and handing over to somebody qualified is the entire correct response."),
 C("The three things to find out before you need them are the first aiders, the emergency numbers and:",
   ["The alarm code", "The assembly point",
    "The manager's number", "The insurance details"], 1,
   "Nobody learns anything during an emergency; what you know when it starts is what you have.")]),

("The customer who is angry", 10, """<p>Ordinary complaints were module 2. This is the customer who has gone past that — raised voice, an audience, and a situation that is now about how they feel rather than about the item.</p>

<p><b>What is actually happening.</b> Anger at this level is almost never about what is being said. It is usually the third thing that has gone wrong for that person today, or a wasted journey, or a feeling of having been dismissed by somebody earlier. You are meeting the accumulation, and understanding that is what stops you answering it defensively.</p>

<p><b>What lowers the temperature, and these are reliable.</b> Lower your own voice slightly rather than matching theirs — people tend to come down to meet it. Let them finish without interrupting, because interrupting somebody angry restarts them. Use their words back: <i>so the delivery never came and nobody rang you</i>. And stand still rather than moving about, because movement reads as agitation.</p>

<p><b>What raises it.</b> Explaining. Defending the shop. Saying calm down, which has never once worked. Smiling, which reads as not taking it seriously. And any sentence beginning with the word actually.</p>

<p><b>Move it if you can.</b> An angry person with an audience is performing as well as complaining, and they cannot easily back down in front of people. <i>Come over here and let me sort this out</i> gives them a way to stop being watched, and the temperature usually falls within a few steps.</p>

<p><b>Get somebody early rather than late.</b> Not as a defeat — as the right move. A supervisor arriving while things are still recoverable can resolve it; one arriving after ten minutes of escalation is inheriting something worse. If you think this is heading somewhere you cannot handle, fetch somebody at that moment rather than after you have proved yourself right.</p>

<p><b>And know that some of it is not resolvable.</b> You can do everything correctly and have somebody leave furious. That is not a failure. The measure is whether you kept it from getting worse and kept yourself safe, not whether they left happy.</p>

<p><b>Where anger comes from that has nothing to do with the shop.</b> Money worries, illness, a bereavement, a bad diagnosis, something at home. Retail staff are among the few people such a person will speak to that day, and some of what arrives at a counter is simply the nearest available outlet. Knowing that costs nothing and changes how it lands — not into excusing abuse, which chapter 3 handles, but into not carrying home the assumption that you caused it.</p>

<blockquote>IMPLEMENTATION TIP: The single most effective thing is lowering your own voice. It feels counterintuitive when somebody is shouting and it works more often than anything else on this page, because most people unconsciously match the volume of the person they are talking to.</blockquote>"""
, [
 C("Anger at this level is usually about:",
   ["The item in question", "The accumulation of the person's day",
    "The shop's policy", "The staff member"], 1,
   "Understanding that is what stops you answering it defensively."),
 C("The single most effective de-escalation technique is:",
   ["Apologising repeatedly", "Lowering your own voice",
    "Offering a refund", "Calling a supervisor"], 1,
   "Most people unconsciously match the volume of the person they are talking to."),
 C("Moving an angry customer away from an audience helps because they:",
   ["Are easier to hear", "Cannot easily back down in front of people",
    "Feel more important", "Will be quieter"], 1,
   "Somebody with an audience is performing as well as complaining.")]),

("When it goes past the line", 10, """<p>Some situations stop being customer service. Knowing where that point is, before you meet it, is what lets you act rather than freeze.</p>

<p><b>Where the line is.</b> Threats of any kind. Abuse aimed at who you are — your gender, your age, where you are from, how you look. Somebody coming behind the counter or into a staff area. Anybody who appears to be under the influence and is unpredictable. And your own instinct that this is not safe, which is worth trusting even when you cannot justify it.</p>

<p><b>What to do, in order.</b> Stop serving. Put distance between you and them — a counter, a shelf, space. Do not turn your back and do not walk into a confined area. Get somebody, and if there is nobody, get to where other people are. Use whatever your branch has for this: a phrase, an alarm, a colleague's name that means come now.</p>

<p><b>What not to do, and each of these has hurt somebody.</b> Do not argue, however wrong they are. Do not touch them, at all, for any reason. Do not follow. Do not block the way out. Do not try to keep them there until somebody arrives. And do not stay alone with somebody who is frightening you because leaving feels rude.</p>

<p><b>The permission you may not think you have.</b> You are allowed to walk away from a customer mid-sentence if you feel unsafe. You do not need to finish the transaction, explain yourself, or get authorisation. Any employer who would criticise that is wrong, and it is worth knowing in advance that the permission exists — because the reason people stay in unsafe situations is almost always that they were not sure they were allowed to leave.</p>

<p><b>Afterwards, and this matters.</b> Tell somebody what happened, the same day, and write it down. Not because a form is needed, but because these things escalate over weeks — the same person returns, or somebody else has a similar experience, and a pattern that exists in three people's memories is not a pattern anybody can act on.</p>

<p><b>The colleague version, which is harder.</b> Everything above applies when the person is a member of staff rather than a customer, and it is more difficult because you cannot walk away permanently and because reporting feels disloyal. It is not disloyal. Module 6 named this as one of the things that is not part of learning the job, and the route is the same: write it down, tell somebody, go higher once if nothing happens.</p>

<blockquote>WATCH-OUT: The single most important physical rule in this whole track: never put yourself between a person and the door. That applies to somebody taking goods, somebody angry, and somebody you simply do not like the look of.</blockquote>"""
, [
 C("If you feel unsafe with a customer, you are allowed to:",
   ["Ask them to leave", "Walk away mid-sentence, without explaining or getting authorisation",
    "Refuse service formally", "Call security first"], 1,
   "People stay in unsafe situations mostly because they were unsure they were allowed to leave."),
 C("An incident where somebody was threatening should be written down because:",
   ["A form is required", "These escalate over weeks, and a pattern in three memories is not actionable",
    "Insurance needs it", "The police may ask"], 1,
   "The same person returns, or somebody else has a similar experience."),
 C("Your own instinct that a situation is not safe is:",
   ["Only reliable with experience", "Worth trusting even when you cannot justify it",
    "Best checked with a colleague", "Often an overreaction"], 1,
   "It sits in the list of places where the line has been crossed.")]),

("Somebody is hurt", 10, """<p>An injury to a customer, a colleague or you. What follows is deliberately short on technique, because doing something you are not trained to do can make an injury worse.</p>

<p><b>The first thing, always.</b> Make sure nothing is still causing harm — the spill, the broken glass, the thing about to fall — and then get help. Shout for the nearest colleague and send somebody specific for the trained first aider. <i>You, please get Ndidi</i> works and <i>somebody get help</i> does not, because a group instruction is an instruction to nobody.</p>

<p><b>What you do while waiting.</b> Stay with them. Talk to them. Keep other people back so they have space and are not being watched. That is genuinely valuable and it requires no training at all.</p>

<p><b>What you do not do.</b> Do not move somebody who is hurt unless leaving them is more dangerous than moving them. Do not give food, drink or any medicine, including something they ask for. Do not attempt anything you have not been trained in. And do not let embarrassment — theirs or yours — end it early: people frequently insist they are fine because they are humiliated, and somebody who has hit their head saying they are fine is not information.</p>

<p><b>Calling for outside help.</b> Know your branch's numbers and where they are posted, because they differ by business and by state. If somebody is unconscious, having difficulty breathing, bleeding badly, or you are unsure — call, and call early. Nobody has ever been criticised for calling when it turned out to be less serious than it looked.</p>

<p><b>Then record it, while it is fresh.</b> What happened, when, where, who was there, what was done. Not to allocate blame — because an accurate account written that day protects everybody, including the person who was hurt, and because memory changes fast and in the direction people expect it to.</p>

<p><b>And the near miss.</b> The fall that did not happen, the shelf that nearly came down. Report those too. A near miss is the same event with a better outcome, and it is the only warning anybody gets.</p>

<p><b>If the injured person is you.</b> Say so, immediately, and let somebody else take over. The instinct is to finish the shift, particularly with a small injury and particularly when the shop is busy, and it produces two problems: an untreated injury that gets worse, and no record of an event that may matter later if it does. A cut that needed a plaster on Tuesday and needed stitches on Thursday is a much more difficult conversation than the one you avoided.</p>

<blockquote>WATCH-OUT: 'Somebody get help' is an instruction to nobody. Point at one person and give them one job. It sounds abrupt and it is the difference between help arriving in ninety seconds and in five minutes.</blockquote>"""
, [
 C("When sending for help you should:",
   ["Shout for anybody available", "Point at one person and give them one job",
    "Go yourself", "Use the alarm only"], 1,
   "A group instruction is an instruction to nobody, and it costs minutes."),
 C("Somebody who has hit their head and says they are fine:",
   ["Can be left", "Is not providing information",
    "Should be sent home", "Has decided"], 1,
   "People frequently insist they are fine because they are humiliated."),
 C("A near miss should be:",
   ["Noted informally", "Reported",
    "Discussed at the next meeting", "Ignored if nobody was hurt"], 1,
   "It is the same event with a better outcome, and the only warning anybody gets.")]),

("Fire, water and getting out", 10, """<p>The events where the whole building matters rather than one person. The good news is that your part is small and entirely learnable in advance.</p>

<p><b>If the alarm goes, go.</b> Every time, including when you are certain it is a test, including when you are serving somebody, including when the till is open. Take nothing with you. The habit of treating alarms as probably nothing is the thing that kills people in buildings, and it is built by every occasion somebody stayed to finish something.</p>

<p><b>What you do on the way out.</b> Bring the customers nearest you — say it as an instruction rather than a suggestion, because people genuinely stand still. Do not go back for anything. Do not use a lift where there is one. And go to the assembly point rather than to the car park generally, because the entire purpose of an assembly point is that somebody can count.</p>

<p><b>Why the counting matters.</b> The only question anybody responding wants answered is whether everybody is out. A member of staff who left by a different door and went home has caused somebody to go back into a building to look for them. Get to the point, be seen, and stay until you are told otherwise.</p>

<p><b>Fire itself.</b> Your branch may train some people to use an extinguisher on something very small and very early. If you have not been trained, you are not the person for it — and even if you have, anything beyond a very small fire is not a decision to make. Fires stop being manageable extremely quickly, and the correct instinct is out rather than closer.</p>

<p><b>Water, which is more common than fire.</b> A burst pipe, a flooded floor, a leak into an electrical area. Get people away from it, do not walk into standing water where there is any electrical risk, and get somebody who knows where the stopcock and the power isolation are. That last thing is worth knowing yourself, and almost nobody does.</p>

<p><b>And the everyday version of all this.</b> Exits kept clear, which is the commonest failing in every shop everywhere. A delivery cage parked in front of a fire door on a busy Saturday is a routine, invisible, entirely normal decision, and it is the reason people cannot get out of buildings.</p>

<p><b>What to do about the customer who will not leave.</b> Somebody arguing about a purchase while an alarm sounds, or refusing to abandon a full trolley. Say it once, plainly, that the building must be emptied and the goods do not matter, and then leave yourself. You cannot make an adult leave a building and you must not stay to persuade them — tell whoever is responding exactly where they were, which is far more useful than being in there with them.</p>

<p><b>The everyday habit that makes an evacuation work.</b> Knowing two ways out rather than one, from wherever you usually stand. The main door is the one everybody thinks of and it is also the one most likely to be where the problem is. Thirty seconds of noticing, once, is the whole preparation — and it is the kind of thing that only ever gets done by somebody who has just read about it.</p>

<blockquote>IMPLEMENTATION TIP: Walk your nearest fire exit route once this week, physically, and check it is clear. Then do it again in a month. The blockage is never there when somebody is looking for it; it appears on the day everybody is busy.</blockquote>"""
, [
 C("When the fire alarm sounds you should leave:",
   ["After securing the till", "Every time, taking nothing with you",
    "Once it is confirmed real", "After telling a supervisor"], 1,
   "Treating alarms as probably nothing is built by every occasion somebody stayed to finish something."),
 C("Going to the assembly point rather than leaving the area matters because:",
   ["It is policy", "Somebody needs to count",
    "It is safer ground", "Emergency services gather there"], 1,
   "A member of staff who went home has caused somebody to re-enter the building to look for them."),
 C("A delivery cage parked in front of a fire door is:",
   ["Acceptable briefly", "The reason people cannot get out of buildings",
    "A tidiness issue", "Permitted when supervised"], 1,
   "It is a routine, invisible, entirely normal decision, which is exactly the problem.")]),

("Robbery", 10, """<p>The chapter nobody wants to read and the one with the least ambiguity in it. If it happens, there is one correct response and it does not require judgement.</p>

<p><b>Comply.</b> Give them what they ask for. Do not resist, do not argue, do not delay, do not attempt to protect the till or the safe or the stock. Do exactly what you are told, calmly, and let them leave.</p>

<p><b>Why this is stated so flatly.</b> Because in the moment there will be an impulse to do something — to refuse, to be brave, to protect the shop's money. That impulse has got people killed in this trade, and it comes most strongly to people who take their job seriously. Money is insured. Your employer would rather lose every naira in the building than have you hurt, and any employer who would not is not one whose money is worth protecting.</p>

<p><b>What else to do while it is happening.</b> Keep your hands visible and your movements slow, and say what you are doing before you do it — <i>I am opening the drawer now</i>. Do not make sudden movements toward anything, including an alarm, unless you can do it without being noticed and without risk. Do not stare, and do not challenge. If there are customers, do not draw attention to them.</p>

<p><b>Afterwards, in order.</b> Get everybody safe and check whether anybody is hurt. Lock the door if it is safe to do so. Call the police and whoever your branch says. Do not touch anything they touched, and do not tidy up — the scene is evidence. Then write down what you remember as soon as you can, separately from other people rather than agreeing a version together, because independent accounts are worth far more than a shared one and memory changes quickly.</p>

<p><b>And then the part that matters most and gets the least attention.</b> Everybody present is affected, including the people who seemed calm, including the ones who were not directly threatened, including you if you think you are fine. It is normal to be shaky hours later, to sleep badly, to not want to come in. Tell somebody. A business that treats this as paperwork and sends people back to the till is failing at something basic, and it is worth asking for what you need.</p>

<p><b>Reducing the chance of it happening at all.</b> Not your responsibility and worth knowing anyway: robberies are less likely where cash is visibly low and frequently banked, where staff are visible and alert, and where a shop is well lit and not obviously empty. If you are ever asked whether something feels unsafe — a routine that leaves large cash in a drawer, a closing procedure with one person alone — that is a question worth answering honestly rather than politely.</p>

<blockquote>WATCH-OUT: Never chase anybody out of the shop, and never follow to see where they go. This is the point at which people are most often hurt, and the goods involved are worth nothing beside it.</blockquote>"""
, [
 C("During a robbery the correct response is to:",
   ["Trigger the alarm immediately", "Comply, calmly and without delay",
    "Delay them until help arrives", "Protect the safe"], 1,
   "The impulse to do something comes most strongly to people who take their job seriously."),
 C("Afterwards, accounts should be written:",
   ["Together, to agree the facts", "Separately, as soon as possible",
    "After the police arrive", "By the supervisor only"], 1,
   "Independent accounts are worth far more than a shared one, and memory changes quickly."),
 C("The point at which people are most often hurt in a robbery is:",
   ["Handing over the money", "Chasing or following afterwards",
    "The first moments", "Triggering the alarm"], 1,
   "And the goods involved are worth nothing beside it.")]),

("Somebody collapses", 10, """<p>A customer or colleague becomes seriously unwell. It happens in shops more than people expect, partly because shops are where people are.</p>

<p><b>The first thirty seconds.</b> Get help — one person, one instruction, sent for the trained first aider and to call for an ambulance. Clear space around them. Do not crowd, and move other people back rather than letting a circle form.</p>

<p><b>What you can do without any training.</b> Stay with them. Talk to them, calmly, even if they do not seem to respond, because hearing somebody is reassuring and because a change in how they respond is information for whoever arrives. Note the time. Find out anything obvious — did they say something before, are they with anybody, is there a medical bracelet or card.</p>

<p><b>What you do not do, and this list is the important part.</b> Do not give anything by mouth, including water, including something they ask for. Do not move them unless they are in immediate danger where they are. Do not give any medicine, including from the shelves, including from a pharmacy counter, including if a bystander suggests it and even if it seems obviously right. And do not attempt any technique you have not been trained in.</p>

<p><b>The pharmacy version, which needs its own line.</b> If you work somewhere that sells medicine, the pressure to hand something over will be higher and so is the risk. Anything of that kind is the pharmacist's decision, not yours, and that holds in an emergency exactly as it holds on an ordinary Tuesday.</p>

<p><b>When somebody refuses help.</b> Adults are entitled to decline, and you cannot insist. Stay nearby, keep watching, and get help anyway if they deteriorate or lose consciousness — at which point they are no longer declining anything.</p>

<p><b>And afterwards.</b> Write down what you saw and when, while it is clear. If it was distressing, say so to somebody. Being present at something like this affects people for days and it is not a sign of weakness; the ones who say they are unaffected are frequently the ones who need a conversation most.</p>

<p><b>The thing that makes this easier for everybody.</b> Knowing, before it happens, that you are not expected to fix it. A shop assistant who believes they must do something medical will hesitate, improvise, or freeze. One who knows their job is to get help, clear space, stay and note the time will do those four things immediately and well. The limits are not a restriction on what you can contribute — they are what makes the contribution reliable.</p>

<blockquote>WATCH-OUT: The instinct to give somebody water is almost universal and it is one of the few things that can make a situation considerably worse. Nothing by mouth, however reasonable it seems and however much they ask.</blockquote>"""
, [
 C("Giving water to somebody who has collapsed is:",
   ["Helpful and instinctive", "One of the few things that can make it considerably worse",
    "Acceptable in small amounts", "Fine if they ask"], 1,
   "Nothing by mouth, however reasonable it seems."),
 C("An adult who refuses help:",
   ["Must be helped anyway", "Is entitled to decline, and should be watched",
    "Should be asked to leave", "Signs a form"], 1,
   "Get help anyway if they deteriorate or lose consciousness, at which point they are no longer declining."),
 C("Talking to somebody who does not seem to respond is worth doing because:",
   ["It passes the time", "Hearing somebody is reassuring, and any change is information",
    "It keeps them awake", "Policy requires it"], 1,
   "It requires no training at all and is genuinely valuable.")]),

("Okelewo Stores: the afternoon the power went", 10, """<p>Eleven months in. Not the most dramatic thing that happened at the Ibadan branch, and the most useful to read, because almost everything in it was ordinary.</p>

<p><b>What happened.</b> Power failed at about two on a Friday, the generator did not start, and the shop went dark with perhaps twenty customers in it. No emergency, no danger, and immediately a difficult situation: tills down, chillers off, people unable to see well, and a queue holding items they could not pay for.</p>

<p><b>The first three minutes.</b> The supervisor said, loudly and once, that the power was out, the shop was safe, and everybody should stay where they were for a moment. Ada opened the front doors wide, which brought in enough light to see by, and stood near the entrance — not to stop anybody but because somebody standing at a door in the dark is reassuring in a way that is hard to explain.</p>

<p><b>What went right afterwards.</b> Customers holding goods were asked to leave them at the counter rather than being asked to put them back. Nobody was accused of anything. Two people did walk out with items and everybody saw it, and nobody was chased — the supervisor said afterwards that she had watched Ada watch them go and be visibly unhappy about it, and had said good, that is the right unhappy.</p>

<p><b>The chillers, which were the actual cost.</b> Ada's contribution was remembering module 4 and saying it: the chillers should stay shut. Nobody opened them for two hours and almost nothing was lost, which would not have been true if the ordinary instinct — check whether things are still cold — had been followed.</p>

<p><b>What went wrong.</b> Nobody knew where the torches were. There were two, both in the office, and it took eleven minutes to find them because the person who knew was not on shift. That was fixed the following week and it is the most repeatable failure in this chapter.</p>

<p><b>And what Ada wrote down that evening.</b> Four lines: what happened, what was lost, that the torches were not findable, and that the generator had not started. The last of those turned out to matter — it had failed to start twice before and each time it had been mentioned to somebody different, so nobody had a count.</p>

<p><b>Why this chapter is here rather than a robbery or a fire.</b> Because most people will never meet those, and almost everybody in this market will work through a power failure. The module's whole argument is visible in a small event: nobody was in danger, and the difference between the branch that handled it and one that did not was three or four ordinary decisions made in the first minutes by people who had thought about it beforehand.</p>

<blockquote>IMPLEMENTATION TIP: Find out where your branch's torches are, whether they work, and whether the doors can be opened in a power failure. Three questions, five minutes, and one of them is the difference between eleven minutes of dark and none.</blockquote>"""
, [
 C("Ada's contribution during the power failure was remembering that:",
   ["The tills needed securing", "The chillers should stay shut",
    "The doors should be locked", "Customers should be counted"], 1,
   "Nobody opened them for two hours and almost nothing was lost."),
 C("When two customers walked out with items, the response was:",
   ["To follow them", "To let them go",
    "To call the police", "To lock the doors"], 1,
   "The supervisor's comment was that being unhappy about it was the right unhappy."),
 C("The most repeatable failure in the chapter was:",
   ["The generator", "Nobody knowing where the torches were",
    "The chillers", "The tills"], 1,
   "There were two, both in the office, and it took eleven minutes to find them.")]),

("Review, and the things to find out this week", 10, """<p>The module in short, and then the only homework in this track that genuinely cannot wait.</p>

<p><b>People before stock and cash.</b> Every chapter here reduces to it. The instinct to protect the shop's property is normal, well-intentioned and wrong, and it is strongest in the people who take the job most seriously.</p>

<p><b>The angry customer.</b> Lower your voice, let them finish, use their words, stand still, move them away from an audience, get somebody early rather than late. Explaining, defending and 'calm down' all make it worse.</p>

<p><b>Past the line — threats, abuse about who you are, somebody behind the counter, your own instinct.</b> Stop serving, put distance, do not touch, do not follow, do not block the exit, get somebody. You are allowed to walk away without explaining, and never put yourself between a person and the door.</p>

<p><b>Somebody hurt.</b> Stop the cause, point at one person and give them one job, stay with them, keep people back. Do not move them, do not give anything by mouth, do not exceed your training. Record it, including near misses.</p>

<p><b>Alarm means out.</b> Every time, take nothing, bring the nearest customers, go to the assembly point so somebody can count. Keep the exits clear, which is the commonest failing in every shop everywhere.</p>

<p><b>Robbery: comply.</b> Slow movements, say what you are doing, let them leave, never chase. Afterwards, safety first, do not touch the scene, write independent accounts, and expect it to affect you for days.</p>

<p><b>Collapse.</b> Get help, clear space, stay and talk, note the time, and give nothing by mouth or from the shelves.</p>

<p><b>The homework, and it is three questions.</b> Who are the trained first aiders on your shifts? Where are the emergency numbers written, and are they current? Where is the assembly point? Add two more if you can: where are the torches, and can the doors be opened without power.</p>

<p><b>Why this is the one thing not to postpone.</b> Everything else in this track improves gradually and forgives a slow start. This module is the opposite: it is worth nothing at all until the day it is needed, and on that day you will have exactly what you already knew.</p>

<p><b>One more thing, about how this module should sit with you.</b> Reading it in one go is heavy, and it can leave somebody feeling that a shop is a dangerous place. It is not. The overwhelming majority of retail shifts contain none of this, and most people work for years and meet perhaps one incident from this entire module. The preparation is worth doing precisely because the events are rare — rare things get met by people who have never met them before, and the ten minutes of asking is what stands in for the experience nobody has.</p>

<blockquote>WORTH KNOWING: The next module is about getting better — what to practise, how to be trusted with more, and what actually gets somebody promoted. After the weight of this one, that is a considerably more cheerful subject.</blockquote>"""
, [
 C("The homework is described as the one thing not to postpone because this module:",
   ["Is examined", "Is worth nothing until the day it is needed",
    "Takes longest to learn", "Is required by law"], 1,
   "On that day you will have exactly what you already knew."),
 C("The two extra questions beyond first aiders, numbers and assembly point are the torches and:",
   ["The alarm code", "Whether the doors open without power",
    "The stopcock", "Who holds keys"], 1,
   "Both came directly from what went wrong during the power failure."),
 C("The instinct to protect the shop's property is described as:",
   ["A sign of a good employee", "Normal, well-intentioned and wrong",
    "Rare", "Trainable"], 1,
   "And strongest in the people who take the job most seriously.")]),
]


QUESTIONS = [
 Q("Goods and cash are described as:", ["The shop's priority", "Insured and replaceable", "Worth protecting carefully", "The manager's responsibility"], 1,
   "Neither is worth an injury to anybody.", "Ch1 §3", "The rule"),
 Q("The correct response in almost every situation in this module is the first thirty seconds and then:", ["Continuing yourself", "Handing over to somebody qualified", "Recording it", "Calling the manager"], 1,
   "The module deliberately teaches nothing beyond that.", "Ch1 §4", "The rule"),
 Q("If a branch instruction asks you to risk yourself to protect goods, that instruction is:", ["To be followed", "Wrong, and worth raising", "A matter of judgement", "Standard in some businesses"], 1,
   "It is the one case where the module says not to follow the branch.", "Ch1 §7", "The rule"),
 Q("Anger at the escalated level is usually the result of:", ["The current problem", "An accumulation across that person's day", "Poor service", "A policy dispute"], 1,
   "You are meeting the accumulation rather than the incident.", "Ch2 §2", "Angry customers"),
 Q("Interrupting somebody who is angry:", ["Shortens it", "Restarts them", "Shows attention", "Redirects them"], 1,
   "Letting them finish is one of the reliable de-escalation techniques.", "Ch2 §3", "Angry customers"),
 Q("Which of these raises the temperature?", ["Standing still", "Explaining", "Using their words back", "Lowering your voice"], 1,
   "Along with defending the shop, saying calm down, and any sentence beginning with 'actually'.", "Ch2 §4", "Angry customers"),
 Q("Getting a supervisor early rather than late is:", ["An admission of failure", "The right move", "Only for serious cases", "A last resort"], 1,
   "One arriving after ten minutes of escalation is inheriting something worse.", "Ch2 §6", "Angry customers"),
 Q("The measure of how you handled an escalated situation is:", ["Whether they left happy", "Whether you kept it from getting worse and stayed safe", "Whether a refund was avoided", "Whether a supervisor was needed"], 1,
   "Some of it is not resolvable however correctly you act.", "Ch2 §7", "Angry customers"),
 Q("The line has been crossed when there are threats, abuse about who you are, somebody behind the counter, or:", ["A raised voice", "Your own instinct that it is not safe", "A refund demand", "An audience"], 1,
   "Worth trusting even when you cannot justify it.", "Ch3 §2", "Past the line"),
 Q("On feeling unsafe, the first action is to:", ["Call for help", "Stop serving and put distance between you", "Ask them to leave", "Move to the office"], 1,
   "Do not turn your back and do not walk into a confined area.", "Ch3 §3", "Past the line"),
 Q("Which of these has hurt people?", ["Getting a colleague", "Blocking the way out", "Putting distance between you", "Using an alarm phrase"], 1,
   "Along with arguing, touching, following, and trying to keep somebody there.", "Ch3 §4", "Past the line"),
 Q("People stay in unsafe situations mostly because:", ["They feel responsible", "They were unsure they were allowed to leave", "They fear dismissal", "They underestimate the risk"], 1,
   "Which is why the permission is worth knowing in advance.", "Ch3 §5", "Past the line"),
 Q("The most important physical rule in the track is never to:", ["Work alone at night", "Put yourself between a person and the door", "Handle large amounts of cash", "Challenge a customer"], 1,
   "It applies to theft, to anger, and to anybody you do not like the look of.", "Ch3 §7", "Past the line"),
 Q("The first action when somebody is hurt is to:", ["Call an ambulance", "Make sure nothing is still causing harm", "Move them to safety", "Find the first aider"], 1,
   "Then get help, with one person given one instruction.", "Ch4 §2", "Injury"),
 Q("'Somebody get help' fails because:", ["It is unclear", "A group instruction is an instruction to nobody", "It causes panic", "It is too quiet"], 1,
   "It is the difference between ninety seconds and five minutes.", "Ch4 §2", "Injury"),
 Q("While waiting for help you should stay, talk, and:", ["Take notes", "Keep other people back", "Offer water", "Sit them up"], 1,
   "It requires no training at all and is genuinely valuable.", "Ch4 §3", "Injury"),
 Q("An injured person should not be moved unless:", ["They ask", "Leaving them is more dangerous than moving them", "They can walk", "Help is delayed"], 1,
   "Doing something you are not trained for can make an injury worse.", "Ch4 §4", "Injury"),
 Q("An accurate account written the same day protects:", ["The business", "Everybody, including the person who was hurt", "The witness", "The insurer"], 1,
   "Memory changes fast and in the direction people expect it to.", "Ch4 §6", "Injury"),
 Q("A near miss is described as:", ["Not worth reporting", "The same event with a better outcome", "A training matter", "A supervisor's concern"], 1,
   "And the only warning anybody gets.", "Ch4 §7", "Injury"),
 Q("When the alarm sounds you take:", ["Your belongings", "Nothing", "The till key", "Your phone only"], 1,
   "Every time, including when you are certain it is a test.", "Ch5 §2", "Evacuation"),
 Q("Treating alarms as probably nothing is built by:", ["Frequent tests", "Every occasion somebody stayed to finish something", "Poor training", "False alarms"], 1,
   "It is the thing that kills people in buildings.", "Ch5 §2", "Evacuation"),
 Q("Customers near you should be brought out with:", ["A suggestion", "An instruction", "A gesture", "The alarm"], 1,
   "People genuinely stand still.", "Ch5 §3", "Evacuation"),
 Q("The purpose of an assembly point is that somebody can:", ["Give instructions", "Count", "Take names", "Meet the fire service"], 1,
   "A member of staff who went home causes somebody to re-enter the building.", "Ch5 §4", "Evacuation"),
 Q("If you have not been trained on an extinguisher you are:", ["Allowed to try on small fires", "Not the person for it", "Expected to attempt it", "Required to assist"], 1,
   "Fires stop being manageable extremely quickly.", "Ch5 §5", "Evacuation"),
 Q("The commonest failing in every shop everywhere is:", ["Untested alarms", "Exits not kept clear", "Missing extinguishers", "Untrained staff"], 1,
   "A delivery cage in front of a fire door is a routine, invisible decision.", "Ch5 §7", "Evacuation"),
 Q("In a robbery the correct response is to:", ["Delay", "Comply", "Trigger the alarm first", "Protect the drawer"], 1,
   "Calmly, without argument, letting them leave.", "Ch6 §2", "Robbery"),
 Q("The impulse to resist comes most strongly to people who:", ["Are inexperienced", "Take their job seriously", "Have been robbed before", "Work alone"], 1,
   "Which is exactly why the chapter states the rule so flatly.", "Ch6 §3", "Robbery"),
 Q("During a robbery you should say what you are doing because:", ["It is polite", "Sudden or unexplained movement is dangerous", "It records the event", "It delays them"], 1,
   "Keep hands visible and movements slow.", "Ch6 §4", "Robbery"),
 Q("Afterwards you should not:", ["Lock the door", "Tidy up", "Check for injuries", "Call the police"], 1,
   "The scene is evidence.", "Ch6 §5", "Robbery"),
 Q("Accounts written separately rather than agreed together are:", ["Harder to reconcile", "Worth far more", "Required by police", "Less reliable"], 1,
   "And memory changes quickly.", "Ch6 §5", "Robbery"),
 Q("Who is affected after a robbery?", ["Those directly threatened", "Everybody present, including those who seemed calm", "The person who handed over the money", "Staff who were not on shift"], 1,
   "It is normal to be shaky hours later and to sleep badly.", "Ch6 §6", "Robbery"),
 Q("When somebody collapses, you should note:", ["Their name", "The time", "Their address", "Witnesses"], 1,
   "Along with anything obvious such as a medical bracelet or card.", "Ch7 §3", "Collapse"),
 Q("You must not give medicine even:", ["From a first aid kit", "If a bystander suggests it and it seems obviously right", "With the person's consent", "In a pharmacy"], 1,
   "In a pharmacy it is the pharmacist's decision, in an emergency exactly as on an ordinary day.", "Ch7 §4", "Collapse"),
 Q("Talking to an unresponsive person is worth doing because it is reassuring and because:", ["It keeps them conscious", "Any change in response is information", "It records the event", "It calms bystanders"], 1,
   "And it requires no training at all.", "Ch7 §3", "Collapse"),
 Q("Somebody who loses consciousness after refusing help:", ["Has made their decision", "Is no longer declining anything", "Should still be left", "Requires a witness"], 1,
   "Adults are entitled to decline; that ends when they cannot.", "Ch7 §5", "Collapse"),
 Q("People who say they were unaffected by a distressing incident are frequently:", ["Genuinely fine", "The ones who need a conversation most", "More experienced", "Less involved"], 1,
   "Being present affects people for days and it is not a sign of weakness.", "Ch7 §6", "Collapse"),
 Q("During the power failure, Ada opened the front doors:", ["To let customers leave", "Because it brought in enough light to see by", "To ventilate the shop", "On instruction"], 1,
   "And stood near the entrance, which is reassuring in a way that is hard to explain.", "Ch8 §3", "The power failure"),
 Q("Customers holding goods were asked to:", ["Put them back", "Leave them at the counter", "Wait for power", "Pay in cash"], 1,
   "And nobody was accused of anything.", "Ch8 §4", "The power failure"),
 Q("The supervisor's comment about Ada watching two people leave with items was:", ["That she should have acted", "That being unhappy about it was the right unhappy", "That it should be reported", "That it was unavoidable"], 1,
   "Nobody was chased.", "Ch8 §4", "The power failure"),
 Q("Almost nothing was lost from the chillers because:", ["The power returned quickly", "Nobody opened them for two hours", "The generator started", "Stock was moved"], 1,
   "The ordinary instinct is to check whether things are still cold.", "Ch8 §5", "The power failure"),
 Q("It took eleven minutes to find the torches because:", ["They were broken", "The person who knew where they were was not on shift", "They were in the stockroom", "Nobody looked"], 1,
   "Fixed the following week, and the most repeatable failure in the chapter.", "Ch8 §6", "The power failure"),
 Q("The generator's failure mattered because it had failed twice before and:", ["Nobody had reported it", "Each time it was mentioned to somebody different, so nobody had a count", "It was under warranty", "It was scheduled for service"], 1,
   "Which is why Ada writing it down that evening was the useful part.", "Ch8 §7", "The power failure"),
]


BANNED = ["at the end of the day"]


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
    if len(LESSONS) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(LESSONS))

    rebalance(QUESTIONS, "shopfloor:hard_moments:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:hard_moments:checks")

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
        "title": "RF 7 — When It Goes Wrong",
        "desc": ("The days that are not about trading. The rule that comes before every other "
                 "rule, the customer who has gone past complaining, where the line is and what "
                 "to do when it is crossed, injury, evacuation, robbery, and somebody "
                 "collapsing — in each case the first thirty seconds, who to call, and where "
                 "your responsibility ends."),
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
