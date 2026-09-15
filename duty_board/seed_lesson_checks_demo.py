# Paste into: bench --site xlevel.clouderp.one console
#
# Seeds three check questions onto ONE lesson so you can see the block render.
# Idempotent: re-running replaces the demo set rather than stacking duplicates.
# Set MODULE_TITLE to a course a test client is enrolled on, or set LESSON
# directly if you already know the lesson name.

MODULE_TITLE = None      # e.g. "Understanding Your Monthly Reports"
LESSON = None            # e.g. "a1b2c3d4e5" — overrides MODULE_TITLE when set

if not LESSON:
    if MODULE_TITLE:
        mod = frappe.db.get_value("Duty Training Module", {"title": MODULE_TITLE}, "name")
    else:
        # fall back to the first lesson of the first client-audience module
        mod = frappe.db.get_value("Duty Training Module", {"audience": "Client"}, "name")
    if not mod:
        raise Exception("No module found — set MODULE_TITLE.")
    LESSON = frappe.db.get_value(
        "Duty Lesson", {"module": mod}, "name", order_by="sort_order asc, creation asc"
    )
    if not LESSON:
        raise Exception("That module has no lessons.")

print("Seeding checks on lesson:", LESSON, "-", frappe.db.get_value("Duty Lesson", LESSON, "title"))

# clear any previous demo set for this lesson
for old in frappe.get_all("Duty Lesson Check", filters={"lesson": LESSON}, pluck="name"):
    frappe.delete_doc("Duty Lesson Check", old, force=1, ignore_permissions=True)

DEMO = [
    {
        "question": "A supplier invoice arrives for more than the purchase order. What should happen first?",
        "opt_a": "Pay it — the supplier knows their own prices",
        "opt_b": "Hold it as an exception and match it against the order and the receipt",
        "opt_c": "Amend the purchase order to agree with the invoice",
        "opt_d": "Post it to a suspense account and move on",
        "correct": "B",
        "rationale": "The three-way match exists precisely for this moment. Amending the order to fit "
                     "the invoice destroys the evidence that the price changed at all.",
    },
    {
        "question": "Why is a blind count sheet used during a full stock count?",
        "opt_a": "It is faster to print",
        "opt_b": "It stops the counter seeing the expected figure, so they count what is there",
        "opt_c": "It is required by the auditors",
        "opt_d": "It hides the item cost from casual staff",
        "correct": "B",
        "rationale": "Show someone the expected quantity and they will find it. A blind sheet measures "
                     "the shelf rather than the system.",
    },
    {
        "question": "Who should be able to approve a stock adjustment?",
        "opt_a": "Anyone with stock permissions, to keep the floor moving",
        "opt_b": "The person who found the variance, since they have the detail",
        "opt_c": "A named second person who did not raise the adjustment",
        "opt_d": "The branch manager only, in every case",
        "correct": "C",
        "rationale": "Self-adjustment is the single most common route to concealed shrinkage. Two names, "
                     "and never the same one twice.",
    },
]

for i, q in enumerate(DEMO):
    doc = frappe.new_doc("Duty Lesson Check")
    doc.lesson = LESSON
    doc.sort_order = i + 1
    doc.active = 1
    for k, v in q.items():
        setattr(doc, k, v)
    doc.insert(ignore_permissions=True)

frappe.db.commit()
print("Created", len(DEMO), "checks. Reopen that lesson in the portal.")
