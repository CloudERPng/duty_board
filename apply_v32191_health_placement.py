#!/usr/bin/env python3
"""Duty Board v3.219.1 - ACADEMY HEALTH WHERE IT WOULD BE LOOKED FOR.

v3.219.0 put Academy health on the page menu and in the rail overflow. That was
wrong, and it was demonstrated immediately: the room's Training Academy dialog
was opened, Cohorts and Seat orders were sitting there, and the feature was
reported missing. Per-room tools used occasionally were prominent; the
cross-room view meant to be checked weekly was two levels deeper.

  - Academy health becomes a first-class rail item beside Team training, with
    its own chart icon.
  - The room's Training Academy dialog gains an "Academy health (all clients)"
    link, so somebody starting where the work is can reach the overview.
  - The duplicated _more_extra initialisation left by the previous patch is
    tidied, and the overflow entry now follows Team training rather than
    interrupting it.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.219.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv


ICON_OLD = '\tconst RSVG = {\n\t\tday: '

ICON_NEW = '\tconst RSVG = {\n\t\tpulse: \'<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>\',\n\t\tday: '

RAIL_OLD = '\t\t\tboard.rail.push({ id: "training", ic: board._rsvg.cap, label: __("Team training"), go: () => board.team_training_dialog() });'

RAIL_NEW = '\t\t\tboard.rail.push({ id: "training", ic: board._rsvg.cap, label: __("Team training"), go: () => board.team_training_dialog() });\n\t\t\tboard.rail.push({ id: "academyhealth", ic: board._rsvg.pulse, label: __("Academy health"), go: () => board.academy_health_dialog() });'

TIDY_OLD = '\t\t\tpage.add_menu_item(__("\\u{1F4C8} Academy health"), () => board.academy_health_dialog());\n\t\t\tboard._more_extra = board._more_extra || [];\n\t\t\tboard._more_extra.push({ icon: "\\u{1F4C8}", label: __("Academy health"), go: () => board.academy_health_dialog() });\n\t\t\tboard._more_extra = board._more_extra || [];\n\t\t\tboard._more_extra.push({ icon: "🎓", label: __("Team training"), go: () => board.team_training_dialog() });'

TIDY_NEW = '\t\t\tpage.add_menu_item(__("\\u{1F4C8} Academy health"), () => board.academy_health_dialog());\n\t\t\tboard._more_extra = board._more_extra || [];\n\t\t\tboard._more_extra.push({ icon: "🎓", label: __("Team training"), go: () => board.team_training_dialog() });\n\t\t\tboard._more_extra.push({ icon: "\\u{1F4C8}", label: __("Academy health"), go: () => board.academy_health_dialog() });'

DLG_OLD = '\t\td.set_secondary_action_label(`\\u{1F9FE} ${__("Seat orders")}`);\n\t\td.set_secondary_action(() => { d.hide(); this.academy_orders_dialog(); });'

DLG_NEW = '\t\td.set_secondary_action_label(`\\u{1F9FE} ${__("Seat orders")}`);\n\t\td.set_secondary_action(() => { d.hide(); this.academy_orders_dialog(); });\n\t\td.$wrapper.on("click", ".duty-ah-open", () => { d.hide(); this.academy_health_dialog(); });\n\t\tsetTimeout(() => d.$wrapper.find(".modal-footer").prepend(`<span style="margin-right:auto;padding-left:4px">${this.academy_health_link()}</span>`), 0);'

FOOT_OLD = '\tacademy_health_css() {'

FOOT_NEW = '\tacademy_health_link() {\n\t\t/* Somebody looking for anything academy-related opens the room dialog\n\t\t   first, so the cross-room view must be reachable from inside it and\n\t\t   not only from the page menu two levels out. */\n\t\treturn `<a class="duty-ah-open" style="cursor:pointer;font-size:12px;font-weight:600">\\u{1F4C8} ${__("Academy health (all clients)")}</a>`;\n\t}\n\n\tacademy_health_css() {'



def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if 'id: "academyhealth"' in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.219.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.219.0.")

    edits = [
        (ICON_OLD, ICON_NEW, "pulse icon"),
        (RAIL_OLD, RAIL_NEW, "rail item"),
        (TIDY_OLD, TIDY_NEW, "tidy overflow"),
        (DLG_OLD, DLG_NEW, "room dialog handler"),
        (FOOT_OLD, FOOT_NEW, "room dialog link"),
    ]
    problems = []
    for old, _new, label in edits:
        n = files[JS].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for old, new, _label in edits:
        files[JS] = files[JS].replace(old, new, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(files[JS])
    print("  duty_board.js: rail item, room-dialog link, overflow tidied")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.219.0"', '"3.219.1"'))
    print("wrote __init__.py -> 3.219.1")


if __name__ == "__main__":
    main()
