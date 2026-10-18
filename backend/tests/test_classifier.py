from app.services.classifier import Category, classify


def test_interview_wins_tie_over_internship():
    cat, score = classify("Interview invitation - Software Engineer Intern", "")
    assert cat == Category.interview
    assert score >= 3


def test_referral():
    cat, _ = classify("Referral request for SWE role", "Could you refer me?")
    assert cat == Category.referral_request


def test_recruiter_from_body():
    cat, _ = classify("Quick chat?", "I came across your profile and I'm a recruiter at Acme.")
    assert cat == Category.recruiter


def test_internship_application():
    cat, _ = classify("Thank you for applying", "Your application for the Summer 2027 internship was received.")
    assert cat == Category.internship_application


def test_irrelevant_mail_is_ignored():
    cat, _ = classify("Your weekly grocery receipt", "Thanks for shopping with us.")
    assert cat is None
