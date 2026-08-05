# Copyright (c) 2026, Zhift Platforms Ltd
# Client Document — check-out / check-in controller for Duty Board Document Hub

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime, time_diff_in_hours
from duty_board.permissions import require_staff

FORCE_RELEASE_ROLES = {"System Manager", "Duty Board Manager"}


class ClientDocument(Document):
    def after_insert(self):
        log_activity(self.name, "Created", details=f"Document created: {self.title}")

    def validate(self):
        if cint(self.is_financial_statement):
            if not self.statement_type:
                frappe.throw(_("Choose the statement type."))
            if not self.period_year:
                frappe.throw(_("Period year is required for a financial statement."))
            if self.statement_type == "Management Account" and not self.period_month:
                frappe.throw(_("Period month is required for a Management Account."))
            if self.statement_type == "Management Account" and not self.due_date:
                self.due_date = _default_due(self.period_month, self.period_year)
        # Protect checkout fields from being edited directly via the form
        if not self.is_new():
            before = self.get_doc_before_save()
            if before and before.status == "Checked Out" and self.status == "Checked Out":
                if (
                    self.checked_out_by != before.checked_out_by
                    or str(self.checked_out_at) != str(before.checked_out_at)
                ):
                    frappe.throw(
                        _("Checkout fields cannot be edited directly. Use Check In or Force Release.")
                    )


# ---------------------------------------------------------------------------
# Whitelisted API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def checkout(name):
    """Lock the document for the current user."""
    require_staff()
    doc = frappe.get_doc("Client Document", name)

    if doc.status == "Checked Out":
        frappe.throw(
            _("Already checked out by {0} since {1}.").format(
                frappe.bold(get_fullname(doc.checked_out_by)),
                frappe.format(doc.checked_out_at, {"fieldtype": "Datetime"}),
            )
        )

    doc.db_set(
        {
            "status": "Checked Out",
            "checked_out_by": frappe.session.user,
            "checked_out_at": now_datetime(),
        },
        notify=True,
    )

    log_activity(name, "Checked Out")
    notify_team(
        subject=_("Document checked out"),
        message=_("{0} checked out '{1}' ({2}).").format(
            get_fullname(frappe.session.user), doc.title, doc.client
        ),
        document=name,
        exclude_user=frappe.session.user,
    )

    return {"file_url": doc.latest_file, "version": doc.current_version}


@frappe.whitelist()
def checkin(name, file_url, change_note):
    """Upload a new version and release the lock."""
    require_staff()
    doc = frappe.get_doc("Client Document", name)

    if doc.status != "Checked Out":
        frappe.throw(_("This document is not checked out. Check it out first."))

    is_manager = FORCE_RELEASE_ROLES & set(frappe.get_roles())
    if doc.checked_out_by != frappe.session.user and not is_manager:
        frappe.throw(
            _("Checked out by {0}. Only they (or a manager) can check it in.").format(
                frappe.bold(get_fullname(doc.checked_out_by))
            )
        )

    if not file_url:
        frappe.throw(_("A file is required to check in."))
    if not (change_note or "").strip():
        frappe.throw(_("A change note is required. What did you change?"))

    new_version = (doc.current_version or 0) + 1

    doc.append(
        "versions",
        {
            "version_no": new_version,
            "file": file_url,
            "change_note": change_note.strip(),
            "uploaded_by": frappe.session.user,
            "uploaded_at": now_datetime(),
        },
    )
    doc.current_version = new_version
    doc.latest_file = file_url
    doc.status = "Available"
    doc.checked_out_by = None
    doc.checked_out_at = None
    doc.flags.ignore_validate = True
    doc.save(ignore_permissions=True)

    log_activity(name, "Checked In", details=f"v{new_version}: {change_note.strip()}")
    notify_team(
        subject=_("New version checked in"),
        message=_("{0} checked in v{1} of '{2}': {3}").format(
            get_fullname(frappe.session.user), new_version, doc.title, change_note.strip()
        ),
        document=name,
        exclude_user=frappe.session.user,
    )

    return {"version": new_version}


@frappe.whitelist()
def force_release(name, reason=None):
    """Manager override: release a stuck checkout without a new version."""
    require_staff()
    if not (FORCE_RELEASE_ROLES & set(frappe.get_roles())):
        frappe.throw(_("Only a manager can force-release a document."))

    doc = frappe.get_doc("Client Document", name)
    if doc.status != "Checked Out":
        frappe.throw(_("This document is not checked out."))

    previous_holder = doc.checked_out_by

    doc.db_set(
        {"status": "Available", "checked_out_by": None, "checked_out_at": None},
        notify=True,
    )

    details = f"Released from {previous_holder}"
    if reason:
        details += f" — {reason}"
    log_activity(name, "Force Released", details=details)

    # Tell the person who had it
    notify_team(
        subject=_("Your checkout was released"),
        message=_("'{0}' was force-released by {1}. Any local changes were NOT saved to the hub.").format(
            doc.title, get_fullname(frappe.session.user)
        ),
        document=name,
        only_users=[previous_holder],
    )

    return {"released_from": previous_holder}


@frappe.whitelist()
def restore_version(name, version_no):
    """Promote an old version's file as a brand-new version (non-destructive)."""
    require_staff()
    doc = frappe.get_doc("Client Document", name)

    if doc.status == "Checked Out":
        frappe.throw(_("Cannot restore while checked out. Check in or release first."))

    version_no = int(version_no)
    source = next((v for v in doc.versions if v.version_no == version_no), None)
    if not source:
        frappe.throw(_("Version {0} not found.").format(version_no))

    new_version = (doc.current_version or 0) + 1
    note = f"Restored from v{version_no}"

    doc.append(
        "versions",
        {
            "version_no": new_version,
            "file": source.file,
            "change_note": note,
            "uploaded_by": frappe.session.user,
            "uploaded_at": now_datetime(),
        },
    )
    doc.current_version = new_version
    doc.latest_file = source.file
    doc.save(ignore_permissions=True)

    log_activity(name, "Version Restored", details=f"v{version_no} promoted to v{new_version}")

    return {"version": new_version}


@frappe.whitelist()
def log_download(name):
    """Called from the client when a user downloads the latest file."""
    require_staff()
    log_activity(name, "Downloaded")
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log_activity(document, action, details=None):
    frappe.get_doc(
        {
            "doctype": "Document Activity",
            "document": document,
            "action": action,
            "user": frappe.session.user,
            "timestamp": now_datetime(),
            "details": details,
        }
    ).insert(ignore_permissions=True)


def get_fullname(user):
    return frappe.utils.get_fullname(user) or user


def notify_team(subject, message, document, exclude_user=None, only_users=None):
    """Push a Notification Log entry to team members.

    TODO (integration point): if you want these to also land in the Duty Room
    group chat, call your Duty Room message-creation method here with `message`.
    Kept as standard Notification Log so this module works even if Duty Room
    doctype names change.
    """
    if only_users:
        recipients = [u for u in only_users if u]
    else:
        recipients = get_team_users(exclude_user)

    for user in recipients:
        try:
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "for_user": user,
                    "type": "Alert",
                    "document_type": "Client Document",
                    "document_name": document,
                    "subject": subject,
                    "email_content": message,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Document Hub notify_team failed")


def get_team_users(exclude_user=None):
    """All enabled system users holding the Duty Board User role."""
    users = frappe.get_all(
        "Has Role",
        filters={"role": "Duty Board User", "parenttype": "User"},
        pluck="parent",
    )
    enabled = frappe.get_all(
        "User",
        filters={"name": ["in", users], "enabled": 1, "user_type": "System User"},
        pluck="name",
    )
    return [u for u in enabled if u != exclude_user]


# ---------------------------------------------------------------------------
# Scheduled task — stale checkout alerts (wire into hooks.py)
# ---------------------------------------------------------------------------

def alert_stale_checkouts(threshold_hours=48):
    """Notify holders + managers about documents locked longer than threshold."""
    stale = frappe.get_all(
        "Client Document",
        filters={"status": "Checked Out"},
        fields=["name", "title", "client", "checked_out_by", "checked_out_at"],
    )

    now = now_datetime()
    for d in stale:
        hours = time_diff_in_hours(now, d.checked_out_at)
        if hours < threshold_hours:
            continue

        msg = _("'{0}' ({1}) has been checked out by {2} for {3} hours.").format(
            d.title, d.client, get_fullname(d.checked_out_by), int(hours)
        )
        # Alert the holder and all managers
        managers = frappe.get_all(
            "Has Role",
            filters={"role": ["in", list(FORCE_RELEASE_ROLES)], "parenttype": "User"},
            pluck="parent",
        )
        recipients = list(set([d.checked_out_by] + managers))
        notify_team(
            subject=_("Stale document checkout"),
            message=msg,
            document=d.name,
            only_users=recipients,
        )


MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]


def _default_due(period_month, period_year):
    """Nth working day (Mon–Fri) of the month AFTER the period."""
    import datetime

    try:
        n = frappe.utils.cint(frappe.db.get_single_value("Duty Settings", "stmt_due_working_day")) or 6
    except Exception:
        n = 6
    m = MONTHS.index(period_month) + 1 if period_month in MONTHS else 1
    y = frappe.utils.cint(period_year)
    m += 1
    if m > 12:
        m, y = 1, y + 1
    d = datetime.date(y, m, 1)
    count = 0
    while True:
        if d.weekday() < 5:
            count += 1
            if count >= n:
                return d
        d += datetime.timedelta(days=1)


def statement_state(doc):
    """Derived delivery state for unpublished statements."""
    from frappe.utils import getdate, today

    if cint(doc.published):
        return None
    eff = doc.delayed_until or doc.due_date
    if not eff:
        return {"state": "prep", "label": _("in preparation")}
    eff_d = getdate(eff)
    t = getdate(today())
    ds = eff_d.strftime("%-d %b") if hasattr(eff_d, "strftime") else str(eff)
    if t > eff_d:
        return {"state": "late", "label": _("Running late — we owe you an update")}
    if doc.delayed_until:
        return {"state": "delayed", "label": _("New date: {0} — {1}").format(ds, (doc.delay_reason or "")[:200])}
    return {"state": "ontrack", "label": _("On track — due {0}").format(ds)}


def statement_label(doc):
    if doc.statement_type == "Annual Report":
        return _("{0} Annual Report").format(doc.period_year)
    return _("{0} {1} Management Account").format(doc.period_month or "", doc.period_year).strip()


def _thread_add(doc, entry_type, note, at_version=None):
    doc.append(
        "review_thread",
        {
            "entry_type": entry_type,
            "user": frappe.session.user,
            "when": frappe.utils.now_datetime(),
            "at_version": at_version if at_version is not None else cint(doc.publish_seq),
            "note": (note or "")[:5000],
        },
    )
    doc.save(ignore_permissions=True)


def _notify_statement_staff(doc, title, body):
    """Bookkeeper on the customer's room + whoever published, deduped."""
    targets = set()
    if doc.published_by:
        targets.add(doc.published_by)
    try:
        from duty_board.client_room import _financial_room

        rn = _financial_room(doc.client)
        room = frappe.db.get_value("Client Room", rn, ["name", "bookkeeper"], as_dict=True) if rn else None
        if room and room.bookkeeper:
            targets.add(room.bookkeeper)
    except Exception:
        pass
    for u in targets:
        try:
            from duty_board.api import _notify_user

            _notify_user(u, title, body)
        except Exception:
            pass


@frappe.whitelist()
def publish_statement(name, note=None, highlights=None):
    """Approve for client: snapshot the document's CURRENT latest file as
    the immutable published artifact for its period. Books managers only.
    Republishing bumps the sequence; clients only ever see snapshots."""
    from duty_board.permissions import require_staff

    require_staff()
    try:
        from duty_board.accounting import books_access

        acc = books_access()
        if not (acc and acc.get("allowed") and acc.get("manager")):
            frappe.throw(_("Only Books managers publish financial statements."), frappe.PermissionError)
    except frappe.PermissionError:
        raise
    except Exception:
        frappe.throw(_("Books access could not be verified."), frappe.PermissionError)
    doc = frappe.get_doc("Client Document", name)
    if not cint(doc.is_financial_statement):
        frappe.throw(_("This document is not flagged as a financial statement."))
    if doc.checked_out_by:
        frappe.throw(_("Checked out by {0} — check it in before publishing.").format(doc.checked_out_by))
    if not doc.latest_file:
        frappe.throw(_("No file yet — check in a version first."))
    src_name = frappe.db.get_value("File", {"file_url": doc.latest_file})
    if not src_name:
        frappe.throw(_("Working file is missing."))
    src = frappe.get_doc("File", src_name)
    seq = cint(doc.publish_seq) + 1
    base = src.file_name or "statement.xlsx"
    snap = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"PUBLISHED-v{seq}-{base}",
            "is_private": 1,
            "content": src.get_content(),
            "attached_to_doctype": "Client Document",
            "attached_to_name": doc.name,
        }
    ).insert(ignore_permissions=True)
    doc.db_set("published", 1, update_modified=False)
    doc.db_set("published_on", frappe.utils.now_datetime(), update_modified=False)
    doc.db_set("published_by", frappe.session.user, update_modified=False)
    doc.db_set("published_file_url", snap.file_url, update_modified=False)
    doc.db_set("published_file_name", base, update_modified=False)
    doc.db_set("publish_seq", seq, update_modified=False)
    if highlights is not None:
        clean = "\n".join([l.strip() for l in (highlights or "").splitlines() if l.strip()][:5])
        doc.db_set("highlights", clean or None, update_modified=False)
    was_approved = doc.review_status == "Approved"
    doc.db_set("review_status", "Awaiting Client Review", update_modified=False)
    frappe.db.commit()
    doc.reload()
    if note or was_approved:
        _thread_add(
            doc, "Staff Note",
            (note or "") + (_(" (republished after approval — needs a fresh approval)") if was_approved else ""),
            seq,
        )
    try:
        frappe.get_doc(
            {
                "doctype": "Document Activity",
                "document": doc.name,
                "activity": "Published to client (v{0})".format(seq),
                "user": frappe.session.user,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
    label = statement_label(doc)
    verb = _("republished (v{0})").format(seq) if seq > 1 else _("published")
    try:
        from duty_board.client_room import _financial_room, _post, _push_room_clients

        room_name = _financial_room(doc.client)
        if room_name:
            room = frappe.get_doc("Client Room", room_name)
            msg = _("📊 {0} {1} — now on your portal under Financial Statements.").format(label, verb)
            if note:
                msg += _(" Note from the team: “{0}”").format((note or "")[:300])
            _post(room, msg)
            _push_room_clients(room, _("📊 Financial statement · Xlevel"), label)
    except Exception:
        pass
    return {"ok": 1, "seq": seq, "label": label}


@frappe.whitelist()
def declare_delay(name, new_date, reason):
    """Honest-delay declaration: new date + required reason → client told."""
    from duty_board.permissions import require_staff

    require_staff()
    reason = (reason or "").strip()
    if not reason:
        frappe.throw(_("A reason is required — the client deserves one."))
    if not new_date:
        frappe.throw(_("Give the new delivery date."))
    doc = frappe.get_doc("Client Document", name)
    if not cint(doc.is_financial_statement) or cint(doc.published):
        frappe.throw(_("Delays apply to unpublished financial statements."))
    doc.db_set("delayed_until", new_date, update_modified=False)
    doc.db_set("delay_reason", reason[:500], update_modified=False)
    doc.db_set("delay_declared_by", frappe.session.user, update_modified=False)
    doc.db_set("delay_declared_on", frappe.utils.now_datetime(), update_modified=False)
    frappe.db.commit()
    doc.reload()
    ds = frappe.utils.getdate(new_date).strftime("%-d %b")
    _thread_add(doc, "Staff Note", _("New delivery date {0}: {1}").format(ds, reason))
    label = statement_label(doc)
    try:
        frappe.get_doc(
            {
                "doctype": "Document Activity",
                "document": doc.name,
                "activity": "Delay declared → {0}".format(new_date),
                "user": frappe.session.user,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass
    try:
        from duty_board.client_room import _financial_room, _post, _push_room_clients

        room_name = _financial_room(doc.client)
        if room_name:
            room = frappe.get_doc("Client Room", room_name)
            _post(room, _("📊 {0} — new delivery date {1}. Reason: {2}").format(label, ds, reason[:200]))
            _push_room_clients(room, _("📊 {0} · Xlevel").format(label), _("New delivery date {0}").format(ds))
    except Exception:
        pass
    return {"ok": 1}
