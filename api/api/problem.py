""" Module for interacting with the problems """

import imp
import pymongo

import api

from datetime import datetime
from api.common import validate, check, safe_fail, InternalException, SevereInternalException, WebException
from voluptuous import Schema, Length, Required, Range
from bson import json_util
from os.path import join, isfile

from api.annotations import log_action
from api.writeups import get_writeups_for_problem

grader_base_path = "./graders"

submission_schema = Schema({
    Required("tid"): check(
        ("This does not look like a valid tid.", [str, Length(max=100)])),
    Required("pid"): check(
        ("This does not look like a valid pid.", [str, Length(max=100)])),
    Required("key"): check(
        ("This does not look like a valid key.", [str, Length(max=100)])),
    Required("points"): check(
        ("Points must be a positive integer.", [int, Range(min=0)])),
    Required("index"): check(
        ("Index must be a positive integer.", [int, Range(min=0)]))
})

grader_schema = Schema({
    Required("grader"): check(
        ("The grader path must be a string.", [str])),
    Required("score"): check(
        ("Score must be a positive integer.", [int, Range(min=0)]))
})

problem_schema = Schema({
    Required("name"): check(
        ("The problem's display name must be a string.", [str])),
    Required("category"): check(
        ("Category must be a string.", [str])),
    Required("description"): check(
        ("The problem description must be a string.", [str])),
    Required("threshold"): check(
        ("Threshold must be a positive integer.", [int, Range(min=0)])),
    "disabled": check(
        ("A problem's disabled state is either True or False.", [
            lambda disabled: type(disabled) == bool])),
    "autogen": check(
        ("A problem should either be autogenerated or not, True/False", [
            lambda autogen: type(autogen) == bool])),
    "related_problems": check(
        ("Related problems should be a list of related problems.", [list])),
    "score": check(
        ("You should not specify a score for a problem (specify it to its graders instead).",
            [lambda _:False])),
    "grader_count": check(
        ("You should not specify a grader count for a problem.", [lambda _: False])),
    "pid": check(
        ("You should not specify a pid for a problem.", [lambda _: False])),
    "weightmap": check(
        ("Weightmap should be a dict.", [dict])),
    "tags": check(
        ("Tags must be described as a list.", [list])),
    "hint": check(
        ("A hint must be a string.", [str])),
    "generator": check(
        ("A generator must be a path.", [str])),
    "_id": check(
        ("Your problems should not already have _ids.", [lambda id: False])),
    "graders": check(
        ("graders must be a dict.", [dict]))
})

def get_all_categories(show_disabled=False):
    """
    Gets the set of distinct problem categories.

    Args:
        show_disabled: Whether to include categories that are only on disabled problems
    Returns:
        The set of distinct problem categories.
    """

    db = api.common.get_conn()

    match = {}
    if not show_disabled:
        match.update({"disabled": False})

    return db.problems.find(match).distinct("category")

#TODO: Sanity checks for autogen
def analyze_problems():
    """
    Checks the sanity of inserted problems.
    Includes weightmap and grader verification.

    Returns:
        A list of error strings describing the problems.
    """

    grader_missing_error = "{}: Missing grader at '{}'."
    unknown_weightmap_pid = "{}: Has weightmap entry '{}' which does not exist."

    problems = get_all_problems()

    errors = []

    for problem in problems:
        for grader in problem['graders']:
            if not isfile(join(grader_base_path, grader['grader'])):
                errors.append(grader_missing_error.format(problem["name"], grader["grader"]))

        for pid in problem["weightmap"].keys():
            if safe_fail(get_problem, pid=pid) is None:
                errors.append(unknown_weightmap_pid.format(problem["name"], pid))
    return errors

def insert_problem(problem):
    """
    Inserts a problem into the database. Does sane validation.

    Args:
        Problem dict.
        score: points awarded for completing the problem.
        category: problem's category
        description: description of the problem.
        graders: list of dictionaries containing grader paths and scores.
        threshold: Amount of points necessary for a team to unlock this problem.

        Optional:
        disabled: True or False. Defaults to False.
        hint: hint for completing the problem.
        tags: list of problem tags.
        relatedproblems: list of related problems.
        weightmap: problem's unlock weightmap
        autogen: Whether or not the problem will be auto generated.
    Returns:
        The newly created problem id.
    """

    db = api.common.get_conn()

    validate(problem_schema, problem)

    problem["pid"] = api.common.hash(problem["name"])
    problem["disabled"] = problem.get("disabled", False)

    score = 0
    for grader in problem['graders']:
        score += grader['score']
        validate(grader_schema, grader)

    problem['score'] = score
    problem['grader_count'] = len(problem['graders'])

    weightmap = {}

    if problem.get("weightmap"):
        for name, weight in problem["weightmap"].items():
            name_hash = api.common.hash(name)
            weightmap[name_hash] = weight

    problem["weightmap"] = weightmap

    if safe_fail(get_problem, pid=problem["pid"]) is not None:
        raise WebException("Problem with identical pid already exists.")

    if safe_fail(get_problem, name=problem["name"]) is not None:
        raise WebException("Problem with identical name already exists.")

    db.problems.insert(problem)
    api.cache.fast_cache.clear()

    return problem["pid"]

def remove_problem(pid):
    """
    Removes a problem from the given database.

    Args:
        pid: the pid of the problem to remove.
    Returns:
        The removed problem object.
    """

    db = api.common.get_conn()
    problem = get_problem(pid=pid)

    db.problems.remove({"pid": pid})
    api.cache.fast_cache.clear()

    return problem

def set_problem_disabled(pid, disabled):
    """
    Updates a problem's availability.

    Args:
        pid: the problem's pid
        disabled: whether or not the problem should be disabled.
    Returns:
        The updated problem object.
    """

    return update_problem(pid, {"disabled": disabled})

def update_problem(pid, updated_problem):
    """
    Updates a problem with new properties.

    Args:
        pid: the pid of the problem to update.
        updated_problem: an updated problem object.
    Returns:
        The updated problem object.
    """

    db = api.common.get_conn()

    if updated_problem.get("name", None) is not None:
        if safe_fail(get_problem, name=updated_problem["name"]) is not None:
            raise WebException("Problem with identical name already exists.")

    problem = get_problem(pid=pid, show_disabled=True).copy()
    problem.update(updated_problem)

    # pass validation by removing/readding pid
    problem.pop("pid", None)
    validate(problem_schema, problem)
    problem["pid"] = pid

    db.problems.update({"pid": pid}, problem)
    api.cache.fast_cache.clear()

    return problem

def search_problems(*conditions):
    """
    Aggregates all problems that contain all of the given properties from the list specified.

    Args:
        conditions: multiple mongo queries to search.
    Returns:
        The list of matching problems.
    """

    db = api.common.get_conn()

    return list(db.problems.find({"$or": list(conditions)}, {"_id":0}))

def insert_problem_from_json(blob):
    """
    Converts json blob of problem(s) into dicts. Runs insert_problem on each one.
    See insert_problem for more information.

    Returns:
        A list of the created problem pids if an array of problems is specified.
    """

    result = json_util.loads(blob)

    if type(result) == list:
        return [insert_problem(problem) for problem in result]
    elif type(result) == dict:
        return insert_problem(result)
    else:
        raise InternalException("JSON blob does not appear to be a list of problems or a single problem.")

@api.cache.memoize(timeout=60, fast=True)
def get_graders(pid):
    """
    Returns the grader modules for a given problem.

    Args:
        pid: the problem id
    Returns:
        The grader modules as a list.
    """

    modules = []
    prob = get_problem(pid=pid, show_disabled=True)
    for grader in prob['graders']:
        try:
            path = grader["grader"]
            mod = imp.load_source(path[:-3], join(grader_base_path, path))
            modules.append((mod, grader['score']))
        except FileNotFoundError:
            raise InternalException("Problem grader for {} is offline.".format(prob['name']))
    return modules

def grade_problem(pid, key, tid=None):
    """
    Grades the problem with its associated grader script.

    Args:
        tid: tid if provided
        pid: problem's pid
        key: user's submission
    Returns:
        A dict.
        correct: boolean
        points: number of points the problem is worth.
        message: message returned from the grader.
    """

    if tid is None:
        tid = api.user.get_user()["tid"]

    #If the problem is autogenerated, let
    #api.autogen deal with it.
    if api.autogen.is_autogen_problem(pid):
        return api.autogen.grade_problem_instance(pid, tid, key)

    problem = get_problem(pid=pid, show_disabled=True)
    graders = get_graders(pid)

    correct, message = False, None
    score = 0
    idx = 0
    for i in range(len(graders)):
        grader = graders[i]
        (correct, message) = grader[0].grade(tid, key)
        if correct:
            score = grader[1]
            idx = i
            break

    return {
        "correct": correct,
        "points": score,
        "message": message,
        "index": idx
    }

@log_action
def submit_key(tid, pid, key, uid=None, ip=None):
    """
    User problem submission. Problem submission is inserted into the database.

    Args:
        tid: user's team id
        pid: problem's pid
        key: answer text
        uid: user's uid
    Returns:
        A dict.
        correct: boolean
        points: number of points the problem is worth.
        message: message returned from the grader.
    """

    db = api.common.get_conn()
    validate(submission_schema, {"tid": tid, "pid": pid, "key": key, 'points': 0, 'index': 0})

    if pid not in get_unlocked_pids(tid):
        raise InternalException("You can't submit flags to problems you haven't unlocked.")

    if pid in get_solved_pids(tid=tid):
        exp = WebException("You have already solved this problem.")
        exp.data = {'code': 'solved'}
        raise exp

    user = api.user.get_user(uid=uid)
    if user is None:
        raise InternalException("User submitting flag does not exist.")

    uid = user["uid"]

    result = grade_problem(pid, key, tid)

    problem = get_problem(pid=pid)

    eligibility = api.team.get_team(tid=tid)['eligible']

    submission = {
        'uid': uid,
        'tid': tid,
        'timestamp': datetime.utcnow(),
        'pid': pid,
        'ip': ip,
        'key': key,
        'index': result['index'],
        'points': result['points'],
        'eligible': eligibility,
        'category': problem['category'],
        'correct': result['correct']
    }

    subs = get_submissions(tid=tid)
    if (key, pid) in [(submission["key"], submission["pid"]) for submission in subs]:
        exp = WebException("You or one of your teammates has already tried this solution.")
        exp.data = {'code': 'repeat'}
        raise exp

    if submission['correct']:
        idx = result['index']
        if (pid, idx) in [(sub['pid'], sub['index']) for sub in subs]:
            exp = WebException("You have already solved this subpart!")
            exp.data = {'code': 'solved'}
            raise exp

    db.submissions.insert(submission)

    if submission["correct"]:
        api.cache.invalidate_memoization(api.stats.get_score, {"kwargs.tid":tid}, {"kwargs.uid":uid})
        api.cache.invalidate_memoization(get_unlocked_pids, {"args":tid})
        api.cache.invalidate_memoization(get_solved_pids, {"kwargs.tid":tid}, {"kwargs.uid":uid})

        api.cache.invalidate_memoization(api.stats.get_score_progression, {"kwargs.tid":tid}, {"kwargs.uid":uid})

        api.achievement.process_achievements("submit", {"uid": uid, "tid": tid, "pid": pid})

    return result


def count_submissions(pid=None, uid=None, tid=None, category=None, correctness=None, eligibility=None):
    db = api.common.get_conn()
    match = {}
    if uid is not None:
        match.update({"uid": uid})
    elif tid is not None:
        match.update({"tid": tid})

    if pid is not None:
        match.update({"pid": pid})

    if category is not None:
        match.update({"category": category})

    if correctness is not None:
        match.update({"correct": correctness})

    if eligibility is not None:
        match.update({"eligible": eligibility})

    return db.submissions.find(match, {"_id": 0}).count()


def get_submissions(pid=None, uid=None, tid=None, category=None, correctness=None, eligibility=None):
    """
    Gets the submissions from a team or user.
    Optional filters of pid or category.

    Args:
        uid: the user id
        tid: the team id

        category: category filter.
        pid: problem filter.
        correctness: correct filter
    Returns:
        A list of submissions from the given entity.
    """

    db = api.common.get_conn()

    match = {}

    if uid is not None:
        match.update({"uid": uid})
    elif tid is not None:
        match.update({"tid": tid})

    if pid is not None:
        match.update({"pid": pid})

    if category is not None:
        match.update({"category": category})

    if correctness is not None:
        match.update({"correct": correctness})

    if eligibility is not None:
        match.update({"eligible": eligibility})

    return list(db.submissions.find(match, {"_id":0}))

def clear_all_submissions():
    """
    Removes all submissions from the database.
    """

    db = api.common.get_conn()
    db.submissions.remove()

def clear_submissions(uid=None, tid=None, pid=None):
    """
    Clear submissions for a given team, user, or problems.

    Args:
        uid: the user's uid to clear from.
        tid: the team's tid to clear from.
        pid: the pid to clear from.
    """

    db = api.common.get_conn()

    match = {}


    if pid is not None:
        match.update({"pid", pid})
    elif uid is not None:
        match.update({"uid": uid})
    elif tid is not None:
        match.update({"tid": tid})
    else:
        raise InternalException("You must supply either a tid, uid, or pid")

    return db.submissions.remove(match)

def invalidate_submissions(pid=None, uid=None, tid=None):
    """
    Invalidates the submissions for a given problem. Can be filtered by uid or tid.
    Passing no arguments will invalidate all submissions.

    Args:
        pid: the pid of the problem.
        uid: the user's uid that will his submissions invalidated.
        tid: the team's tid that will have their submissions invalidated.
    """

    db = api.common.get_conn()

    match = {}

    if pid is not None:
        match.update({"pid": pid})

    if uid is not None:
        match.update({"uid": uid})
    elif tid is not None:
        match.update({"tid": tid})

    db.submissions.update(match, {"correct": False})

def reevaluate_submissions_for_problem(pid):
    """
    In the case of the problem or grader being updated, this will reevaluate submissions for a problem.

    Args:
        pid: the pid of the problem to be reevaluated.
    """

    db = api.common.get_conn()

    get_problem(pid=pid, show_disabled=True)

    keys = {}
    for submission in get_submissions(pid=pid):
        key = submission["key"]
        if key not in keys:
            result = grade_problem(pid, key, submission["tid"])
            if result["correct"] != submission["correct"]:
                keys[key] = result["correct"]
            else:
                keys[key] = None

    for key, change in keys.items():
        if change is not None:
            db.submissions.update({"key": key}, {"$set": {"correct": change}}, multi=True)

def reevaluate_all_submissions():
    """
    In the case of the problem or grader being updated, this will reevaluate all submissions.
    """

    api.cache.clear_all()
    for problem in get_all_problems(show_disabled=True):
        reevaluate_submissions_for_problem(problem["pid"])

def get_problem(pid=None, name=None, tid=None, show_disabled=False):
    """
    Gets a single problem.

    Args:
        pid: The problem id
        name: The name of the problem
        show_disabled: Boolean indicating whether or not to show disabled problems.
    Returns:
        The problem dictionary from the database
    """

    db = api.common.get_conn()

    match = {}

    if pid is not None:
        match.update({'pid': pid})
    elif name is not None:
        match.update({'name': name})
    else:
        raise InternalException("Must supply pid or display name")

    if tid is not None and pid not in get_unlocked_pids(tid):
        raise InternalException("You cannot get this problem")

    if not show_disabled:
        match.update({"disabled": False})

    db = api.common.get_conn()
    problem = db.problems.find_one(match, {"_id":0})

    if problem is None:
        raise SevereInternalException("Could not find problem! You gave " + str(match))

    writeups = get_writeups_for_problem(pid)
    problem['writeups'] = writeups

    return problem

def get_all_problems(category=None, show_disabled=False):
    """
    Gets all of the problems in the database.

    Args:
        category: Optional parameter to restrict which problems are returned
        show_disabled: Boolean indicating whether or not to show disabled problems.
    Returns:
        List of problems from the database
    """

    db = api.common.get_conn()

    match = {}
    if category is not None:
        match.update({'category': category})

    if not show_disabled:
        match.update({'disabled': False})

    return list(db.problems.find(match, {"_id":0}).sort('score', pymongo.ASCENDING))

def get_solve_counts(tid=None, uid=None, category=None):
    partially_solved_pids = [sub['pid'] for sub in get_submissions(tid=tid, uid=uid, category=category, correctness=True)]
    counts = {pid: partially_solved_pids.count(pid) for pid in set(partially_solved_pids)}
    return counts

def get_solved_pids(tid=None, uid=None, category=None):
    """
    Gets the solved pids for a given team or user.

    Args:
        tid: The team id
        category: Optional parameter to restrict which problems are returned
    Returns:
        List of solved problem ids
    """
    counts = get_solve_counts(tid, uid, category)
    solved = []
    for pid in counts:
        prob = get_problem(pid)
        if prob['grader_count'] == counts[pid]:
            solved.append(pid)
    return list(set(solved))

def get_solved_problems(tid=None, uid=None, category=None):
    """
    Gets the solved problems for a given team or user.

    Args:
        tid: The team id
        category: Optional parameter to restrict which problems are returned
    Returns:
        List of solved problem dictionaries
    """
    return [get_problem(pid=pid) for pid in get_solved_pids(tid=tid, uid=uid, category=category)]

def get_unlocked_pids(tid, category=None):
    """
    Gets the unlocked pids for a given team.

    Args:
        tid: The team id
        category: Optional parameter to restrict which problems are returned
    Returns:
        List of unlocked problem ids
    """

    solved = get_solved_problems(tid=tid, category=category)

    unlocked = []
    for problem in get_all_problems():
        if 'weightmap' not in problem or 'threshold' not in problem:
            unlocked.append(problem['pid'])
        else:
            weightsum = sum(problem['weightmap'].get(p['pid'], 0) for p in solved)
            if weightsum >= problem['threshold']:
                unlocked.append(problem['pid'])

    return unlocked

def get_unlocked_problems(tid, category=None):
    """
    Gets the unlocked problems for a given team.

    Args:
        tid: The team id
        category: Optional parameter to restrict which problems are returned
    Returns:
        List of unlocked problem dictionaries
    """
    counts = get_solve_counts(tid=tid)
    solved = get_solved_pids(tid=tid)
    unlocked = [get_problem(pid=pid) for pid in get_unlocked_pids(tid, category=category)]
    for problem in unlocked:
        if api.autogen.is_autogen_problem(problem["pid"]):
            problem.update(api.autogen.get_problem_instance(problem["pid"], tid))
        problem['solved'] = problem['pid'] in solved
        if problem['pid'] in counts:
            problem['solve_count'] = counts[problem['pid']]
        else:
            problem['solve_count'] = 0
    return unlocked
