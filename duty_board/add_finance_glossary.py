#!/usr/bin/env python3
"""Add a 'words used here' panel to every finance chapter.

Olamide's observation: the prose explains terms as it goes, but a reader who
meets 'accrual' in one clause of a flowing sentence and misses it is quietly
lost for the rest of the chapter, with no way back except rereading. The track
carries 50 accounting terms, up to 11 in a single chapter.

The fix is additive rather than surgical. Definitions live once in GLOSSARY
below and are injected at the foot of each chapter that uses them, so:

  - the prose is untouched, and keeps its pace and tone
  - a definition improved here improves everywhere it appears
  - the panel sits immediately above the check questions, which is where a
    learner is already scrolling to test themselves

Rules applied when selecting terms for a chapter:
  - a term whose name appears in the chapter title is skipped, because that
    chapter already defines it at length and repeating it is condescending
  - at most SIX terms per chapter, chosen by order of first appearance, so a
    heavy chapter gets help rather than an essay
  - idempotent: the marker comment prevents a second run doubling the panel

Run from the app package directory:  python3 add_finance_glossary.py
"""

import io
import json
import re
import sys

DATA = "academy_finance_data.json"
MARKER = "<!--terms-->"
MAX_PER_CHAPTER = 6
CHECK_ONLY = "--check" in sys.argv


# term -> definition. Written in the same register as the chapters: plain,
# concrete, naira where it helps, and ending on why it matters or what people
# get wrong — because a definition that stops at the meaning is a dictionary
# entry, and this is meant to teach.
GLOSSARY = {
"accrual":
 "A cost you have incurred but not yet been invoiced for, entered so it lands in the month that used it. December's electricity, consumed in December and billed in January, belongs in December. Somebody has to estimate the amount, which is why an accrual set too low flatters this month and punishes the next.",

"prepayment":
 "The mirror of an accrual: money paid in advance for something you have not yet consumed. A year's insurance paid in January is not a January cost — eleven twelfths of it sits on the balance sheet and moves into the P&L month by month as it is used up.",

"provision":
 "An amount set aside for something expected but not certain — that some customers will not pay, that a warranty will be claimed, that a dispute will be lost. It reduces both profit and the asset it relates to. It is the most judgement-heavy line in a set of accounts, and therefore the most useful one to ask about.",

"write-off":
 "The point at which an estimate becomes an admission: this stock is gone, this customer will not pay. It lands in one month and usually describes deterioration that happened across many, which is why the useful question is not 'why this month' but 'how long was this true before anybody wrote it down'.",

"amortisation":
 "Depreciation for things you cannot touch — software licences, development costs, goodwill from an acquisition. The cost is spread across the years the thing is useful rather than charged entirely to the year it was bought. Same idea, different word, and the word changes only because the asset is intangible.",

"depreciation":
 "The way the cost of an asset is spread across the years it is used. Vehicles costing ₦24,000,000 over five years carry ₦4,800,000 a year. It is a real cost — the vehicles are genuinely being used up — but no money moves when it is charged, because the money left when they were bought. It sets nothing aside for replacement.",

"net book value":
 "What an asset shows on the balance sheet: its original cost less all the depreciation charged so far. Vehicles at ₦24,000,000 cost with ₦19,200,000 charged show ₦4,800,000. That is not what they are worth — it is how much of the original cost has yet to reach the P&L. Reading it as a valuation is the commonest error in this part of the accounts.",

"absorption":
 "The machinery that gets a share of overhead onto each product — total the overhead, pick a basis such as units or floor space, and apply the resulting rate. Useful for pricing and for valuing stock. Poor for deciding whether to accept an order or drop a line, because the overhead it loads on mostly would not change either way.",

"contribution":
 "Selling price less variable cost. It measures what a sale contributes toward the costs you are paying anyway — rent, salaries, power — and, once those are covered, toward profit. It is the right number for short-run decisions precisely because it excludes everything that does not change with the decision.",

"gross margin":
 "Gross profit as a percentage of revenue: what is left of each naira of sales after the goods themselves are paid for. On ₦60,000,000 of revenue and ₦39,000,000 of cost of sales, gross profit is ₦21,000,000 and margin is 35%. Not to be confused with markup, which is the uplift on cost and is always the larger-looking number.",

"markup":
 "The amount added to cost to reach a selling price, expressed as a percentage of the cost. Buy at ₦1,000, sell at ₦1,500, and the markup is 50% while the margin is 33%. Pricing for a 40% margin by adding 40% to cost actually achieves 29%, which is an expensive and very common mistake.",

"gearing":
 "How much of the business is funded by borrowing rather than by its owners. Borrowings of ₦80,000,000 against equity of ₦40,000,000 means twice as much of other people's money as your own. Gearing magnifies both good years and bad ones, so the right level depends on how volatile your trading is rather than on any standard ratio.",

"equity":
 "What the owners' stake amounts to: everything the business owns less everything it owes. It rises when the business earns and when owners put money in, and falls when it loses and when owners take money out. It is not what the business would sell for — it is book value, and book value is history.",

"retained earnings":
 "Every naira of profit the business has ever made and not paid out, accumulated since it began. This is the line that permanently connects the P&L to the balance sheet: each period's profit lands here, and each dividend or drawing leaves from here.",

"working capital":
 "The money tied up in running the business day to day: stock, plus what customers owe you, less what you owe suppliers. It is the funding your trading consumes before it returns anything, which is why growth absorbs cash and why a profitable business can still run short.",

"receivables":
 "Money customers owe you for goods already delivered — also called debtors. Every naira sitting here is a naira you have spent on goods and not recovered, so in effect you are lending it to your customers, sometimes while paying interest on an overdraft to do so.",

"payables":
 "What you owe suppliers for goods and services already received — also called creditors. It is the one large balance-sheet figure where bigger can be better: supplier credit is usually the cheapest funding a business will ever get, and every day of it is a day you do not need an overdraft.",

"cost of sales":
 "What the goods you actually sold cost you — not what you bought this month, and not what is sitting in the warehouse. Worked out as opening stock plus purchases less closing stock, which quietly assumes anything missing was sold. That assumption is why stock losses disappear into this line with no label attached.",

"gross profit":
 "Revenue less cost of sales: what is left after paying for the goods, before any of the costs of running the business. It describes the trading itself, which is why it is the first place to look when something has changed.",

"operating profit":
 "Gross profit less the costs of running the business. It deliberately excludes interest and tax, because neither is the operating manager's doing — so it answers whether the trading operation works, independently of how the business is financed.",

"net profit":
 "What is left after everything, including interest and tax. It answers what the owners actually made. Two units with identical operating profit can have very different net profit purely because one carries debt, which is a financing decision usually made above the operating manager.",

"EBITDA":
 "Earnings before interest, tax, depreciation and amortisation — operating profit with the non-cash charges added back. Popular because it approximates cash generated by trading, and misused because it flatters any business with heavy assets. It is not profit, and it is not what the owners keep.",

"cash cycle":
 "How long the business funds its own trading before the money comes back: stock days plus debtor days less creditor days. At 61 + 60 − 55 it is 66 days. This single number determines how much cash your growth will consume, which is why growing businesses run short more often than shrinking ones.",

"stock days":
 "How long stock sits before it sells, calculated as stock divided by cost of sales times 365. Stock of ₦30,000,000 on cost of sales of ₦180,000,000 is 61 days. Rising stock days means cash is converting into goods faster than goods are converting back into cash.",

"debtor days":
 "How long customers take to pay, calculated as receivables divided by revenue times 365. Receivables of ₦24,000,000 on revenue of ₦146,000,000 is about 60 days. Judge it against your terms: 60 days on 30-day terms means the business is financing its customers.",

"creditor days":
 "How long you take to pay suppliers, calculated as payables divided by cost of sales times 365. Rising creditor days can mean sharp treasury management or a business quietly running out of money, and the accounts cannot tell you which. The supplier can.",

"break-even":
 "The point at which contribution exactly covers fixed costs — where the business stops losing and has not yet started earning. Fixed costs of ₦5,200,000 at 28% contribution need ₦18,570,000 of revenue. It is a staircase rather than a single point, because fixed costs step as you grow.",

"margin of safety":
 "How far sales could fall before you reach break-even, usually as a percentage. A branch trading at ₦24,000,000 against a break-even of ₦18,570,000 has about 23%. Two branches earning identical profit with margins of safety of 40% and 8% are in entirely different positions, and only the second should worry you.",

"relevant cost":
 "A cost that actually changes because of the decision in front of you. It must be in the future, it must involve money moving, and it must differ between the options. Costs failing any of those three are noise, however large and however carefully calculated.",

"sunk cost":
 "Money already spent that cannot be recovered, and which is therefore irrelevant to every decision from now on. It is hard to ignore because abandoning feels like admitting it was wasted — so organisations protect the money already spent by spending more of it.",

"opportunity cost":
 "The value of what you give up by choosing one option instead of the best alternative. It never appears in any accounting system and is frequently the largest cost in a decision. A warehouse bay holding slow stock costs whatever fast-moving stock would have earned in it.",

"fixed cost":
 "A cost that does not move with sales — rent, most salaries, a security contract. It is fixed only within a relevant range: push volume past what your current premises or team can handle and it steps up. Knowing where your range ends is worth more than the classification itself.",

"variable cost":
 "A cost that moves roughly in proportion to activity — sales commission, card transaction fees, delivery fuel, packaging. Budgeting these as a rate per unit rather than a monthly lump is what lets a budget flex when volume differs from plan.",

"step cost":
 "A cost that holds flat and then jumps. One supervisor covers a shop up to a point, then you need a second. These are the costs that surprise people, because they behave exactly like fixed costs right up until they do not.",

"overhead":
 "Costs incurred for the business generally rather than for any particular product or branch — head office, insurance, the finance team, systems. Because they belong to nothing specific, they have to be shared out by a rule, and that rule is always a choice somebody made.",

"flexed budget":
 "A budget recalculated at the volume actually achieved, so the comparison is fair. A branch that budgeted ₦3,600,000 of variable cost on ₦18,000,000 of revenue should be measured against ₦4,400,000 when it delivers ₦22,000,000 — otherwise a good month is reported as an overspend.",

"variance":
 "The difference between what happened and what the budget said should happen. The total is the least useful part; splitting it into volume, price, mix and usage tells you what to do and, just as importantly, who to speak to. Favourable and adverse are arithmetic labels rather than judgements.",

"capital expenditure":
 "Money spent on things that will be used over several years — vehicles, equipment, premises, systems. The cash leaves at once while the P&L sees it slowly as depreciation, which is why a run of individually sensible capital decisions can leave a business unable to fund its trading.",

"payback":
 "How long a capital investment takes to return the money spent on it. A ₦9,000,000 vehicle saving ₦300,000 a month pays back in thirty months. Crude, ignores everything after payback and ignores the time value of money — and it is the number owners actually ask for, because it answers when the cash comes home.",

"covenant":
 "A condition attached to a loan or facility — a minimum cover ratio, a gearing limit, a restriction on further borrowing or on dividends. Breaching one can make the whole facility repayable even if every payment was made on time, and the decisions that breach covenants are exactly the ones taken without reading the facility letter.",

"current ratio":
 "Current assets divided by current liabilities: a rough test of whether what becomes cash within a year covers what falls due within a year. Below 1 does not guarantee failure, but it does mean the business is relying on something not yet on the page.",

"quick ratio":
 "The current ratio with stock stripped out, because stock becomes cash only after it sells and is then collected. For a stock-heavy retailer the two ratios can differ enormously, and the quick ratio is the honest one.",

"revaluation":
 "Restating an asset, usually property, at a higher current value. It raises assets and raises equity through a reserve rather than through profit — so nothing was earned and no cash arrived. When equity jumps, it is worth checking whether the business earned it or revalued it.",

"shrinkage":
 "Stock that has gone without being sold — theft, damage, expiry, miscounting. It never appears as a line called shrinkage: the cost-of-sales arithmetic treats anything missing as sold, so it arrives silently as a worse margin with no explanation attached.",

"cut-off":
 "Getting transactions into the right period at month-end. Goods received on the last day but entered on the first of the next month, or an invoice posted before the stock arrived, both distort the accounts. The signature is a margin that looks wrong one month and unusually good the next as the errors reverse.",

"materiality":
 "Whether a figure is large enough to change somebody's decision. It is what lets you ignore small variances sensibly rather than investigating everything — and a variance report that lists forty items is read as noise, losing the two that mattered among the thirty-eight that did not.",

"discounting":
 "Recognising that money arriving in the future is worth less than money today. At 25% a year, ₦1,000,000 arriving in three years is worth barely half its face value. It matters most in a high-rate market, where an appraisal that ignores it materially overstates any proposal whose benefits arrive late.",

"liquidity":
 "Whether you can meet what falls due — a question about timing rather than about wealth. A business can be entirely solvent, with assets comfortably exceeding liabilities, and still fail because the assets are stock and receivables while the obligations are payroll on Friday.",

"solvency":
 "Whether the business owns more than it owes over the long run. Distinct from liquidity: solvency is about the size of the hole, liquidity is about whether you can pay this week. Businesses fail from the second far more often than from the first.",

"capital allowance":
 "The deduction tax law permits for spending on assets, which replaces accounting depreciation when taxable profit is computed. It runs on a different schedule and to different rules, which is one reason the tax charge in the accounts rarely equals the tax paid in the same period.",
}

# terms whose name is essentially the chapter's subject: skip in that chapter
TITLE_WORDS = {t: set(re.findall(r"[a-z]+", t)) for t in GLOSSARY}


def terms_for(title, html):
    text = re.sub(r"<[^>]+>", " ", html).lower()
    tl = title.lower()
    found = []
    for term in GLOSSARY:
        if term in tl:                       # the chapter is about it already
            continue
        pos = text.find(term)
        if pos >= 0:
            found.append((pos, term))
    found.sort()
    return [t for _p, t in found[:MAX_PER_CHAPTER]]


def panel(terms):
    rows = "".join(
        '<p><b>%s.</b> %s</p>' % (t[0].upper() + t[1:], GLOSSARY[t]) for t in terms
    )
    return (
        '\n%s\n<div class="lexi"><b>The words used here</b>%s</div>' % (MARKER, rows)
    )


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    total_terms = 0
    added = 0
    report = []
    for key, mod in data.items():
        for l in mod["lessons"]:
            if MARKER in l["html"]:
                continue
            terms = terms_for(l["title"], l["html"])
            if not terms:
                report.append("   %-46s no terms" % l["title"][:46])
                continue
            total_terms += len(terms)
            added += 1
            if not CHECK_ONLY:
                l["html"] = l["html"].rstrip() + panel(terms)
            report.append("   %-46s %d: %s" % (l["title"][:46], len(terms), ", ".join(terms)))

    print("\n".join(report))
    print("\nchapters gaining a panel: %d | definitions placed: %d | glossary size: %d"
          % (added, total_terms, len(GLOSSARY)))

    if CHECK_ONLY:
        print("--check given; nothing written.")
        return

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"]))
            for m in data.values() for l in m["lessons"]]
    print("chapter mean now %d characters" % (sum(lens) / len(lens)))


if __name__ == "__main__":
    main()
