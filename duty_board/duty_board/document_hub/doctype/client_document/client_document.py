# Copyright (c) 2026, Zhift Platforms Ltd
# Client Document — check-out / check-in controller for Duty Board Document Hub

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_hours

FORCE_RELEASE_ROLES = {"System Manager", "Duty Board Manager"}


class ClientDocument(Document):
    def after_insert(self):
        log_activity(self.name, "Created", details=f"Document created: {self.title}")

    def validate(self):
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
