""" Module for writeup functionality. Does not include comments (writeup_comments.py) """

import imp
import pymongo

import api

from datetime import datetime
from api.common import validate, check, safe_fail, InternalException, SevereInternalException, WebException
from voluptuous import Schema, Length, Required, Range
from bson import json_util
from os.path import join, isfile

from api.annotations import log_action

writeup_schema = Schema({
    Required("wid"): check(
        ("This does not look like a valid wid.", [str, Length(max=100)])),
    Required("uid"): check(
        ("This does not look like a valid uid.", [str, Length(max=100)])),
    Required("tid"): check(
        ("This does not look like a valid tid.", [str, Length(max=100)])),
    Required("pid"): check(
        ("This does not look like a valid pid.", [str, Length(max=100)])),
    Required("title"): check(
        ("The writeup title must be a string.", [str])),
    Required("url"): check(
        ("The writeup URL must be a string.", [str])),
})

vote_schema = Schema({
    Required("wid"): check(
        ("This does not look like a valid wid.", [str, Length(max=100)])),
    Required("uid"): check(
        ("This does not look like a valid uid.", [str, Length(max=100)])),
    Required("tid"): check(
        ("This does not look like a valid tid.", [str, Length(max=100)])),
    Required("up"): check(
        ("Upvote-ness must be a boolean.", [lambda up: type(up) == bool]))
})

def get_raw_writeups_for_problem(pid):
    db = api.common.get_conn()
    match = {"pid": pid}
    return list(db.writeups.find(match, {"_id": 0}))

def get_writeups_for_problem(pid):
    raw = get_raw_writeups_for_problem(pid)
    res = []
    for writeup in raw:
        score = get_score(writeup['wid'])
        new_writeup = writeup.copy()
        new_writeup['voteCount'] = score
        team = api.team.get_team(tid=new_writeup['tid'])
        new_writeup['author'] = team['team_name']
        res.append(new_writeup)
    return list(reversed(sorted(res, key=lambda w: w['voteCount'])))

@log_action
def add_writeup(pid, uid, title, url):
    # TODO: import rfc3987 checker and check url validity
    if uid is None:
        uid = api.user.get_user()["uid"]
    db = api.common.get_conn()
    wid = api.common.token()

    # Make sure the problem actually exists, and that this team has solved it.
    api.problem.get_problem(pid=pid)
    team = api.user.get_team(uid=uid)
    solved = pid in api.problem.get_solved_pids(tid=team["tid"])
    # TODO: fix this
    assert solved

    writeup = {
        "wid": wid,
        "uid": uid,
        "pid": pid,
        "tid": team["tid"],
        "title": title,
        "url": url
    }

    validate(writeup_schema, writeup)

    db.writeups.insert(writeup)

    api.cache.invalidate_memoization(api.problem.get_problem, {"args":pid})
    # TODO: achievement handling

def remove_writeup(wid):
    """
    Removes a writeup from the given database.

    Args:
        wid: the wid of the writeup to remove.
    Returns:
        The removed writeup object.
    """

    db = api.common.get_conn()
    writeup = db.writeups.find_one({'wid': wid}, {'_id': 0})
    db.writeups.remove({'wid': wid})
    db.writeup_votes.remove({'wid': wid})
    return writeup

def get_votes_by(uid=None, tid=None):
    db = api.common.get_conn()
    match = {}
    if uid is not None:
        match.update({"uid": uid})
    elif tid is not None:
        match.update({"tid": tid})
    return list(db.writeup_votes.find(match, {"_id":0}))

def get_voted_on(uid=None, tid=None):
    votes = get_votes_by(uid, tid)
    return [v["wid"] for v in votes]

def get_votes_on(wid):
    db = api.common.get_conn()
    match = {}
    return list(db.writeup_votes.find({'wid': wid}, {"_id":0}))

@log_action
def apply_vote(wid, direction):
    db = api.common.get_conn()
    tid = api.user.get_user()["tid"]
    uid = api.user.get_user()["uid"]
    vote = {
        'wid': wid,
        'uid': uid,
        'tid': tid,
        'up': direction
    }
    validate(vote_schema, vote)
    if wid in get_voted_on(uid, tid):
        db.writeup_votes.update({"wid":wid, "tid":tid, "uid":uid}, vote)
    else:
        db.writeup_votes.insert(vote)
    return get_score(wid)

def upvote_writeup(wid):
   return apply_vote(wid, True)

def downvote_writeup(wid):
   return apply_vote(wid, False)

def get_score(wid):
    votes = get_votes_on(wid)
    directions = [v['up'] for v in votes]
    score = sum([(1 if v else (-1)) for v in directions])
    return score
