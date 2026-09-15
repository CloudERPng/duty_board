#!/usr/bin/env python3
"""Duty Board v3.218.0 - THE FIRST-COHORT PASS.

Eight fixes from the functional review, chosen because each is hours rather
than days and together they remove most of the friction a first paying cohort
would hit. Three of them are things already computed that never reached a
screen.

S1  The invitation email. Frappe's default welcome says nothing about training,
    gives no reason for the message and reads like machinery, so a meaningful
    share of invited staff never open it - and nothing reports that as the
    reason a cohort went quiet. Replaced with an invitation from their own
    administrator by name, saying what it is for, how long chapters take, and
    that the certificate is theirs to keep.

A1  Seat orders are visible. academy_my_orders was written in v3.212.0 and
    called from nowhere; an administrator requested seats and then had to email
    us to find out what happened.

A2  Never signed in. last_seen was fetched for the roster and never rendered,
    so an onboarding failure looked identical to someone ignoring their
    training. They need opposite responses.

A6  Remind everyone overdue, instead of one click per person.

L5  The failure dead end. Exhausting your attempts said "speak to your training
    coordinator" and told the coordinator nothing. Administrators are now
    notified, see who is blocked, and can grant one further attempt to one
    person without loosening the policy for everybody.

L1  Resume actually resumes - straight to the first unread chapter rather than
    back to the course page.

L2  Due dates reach the learner. We were emailing "due in three days" and then
    showing a portal with no deadline anywhere on it.

L3  Time remaining on the card, computed from the chapters still unread.

  Duty Training Record: +extra_attempts.

Deploy: apply -> bench migrate -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. Anchored, idempotent. Requires v3.217.2.
"""

import io
import json as _json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
TRDT = "duty_board/duty_board/doctype/duty_training_record/duty_training_record.json"
CHECK_ONLY = "--check" in sys.argv


CC_OLD = 'const courseCard = (r) => {\n\t\t\t\tconst st = stateOf(r);\n\t\t\t\tconst pct = r.lessons_total ? Math.round((r.lessons_done / r.lessons_total) * 100) : 0;\n\t\t\t\treturn `<div class="lmscard cc ${st}" onclick="openCourse(\'${esc(r.record)}\')">\n\t\t\t\t\t<div class="lmstile ${st === "done" ? "gold" : ""}">${st === "done"\n\t\t\t\t\t\t? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>`\n\t\t\t\t\t\t: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>`}</div>\n\t\t\t\t\t<div class="lmsbody">\n\t\t\t\t\t\t<b>${esc(r.module_title)}</b>\n\t\t\t\t\t\t<div class="lmsmeta">${esc(r.product || "")}${r.lessons_total ? `${r.product ? " · " : ""}${r.lessons_total} lesson${r.lessons_total === 1 ? "" : "s"}` : ""}</div>\n\t\t\t\t\t\t${st === "done"\n\t\t\t\t\t\t\t? `<div class="lmsdone">Completed${r.completed_on ? " · " + esc(r.completed_on) : ""}</div>${r.cert ? `<div class="certacts"><a href="/api/method/duty_board.client_room.client_shelf_file?id=${esc(r.cert)}" target="_blank" onclick="event.stopPropagation()">Certificate</a></div>` : ""}`\n\t\t\t\t\t\t\t: `<div class="lmsbar"><i style="width:${pct}%"></i></div>\n\t\t\t\t\t\t\t<div class="lmsfoot"><span class="lmsmeta">${r.lessons_total ? `${r.lessons_done} of ${r.lessons_total} read` : ""}</span>\n\t\t\t\t\t\t\t<span class="lmscta">${st === "ready" ? "Take the assessment →" : st === "started" ? "Continue learning →" : "Start course →"}</span></div>`}\n\t\t\t\t\t</div>\n\t\t\t\t</div>`;\n\t\t\t};\n\t\t\t'

CC_NEW = 'const courseCard = (r) => {\n\t\t\t\tconst st = stateOf(r);\n\t\t\t\tconst pct = r.lessons_total ? Math.round((r.lessons_done / r.lessons_total) * 100) : 0;\n\t\t\t\tconst mins = (m) => (!m ? "" : m < 60 ? m + " min" : Math.round((m / 60) * 10) / 10 + " hr");\n\t\t\t\tconst go = st === "started" && r.next_lesson\n\t\t\t\t\t? `openLesson(\'${esc(r.next_lesson)}\',\'${esc(r.record)}\')`\n\t\t\t\t\t: `openCourse(\'${esc(r.record)}\')`;\n\t\t\t\tconst due = r.due_on && st !== "done"\n\t\t\t\t\t? `<span class="lmsdue${r.overdue ? " late" : ""}">${r.overdue ? "Overdue \\u00b7 " : "Due "}${esc(String(r.due_on).slice(0, 10))}</span>`\n\t\t\t\t\t: "";\n\t\t\t\treturn `<div class="lmscard cc ${st}" onclick="${go}">\n\t\t\t\t\t<div class="lmstile ${st === "done" ? "gold" : ""}">${st === "done"\n\t\t\t\t\t\t? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>`\n\t\t\t\t\t\t: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>`}</div>\n\t\t\t\t\t<div class="lmsbody">\n\t\t\t\t\t\t<b>${esc(r.module_title)}</b>\n\t\t\t\t\t\t<div class="lmsmeta">${esc(r.product || "")}${r.lessons_total ? `${r.product ? " \\u00b7 " : ""}${r.lessons_total} lesson${r.lessons_total === 1 ? "" : "s"}` : ""}${r.minutes_left && st !== "done" ? ` \\u00b7 ${mins(r.minutes_left)} left` : ""}</div>\n\t\t\t\t\t\t${due}\n\t\t\t\t\t\t${st === "done"\n\t\t\t\t\t\t\t? `<div class="lmsdone">Completed${r.completed_on ? " \\u00b7 " + esc(r.completed_on) : ""}</div>${r.cert ? `<div class="certacts"><a href="/api/method/duty_board.client_room.client_shelf_file?id=${esc(r.cert)}" target="_blank" onclick="event.stopPropagation()">Certificate</a></div>` : ""}`\n\t\t\t\t\t\t\t: `<div class="lmsbar"><i style="width:${pct}%"></i></div>\n\t\t\t\t\t\t\t<div class="lmsfoot"><span class="lmsmeta">${r.lessons_total ? `${r.lessons_done} of ${r.lessons_total} read` : ""}</span>\n\t\t\t\t\t\t\t<span class="lmscta">${st === "ready" ? "Take the assessment \\u2192" : st === "started" ? "Resume \\u2192" : "Start course \\u2192"}</span></div>`}\n\t\t\t\t\t</div>\n\t\t\t\t</div>`;\n\t\t\t};\n\t\t\t'

TR_OLD = '\t\t\t"lessons_total": lesson_counts.get(r.module, 0) if r.trainee == user else None,\n\t\t\t"lessons_done": done_counts.get(r.module, 0) if r.trainee == user else None,'

TR_NEW = '\t\t\t"lessons_total": lesson_counts.get(r.module, 0) if r.trainee == user else None,\n\t\t\t"lessons_done": done_counts.get(r.module, 0) if r.trainee == user else None,\n\t\t\t"due_on": str(due.get(r.name)) if due.get(r.name) else None,\n\t\t\t"overdue": bool(\n\t\t\t\tdue.get(r.name) and r.status != "Completed" and getdate(due[r.name]) < getdate(today())\n\t\t\t),\n\t\t\t"minutes_left": left_mins.get(r.module) if r.trainee == user else None,\n\t\t\t"next_lesson": next_lesson.get(r.module) if r.trainee == user else None,'

TR_CALC_OLD = '\t\tfor p in frappe.get_all(\n\t\t\t"Duty Lesson Progress",\n\t\t\tfilters={"user": user, "module": ["in", my_modules], "completed_at": ["is", "set"]},\n\t\t\tfields=["module"],\n\t\t):\n\t\t\tdone_counts[p.module] = done_counts.get(p.module, 0) + 1'

TR_CALC_NEW = '\t\tfor p in frappe.get_all(\n\t\t\t"Duty Lesson Progress",\n\t\t\tfilters={"user": user, "module": ["in", my_modules], "completed_at": ["is", "set"]},\n\t\t\tfields=["module"],\n\t\t):\n\t\t\tdone_counts[p.module] = done_counts.get(p.module, 0) + 1\n\t\t# what is left to read, and where to resume — the card can then say\n\t\t# "45 min left" and go straight to the next unread chapter\n\t\tread = {\n\t\t\tp.lesson\n\t\t\tfor p in frappe.get_all(\n\t\t\t\t"Duty Lesson Progress",\n\t\t\t\tfilters={"user": user, "module": ["in", my_modules], "completed_at": ["is", "set"]},\n\t\t\t\tfields=["lesson"],\n\t\t\t)\n\t\t}\n\t\tfor l in frappe.get_all(\n\t\t\t"Duty Lesson", filters={"module": ["in", my_modules]},\n\t\t\tfields=["name", "module", "est_minutes"],\n\t\t\torder_by="sort_order asc, creation asc",\n\t\t):\n\t\t\tif l.name in read:\n\t\t\t\tcontinue\n\t\t\tleft_mins[l.module] = left_mins.get(l.module, 0) + (cint(l.est_minutes) or 5)\n\t\t\tnext_lesson.setdefault(l.module, l.name)'

TR_INIT_OLD = 'def client_get_training():\n\troom = _learning_room()\n\trows = _training_rows(room)\n\tuser = frappe.session.user\n\tmy_modules = [r.module for r in rows if r.trainee == user]\n\tlesson_counts, done_counts = {}, {}'

TR_INIT_NEW = 'def client_get_training():\n\troom = _learning_room()\n\trows = _training_rows(room)\n\tuser = frappe.session.user\n\tmy_modules = [r.module for r in rows if r.trainee == user]\n\tlesson_counts, done_counts = {}, {}\n\tleft_mins, next_lesson = {}, {}\n\tdue = {\n\t\td.name: d.due_on\n\t\tfor d in frappe.get_all(\n\t\t\t"Duty Training Record",\n\t\t\tfilters={"name": ["in", [r.name for r in rows] or [""]]},\n\t\t\tfields=["name", "due_on"],\n\t\t)\n\t\tif d.due_on\n\t}'

INV_OLD = '\t\t\tfrappe.get_doc({\n\t\t\t\t"doctype": "User",\n\t\t\t\t"email": email,\n\t\t\t\t"first_name": email.split("@")[0].strip(),\n\t\t\t\t"user_type": "Website User",\n\t\t\t\t"send_welcome_email": 1,\n\t\t\t}).insert(ignore_permissions=True)'

INV_NEW = '\t\t\tfrappe.get_doc({\n\t\t\t\t"doctype": "User",\n\t\t\t\t"email": email,\n\t\t\t\t"first_name": email.split("@")[0].strip(),\n\t\t\t\t"user_type": "Website User",\n\t\t\t\t"send_welcome_email": 0,\n\t\t\t}).insert(ignore_permissions=True)'

INV_SEND_OLD = '\tfrappe.db.commit()\n\tif invited or rejoined:\n\t\ttry:\n\t\t\t_post(\n\t\t\t\troom,'

INV_SEND_NEW = '\tfrappe.db.commit()\n\tfor email in invited + rejoined:\n\t\t_academy_invite(room, email)\n\tif invited or rejoined:\n\t\ttry:\n\t\t\t_post(\n\t\t\t\troom,'

HELPER_OLD = '@frappe.whitelist()\ndef client_admin_people():'

HELPER_NEW = 'def _academy_invite(room, email):\n\t"""The invitation that decides whether a paid-for cohort ever starts.\n\n\tFrappe\'s own welcome email says nothing about training, gives no reason for\n\tthe message, and reads like machinery — which in practice means a meaningful\n\tshare of invited staff never open it, and nothing in the system reports that\n\tas the reason a cohort went quiet.\n\n\tThis one comes from their own administrator by name, says what it is for,\n\thow long it takes, and what they earn."""\n\ttry:\n\t\tuser = frappe.get_doc("User", email)\n\t\tkey = frappe.generate_hash()\n\t\tuser.db_set("reset_password_key", key, update_modified=False)\n\t\ttry:\n\t\t\tuser.db_set("last_reset_password_key_generated_on", now_datetime(), update_modified=False)\n\t\texcept Exception:\n\t\t\tpass\n\t\tlink = frappe.utils.get_url("/update-password?key=" + key)\n\t\twho = frappe.utils.get_fullname(frappe.session.user)\n\t\torg = room.customer or ""\n\t\tfrappe.sendmail(\n\t\t\trecipients=[email],\n\t\t\tsubject=_("{0} has set up your training account").format(who),\n\t\t\tmessage="""<p>Hello,</p>\n<p><b>{who}</b> has given you access to the {org} training portal, where your\ncourses, assessments and certificates live.</p>\n<p>Here is what to expect. Each course is a set of short chapters you read at\nyour own pace, with a few questions at the end of each one so you can check it\nlanded. When you have read them all, you sit a short timed assessment. Pass it\nand you earn a certificate with a serial number anyone can verify — it is yours\nto keep, and it does not expire.</p>\n<p>Most chapters take five to ten minutes. You can stop and pick up where you\nleft off at any time, on a phone or a computer.</p>\n<p><a href="{link}" style="display:inline-block;background:#0A473F;color:#fff;\ntext-decoration:none;padding:11px 22px;border-radius:8px;font-weight:600">\nSet your password and begin</a></p>\n<p style="font-size:12px;color:#6B7C77">If the button does not work, copy this\ninto your browser:<br>{link}</p>\n<p style="font-size:12px;color:#6B7C77">You are receiving this because {who} at\n{org} added you. If that seems wrong, speak to them before using the link.</p>\n<p>&mdash; CloudERP.One Academy &middot; Xlevel Retail Systems Ltd</p>""".format(\n\t\t\t\twho=frappe.utils.escape_html(who),\n\t\t\t\torg=frappe.utils.escape_html(org),\n\t\t\t\tlink=link,\n\t\t\t),\n\t\t)\n\texcept Exception:\n\t\tfrappe.log_error(frappe.get_traceback(), "duty_board academy invite")\n\n\n@frappe.whitelist()\ndef client_admin_people():'

QS_OLD = '\t\t"max_attempts": pol.max_attempts,'

QS_NEW = '\t\t"max_attempts": (pol.max_attempts + extra) if pol.max_attempts else 0,'

QS_SIG_OLD = 'def _quiz_state(module, user):'

QS_SIG_NEW = 'def _quiz_state(module, user, record=None):'

QS_EXTRA_OLD = '\tpol = _exam_policy(module)\n\tused = len(attempts)'

QS_EXTRA_NEW = '\tpol = _exam_policy(module)\n\t# an administrator may grant further attempts on one person\'s record\n\t# without loosening the policy for everybody\n\textra = cint(frappe.db.get_value("Duty Training Record", record, "extra_attempts")) if record else 0\n\tused = len(attempts)'

QS_LEFT_OLD = '\t\t"attempts_left": max(0, pol.max_attempts - used) if pol.max_attempts else None,'

QS_LEFT_NEW = '\t\t"attempts_left": max(0, pol.max_attempts + extra - used) if pol.max_attempts else None,'

GATE_OLD = '\tst = _quiz_state(module, user)\n\tif st["passed"]:\n\t\treturn st\n\tif record:'

GATE_NEW = '\tst = _quiz_state(module, user, record)\n\tif st["passed"]:\n\t\treturn st\n\tif record:'

ESC_OLD = 'def _topic_breakdown(pairs):'

ESC_NEW = 'def _escalate_if_blocked(rec, state):\n\t"""Tell the client\'s administrators when somebody runs out of attempts.\n\n\tWithout this the portal says "speak to your training coordinator" and the\n\tcoordinator is never told — so a blocked learner stays blocked until they\n\tadmit it, which is how a paid-for cohort quietly stops."""\n\tif state.get("passed") or state.get("attempts_left") != 0:\n\t\treturn\n\ttry:\n\t\troom = frappe.get_doc("Client Room", rec.room)\n\t\ttitle = frappe.db.get_value("Duty Training Module", rec.module, "title") or rec.module\n\t\twho = frappe.utils.get_fullname(frappe.session.user)\n\t\tfrom duty_board.api import _notify_user\n\n\t\tfor a in _room_admins(room):\n\t\t\t_notify_user(\n\t\t\t\ta.user,\n\t\t\t\t_("\\u26A0\\uFE0F Assessment attempts used up"),\n\t\t\t\t_("{0} cannot sit {1} again without your approval.").format(who, title),\n\t\t\t)\n\texcept Exception:\n\t\tfrappe.log_error(frappe.get_traceback(), "duty_board attempt escalation")\n\n\ndef _topic_breakdown(pairs):'

SUB_OLD = '\tstate = _quiz_state(rec.module, frappe.session.user)\n\treturn {\n\t\t"score": score,\n\t\t"passed": passed,\n\t\t"pass_mark": pass_mark,\n\t\t"wrong": [] if state["hide_wrong"] else wrong,\n\t\t"breakdown": _topic_breakdown(pairs),'

SUB_NEW = '\tstate = _quiz_state(rec.module, frappe.session.user, rec.name)\n\t_escalate_if_blocked(rec, state)\n\treturn {\n\t\t"score": score,\n\t\t"passed": passed,\n\t\t"pass_mark": pass_mark,\n\t\t"wrong": [] if state["hide_wrong"] else wrong,\n\t\t"breakdown": _topic_breakdown(pairs),'

TF_OLD = '\tstate = _quiz_state(rec.module, frappe.session.user)\n\treturn {\n\t\t"done": 1,'

TF_NEW = '\tstate = _quiz_state(rec.module, frappe.session.user, rec.name)\n\t_escalate_if_blocked(rec, state)\n\treturn {\n\t\t"done": 1,'

ADM_OLD = '@frappe.whitelist()\ndef client_training_admin_options():'

ADM_NEW = '@frappe.whitelist()\ndef client_admin_grant_attempt(record):\n\t"""Give one person one more go, without loosening the policy for everybody."""\n\troom = _require_room_admin()\n\trec = frappe.db.get_value(\n\t\t"Duty Training Record", record, ["room", "trainee", "module", "extra_attempts"], as_dict=True\n\t)\n\tif not rec or rec.room != room.name:\n\t\tfrappe.throw(_("Not found."), frappe.PermissionError)\n\tfrappe.db.set_value(\n\t\t"Duty Training Record", record, "extra_attempts", cint(rec.extra_attempts) + 1,\n\t\tupdate_modified=False,\n\t)\n\tfrappe.db.commit()\n\ttry:\n\t\tfrom duty_board.api import _notify_user\n\n\t\ttitle = frappe.db.get_value("Duty Training Module", rec.module, "title") or ""\n\t\t_notify_user(\n\t\t\trec.trainee, _("\\u2705 Another attempt granted"),\n\t\t\t_("You may sit {0} again.").format(title),\n\t\t)\n\texcept Exception:\n\t\tpass\n\treturn client_training_admin_home()\n\n\n@frappe.whitelist()\ndef client_admin_nudge_all():\n\t"""One reminder to everyone carrying something overdue."""\n\troom = _require_room_admin()\n\t_users, recs = _admin_rows(room)\n\ttargets = sorted({r.trainee for r in recs if r["overdue"]})\n\tsent = 0\n\tfor u in targets:\n\t\ttry:\n\t\t\tclient_training_admin_nudge(u)\n\t\t\tsent += 1\n\t\texcept Exception:\n\t\t\tcontinue\n\treturn {"sent": sent}\n\n\n@frappe.whitelist()\ndef client_training_admin_options():'

BLOCK_OLD = '\t\t\t"courses": [\n\t\t\t\t{\n\t\t\t\t\t"record": r.name, "title": r["title"], "status": r.status,\n\t\t\t\t\t"due_on": str(r.due_on) if r.due_on else None,\n\t\t\t\t\t"overdue": r["overdue"],\n\t\t\t\t}\n\t\t\t\tfor r in sorted(rows, key=lambda x: x["title"])\n\t\t\t],'

BLOCK_NEW = '\t\t\t"courses": [\n\t\t\t\t{\n\t\t\t\t\t"record": r.name, "title": r["title"], "status": r.status,\n\t\t\t\t\t"due_on": str(r.due_on) if r.due_on else None,\n\t\t\t\t\t"overdue": r["overdue"],\n\t\t\t\t\t"blocked": r["blocked"],\n\t\t\t\t}\n\t\t\t\tfor r in sorted(rows, key=lambda x: x["title"])\n\t\t\t],\n\t\t\t"blocked": [\n\t\t\t\t{"record": r.name, "title": r["title"]} for r in rows if r["blocked"]\n\t\t\t],\n\t\t\t"last_seen": last_seen.get(u),\n\t\t\t"never": not last_seen.get(u),'

ROWS_OLD = '\tfor r in recs:\n\t\tr["title"] = titles.get(r.module, r.module)\n\t\tr["overdue"] = bool(\n\t\t\tr.due_on and r.status != "Completed" and getdate(r.due_on) < today_d\n\t\t)\n\treturn users, recs'

ROWS_NEW = '\tfor r in recs:\n\t\tr["title"] = titles.get(r.module, r.module)\n\t\tr["overdue"] = bool(\n\t\t\tr.due_on and r.status != "Completed" and getdate(r.due_on) < today_d\n\t\t)\n\t\tr["blocked"] = False\n\t\tif r.status != "Completed":\n\t\t\tst = _quiz_state(r.module, r.trainee, r.name)\n\t\t\tr["blocked"] = bool(not st["passed"] and st["attempts_left"] == 0)\n\treturn users, recs'

HOME_OLD = '\tusers, recs = _admin_rows(room)\n\tby_user = {}'

HOME_NEW = '\tusers, recs = _admin_rows(room)\n\tlast_seen = {\n\t\tm.user: str(m.last_seen) if m.last_seen else None\n\t\tfor m in frappe.get_all(\n\t\t\t"Client Room Member", filters={"room": room.name, "active": 1},\n\t\t\tfields=["user", "last_seen"],\n\t\t)\n\t}\n\tby_user = {}'

STATS_OLD = '\t\t\t"overdue": sum(1 for r in recs if r["overdue"]),\n\t\t},'

STATS_NEW = '\t\t\t"overdue": sum(1 for r in recs if r["overdue"]),\n\t\t\t"blocked": sum(1 for r in recs if r["blocked"]),\n\t\t\t"never": sum(1 for u in users if not last_seen.get(u)),\n\t\t},'

HEAD_OLD = '\t\t\t\t\t\t<button id="admppl" style="background:#E2E8E5;color:#2A3833">People</button>'

HEAD_NEW = '\t\t\t\t\t\t<button id="admord" style="background:#E2E8E5;color:#2A3833">Orders</button>\n\t\t\t\t\t\t<button id="admppl" style="background:#E2E8E5;color:#2A3833">People</button>'

HOOK_OLD = '\t\t\tdocument.getElementById("admppl").onclick = openPeople;'

HOOK_NEW = '\t\t\tdocument.getElementById("admppl").onclick = openPeople;\n\t\t\tdocument.getElementById("admord").onclick = openOrders;'

ORD_OLD = 'function openPeople() {'

ORD_NEW = 'function openOrders() {\n\tadmFocus(1);\n\tconst host = document.getElementById("adminhost");\n\tconst money = (v) => "\\u20A6" + Number(v || 0).toLocaleString();\n\tapi("duty_board.academy.academy_my_orders")\n\t\t.then((rows) => {\n\t\t\thost.innerHTML = `\n\t\t\t\t<div class="admwrap">\n\t\t\t\t\t<div class="admhead"><div><b>Seat orders</b><span class="muted"> \\u00b7 what you have requested and where it stands</span></div>\n\t\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="admFocus(0);loadAdminTraining()">Back</button></div>\n\t\t\t\t\t${(rows || []).length ? rows.map((o) => `\n\t\t\t\t\t<div class="ordrow">\n\t\t\t\t\t\t<div class="ordwho"><b>${esc(o.track_title)}</b>\n\t\t\t\t\t\t\t<span class="muted">${esc(o.name)} \\u00b7 ${o.seats} seat${o.seats === 1 ? "" : "s"} \\u00b7 ${money(o.total)}${o.requested_on ? " \\u00b7 " + esc(String(o.requested_on).slice(0, 10)) : ""}</span>\n\t\t\t\t\t\t\t${o.decline_reason ? `<span class="muted">${esc(o.decline_reason)}</span>` : ""}</div>\n\t\t\t\t\t\t<span class="ordst ${o.status === "Approved" ? "ok" : o.status === "Requested" ? "wait" : "off"}">${esc(o.status === "Requested" ? "Awaiting payment" : o.status)}</span>\n\t\t\t\t\t</div>`).join("")\n\t\t\t\t\t\t: `<span class="muted">No seat requests yet. Browse the catalogue to request seats on a paid track.</span>`}\n\t\t\t\t\t<p class="muted" style="font-size:12px;margin-top:12px">Proforma invoices are filed under Documents. Seats activate as soon as we confirm your payment.</p>\n\t\t\t\t</div>`;\n\t\t})\n\t\t.catch(fail);\n}\nfunction openPeople() {'

PPL_OLD = '\t\t\t\t\t<span class="muted">${esc(p.user)}${p.assigned ? ` · ${p.complete} of ${p.assigned} complete` : " · no training yet"}</span>'

PPL_NEW = '\t\t\t\t\t<span class="muted">${esc(p.user)}${p.assigned ? ` · ${p.complete} of ${p.assigned} complete` : " · no training yet"}${p.active ? (p.last_seen ? ` · last seen ${esc(String(p.last_seen).slice(0, 10))}` : ` · <span class="pplnever">never signed in</span>`) : ""}</span>'

TILE_OLD = '\t\t\t\t\t\t${tile(s.overdue, "overdue", s.overdue > 0)}'

TILE_NEW = '\t\t\t\t\t\t${tile(s.overdue, "overdue", s.overdue > 0)}\n\t\t\t\t\t\t${tile(s.blocked, "blocked", s.blocked > 0)}'

RALL_OLD = '\t\t\t\t\t\t<button id="admassign">＋ Assign training</button>'

RALL_NEW = '\t\t\t\t\t\t${s.overdue ? `<button id="admrall" style="background:#E2E8E5;color:#2A3833">Remind everyone overdue</button>` : ""}\n\t\t\t\t\t\t<button id="admassign">＋ Assign training</button>'

ROW_OLD = '\t\t\t\t\t\t\t${p.assigned > p.complete ? `<a class="admnudge" data-u="${esc(p.user)}">Remind</a>` : ""}'

ROW_NEW = '\t\t\t\t\t\t\t${(p.blocked || []).length ? `<a class="admgrant" data-r="${esc(p.blocked[0].record)}" title="${esc(p.blocked[0].title)}">Grant attempt</a>` : ""}\n\t\t\t\t\t\t\t${p.assigned > p.complete ? `<a class="admnudge" data-u="${esc(p.user)}">Remind</a>` : ""}'

WHO_OLD = '\t\t\t\t\t\t\t\t<span class="muted">${p.assigned ? `${p.complete} of ${p.assigned} complete` : "nothing assigned"}${p.overdue ? ` · <span class="admlate">${p.overdue} overdue</span>` : ""}</span>'

WHO_NEW = '\t\t\t\t\t\t\t\t<span class="muted">${p.assigned ? `${p.complete} of ${p.assigned} complete` : "nothing assigned"}${p.overdue ? ` · <span class="admlate">${p.overdue} overdue</span>` : ""}${p.never ? ` · <span class="pplnever">never signed in</span>` : ""}${(p.blocked || []).length ? ` · <span class="admlate">blocked</span>` : ""}</span>'

HDL_OLD = '\t\t\thost.querySelectorAll(".admnudge").forEach((a) =>'

HDL_NEW = '\t\t\tconst rall = document.getElementById("admrall");\n\t\t\tif (rall) rall.onclick = () => {\n\t\t\t\trall.disabled = true;\n\t\t\t\tapi("client_admin_nudge_all")\n\t\t\t\t\t.then((r) => { rall.textContent = `Reminded ${r.sent}`; })\n\t\t\t\t\t.catch((e) => { rall.disabled = false; fail(e); });\n\t\t\t};\n\t\t\thost.querySelectorAll(".admgrant").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => {\n\t\t\t\t\ta.textContent = "\\u2026";\n\t\t\t\t\tapi("client_admin_grant_attempt", { record: a.getAttribute("data-r") })\n\t\t\t\t\t\t.then(loadAdminTraining)\n\t\t\t\t\t\t.catch((e) => { a.textContent = "Grant attempt"; fail(e); });\n\t\t\t\t}));\n\t\t\thost.querySelectorAll(".admnudge").forEach((a) =>'

CSS_OLD = '\t.admnudge { font-size: 12px; font-weight: 700; color: var(--brand-700); cursor: pointer; }'

CSS_NEW = '\t.admnudge { font-size: 12px; font-weight: 700; color: var(--brand-700); cursor: pointer; }\n\t.admgrant { font-size: 12px; font-weight: 700; color: #B27409; cursor: pointer; white-space: nowrap; }\n\t.pplnever { color: #B27409; font-weight: 700; }\n\t.ordrow { display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid #F0F4F2; }\n\t.ordwho { flex: 1; min-width: 0; font-size: 14px; }\n\t.ordwho span { display: block; font-size: 12.5px; }\n\t.ordst { font-size: 12px; font-weight: 700; border-radius: 99px; padding: 4px 12px; white-space: nowrap; }\n\t.ordst.ok { background: #E4F3EC; color: #0C6B4F; }\n\t.ordst.wait { background: #FFF7E6; color: #8A5A0B; }\n\t.ordst.off { background: #F1F4F3; color: #6B7C77; }\n\t.lmsdue { display: inline-block; font-size: 12px; font-weight: 600; color: #6B7C77; margin-top: 5px; }\n\t.lmsdue.late { color: #B27409; font-weight: 700; }'



EDITS = [
    (CR, INV_OLD, INV_NEW, "invite: suppress default welcome"),
    (CR, INV_SEND_OLD, INV_SEND_NEW, "invite: send ours"),
    (CR, HELPER_OLD, HELPER_NEW, "_academy_invite"),
    (CR, TR_INIT_OLD, TR_INIT_NEW, "training: due map"),
    (CR, TR_CALC_OLD, TR_CALC_NEW, "training: time left + next lesson"),
    (CR, TR_OLD, TR_NEW, "training payload"),
    (CR, QS_SIG_OLD, QS_SIG_NEW, "_quiz_state takes record"),
    (CR, QS_EXTRA_OLD, QS_EXTRA_NEW, "granted attempts"),
    (CR, QS_OLD, QS_NEW, "max attempts includes grants"),
    (CR, QS_LEFT_OLD, QS_LEFT_NEW, "attempts left includes grants"),
    (CR, GATE_OLD, GATE_NEW, "gate passes record"),
    (CR, ESC_OLD, ESC_NEW, "_escalate_if_blocked"),
    (CR, SUB_OLD, SUB_NEW, "classic submit escalates"),
    (CR, TF_OLD, TF_NEW, "timed finish escalates"),
    (CR, ROWS_OLD, ROWS_NEW, "admin rows: blocked"),
    (CR, HOME_OLD, HOME_NEW, "admin home: last seen"),
    (CR, BLOCK_OLD, BLOCK_NEW, "admin home: blocked + never"),
    (CR, STATS_OLD, STATS_NEW, "admin stats"),
    (CR, ADM_OLD, ADM_NEW, "grant attempt + nudge all"),
    (PORTAL, HEAD_OLD, HEAD_NEW, "Orders button"),
    (PORTAL, HOOK_OLD, HOOK_NEW, "Orders hook"),
    (PORTAL, ORD_OLD, ORD_NEW, "openOrders"),
    (PORTAL, PPL_OLD, PPL_NEW, "people: last seen"),
    (PORTAL, TILE_OLD, TILE_NEW, "blocked tile"),
    (PORTAL, RALL_OLD, RALL_NEW, "remind all button"),
    (PORTAL, WHO_OLD, WHO_NEW, "roster flags"),
    (PORTAL, ROW_OLD, ROW_NEW, "grant attempt link"),
    (PORTAL, HDL_OLD, HDL_NEW, "handlers"),
    (PORTAL, CC_OLD, CC_NEW, "course card"),
    (PORTAL, CSS_OLD, CSS_NEW, "css"),
]


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = _json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            _json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _academy_invite(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.217.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.217.2.")

    problems = []
    for f, old, _new, label in EDITS:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(EDITS))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, TRDT), [
        {"fieldname": "extra_attempts", "fieldtype": "Int",
         "label": "Extra Attempts Granted", "read_only": 1},
    ])
    print("  Duty Training Record: +extra_attempts")

    for f, old, new, _label in EDITS:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: invitation, resume data, granted attempts, escalation, admin tools")
    print("  portal.html: orders view, roster flags, remind-all, resume, due dates, time left")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.217.2"', '"3.218.0"'))
    print("wrote __init__.py -> 3.218.0")


if __name__ == "__main__":
    main()
