import json

import frappe
from frappe import _


def _vapid():
	return frappe.conf.get("duty_vapid_public"), frappe.conf.get("duty_vapid_private")


@frappe.whitelist()
def get_push_config():
	pub, _priv = _vapid()
	return {"public_key": pub}


@frappe.whitelist()
def save_push_subscription(subscription):
	sub = frappe.parse_json(subscription)
	endpoint = (sub or {}).get("endpoint")
	if not endpoint:
		frappe.throw(_("Invalid push subscription."))
	existing = frappe.db.exists("Duty Push Subscription", {"endpoint": endpoint})
	if existing:
		# the device follows whoever is logged in now
		frappe.db.set_value(
			"Duty Push Subscription",
			existing,
			"user",
			frappe.session.user,
			update_modified=False,
		)
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Push Subscription",
				"user": frappe.session.user,
				"endpoint": endpoint,
				"keys": json.dumps(sub.get("keys") or {}),
				"user_agent": frappe.request.headers.get("User-Agent")[:140]
				if frappe.request
				else None,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


def push_to_user(user, title, body=""):
	"""Send a web push to every registered device of a user. Silently does
	nothing if pywebpush or VAPID keys are missing."""
	pub, priv = _vapid()
	if not (pub and priv):
		return
	try:
		from pywebpush import webpush
	except ImportError:
		return

	subs = frappe.get_all(
		"Duty Push Subscription",
		filters={"user": user},
		fields=["name", "endpoint", "keys"],
	)
	dead = []
	for s in subs:
		try:
			webpush(
				subscription_info={
					"endpoint": s.endpoint,
					"keys": json.loads(s.get("keys") or "{}"),
				},
				data=json.dumps({"title": title, "body": body or ""}),
				vapid_private_key=priv,
				vapid_claims={
					"sub": "mailto:"
					+ (frappe.conf.get("duty_vapid_email") or "support@clouderp.one")
				},
			)
		except Exception as e:
			if "410" in str(e) or "404" in str(e):
				dead.append(s.name)
			else:
				frappe.log_error(
					f"Web push failed for {user}: {e}", "Duty Board Push"
				)
	for name in dead:
		frappe.delete_doc(
			"Duty Push Subscription", name, ignore_permissions=True, force=True
		)
	if dead:
		frappe.db.commit()


def generate_vapid():
	"""bench --site <site> execute duty_board.push.generate_vapid
	Prints the three set-config commands to run."""
	from cryptography.hazmat.primitives import serialization
	from py_vapid import Vapid02
	from py_vapid.utils import b64urlencode

	v = Vapid02()
	v.generate_keys()
	pub = b64urlencode(
		v.public_key.public_bytes(
			serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
		)
	)
	priv = b64urlencode(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
	print("Run these three commands:")
	print(f"bench --site <yoursite> set-config duty_vapid_public {pub}")
	print(f"bench --site <yoursite> set-config duty_vapid_private {priv}")
	print("bench --site <yoursite> set-config duty_vapid_email support@clouderp.one")
