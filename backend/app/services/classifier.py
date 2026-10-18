"""Rule-based detection of career-related email threads (stdlib only).

Cheap and deterministic for v1. Swap `classify` for an LLM call later if you want
better recall; the rest of the app only depends on its return shape.
"""
import re
from enum import Enum
from typing import Optional


class Category(str, Enum):
    interview = "interview"
    referral_request = "referral_request"
    recruiter = "recruiter"
    internship_application = "internship_application"
    job_opportunity = "job_opportunity"


# Order doubles as tie-break priority (earlier wins).
PRIORITY = [
    Category.interview,
    Category.referral_request,
    Category.recruiter,
    Category.internship_application,
    Category.job_opportunity,
]

THRESHOLD = 3


def _r(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I)


RULES: dict[Category, list[tuple[re.Pattern, int]]] = {
    Category.interview: [
        (_r(r"\binterview(s|ing|er)?\b"), 3),
        (_r(r"\b(phone|technical|coding|video|onsite|on-site|final) (screen|round|assessment)\b"), 3),
        (_r(r"\b(online assessment|coding challenge|take-home|hackerrank|codility|codesignal)\b"), 3),
        (_r(r"\b(schedule|availability|available)\b.{0,40}\b(call|chat|meeting|time|slot)\b"), 1),
    ],
    Category.referral_request: [
        (_r(r"\breferr(al|als|ed|ing)\b"), 3),
        (_r(r"\brefer (me|you|him|her|them)\b"), 3),
        (_r(r"\b(put in a (good )?word|vouch for)\b"), 2),
    ],
    Category.recruiter: [
        (_r(r"\brecruit(er|ers|ing|ment)\b"), 3),
        (_r(r"\btalent (acquisition|partner|team)\b"), 3),
        (_r(r"\b(hiring manager|sourcer)\b"), 2),
        (_r(r"\b(came across|saw|found|reviewed) your (profile|resume|linkedin|background|application)\b"), 3),
        (_r(r"\byour (background|experience) (looks|seems|would be)\b"), 2),
    ],
    Category.internship_application: [
        (_r(r"\b(internship|internships|intern|co-?op)\b"), 3),
        (_r(r"\b(summer|fall|spring|winter) 20\d\d\b"), 1),
        (_r(r"\b(thank you for applying|thanks for applying|application (received|submitted|status)|your application)\b"), 2),
        (_r(r"\bnew[- ]grad\b"), 2),
    ],
    Category.job_opportunity: [
        (_r(r"\b(job|jobs|position|opening|openings|vacancy|role)\b"), 1),
        (_r(r"\b(we('|’)?re hiring|now hiring|job opportunity|open (position|role))\b"), 3),
        (_r(r"\bapplication\b"), 1),
        (_r(r"\b(software|backend|frontend|full[- ]?stack|machine learning|data|sde|ml|ai) (engineer|developer|role|position)\b"), 2),
        (_r(r"\boffer( letter)?\b"), 1),
    ],
}


def classify(subject: str, text: str) -> tuple[Optional[Category], int]:
    """Return (category, score). Category is None when the best score is below THRESHOLD.

    A pattern hit in the subject counts double; a hit in the body counts once.
    """
    best: Optional[Category] = None
    best_score = 0
    for category in PRIORITY:
        score = 0
        for pattern, weight in RULES[category]:
            if pattern.search(subject):
                score += 2 * weight
            elif pattern.search(text):
                score += weight
        if score > best_score:
            best, best_score = category, score
    if best_score >= THRESHOLD:
        return best, best_score
    return None, best_score
