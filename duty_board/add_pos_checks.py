#!/usr/bin/env python3
"""Add check questions to the ZhiftPOS track.

The POS content was written by somebody who knows the product — it carries
detail (the stack/queue toggle, batch release in reverse order, the offline
sale's two reference numbers) that could not be inferred from a manual. What it
lacks is check questions: 0 across all 74 chapters, which fails the estate
standard in every module and is the single largest blocker to selling it.

These checks are derived strictly from what each chapter states. Nothing here
asserts product behaviour the chapter does not. Where a chapter is silent, the
check tests the reasoning rather than inventing a feature.

Written scenario-first, as the finance and control tracks settled on, so they
do not duplicate the exam bank.

Idempotent: a chapter that already has checks is left alone.

Run from the app package directory:  python3 add_pos_checks.py
"""

import collections
import io
import json
import os
import random
import re
import sys

DATA = "academy_pos_pro_data.json"
CHECK_ONLY = "--check" in sys.argv
# --force refreshes chapters that already have checks, so a corrected rationale
# in this file can reach the data rather than being skipped as already done
FORCE = "--force" in sys.argv

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}


# module key -> chapter index (0-based) -> three checks
CHECKS = {
"concessions_returns": {
 0: [
  C("Why do discounts and returns belong in one module?",
    ["Both are rare", "Both are exceptions to normal arithmetic, both use Power Approvers, both require reasons and leave a record",
     "Both are handled by supervisors", "Both affect stock"], 1,
    "They also share the same risk: the exception path is where margin quietly disappears."),
  C("ZhiftPOS does not try to eliminate exceptions because:",
    ["They are too frequent", "A shop that can never bend loses customers it should keep",
     "Cashiers would resist", "The system cannot prevent them"], 1,
    "It makes every exception recorded and attributable instead."),
  C("An exception missing one of its five parts — what, who asked, who approved, why, and the record — is:",
    ["Acceptable if the amount is small", "The finding",
     "A training matter only", "Corrected at month end"], 1,
    "The missing part is precisely what the control existed to capture.")],
 1: [
  C("A cashier enters a discount amount larger than the line's rate. The till:",
    ["Applies it and shows a negative price", "Caps it — an amount cannot exceed the rate, so a price can never go negative",
     "Requests approval", "Rounds it to zero"], 1,
    "Percentage is capped at 100 for the same reason."),
  C("In approval-based mode the discount reason and the typed explanation:",
    ["May be left blank when the queue is busy", "Neither can be left blank",
     "Are required only above a value", "Are added by the approver"], 1,
    "The reason is stored on the sale line and appears in markdown reporting."),
  C("The point of storing the reason on the line is that month-end figures show:",
    ["How much was discounted", "Not just how much was discounted, but why",
     "Which cashier discounted most", "The approval rate"], 1,
    "Which is what makes the markdown report answerable rather than merely large.")],
 2: [
  C("A markdown reason list has grown to thirty entries. Under queue pressure cashiers will:",
    ["Choose carefully, given the precision", "Pick the first plausible entry, and categories blur",
     "Ask a supervisor", "Leave it blank"], 1,
    "The design target is a reason a cashier can pick in two seconds and have it be true."),
  C("Five short non-overlapping reasons beat thirty precise ones because the reporting:",
    ["Is shorter", "Actually answers something",
     "Runs faster", "Needs fewer approvers"], 1,
    "A long list of precise reasons produces useless data."),
  C("Each reason carries a budget percentage, which turns the markdown report into:",
    ["A total", "A comparison of planned against actual",
     "An approval log", "A cashier ranking"], 1,
    "Which is what lets a number point at a cause.")],
 3: [
  C("An electronics discount request is raised at the Ikeja branch. It routes to:",
    ["The Ikeja branch manager", "The category lead who owns electronics margin, whichever branch it came from",
     "The regional supervisor", "Whoever is available"], 1,
    "Approval authority follows the goods, not the location."),
  C("A cashier requests 15% and the category lead grants 10%. This is:",
    ["A rejection", "An approval with the amount changed",
     "A referral", "An error requiring a new request"], 1,
    "The lead can approve while altering the amount, and the outcome is recorded either way."),
  C("Under code-based mode, a cashier may:",
    ["Type a discount directly if the queue is long", "Not type discounts at all — request, wait, then apply the code",
     "Apply a code twice on one line", "Discount a coded line further"], 1,
    "A coded line cannot be discounted again.")],
 4: [
  C("A promotion's status is Active but today falls outside its Valid From and Valid To window. The till:",
    ["Applies it, since it is Active", "Ignores it",
     "Applies it with approval", "Warns the cashier"], 1,
    "Campaigns end by calendar, not by somebody remembering to switch them off."),
  C("A bonus item added by a promotion can be:",
    ["Discounted further at the till", "Neither edited nor discounted at the till",
     "Removed independently", "Repriced by an approver"], 1,
    "Promotions are decided once, centrally, and cannot be remembered generously."),
  C("A promotion's title and description should be written for:",
    ["The marketing calendar", "The counter, because cashiers see both",
     "The back office", "The audit trail"], 1,
    "They appear where the sale is happening, so they have to make sense there.")],
 5: [
  C("A rate edit differs from a discount because:",
    ["It requires no approval", "A discount is limited by the price; a rate edit replaces the price",
     "It applies to the whole cart", "It is invisible on review"], 1,
    "Which is why Require Override for Rate Edit is recommended wherever rate editing is allowed."),
  C("A cashier's sales regularly carry Rate override markers. This indicates:",
    ["Careful pricing", "Prices being set by memory — the habit the price list exists to end",
     "A promotion problem", "A profile misconfiguration"], 1,
    "Rate-edit frequency per cashier is worth checking weekly."),
  C("The Rate override marker on an edited line is:",
    ["Cleared on completion", "Permanently visible on review",
     "Visible only to approvers", "Removed by the approval"], 1,
    "Deliberately, because a replaced price is the strongest exception at the counter.")],
 6: [
  C("A customer wants a refund and has no receipt or reference of any kind. The console:",
    ["Allows a goodwill return", "Offers no path — no invoice, no return",
     "Permits it with an override", "Searches by customer name"], 1,
    "That wall is what stands in front of the phantom-return fraud."),
  C("An offline sale is being returned. It can be found by:",
    ["The back-office invoice number only", "Its local reference as well as the back-office number",
     "Neither, until it posts", "The customer record"], 1,
    "The local reference and the back-office number both identify it, so a return can be found using either one."),
  C("The invoice summary shows whether the sale is inside the return window. Reading it first:",
    ["Delays the conversation", "Tells you whether this is routine or needs a beyond-window override, before the conversation goes further",
     "Is only relevant for refunds", "Is the approver's job"], 1,
    "Reading the window flag early tells you whether this is routine or needs a beyond-window override.")],
 7: [
  C("Expiring-stock markdowns run at double budget, and eleven approvals all trace to one supplier's short-dated deliveries. The finding belongs to:",
    ["The cashiers", "Purchasing, with the report attached",
     "The branch manager", "The approver"], 1,
    "The budget comparison operating as designed — the number pointed at a cause."),
  C("One cashier's goodwill explanations read 'customer asked' three times in a month. Because the explanations exist, this becomes:",
    ["A disciplinary matter", "A five-minute coaching conversation about writing useful ones",
     "An approval review", "A markdown reason change"], 1,
    "The record made a small problem visible while it was still small."),
  C("The quarter's review took twenty minutes to break down a finding because:",
    ["The volumes were low", "The reasons and explanations were captured on each line",
     "One supplier was involved", "The budget was set correctly"], 1,
    "Without the reason on the line, the same review is an investigation.")],
 8: [
  C("Which cannot be discounted at the till?",
    ["Any line above a value", "Bonus items, promoted lines, coded lines, voucher lines and bundle components",
     "Lines with a customer attached", "Lines added by search"], 1,
    "Hover the greyed control for the reason it is unavailable."),
  C("A discount with no reason, a return with no invoice, and an override with no approver share:",
    ["Different causes", "A missing part of the five-part record, which is the finding in each case",
     "The same approver", "A profile setting"], 1,
    "Every exception records what, who asked, who approved, why, and the record itself."),
  C("Writing a markdown explanation, the audience to write for is:",
    ["The approver at the time", "Somebody who was not there",
     "The month-end report", "The cashier's own recollection"], 1,
    "Pick the true reason and write so it is still useful in three months.")],
},
"extended_counters": {
 0: [
  C("Lay-By carries two exposures at once, which are:",
    ["Credit risk and stock loss", "The customer's money held, and the customer's goods out of the sellable pool",
     "Deposit and instalment risk", "Fraud and shrinkage"], 1,
    "Look past the service and name the money: it is a financial arrangement."),
  C("An airtime voucher is best understood as:",
    ["A consumable item", "Prepaid stock whose entire value is a code",
     "A service line", "A payment method"], 1,
    "That one fact drives every rule about how it is sold."),
  C("Staff Purchase is, in financial terms:",
    ["A discount scheme", "Employee credit — the business lending against future wages",
     "A payroll deduction", "A loyalty benefit"], 1,
    "With a limit, a running balance, and repayment through payroll.")],
 1: [
  C("A lay-by is created for a customer who prefers not to give a phone number. You should:",
    ["Proceed — the deposit secures it", "Not proceed anonymously; the arrangement needs follow-up and the number is how it happens",
     "Record the address instead", "Ask a supervisor to override"], 1,
    "Read the number back or ring it once at entry."),
  C("Goods reserved on a lay-by are:",
    ["Untracked until collection", "Still tracked goods — batch and serial entry applies as in a normal sale",
     "Removed from the system", "Held outside stock"], 1,
    "Reserved goods are still tracked goods, so batch and serial entry applies exactly as in a normal sale."),
  C("The instalment schedule is created:",
    ["When the first instalment falls due", "On payment of the deposit, from the profile's instalment count and spacing",
     "Manually by the cashier", "At the customer's request"], 1,
    "The required deposit itself comes from the profile's Lay-By Deposit percentage.")],
 2: [
  C("The Open Lay-Bys panel should be read as:",
    ["A sales report", "An ageing list — the overdue instalments are the work",
     "A stock listing", "A customer directory"], 1,
    "Check it weekly and follow up overdue instalments by phone from the recorded number."),
  C("A lay-by left silent for months produces:",
    ["An automatic termination", "Goods held for somebody unreachable, a deposit nobody can match to a person, and stock in limbo",
     "A write-off", "A completed sale"], 1,
    "Which is why the weekly panel check exists."),
  C("A customer pays half an instalment. The schedule:",
    ["Rejects it", "Records it as partly paid",
     "Applies it to the final instalment", "Requires approval"], 1,
    "Payments in any workable pattern are fine — two at once, or half of one.")],
 3: [
  C("Before anything is added to a staff purchase, the employee sees:",
    ["Only the item prices", "Their purchase limit, current exposure, remaining balance and estimated monthly repayment",
     "The staff discount rate", "Their payroll record"], 1,
    "The employee sees their own position before committing to anything."),
  C("Where the profile sets a staff discount percentage and a company-wide rate also exists:",
    ["The company rate applies", "The profile percentage takes precedence at this counter",
     "The higher applies", "The cashier chooses"], 1,
    "The discount applies automatically to every line."),
  C("On completion, a staff purchase is booked to the employee purchase account and:",
    ["Settled in cash", "Scheduled for recovery",
     "Held pending approval", "Recorded as a discount"], 1,
    "Employee credit with the controls built in — limit, visible balance, automatic recovery.")],
 4: [
  C("A customer pays for airtime, the slip prints, and they leave without taking it. The code is:",
    ["Recoverable and resellable", "Consumed — it was revealed from stock when the sale completed",
     "Voided automatically", "Held for reissue"], 1,
    "Consumed on issue, whether or not the paper reached the customer's hand."),
  C("The airtime console will not sell more than the denomination's available quantity because:",
    ["Of a profile cap", "Airtime is inventory, and it will not sell codes it does not hold",
     "Carriers limit volume", "Approval is required above a quantity"], 1,
    "Availability is shown at the point of choosing the amount."),
  C("Each airtime voucher prints:",
    ["Grouped on the sale receipt", "On its own slip with its recharge code",
     "As a reference to be redeemed later", "Only on request"], 1,
    "One slip per code, and printed before the customer leaves.")],
 5: [
  C("A customer has lost their receipt for an offline sale. In Sales History it is found by:",
    ["The invoice number only, once posted", "Its local reference, just as posted sales are found by their invoice number",
     "Customer name only", "Neither — offline sales are excluded"], 1,
    "A lost receipt is a one-minute lookup, not a dead end."),
  C("Scanning the day's Sales History, you need to be sure a large entry is not a refund. You can tell because:",
    ["Refunds appear in a separate console", "Returns carry a Return label, so they are never mistaken for sales",
     "Refunds show a negative total only", "Refunds are excluded from the list"], 1,
    "Any entry opens to its lines and payments if you need to look further."),
  C("The cashier and shift filters make Sales History the starting point for:",
    ["Reprinting receipts", "Supervisory review",
     "Stock enquiries", "Customer creation"], 1,
    "Any entry opens to its lines and recorded payments.")],
 6: [
  C("The Inventory tab shows a synchronising marker. This tells you the figure on screen is:",
    ["Incorrect", "The local copy's number, currently being updated",
     "A forecast", "The other branch's number"], 1,
    "Counters summarise items in stock, low on stock and out of stock."),
  C("A customer asks whether an item is at the other branch. Where the profile permits it, this is answered:",
    ["By calling the branch", "From the chair, by filtering the Inventory tab by warehouse",
     "Only by the back office", "Through a material request"], 1,
    "The is-it-at-the-other-branch question answered without leaving the counter."),
  C("A material request must specify the requesting warehouse, the source warehouse, the items and:",
    ["An approver", "A priority — low, medium, high or urgent",
     "A due date", "A cost centre"], 1,
    "It is how the counter asks another location for stock.")],
 7: [
  C("A lay-by goes two instalments overdue, two calls to the recorded number go unanswered, and it is terminated. The refundable portion was:",
    ["Refunded in cash", "Routed to store credit, because cash refunds were still off",
     "Retained in full", "Held pending contact"], 1,
    "Termination ran by the book: manager credentials at the gate, goods back to stock the same hour, record intact."),
  C("The forfeiture policy at Okelewo was decided:",
    ["When the first dispute arose", "Before launch, and printed on every schedule",
     "By the manager case by case", "At termination"], 1,
    "Deciding it before the first dispute is what makes it a policy rather than an argument."),
  C("The overdue lay-by was found by:",
    ["A customer complaint", "The weekly panel check",
     "The month-end report", "The termination run"], 1,
    "The routine caught it on schedule, which is the point of putting it on a calendar.")],
 8: [
  C("What do all the extended counters have in common?",
    ["They are optional", "No side books — everything posts into the same system",
     "They require supervisor access", "They are used weekly"], 1,
    "Each is a financial arrangement run with the controls its money deserves."),
  C("A lay-by instalment can carry which statuses?",
    ["Open or closed", "Unpaid, partly paid, paid or overdue",
     "Pending or settled", "Active or terminated"], 1,
    "Each instalment carries its due date, amounts, balance and status."),
  C("Which habit protects a lay-by arrangement from the classic mess?",
    ["Taking a larger deposit", "Verifying the phone number, separating the goods physically, and printing the schedule",
     "Shortening the instalment count", "Requiring supervisor approval"], 1,
    "Goods held for somebody unreachable is what happens when those are skipped.")],
},
"voucher_programme": {
 0: [
  C("From the moment a card is sold, its value is:",
    ["Revenue", "Money the business owes, until the card is spent or expires",
     "A deferred discount", "A contingent asset"], 1,
    "Everything else in the module — the accounts, the activation gate, the printing rules — follows from that."),
  C("A ₦5,000 card is sold. Anyone holding that card can spend it in your stores, which means the business is carrying:",
    ["A marketing cost", "An obligation to an unknown bearer",
     "A deferred sale", "A customer deposit"], 1,
    "The holder rather than the buyer is who can spend it, and that is what makes tracking every card necessary."),
  C("The Voucher Console keeps a record of every card:",
    ["From sale to redemption", "From creation to final redemption",
     "For the validity period only", "While a balance remains"], 1,
    "Including cards that were created and never sold.")],
 1: [
  C("A batch of complimentary cards is stolen before activation. The cards are:",
    ["Redeemable at face value", "Worthless until somebody with authority switches them on",
     "Automatically voided", "Redeemable at half value"], 1,
    "That is precisely what the activation gate is for."),
  C("A sellable card's validity clock starts:",
    ["At creation", "At the sale", "At activation", "At first redemption"], 1,
    "A complimentary card's clock starts at activation instead."),
  C("A colleague asks why complimentary cards cannot simply be handed out on creation. The answer is that:",
    ["They have no serial number yet", "Until activation a batch is potential money that cost nothing to make",
     "The design is incomplete", "The accounts are not yet posted"], 1,
    "No money changed hands, which is exactly why authority is required to make them live.")],
 2: [
  C("A customer buys a ₦5,000 gift card. The liability account is:",
    ["Debited ₦5,000", "Credited ₦5,000, recording what the business now owes",
     "Unaffected until redemption", "Credited net of tax"], 1,
    "It must be a liability-type account belonging to the company."),
  C("The promotional expense account is left blank. Complimentary redemptions then:",
    ["Fail to post", "Fall back to the liability account — it works, but the books are less clear",
     "Post to revenue", "Are held in suspense"], 1,
    "Naming the expense account is the clearer arrangement."),
  C("Setup should be completed:",
    ["After the first batch is generated", "Before the first card is created",
     "At the first redemption", "At month end"], 1,
    "Because a sold voucher is money owed and the sale has to post somewhere correct.")],
 3: [
  C("The right half of every printed card carries:",
    ["The branded panel", "A standard information panel — usage notes, barcode, written code, serial and validity",
     "The recipient's name", "The issuing branch"], 1,
    "The left half is the branded panel configured per company."),
  C("With a custom design supplied, the console still inserts:",
    ["Nothing — the artwork is used as supplied", "Each card's live details, so one design serves every value and both kinds",
     "Only the barcode", "The company logo"], 1,
    "Which is what stops a separate design being needed per denomination."),
  C("Guided design asks for two taglines because:",
    ["One is a fallback", "Gift cards and complimentary cards each need their own",
     "One is for the back of the card", "Languages differ by branch"], 1,
    "The console then picks the correct one per card.")],
 4: [
  C("You activate 120 cards of a 500-card batch for this month's campaign. The remaining 380 are:",
    ["Voided", "Inert stock, activatable later",
     "Automatically activated at month end", "Returned to the batch pool"], 1,
    "Partial activation is a normal choice rather than an exception."),
  C("Recording issued-to and reason on a complimentary card means those notes are:",
    ["Held in the console only", "Kept on the record and printed on the card itself",
     "Visible to the recipient only", "Cleared on redemption"], 1,
    "A card naming its recipient and purpose is easy to question if it turns up elsewhere."),
  C("On activation the system records:",
    ["The batch number only", "You as the approver, with issue and expiry dates set",
     "The intended recipient", "The campaign code"], 1,
    "Which is what makes the activation log readable against the campaign plan.")],
 5: [
  C("A customer's emailed voucher copy never arrives. It can be:",
    ["Reissued as a new card", "Re-sent from that sale's record",
     "Printed only at the original till", "Recovered from the batch"], 1,
    "The card itself is unaffected — only the delivery failed."),
  C("Blank cards issued at a till during the day are grouped into the day's till batch so that:",
    ["They share a design", "Cards issued today can be reconciled against voucher payments taken today",
     "They expire together", "They can be voided as a group"], 1,
    "That daily check sits on the closing routine."),
  C("A pre-printed card is scanned at payment. The sale marks it Sold and:",
    ["Starts its validity from that day", "Starts its validity from creation",
     "Leaves validity unset", "Extends the original validity"], 1,
    "Which is the difference between a sellable card and a complimentary one.")],
 6: [
  C("A gift card sale is not revenue and carries no sales tax because:",
    ["Vouchers are exempt", "Revenue and tax arrive when goods leave, not when the promise was bought",
     "The tax is charged at activation", "It is a balance sheet transfer"], 1,
    "Event 1 records cash in and credits the liability."),
  C("A customer redeems a card against goods. The liability is:",
    ["Unchanged until expiry", "Reduced by the amount spent, with the sale and its tax recognised on the goods",
     "Written off", "Transferred to revenue in full"], 1,
    "The promise is being settled as the goods leave."),
  C("A complimentary card is redeemed. Its cost is recognised:",
    ["At creation", "As promotional expense at the point of redemption",
     "At activation", "Never — no money came in"], 1,
    "In the account named in Setup, or the liability account if none was named.")],
 7: [
  C("A cluster of already-redeemed errors at the counter suggests:",
    ["Expired cards", "Duplicate issue — two customers holding one balance",
     "A printing fault", "Network failure"], 1,
    "Enforce Voucher Booking reserves each code centrally before issue, which is the control."),
  C("The monthly check against unauthorised activation is:",
    ["Counting the batches", "Reading the activation log against the campaign plan",
     "Reconciling the liability account", "Reviewing redemption rates"], 1,
    "Every activated batch should match a known giveaway, and every activation carries its approver's name."),
  C("The voucher programme's risks are described as specific because vouchers are:",
    ["High value", "Portable value",
     "Difficult to track", "Sold infrequently"], 1,
    "Each risk has a built-in control and a check that takes minutes.")],
 8: [
  C("Which voucher state is permanent and stays on record?",
    ["Expired", "Void", "Redeemed", "Partially redeemed"], 1,
    "The six states are Available, Sold, Partially redeemed, Redeemed, Expired and Void."),
  C("Every card keeps, for life:",
    ["Its issued-to note", "A balance and a serial number",
     "Its original design", "Its activation approver"], 1,
    "Which is what makes a card answerable years after it was created."),
  C("The separation the programme depends on is between:",
    ["Branches", "Creating, handling and accounting",
     "Sellable and complimentary", "Console and till"], 1,
    "Voucher Manager runs the console; counter staff work at the till only.")],
},
"shift_sale": {
 0: [
  C("You have not signed in on this terminal for nine days and the server is unreachable. Offline sign-in will:",
    ["Work — the record is stored permanently", "Refuse, because the stored record covers only the last seven days",
     "Work but tag your sales", "Prompt for a password reset"], 1,
    "Sign in online at least weekly on every terminal you use, or an outage locks you out at the worst time."),
  C("A manager signs you in on their credentials because the terminal has no record of you. The sales in that session are:",
    ["Recorded against the manager", "Tagged for audit, and you are told so at the time",
     "Held until you sign in", "Excluded from the shift"], 1,
    "The tagging is disclosed rather than hidden, which is what makes it an acceptable fallback."),
  C("You have forgotten your password and the terminal is offline. You can:",
    ["Reset by email as normal", "Not reset it — the terminal must be online for a reset",
     "Use offline sign-in with any password", "Clear the stored record"], 1,
    "Which is another reason the weekly online sign-in habit matters.")],
 1: [
  C("The float should be ₦20,000 so you enter 20,000 without counting. The drawer actually holds ₦19,400. Your perfect day will end:",
    ["Balanced", "₦600 short, investigating a shortage that never happened",
     "₦600 over", "Unaffected, since the opening is only a reference"], 1,
    "The opening amount is what the closing count is measured against."),
  C("Entering a typed round float rather than a counted one, habitually, causes:",
    ["Faster opening with no cost", "Real shortages to hide inside the always-a-bit-off habit",
     "The system to reject the shift", "Variances to be waived"], 1,
    "Thirty seconds of counting buys an evening of certainty."),
  C("The float is genuinely short and you record it in the opening note. That note makes the shortfall:",
    ["Disappear from the variance", "Context — it is explained at the point it was found",
     "The previous shift's problem", "A closing adjustment"], 1,
    "The same shortfall discovered at close, unexplained, is a very different conversation.")],
 2: [
  C("A customer is still talking as you scan. The search box is not selected. The scan will:",
    ["Be lost", "Go straight into the cart — no focus is needed",
     "Require you to click first", "Open the search results"], 1,
    "Which is why scanning works mid-conversation."),
  C("Each unit of an item needs its own serial entry. The toggle beside the search box should be set to:",
    ["Stack", "Queue", "Either — it makes no difference", "Auto"], 1,
    "Stack increases an existing line; queue gives every scan its own line."),
  C("You have typed a new quantity into a line but not pressed Enter, and you move on. The quantity:",
    ["Applies automatically", "Is not applied — a half-typed quantity rides through to payment",
     "Reverts and warns you", "Blocks the sale"], 1,
    "Enter applies, Escape abandons. Use the keys.")],
 3: [
  C("Auto-allocate has picked the oldest batch, but you physically took stock from the front of the shelf. You should:",
    ["Leave it — the system knows best", "Click the Batch assigned marker and correct the selection",
     "Reduce and re-add the line", "Note it at close"], 1,
    "Expiry tracking only works when the record and the bag agree."),
  C("You reduce the quantity on a line allocated across two batches. Allocations are released:",
    ["Oldest first", "In reverse order — the last-allocated batch is released first",
     "Proportionally", "Only on removal of the whole line"], 1,
    "Which matters when you are correcting a partly built line rather than starting again."),
  C("A quantity cannot be covered from a single batch and auto-allocate is on. The till:",
    ["Refuses the line", "Asks you, rather than allocating silently",
     "Splits it evenly", "Uses the newest batch"], 1,
    "Auto-allocate handles the ordinary case and defers to you at the boundary.")],
 4: [
  C("A new customer's mobile number matches an existing record. The till:",
    ["Creates a duplicate", "Merges the new entry into the existing record automatically",
     "Refuses the mobile number", "Asks the cashier to choose"], 1,
    "One of two protections that keep the customer list usable."),
  C("A customer has a discount recorded on their record. Attaching them to the sale:",
    ["Requires you to apply the discount manually", "Applies it to the cart automatically, with a Customer discount marker",
     "Prompts for approval", "Affects only future sales"], 1,
    "Recorded policy, applied automatically rather than remembered by the cashier."),
  C("The queue is busy and the sale involves loyalty. The customer should be attached:",
    ["After payment", "Before scanning items", "At the receipt stage", "Only if they ask"], 1,
    "Attaching afterwards means the benefits that depend on the customer were not applied while the cart was built.")],
 5: [
  C("A customer steps away to fetch their wallet. The basket has batch and serial work already done. You should:",
    ["Clear it and rebuild", "Hold it — a hold keeps customer, discounts and batch allocations",
     "Complete it and refund", "Leave it on screen"], 1,
    "Clearing throws away work already done, and hold is the honest habit for a reason."),
  C("Building a basket, taking cash, then clearing it is:",
    ["An efficient correction", "A known fraud pattern, which is why cleared carts are recorded and reviewed",
     "Permitted for supervisors", "Prevented by the system"], 1,
    "Cleared carts are recorded and reviewed precisely because of it, which is why the honest habit is simply to hold."),
  C("Your profile does not permit you to clear, but the Clear button is visible. This means:",
    ["The profile is misconfigured", "An approver holds the permission, and clearing will require approval",
     "Clearing is disabled entirely", "You may clear with a note"], 1,
    "The button appears; the authority sits with somebody else.")],
 6: [
  C("A customer questions an offline receipt with an unfamiliar local reference. You should say:",
    ["It will be reissued when the system is back", "It is a fully valid document, and the sale also receives a back-office number when it posts",
     "It is a provisional record", "It cannot be used for a return"], 1,
    "Both numbers refer to the same sale, and a return can be found using either."),
  C("You are selling pre-printed gift voucher stock. Each physical card must be:",
    ["Left blank — codes generate on completion", "Scanned, so its code binds to the value",
     "Recorded in the closing note", "Activated by a supervisor"], 1,
    "System-issued vouchers are the opposite case: leave codes blank."),
  C("A named customer on a gift voucher sale is:",
    ["Optional, as for any sale", "Required, because the voucher may need emailing or reprinting later",
     "Only needed above a value", "Added by the back office"], 1,
    "It is the one sale type where the walk-in default will not do.")],
 7: [
  C("The close window pre-fills each payment method with the expected figure. Accepting them untouched:",
    ["Saves time with no cost", "Confirms the system against itself and proves nothing about the drawer",
     "Is correct where there is no variance", "Is required before counting"], 1,
    "The pre-fill is the system's expectation, not a count."),
  C("You are ₦200 over and suspect a change error on a busy split sale around 4pm. You should:",
    ["Adjust the count to balance", "Record that explanation in the closing notes",
     "Leave it for the back office", "Carry it into tomorrow's float"], 1,
    "One sentence at close is far cheaper than the same variance investigated days later when nobody remembers."),
  C("Variance is shown beside each method in green and red. Green indicates:",
    ["Short", "Over", "Within tolerance", "Unexplained"], 1,
    "Both directions matter — an over is as much a process signal as a short.")],
 8: [
  C("Duty shows Inactive and a customer is waiting. Selling anyway produces:",
    ["A normal sale", "Orphaned sales needing the back-office repair tool",
     "A queued sale", "An automatic shift open"], 1,
    "Never sell with Duty Inactive — opening takes two minutes and the repair does not."),
  C("A handover mid-day between two cashiers requires:",
    ["One continuous shift", "Two shifts and two counts",
     "A note in the closing field", "A manager override"], 1,
    "Each person's takings are measured against their own opening count."),
  C("The Re-login indicator against a cashier means:",
    ["They must change password", "Their queued sales cannot post until they sign in online",
     "Their shift is unclosed", "Their session expired"], 1,
    "Queued alone is safe and posts automatically; Re-login is the one that needs somebody to act.")],
},
}


def rebalance(items, seed):
    """Spread correct answers evenly across A-D by rotating each option list.

    The first run of this script produced 27 of 27 answers in position B — the
    same author bias that made the first draft of the finance bank 72 percent
    guessable. The rebalance was folded into every BUILDER after that and this
    is a repair script, so it arrived without one. Deterministic seed, so the
    output is reproducible.
    """
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
    for mod_key, chapters in CHECKS.items():
        flat = [c for _i, ch in sorted(chapters.items()) for c in ch]
        rebalance(flat, "pos:%s:checks" % mod_key)
    added = skipped = 0
    for mod_key, chapters in CHECKS.items():
        if mod_key not in data:
            sys.exit("ABORT: module %r not in %s" % (mod_key, DATA))
        lessons = data[mod_key]["lessons"]
        # exam bank for this module, to prove the checks do not duplicate it
        bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip()
                for q in data[mod_key].get("questions") or []}
        for idx, checks in sorted(chapters.items()):
            if idx >= len(lessons):
                sys.exit("ABORT: %s has no chapter %d" % (mod_key, idx + 1))
            l = lessons[idx]
            if l.get("checks") and not FORCE:
                skipped += 1
                continue
            for c in checks:
                norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
                if norm in bank:
                    sys.exit("ABORT: check duplicates exam question: %s" % c["q"][:60])
            if not CHECK_ONLY:
                l["checks"] = [dict(c, sort=i) for i, c in enumerate(checks)]
            added += len(checks)

    print("checks to add: %d | chapters already done: %d" % (added, skipped))
    if CHECK_ONLY:
        print("--check given; nothing written.")
        return

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    tot = sum(len(l.get("checks") or []) for m in data.values() for l in m["lessons"])
    chs = sum(len(m["lessons"]) for m in data.values())
    done = sum(1 for m in data.values() for l in m["lessons"] if l.get("checks"))
    print("track now: %d of %d chapters have checks, %d checks total" % (done, chs, tot))
    sp = collections.Counter(c["ans"] for m in data.values()
                             for l in m["lessons"] for c in (l.get("checks") or []))
    print("check answer spread:", dict(sorted(sp.items())))


if __name__ == "__main__":
    main()
