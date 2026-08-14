#!/usr/bin/env python3
"""Build the Budgets & Control module into academy_finance_data.json.

Track module 6. Uses module 4's cost behaviour to build flexed budgets and
module 1's four margin movers to decompose variances, rather than restating
either.

The organising argument: a budget is asked to be a plan, a target and a
forecast at the same time, and those three want different numbers. Most of what
goes wrong with budgeting follows from pretending one number can be all three.

Checks are written scenario-first and exam questions computational or
definitional, deliberately — the last three modules each shipped a check that
duplicated an exam question, so the separation is now designed in rather than
caught afterwards.

Merges into the data file. Rebalance folded into the build.

Run from the app package directory:  python3 build_finance_m7.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "budgets"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Three jobs, one number, and why nobody believes it", 10, """<p>Ask why a business budgets and you get three answers, all reasonable, all wanting a different number.</p>

<p><b>A budget is a plan.</b> It coordinates: if sales intend to sell ₦240,000,000, buying must purchase for it, the warehouse must hold it, and finance must fund it. For that job the number should be the <i>most likely</i> outcome, because everything else is sized off it.</p>

<p><b>A budget is a target.</b> It motivates and it measures people. For that job the number should be <i>demanding but achievable</i> — deliberately above the most likely outcome, or it motivates nobody.</p>

<p><b>A budget is a forecast.</b> The board and the bank need to know what will actually happen. For that job the number should be <i>unbiased</i>, with no stretch and no cushion.</p>

<p>Those three cannot be the same number, and the moment a business insists they are, everybody in it starts behaving rationally in ways that damage the process.</p>

<p><b>Watch what happens.</b> If the budget is the target and bonuses hang on it, every manager submits the lowest number they can defend. Sandbagging is not dishonesty; it is the correct response to being measured against your own estimate.</p>

<p>Then finance, knowing this, adds a stretch on top. Managers, knowing finance will add a stretch, pad further. Two rounds later the business has a number that describes nobody's expectation of anything and everybody's negotiating position.</p>

<p>Meanwhile the same number is used to plan purchasing and cash — so the padding built to protect a bonus is now sizing your stock order and your overdraft facility.</p>

<p><b>The fix is separation, and it is not expensive.</b> Hold a <i>plan</i> that represents your honest expectation, and set <i>targets</i> separately if you want them. Report against the plan, so variances describe reality rather than negotiation. Reforecast when the plan is clearly wrong, without treating that as failure.</p>

<p>Businesses that separate the two argue about assumptions. Businesses that merge them argue about the number, which is a proxy fight for the bonus, and no useful information passes in either direction.</p>

<p><b>What this means for you as a manager receiving a budget.</b> Ask which job the number in front of you is doing. If it is a target, you are entitled to say what you actually expect and to have both recorded. If it is a plan, then padding it is not prudence — it will resize somebody else's purchasing, and the person whose order arrives short will not know why.</p>

<blockquote>WATCH-OUT: The clearest sign that plan and target have been merged is that nobody in the business will tell you what they honestly expect to happen. When the honest number has nowhere to live, it stops being said out loud — and the business loses the only forecast worth having.</blockquote>

<p><b>One further cost of the merged number, less obvious and more expensive.</b> When the plan is also the target, the business cannot distinguish a manager who forecast accurately and delivered from one who sandbagged and beat a soft number. The second looks better on every report. Over a few years that promotes the wrong people, and the skill the business most needs — honest estimation — is the one it has been quietly selecting against.</p>""",
 [C("Your team is asked for next year's number, and bonuses will be paid against it. You expect ₦48m and could defend ₦42m. Submitting ₦42m is:",
    ["Dishonest", "The rational response to being measured against your own estimate",
     "Required by good practice", "Irrelevant to planning"], 1,
    "It is the process, not the person, that produces this — which is why plan and target should be separate numbers."),
  C("Finance adds a stretch because it expects padding; managers pad because they expect a stretch. After two rounds the number describes:",
    ["The most likely outcome", "A demanding target",
     "Nobody's expectation and everybody's negotiating position", "The board's requirement"], 2,
    "And that number is then used to size purchasing and the overdraft facility."),
  C("Nobody in the business will say what they honestly expect next quarter. This most likely indicates:",
    ["Good commercial discipline", "Plan and target have been merged, so the honest number has nowhere to live",
     "A forecasting system failure", "Excessive caution"], 1,
    "The business loses the only forecast worth having, and does not notice.")]),

("Building a budget that means something", 10, """<p>Most budgets are built by taking last year and adding a percentage. It is fast, it is defensible, and it carries forward every inefficiency in the business unexamined — including the ones somebody would fix if asked.</p>

<p><b>Build revenue from drivers, not from a percentage.</b> A branch's revenue is roughly transactions multiplied by average basket. Those are two things a manager can discuss, influence and be wrong about in identifiable ways. "Revenue up 12%" is a single number that can only be argued about as a whole.</p>

<p>Driver-based budgeting also tells you where a miss came from. If transactions held and basket fell, that is a mix or pricing question. If basket held and transactions fell, that is footfall or availability. The percentage version tells you only that you missed.</p>

<p><b>Build costs by behaviour, using module 4.</b> Separate the fixed from the variable and budget them differently. Fixed costs should be budgeted as commitments — rent, salaries, contracts, each with a known amount and date. Variable costs should be budgeted as a <i>rate</i>: naira per delivery, per transaction, per unit. That way the cost budget flexes automatically with volume rather than being wrong the moment volume differs.</p>

<p><b>State the assumptions separately and in writing.</b> Exchange rate, inflation on key inputs, fuel, headcount, the opening date of a new branch, whether a large customer renews. These are the things that will actually determine whether the budget holds, and they are usually buried inside the numbers where nobody can see or challenge them.</p>

<p>A budget with its assumptions listed on one page can be reviewed intelligently. A budget without them can only be believed or disbelieved.</p>

<p><b>Then do the thing almost nobody does: write down what happens if an assumption breaks.</b> If the exchange rate moves 15%, which line moves and by how much? If the large customer leaves, what is the profit effect? This takes an hour and converts a budget into a small set of scenarios, which is far more useful than a single line that will be wrong.</p>

<p><b>Build the cash budget alongside, not afterwards.</b> Module 3's point applies directly: a profitable budget that the business cannot fund is not a plan, it is an aspiration. Growth of 30% requires working capital, and the budget that shows the profit without showing the funding has hidden the hardest part of the year.</p>

<p><b>And a caution about precision.</b> Budgets carrying figures to the naira invite an accuracy nobody has. Round sensibly. The false precision does not improve the estimate and it does encourage arguments about the third decimal place of an assumption that is itself a guess.</p>

<blockquote>IMPLEMENTATION TIP: Ask for one page listing every assumption behind your budget, with the number attached to each. If that page cannot be produced, the budget was built by extrapolation, and nobody in the business can tell you what would have to be true for it to hold.</blockquote>

<p><b>Who should build it.</b> A budget written entirely by finance is accurate about costs and ignorant about the market; one written entirely by operations is optimistic about revenue and vague about cost. The workable arrangement is that the people who will be held to the numbers propose them, finance challenges the assumptions rather than the totals, and disagreements are settled by arguing about which assumption is right. That is a slower process and it produces a number people will defend rather than resent.</p>""",
 [C("Your branch budget says 'revenue up 12%'. Transactions and average basket are not shown. The practical problem is:",
    ["It is too ambitious", "A miss cannot be diagnosed — you learn only that you missed",
     "It ignores inflation", "It cannot be approved"], 1,
    "Drivers tell you whether footfall or basket moved, which have different remedies."),
  C("Fuel is budgeted as a fixed monthly figure. When deliveries run 30% above plan, the fuel variance will:",
    ["Be zero", "Show an overspend that is really just higher activity",
     "Show an underspend", "Be unaffected"], 1,
    "Variable costs budgeted as a rate flex with volume; budgeted as a lump they generate meaningless variances."),
  C("A budget shows 30% growth and healthy profit, with no cash budget alongside. It is:",
    ["Complete", "An aspiration — the hardest part of the year is missing",
     "Conservative", "Ready for approval"], 1,
    "Growth requires working capital, and a profitable plan the business cannot fund is not a plan.")]),

("The comparison that is actually fair", 10, """<p>A branch budgeted ₦18,000,000 of revenue and ₦3,600,000 of variable cost. It achieved ₦22,000,000 of revenue and spent ₦4,300,000. Has it overspent by ₦700,000?</p>

<p>Obviously not — it sold more, so it should have spent more. But that comparison is made in businesses every month, and managers are asked to explain overspends that are simply the arithmetic of a good month.</p>

<p><b>A flexed budget fixes it.</b> Recalculate the budget at the volume actually achieved, then compare. Budgeted variable cost was 20% of revenue. At ₦22,000,000 of revenue the flexed allowance is ₦4,400,000. Actual spend was ₦4,300,000, so the branch is ₦100,000 <i>under</i> — a small favourable variance, not a ₦700,000 overspend.</p>

<p>The fixed portion does not flex. Rent budgeted at ₦1,200,000 stays ₦1,200,000 whatever the volume, and any difference there is a real variance.</p>

<p><b>Why this matters beyond fairness.</b> Unflexed comparison destroys the credibility of the whole reporting process. A manager told they overspent in their best month learns that the numbers do not describe reality, and thereafter defends rather than investigates. You lose the variance analysis entirely, and you lose it precisely with the managers who are performing.</p>

<p><b>Flexing splits every variance into two honest halves.</b> The <b>volume</b> effect — we sold more or fewer units than planned — and the <b>performance</b> effect — at the volume we actually did, were we efficient? Only the second is usually the manager's to answer, and separating them is what makes the conversation about performance rather than about luck.</p>

<p><b>What must be split correctly for this to work.</b> Everything rests on the fixed-variable split from module 4. Treat a mixed cost as fully variable and you will flex the fixed portion too, granting a bigger allowance in a busy month than the business actually incurred. Treat it as fully fixed and you will penalise growth. This is the practical reason to do the high-low exercise properly rather than eyeballing it.</p>

<p><b>The step-cost complication, honestly.</b> Flexing assumes costs move smoothly, and step costs do not. A branch that passed the volume where a second supervisor was needed will show an unfavourable variance that is entirely correct and entirely unavoidable. That is not a failure — it is information about where your capacity band ended, and it should be reported as such rather than argued about.</p>

<blockquote>IMPLEMENTATION TIP: Before responding to any variance, ask whether the budget was flexed for actual volume. If it was not, roughly a third of the variance in a growing business is arithmetic rather than performance, and answering it as though it were performance wastes everybody's time.</blockquote>

<p><b>What flexing cannot do.</b> It corrects for volume and nothing else. If the sales mix shifted, if prices moved, or if a one-off event distorted the month, the flexed comparison is still comparing two different situations — more fairly, but not fairly. Flexing is a large improvement on the raw comparison and it is not the end of the analysis, and treating it as complete is how a mix problem hides inside a clean-looking cost report.</p>""",
 [C("Budget: ₦18m revenue, ₦3.6m variable cost. Actual: ₦22m revenue, ₦4.3m spent. The flexed allowance is:",
    ["₦3.6m, so ₦700,000 overspent", "₦4.4m, so ₦100,000 underspent",
     "₦4.3m, so nil variance", "₦5.28m, so ₦980,000 underspent"], 1,
    "20% of ₦22m is ₦4.4m. The apparent overspend was the arithmetic of a good month."),
  C("A manager is told they overspent in their strongest month because the budget was not flexed. The lasting damage is:",
    ["A difficult conversation", "They learn the numbers do not describe reality, and defend rather than investigate",
     "An incorrect bonus", "Nothing, once explained"], 1,
    "And you lose variance analysis precisely with the managers who are performing."),
  C("A branch passed the volume at which a second supervisor was needed, producing an unfavourable cost variance. This should be:",
    ["Charged to the manager", "Reported as information about where the capacity band ended",
     "Excluded from the report", "Recovered next month"], 1,
    "Step costs do not flex smoothly, and the variance is both correct and unavoidable.")]),

("Variances that tell you something", 10, """<p>A variance is the difference between what happened and what should have happened. Most reporting stops there, which is the least useful place to stop — the total tells you something went differently, not what to do.</p>

<p><b>Decomposing a revenue variance.</b> Budget ₦18,000,000 from 3,000 units at ₦6,000. Actual ₦19,800,000 from 3,600 units at ₦5,500. Favourable by ₦1,800,000, and the headline hides two opposing stories.</p>

<p><b>Volume variance:</b> 600 extra units at the budgeted ₦6,000 is ₦3,600,000 favourable.<br>
<b>Price variance:</b> ₦500 below budget across 3,600 units is ₦1,800,000 adverse.</p>

<p>The two net to the ₦1,800,000 reported. But the decomposition says the business bought its volume with price — and depending on your margin, that may have been a poor trade even though the headline is favourable. A single positive number concealed a pricing problem.</p>

<p><b>Cost variances split the same way.</b> A materials overspend divides into a <b>price</b> element — we paid more per unit than planned — and a <b>usage</b> element — we consumed more units than the output required. Those belong to different people: price is usually buying, usage is usually operations. Reporting them combined guarantees the conversation happens with the wrong person.</p>

<p><b>Mix, from module 1, appears here too.</b> Where several products are sold, a favourable volume variance can hide a shift toward low-margin lines. Total units up, total contribution down, and nothing in the headline variance says so.</p>

<p><b>The rule about signs, which trips people up.</b> Favourable and adverse are arithmetic labels, not judgements. A favourable maintenance variance may mean servicing was skipped, which is a future breakdown bought at a discount. A favourable staff cost variance may mean posts were unfilled and service suffered. <b>Ask what a favourable variance cost you</b> — it is the question nobody asks, because good news does not get investigated.</p>

<p><b>And materiality, so the exercise stays useful.</b> Set a threshold — a percentage and an absolute figure, both — and investigate only what crosses it. A report that lists forty variances gets read as noise, and the two that mattered are lost among thirty-eight that did not.</p>

<blockquote>WATCH-OUT: Variances net off, and netting hides. A department reporting a small total variance may contain a large adverse and a large favourable that have nothing to do with each other. Always look at the components before concluding that a quiet total means a quiet month.</blockquote>

<p><b>A note on standards, which is where variances come from in a manufacturing setting.</b> If your business uses standard costs — an expected cost per unit against which actuals are measured — then every variance is measured against somebody's estimate of what things should cost. Standards that have not been revisited in two years produce variances that describe the passage of time rather than performance. Ask when the standards were last set before taking any usage variance seriously.</p>""",
 [C("Budget 3,000 units at ₦6,000. Actual 3,600 at ₦5,500. The favourable ₦1.8m headline conceals:",
    ["Nothing — it is simply a good month", "A ₦3.6m favourable volume effect against a ₦1.8m adverse price effect",
     "A stock error", "A mix improvement"], 1,
    "The business bought its volume with price, which may have been a poor trade."),
  C("Maintenance came in ₦400,000 under budget. Before recording it as favourable you should ask:",
    ["Whether the budget was too high", "Whether servicing was skipped, buying a future breakdown at a discount",
     "Whether it was flexed", "Whether it belongs to another period"], 1,
    "Good news does not get investigated, which is exactly why it is worth investigating."),
  C("A department reports a variance of ₦50,000 on ₦8m of cost. The most useful next step is:",
    ["Accept it as immaterial", "Look at the components, since a small total can net a large adverse against a large favourable",
     "Flex the budget", "Reforecast"], 1,
    "Netting hides, and a quiet total does not mean a quiet month.")]),

("Investigating without a witch hunt", 10, """<p>Variance analysis has a reputation problem. Done badly it is a monthly exercise in finding someone to blame for arithmetic, and managers learn to prepare defences rather than explanations. Done well it is the cheapest diagnostic a business has.</p>

<p><b>The difference is almost entirely in the first question asked.</b> "Why did you overspend?" invites a defence. "What does this number tell us?" invites an investigation. They cost the same and produce completely different meetings.</p>

<p><b>A sequence that works.</b></p>

<p><b>First, is the number right?</b> A surprising variance is more often a coding error, a missing accrual, an invoice in the wrong period or a cut-off problem than a real operational event. Checking this first costs ten minutes and saves an hour of explaining something that did not happen.</p>

<p><b>Second, was the budget right?</b> A variance measures the gap between actual and budget, and the budget is the half more likely to be wrong. If fuel was budgeted before a 40% price rise, the variance is describing the assumption, not the driver.</p>

<p><b>Third, was it controllable?</b> Currency, a regulated price, a landlord's increase, a national fuel move — real, significant, and not the manager's doing. Holding somebody to an uncontrollable variance teaches them the report is unfair, and they stop engaging with the parts that are theirs.</p>

<p><b>Only fourth: was it performance?</b> And by this point the question is narrow enough to be answerable.</p>

<p><b>Ask about favourable variances with the same seriousness.</b> A business that investigates only overspends is running a one-sided control, and it teaches managers that the way to a quiet month is an underspend — regardless of what was not done to achieve it.</p>

<p><b>The trend matters more than the month.</b> A single adverse variance is noise. The same adverse variance for four months is a structural problem, and the fourth month is far too late to be discovering it. Report a rolling picture, not a monthly snapshot, and the pattern surfaces while it is still small.</p>

<p><b>What a good variance explanation contains.</b> The cause, the amount attributable to it, whether it recurs, and what is being done. "Fuel was up" is not an explanation. "Fuel prices rose 18% in March, worth ₦620,000 of the ₦740,000 variance, it recurs at that level, and we have moved two routes to night deliveries which recovers about ₦200,000 a month from May" is one — and it can be acted on by somebody who was not there.</p>

<blockquote>IMPLEMENTATION TIP: Require every material variance explanation to state whether it recurs. That single word changes how the number is treated: a one-off is history, a recurring one belongs in the reforecast immediately and in next year's budget permanently.</blockquote>

<p><b>Where to spend the investigation effort.</b> Not evenly. The largest variances get attention automatically; the useful discipline is to look hard at the ones that are moderate and persistent, because those are where structural problems live and they never trip a threshold. A ₦200,000 adverse variance every month for a year is ₦2.4m, and it will have been discussed nine times without ever being investigated once.</p>""",
 [C("A variance of ₦900,000 appears with no operational explanation anyone can identify. Check first:",
    ["Whether the manager overspent", "Whether the number is right — coding, accruals, cut-off",
     "Whether it recurs", "Whether it was controllable"], 1,
    "Surprising variances are more often data problems than events, and checking costs ten minutes."),
  C("Fuel was budgeted before a 40% national price rise. The resulting variance is describing:",
    ["Poor route management", "The assumption, not the driver",
     "A coding error", "A volume effect"], 1,
    "The budget is the half more likely to be wrong, and it is the second question to ask."),
  C("A business investigates overspends but never underspends. Managers learn that:",
    ["Cost control is valued", "The route to a quiet month is an underspend, regardless of what went undone",
     "Budgets are accurate", "Favourable variances are unimportant"], 1,
    "It is a one-sided control, and it rewards the wrong thing quietly.")]),

("Forecast and budget are different animals", 10, """<p>A budget is set once and stands as the reference point for the year. A forecast is your current best estimate of the outcome, updated as reality arrives. Businesses that confuse the two either never update — and steer by a number they know is wrong — or update constantly, and lose the reference point that made variances meaningful.</p>

<p><b>You need both, and they answer different questions.</b> The budget answers "what did we commit to, and how are we doing against it?" The forecast answers "given what we now know, where will we land?" The first is accountability, the second is management.</p>

<p><b>The reforecast is where the useful conversation happens.</b> Four months into a year, you know things the budget could not: a customer left, the currency moved, a branch opened late. A reforecast folds those in. Reporting only against a budget built with none of that information means the whole business is steering by a map drawn before the journey began.</p>

<p><b>Rolling forecasts, briefly.</b> Instead of forecasting to a fixed year-end — which gets shorter and less useful every month until December forecasts almost nothing — you forecast a constant horizon, typically twelve months, extending by one each month. The horizon never collapses, and planning does not become an annual panic in the fourth quarter.</p>

<p>The cost is discipline: a rolling forecast that becomes a monthly re-budgeting exercise consumes enormous time. Keep it at driver level — volumes, prices, headcount, key costs — rather than rebuilding every line.</p>

<p><b>What a reforecast must not become.</b> An opportunity to move the goalposts. If the target reforecasts downward every time performance disappoints, it has stopped being a forecast and become an excuse with arithmetic attached. The protection is the separation from chapter one: <b>report against the original budget for accountability, and against the current forecast for management.</b> Show both. The gap between them is itself information, and hiding it serves nobody.</p>

<p><b>The connection to cash.</b> Module 3's thirteen-week cash forecast is not the same instrument. The budget is annual and about profit; the cash forecast is weekly and about survival. A business needs both, and the one that is easiest to neglect is the one that will actually stop you trading.</p>

<blockquote>WATCH-OUT: A forecast that always shows the business hitting budget by year end, month after month, is not a forecast. It is a statement of hope maintained by moving the recovery further out each month, and it usually collapses in the final quarter when there is no more year left to move it into.</blockquote>

<p><b>How often to reforecast.</b> Quarterly suits most businesses: frequent enough to stay current, infrequent enough that it does not consume the organisation. Monthly reforecasting is justified where conditions genuinely move that fast — heavy currency exposure, volatile input costs — and is otherwise a way of appearing responsive while spending management time that would be better used on the operation itself.</p>""",
 [C("Four months in, a customer has left and the currency has moved. Reporting only against the original budget means:",
    ["Accountability is preserved perfectly", "The business is steering by a map drawn before the journey began",
     "Variances are meaningless", "The budget must be rewritten"], 1,
    "You need both: budget for accountability, reforecast for management."),
  C("Each month the forecast shows a shortfall recovered later in the year, and each month the recovery moves out. This is:",
    ["Prudent forecasting", "Hope maintained by moving the recovery out, which collapses in the final quarter",
     "A rolling forecast", "Normal seasonality"], 1,
    "It is not a forecast at all, and the collapse arrives when there is no more year to move it into."),
  C("A rolling twelve-month forecast avoids which problem?",
    ["Budget padding", "A horizon that collapses toward year end until December forecasts almost nothing",
     "Variance netting", "Uncontrollable costs"], 1,
    "The cost is discipline — keep it at driver level or it becomes monthly re-budgeting.")]),

("The behaviour a budget creates", 10, """<p>A budget is not a neutral measuring instrument. It changes what people do, and some of what it produces is expensive and entirely predictable.</p>

<p><b>Use it or lose it.</b> A department with unspent budget in the last month of the year, knowing next year's allocation is based on this year's spend, will spend it. This is not waste caused by careless managers; it is the correct response to a rule that punishes underspending. Any business that allocates next year from last year's actuals has built this in deliberately without meaning to.</p>

<p><b>Deferring into next period.</b> The mirror image. A manager near their limit delays a genuinely needed repair, a hire, or a stock purchase into the next period. The budget is met and the business is worse off, and the cost appears in a later period with no label on it.</p>

<p><b>Gaming the measure rather than the outcome.</b> If the budget measures cost, cost falls and quality falls with it. If it measures revenue, revenue rises and margin falls. Whatever a budget measures will improve, and whatever it does not measure is where the improvement is coming from. This is not cynicism, it is simply what measurement does.</p>

<p><b>The annual cliff.</b> A budget with a hard year-end creates a distortion around it in both directions — sales pulled forward into December, costs pushed into January. The trading pattern of the business bends around an arbitrary date, and the numbers on either side describe the calendar as much as the business.</p>

<p><b>What actually reduces this.</b> Not tighter enforcement, which increases the incentive to game. Rather:</p>

<p><b>Measure more than one thing.</b> Cost alongside service, revenue alongside margin. Gaming one measure becomes visible in the other.</p>

<p><b>Separate the target from the plan</b>, as chapter one argued, so the number is not simultaneously a bonus threshold and a purchasing input.</p>

<p><b>Do not allocate next year from this year's spend.</b> Build from drivers, so underspending is not punished.</p>

<p><b>Reward the explanation as much as the number.</b> A manager who reports an honest miss early with a clear cause is more valuable than one who delivers the number by means nobody examined — and if the incentives say otherwise, the incentives will win.</p>

<blockquote>IMPLEMENTATION TIP: Look at the last month of your financial year against the eleven before it. A spike in discretionary spending, or a cluster of sales landing just before the cut-off, tells you the budget is shaping behaviour more than the business is. It is one chart and it is uncomfortable reading.</blockquote>

<p><b>The behaviour a budget creates in the person receiving it.</b> Managers held to numbers they did not build and cannot influence stop treating the budget as a management tool and start treating it as an examination — something to survive monthly rather than to use. That is the most expensive behaviour of all, because the budget then delivers none of its planning or forecasting value, and the business is paying for a process that produces only a monthly argument.</p>""",
 [C("A department spends its remaining budget in the final month because next year's allocation is based on this year's spend. This is:",
    ["Careless management", "The correct response to a rule that punishes underspending",
     "Fraud", "A variance error"], 1,
    "The business built the behaviour in without meaning to, by choosing that allocation method."),
  C("A budget measures cost only. Over time you should expect:",
    ["Cost and quality both to improve", "Cost to fall, with quality falling where nobody is measuring",
     "No behavioural change", "Revenue to rise"], 1,
    "Whatever is not measured is where the improvement is coming from."),
  C("Sales cluster just before year end and discretionary costs just after. This tells you:",
    ["Trading is seasonal", "The budget is shaping behaviour more than the business is",
     "The year end is wrongly placed", "Variances need flexing"], 1,
    "Compare the last month of your financial year against the eleven before it — the distortion is visible in one chart.")]),

("The capital request you are asked to sign", 10, """<p>Capital spending is budgeted separately from operating cost, because the money leaves at once and the benefit arrives over years. Most managers meet it as a request to approve, so this chapter is about reading one properly.</p>

<p><b>Payback: how long until we get our money back?</b> A ₦9,000,000 vehicle saving ₦300,000 a month pays back in thirty months. Crude, ignores everything after payback and ignores the time value of money — and it is the number most decisions are actually made on, because it answers the question owners really ask, which is when the cash comes home.</p>

<p><b>Return on investment: the annual return as a percentage of the outlay.</b> ₦3,600,000 a year on ₦9,000,000 is 40%. Useful for comparing options of similar length, and it hides timing entirely.</p>

<p><b>Discounted methods,</b> which recognise that ₦1,000,000 in three years is worth less than ₦1,000,000 today. In a high interest rate environment this matters enormously — at 25%, money three years out is worth barely half its face value. If a proposal's benefits arrive late, an undiscounted appraisal materially overstates it.</p>

<p><b>The three questions worth more than the arithmetic.</b></p>

<p><b>1. Are the benefits real, and would somebody notice if they did not arrive?</b> Cost savings that require headcount to fall must be matched by headcount actually falling. "Efficiency savings" that nobody is accountable for delivering are, in practice, decoration on the proposal.</p>

<p><b>2. What is the do-nothing case?</b> Every proposal compares itself to a static present, which is rarely the alternative. If the current vehicles are failing, the comparison is not "spend ₦9,000,000 versus spend nothing" but "spend ₦9,000,000 versus rising repair costs and missed deliveries".</p>

<p><b>3. What happens if the volume assumption is wrong?</b> Most capital cases assume growth. Ask what payback looks like at flat volume, because that is the scenario nobody models and it is the one that arrives.</p>

<p><b>And the point that connects to module 3.</b> Capital spending is a cash event, immediately and in full, while the P&L sees it slowly as depreciation. A business can approve a run of individually sensible capital projects and find itself unable to fund its trading, because each was assessed on return and none against the cash cycle. Approve capital against the cash forecast, not only against the return.</p>

<blockquote>WATCH-OUT: Be most suspicious of proposals where the benefits are diffuse and the costs are precise. The ₦9,000,000 is certain and will be spent; the ₦300,000 a month is an estimate somebody made, and nobody will revisit it once the vehicle is bought. Ask who will be accountable for the benefit and when it will be checked.</blockquote>

<p><b>The post-implementation review nobody does.</b> Twelve months after a capital project, compare what was promised against what arrived. Almost no business does this, and the consequence is that the quality of capital proposals never improves — nobody is ever shown to have been optimistic, so optimism carries no cost. One review a year, on the largest project, changes how the next proposal is written.</p>""",
 [C("A proposal claims ₦4m of annual 'efficiency savings' with no headcount reduction and no named owner. You should treat it as:",
    ["A sound benefit", "Decoration on the proposal until somebody is accountable for delivering it",
     "A cost avoidance", "A depreciation saving"], 1,
    "Savings that nobody is accountable for delivering are not benefits, they are hopes with a number attached."),
  C("A capital case compares spending ₦9m against 'doing nothing', while the existing vehicles are failing. The comparison is:",
    ["Correct and conservative", "Wrong — the alternative is rising repairs and missed deliveries, not a static present",
     "Too pessimistic", "Irrelevant to payback"], 1,
    "Every proposal compares itself to a static present, which is rarely the actual alternative."),
  C("Several individually sound capital projects are approved on return, and the business cannot fund its trading. The missing test was:",
    ["Discounting", "Payback period", "Approval against the cash forecast",
     "Return on investment"], 2,
    "Capital is a cash event in full and immediately, while the P&L sees it slowly as depreciation.")]),

("The budget conversations you actually have", 10, """<p>This is the chapter to keep. Five conversations every operating manager has, and what to bring to each.</p>

<p><b>1. "Here is your budget for next year."</b></p>

<p>Ask which job the number is doing — plan, target or forecast. Ask for the assumptions on one page. Say what you honestly expect and have it recorded, whatever the target is. <i>What goes wrong:</i> accepting a number without its assumptions, then being held to it when an assumption you never saw turns out to be wrong.</p>

<p><b>2. "You are ₦700,000 over on variable costs."</b></p>

<p>Ask whether the budget was flexed for actual volume. If not, a good chunk of that is arithmetic. Then split what remains into price and usage before answering. <i>What goes wrong:</i> explaining a variance that was never real, which trains everybody that the report cannot be trusted.</p>

<p><b>3. "Explain this variance."</b></p>

<p>Bring the cause, the amount attributable, whether it recurs, and the action. Check the number is right before checking the operation. State plainly where it was not controllable — once, without arguing. <i>What goes wrong:</i> "costs were high", which is not an explanation and invites the conversation to become about you rather than about the number.</p>

<p><b>4. "We need to reforecast."</b></p>

<p>Reforecast the drivers, not the outcome. Show the original budget alongside, because the gap is information. Resist the reforecast that always lands on target — it fools nobody twice. <i>What goes wrong:</i> reforecasting as a way of retiring a miss quietly, which destroys the credibility of every forecast afterwards.</p>

<p><b>5. "Can you approve this capital request?"</b></p>

<p>Ask who owns the benefit and when it will be checked. Ask what the do-nothing case actually costs. Ask what payback looks like at flat volume. Check it against the cash forecast, not only the return. <i>What goes wrong:</i> approving precise costs against diffuse benefits nobody revisits.</p>

<p><b>The thread running through all five.</b> A budget is a set of assumptions with numbers attached. Almost every unproductive budget conversation happens because the assumptions were left out and only the numbers were discussed — so people argue about a figure when they disagree about a belief, and neither side can say what would change their mind.</p>

<p><b>And the sentence worth carrying out of this module.</b> The purpose of a budget is not to be right. It is to make the business's expectations explicit enough that being wrong teaches you something. A budget nobody can be wrong against, because nobody knows what it assumed, teaches nothing at all.</p>

<blockquote>IMPLEMENTATION TIP: Keep your own record of what you said you expected, separately from what you were given as a target. Over a couple of years it will tell you how good your own judgement is — which is information nobody else in the business will ever collect on your behalf, and it is worth more than any budget.</blockquote>

<p><b>A closing word on what control actually means.</b> The word suggests restriction, and in most businesses budgetary control is experienced as exactly that. But control in its useful sense means knowing where you are and being able to change direction — closer to steering than to restraining. A business with tight budgets and no reforecasting has restraint without control: it can stop people spending and it cannot tell where it is going. The reverse — loose limits and excellent visibility — is usually the better position of the two.</p>""",
 [C("You are handed next year's budget as a single revenue figure. The first thing to ask for is:",
    ["A higher figure", "The assumptions on one page",
     "A monthly phasing", "The prior year comparison"], 1,
    "Otherwise you are held to a number built on beliefs you never saw and cannot challenge."),
  C("Asked to explain a variance, the most useful thing you can add beyond the cause is:",
    ["Who was responsible", "Whether it recurs",
     "The percentage", "The prior year figure"], 1,
    "A one-off is history; a recurring variance belongs in the reforecast immediately."),
  C("A budget nobody can be wrong against, because nobody knows what it assumed:",
    ["Is safely conservative", "Teaches the business nothing",
     "Reduces gaming", "Improves accountability"], 1,
    "The purpose is to make expectations explicit enough that being wrong is informative.")]),
]


QUESTIONS = [
 Q("A budget is asked to be a plan, a target and a forecast. For planning purposes the number should be:", ["Demanding but achievable", "The most likely outcome", "Deliberately conservative", "The board's requirement"], 1,
   "Purchasing, stock and funding are all sized off it.", "Ch1 §2", "What a budget is for"),
 Q("Sandbagging a budget is best understood as:", ["Dishonesty", "The rational response to being measured against your own estimate", "A forecasting error", "Poor planning"], 1,
   "It is produced by the process, not the person.", "Ch1 §5", "What a budget is for"),
 Q("Padding built to protect a bonus becomes dangerous because the same number:", ["Is reported to the board", "Sizes purchasing and the overdraft facility", "Sets the tax provision", "Determines headcount"], 1,
   "The person whose order arrives short will not know why.", "Ch1 §7", "What a budget is for"),
 Q("Businesses that separate plan from target argue about:", ["The number", "Assumptions", "Bonuses", "Allocation"], 1,
   "Businesses that merge them argue about the number, which is a proxy fight for the bonus.", "Ch1 §9", "What a budget is for"),
 Q("Building a budget as 'last year plus a percentage' carries forward:", ["Only inflation", "Every inefficiency in the business, unexamined", "The prior year's assumptions explicitly", "Nothing of consequence"], 1,
   "Including the ones somebody would fix if asked.", "Ch2 §1", "Building a budget"),
 Q("Revenue is better budgeted from:", ["A growth percentage", "Transactions multiplied by average basket", "Last year's actual", "The market forecast"], 1,
   "Drivers can be discussed, influenced, and wrong in identifiable ways.", "Ch2 §2", "Building a budget"),
 Q("Variable costs should be budgeted as:", ["A monthly lump sum", "A rate per unit of activity", "A percentage of profit", "Last year's total"], 1,
   "So the budget flexes with volume rather than being wrong the moment volume differs.", "Ch2 §5", "Building a budget"),
 Q("A budget with no stated assumptions can only be:", ["Flexed", "Believed or disbelieved", "Reforecast", "Approved"], 1,
   "With assumptions on one page it can be reviewed intelligently.", "Ch2 §7", "Building a budget"),
 Q("Budgeting to the exact naira mainly produces:", ["Better estimates", "False precision and arguments about guesses", "Easier approval", "Improved variance analysis"], 1,
   "Round sensibly; the accuracy is not there to be had.", "Ch2 §10", "Building a budget"),
 Q("Budget ₦18m revenue with 20% variable cost. Actual revenue ₦22m. The flexed allowance is:", ["₦3.6m", "₦4.4m", "₦4.3m", "₦3.96m"], 1,
   "20% of the volume actually achieved.", "Ch3 §3", "Flexed budgets"),
 Q("Which cost does NOT flex with volume?", ["Delivery fuel", "Sales commission", "Branch rent", "Packaging"], 2,
   "Fixed costs stay put, and a difference there is a real variance.", "Ch3 §4", "Flexed budgets"),
 Q("Flexing splits a variance into:", ["Price and usage", "Volume and performance", "Fixed and variable", "Controllable and uncontrollable"], 1,
   "Only the second is usually the manager's to answer.", "Ch3 §6", "Flexed budgets"),
 Q("Treating a mixed cost as fully variable when flexing will:", ["Penalise growth", "Grant a bigger allowance in a busy month than was actually incurred", "Have no effect", "Understate the fixed cost"], 1,
   "Which is the practical reason to do the high-low split properly.", "Ch3 §7", "Flexed budgets"),
 Q("In a growing business, comparing against an unflexed budget means roughly what share of the variance is arithmetic?", ["None", "About a third", "All of it", "It cannot be estimated"], 1,
   "Answering it as though it were performance wastes everybody's time.", "Ch3 §9", "Flexed budgets"),
 Q("Budget 3,000 units at ₦6,000; actual 3,600 at ₦5,500. The volume variance is:", ["₦1.8m favourable", "₦3.6m favourable", "₦1.8m adverse", "₦3.3m favourable"], 1,
   "600 extra units at the budgeted price.", "Ch4 §3", "Variance analysis"),
 Q("On those figures the price variance is:", ["₦1.8m adverse", "₦1.8m favourable", "₦3.6m adverse", "₦500 adverse"], 0,
   "₦500 below budget across the 3,600 units actually sold.", "Ch4 §4", "Variance analysis"),
 Q("A materials cost variance splits into price and usage. Usage usually belongs to:", ["Buying", "Operations", "Finance", "Sales"], 1,
   "Reporting them combined guarantees the conversation happens with the wrong person.", "Ch4 §6", "Variance analysis"),
 Q("'Favourable' and 'adverse' are:", ["Judgements", "Arithmetic labels", "Performance ratings", "Statutory terms"], 1,
   "A favourable maintenance variance may be a future breakdown bought at a discount.", "Ch4 §8", "Variance analysis"),
 Q("A variance report listing forty items is:", ["Thorough", "Read as noise, losing the two that mattered", "Best practice", "Required for control"], 1,
   "Set a threshold in percentage and absolute terms, and investigate what crosses it.", "Ch4 §9", "Variance analysis"),
 Q("The first check on a surprising variance is:", ["Who is responsible", "Whether the number is right", "Whether it recurs", "Whether it was controllable"], 1,
   "Coding, accruals and cut-off explain more surprises than operations do.", "Ch5 §4", "Investigating variances"),
 Q("The second question is whether:", ["The manager underperformed", "The budget was right", "The cost was material", "It was seasonal"], 1,
   "The budget is the half more likely to be wrong.", "Ch5 §5", "Investigating variances"),
 Q("Holding a manager to an uncontrollable variance teaches them:", ["To manage costs tightly", "That the report is unfair, so they disengage from the parts that are theirs", "To forecast better", "To escalate earlier"], 1,
   "You lose engagement with the controllable half as well.", "Ch5 §6", "Investigating variances"),
 Q("A good variance explanation must state the cause, the amount, the action and:", ["Who approved it", "Whether it recurs", "The percentage", "The budget holder"], 1,
   "A one-off is history; a recurring variance belongs in the reforecast.", "Ch5 §10", "Investigating variances"),
 Q("The same adverse variance for four consecutive months is:", ["Noise", "A structural problem discovered three months late", "A budgeting error", "Immaterial"], 1,
   "Report a rolling picture so the pattern surfaces while it is small.", "Ch5 §9", "Investigating variances"),
 Q("A budget is set once; a forecast is:", ["Set at the half year", "Your current best estimate, updated as reality arrives", "The board's target", "The cash projection"], 1,
   "Budget for accountability, forecast for management.", "Ch6 §1", "Forecast versus budget"),
 Q("A rolling twelve-month forecast prevents:", ["Budget padding", "The horizon collapsing toward year end", "Variance netting", "Capital overspend"], 1,
   "Planning stops becoming an annual fourth-quarter panic.", "Ch6 §5", "Forecast versus budget"),
 Q("When reforecasting, you should report:", ["Only the new forecast", "Both the original budget and the current forecast", "Only the budget", "Neither, until year end"], 1,
   "The gap between them is itself information.", "Ch6 §7", "Forecast versus budget"),
 Q("A reforecast used to retire a miss quietly:", ["Improves accuracy", "Destroys the credibility of every forecast afterwards", "Is standard practice", "Reduces variance"], 1,
   "It has become an excuse with arithmetic attached.", "Ch6 §7", "Forecast versus budget"),
 Q("The annual budget and the thirteen-week cash forecast differ because:", ["One is more accurate", "One is about profit over a year, the other about survival week by week", "One is internal", "One is audited"], 1,
   "The easiest to neglect is the one that will actually stop you trading.", "Ch6 §8", "Forecast versus budget"),
 Q("Allocating next year's budget from this year's actual spend creates:", ["Accuracy", "Use-it-or-lose-it spending in the final month", "Better forecasting", "Lower costs"], 1,
   "The business builds the behaviour in without meaning to.", "Ch7 §2", "Budget behaviour"),
 Q("Deferring a needed repair into the next period achieves:", ["A genuine saving", "The budget met and the business worse off", "A favourable usage variance", "Improved cash"], 1,
   "The cost appears in a later period with no label on it.", "Ch7 §3", "Budget behaviour"),
 Q("Whatever a budget measures will improve, and:", ["Everything else improves with it", "Whatever it does not measure is where the improvement comes from", "Costs always fall", "Quality is unaffected"], 1,
   "Not cynicism — simply what measurement does.", "Ch7 §4", "Budget behaviour"),
 Q("The most effective reduction in budget gaming is:", ["Tighter enforcement", "Measuring more than one thing", "Larger bonuses", "Monthly reforecasting"], 1,
   "Tighter enforcement increases the incentive to game.", "Ch7 §6", "Budget behaviour"),
 Q("A hard year-end creates:", ["More accurate reporting", "Sales pulled forward and costs pushed back around an arbitrary date", "Better forecasting", "Lower variances"], 1,
   "The trading pattern bends around the calendar.", "Ch7 §5", "Budget behaviour"),
 Q("A ₦9m vehicle saving ₦300,000 a month has a payback of:", ["12 months", "30 months", "36 months", "24 months"], 1,
   "Crude, ignores the time value of money, and it is what owners actually ask.", "Ch8 §2", "Capital budgets"),
 Q("Returning ₦3.6m a year on a ₦9m outlay is a return of:", ["25%", "40%", "30 months", "12%"], 1,
   "Useful for comparing options of similar length; it hides timing entirely.", "Ch8 §3", "Capital budgets"),
 Q("Discounting matters most when:", ["Interest rates are low", "Benefits arrive late and rates are high", "The outlay is small", "Payback is under a year"], 1,
   "At 25%, money three years out is worth barely half its face value.", "Ch8 §4", "Capital budgets"),
 Q("Capital spending should be approved against return and also against:", ["The depreciation charge", "The cash forecast", "The tax position", "The budget variance"], 1,
   "It is a cash event in full and immediately, while the P&L sees it slowly.", "Ch8 §9", "Capital budgets"),
 Q("Be most suspicious of capital proposals where:", ["Costs are diffuse and benefits precise", "Benefits are diffuse and costs precise", "Both are precise", "Payback is short"], 1,
   "The outlay is certain; the benefit is an estimate nobody will revisit.", "Ch8 §10", "Capital budgets"),
 Q("Told you are over on variable costs, ask first whether:", ["The team was busy", "The budget was flexed for actual volume", "Prices rose", "It recurs"], 1,
   "In a growing business much of it is arithmetic rather than performance.", "Ch9 §4", "Budget conversations"),
 Q("Reforecasting should be done at the level of:", ["The outcome", "The drivers", "The department total", "The prior year"], 1,
   "And the original budget shown alongside.", "Ch9 §8", "Budget conversations"),
 Q("Most unproductive budget conversations happen because:", ["Numbers are wrong", "Assumptions were left out and only numbers were discussed", "Targets are too high", "Reporting is late"], 1,
   "People argue about a figure when they disagree about a belief.", "Ch9 §10", "Budget conversations"),
 Q("The purpose of a budget is:", ["To be right", "To make expectations explicit enough that being wrong teaches you something", "To control spending", "To satisfy the board"], 1,
   "A budget nobody can be wrong against teaches nothing at all.", "Ch9 §11", "Budget conversations"),
]


def rebalance(items, seed):
    """Spread correct answers evenly across A-D by rotating each option list."""
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
    rebalance(QUESTIONS, "finance:budgets:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:budgets:checks")

    mod = {
        "title": "Budgets and Control",
        "desc": ("A budget is asked to be a plan, a target and a forecast at once, and "
                 "those want different numbers. Building from drivers, flexing for actual "
                 "volume, decomposing variances into price, volume, mix and usage, "
                 "investigating without a witch hunt, forecast against budget, the "
                 "behaviour budgets create, and reading a capital request."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    path = "academy_finance_data.json"
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
