from flask import Flask, request, session, send_from_directory, render_template
from flask import Blueprint
import api

from api.common import WebSuccess, WebError
from api.annotations import api_wrapper, require_login, require_teacher, require_admin, check_csrf
from api.annotations import block_before_competition, block_after_competition, block_before_end
from api.annotations import log_action

blueprint = Blueprint("writeups_api", __name__)

@blueprint.route('/submit_writeup', methods=['POST'])
@api_wrapper
@check_csrf
@require_login
@block_before_end(WebError("The competition has not ended yet!"))
def add_writeup_hook():
    pid = request.form.get('pid', None)
    title = request.form.get('title', None)
    url = request.form.get('url', None)
    uid = api.user.get_user()["uid"]
    team = api.user.get_team(uid=uid)
    tid = team['tid']
    if title is None or pid is None or url is None:
        return ("Please supply a pid and writeup data.")
    api.cache.invalidate_memoization(api.problem.get_solved_pids, {"args":tid})
    if pid not in api.problem.get_solved_pids(tid):
        return ("Your team hasn't solved this problem yet!")
    api.writeups.add_writeup(pid, uid, title, url)
    return ("Your writeup has been added!")

@blueprint.route('/by_problem/<path:pid>', methods=['GET'])
@api_wrapper
@require_login
@block_before_end(WebError("The competition has not ended yet!"))
def get_writeups(pid):
    writeups = api.writeups.get_writeups_for_problem(pid)
    return WebSuccess(data=writeups)

@blueprint.route('/downvote', methods=['POST'])
@api_wrapper
@check_csrf
@require_login
@block_before_end(WebError("The competition has not ended yet!"))
def downvote_hook():
    wid = request.form.get("wid", None)

    if wid is None:
        return WebError("Please supply a wid.")

    return api.writeups.downvote_writeup(wid)

@blueprint.route('/upvote', methods=['POST'])
@api_wrapper
@check_csrf
@require_login
@block_before_end(WebError("The competition has not ended yet!"))
def upvote_hook():
    wid = request.form.get("wid", 'NOTAWID')

    if wid is None:
        return WebError("Please supply a wid.")

    return api.writeups.upvote_writeup(wid)
