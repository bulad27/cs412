"""
==========================================================

This is a small simulated coding environment that demonstrates USER MODELING
and ADAPTATION. It reads a user's profile (a "user model") and changes how it
behaves - how much guidance it gives, whether it auto-formats code, how it
phrases error messages, and how prominent its AI-assistance features are -
based on the attributes in that model.

The user model attributes and the adaptation rules they drive are documented
in the accompanying written report; this file only implements them.

Usage:
    python3 adaptive_coding_assistant.py --demo
        Runs the same sample code through BOTH built-in profiles so you can
        see the system behave differently for each one.

    python3 adaptive_coding_assistant.py --profile beginner_learner --file sample_code.py
        Runs one named profile (from user_profiles.json) on a chosen file.

    python3 adaptive_coding_assistant.py --profile experienced_professional --file sample_code.py
"""

import argparse
import ast
import json
import sys
import textwrap

try:
    import black
    HAS_BLACK = True
except ImportError:
    HAS_BLACK = False


def load_profiles(path="user_profiles.json"):
    with open(path, "r") as f:
        return json.load(f)



def analyze_code(code):
    """Return a list of (line_no, short_message, beginner_explanation)."""
    findings = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [(e.lineno or 0, "Syntax error", str(e))]

    for node in ast.walk(tree):
        # bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append((
                node.lineno,
                "Bare 'except:' clause",
                "Catching every exception silently can hide real bugs. "
                "Prefer 'except SomeSpecificError:' so unexpected errors "
                "aren't swallowed.",
            ))
        # mutable default argument
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append((
                        node.lineno,
                        f"Mutable default argument in '{node.name}'",
                        "Lists/dicts as default arguments are created ONCE and "
                        "shared across every call, which can cause surprising "
                        "bugs. Use 'None' and create the list inside the "
                        "function instead.",
                    ))
            if ast.get_docstring(node) is None:
                findings.append((
                    node.lineno,
                    f"'{node.name}' has no docstring",
                    "A short docstring explaining what the function does, "
                    "its parameters, and its return value makes code easier "
                    "for others (and future you) to understand.",
                ))
    return findings


def auto_format(code):
    if HAS_BLACK:
        try:
            return black.format_str(code, mode=black.Mode())
        except Exception:
            return code
    return code


def ai_assistant_response(code, profile):
    if profile["ai_usage"] != "Yes":
        return None

    if profile["ai_preferred_use_case"].startswith("Learning"):
        return (
            "AI Tutor: This function loops over 'items' and adds each value to "
            "'total', then applies a tax multiplier. Concept to review: mutable "
            "default arguments (see the hint above) - this is a very common "
            "beginner pitfall in Python. Want a short explanation of how "
            "Python default arguments work?"
        )
    else:
        return (
            "AI Quick-Fix: Suggest replacing the manual loop with "
            "'sum(items)', and giving 'discounts' a default of 'None' instead "
            "of a mutable list. Apply suggested fixes? [y/n]"
        )


def run_session(code, profile, out=sys.stdout):
    def p(line=""):
        print(line, file=out)

    p("=" * 72)
    p(f" SESSION FOR USER MODEL: {profile['profile_name']}")
    p("=" * 72)
    p("User model (attributes considered by the system):")
    for key in ("experience_level", "primary_goal", "ai_usage", "ai_trust",
                "ai_preferred_use_case", "formatting_assistance",
                "guidance_preference"):
        p(f"   - {key}: {profile[key]}")
    p("-" * 72)

    # --- Adaptation Rule 1: formatting assistance --------------------------
    p("[1] FORMATTING ASSISTANCE")
    if profile["formatting_assistance"] == "High":
        formatted = auto_format(code)
        p("Rule: formatting_assistance = High -> auto-format applied automatically.")
        p(formatted.rstrip())
    else:
        p("Rule: formatting_assistance = Low -> formatting left to the user "
          "(available on request only, not applied automatically).")
        p(code.rstrip())
    p()

    p("[2] CODE FEEDBACK / HINTS")
    findings = analyze_code(code)
    if not findings:
        p("No issues detected.")
    else:
        verbose = profile["guidance_preference"] == "High"
        for line_no, short_msg, explanation in findings:
            if verbose:
                p(f"Line {line_no}: {short_msg}")
                p(f"    Why this matters: {explanation}")
            else:
                p(f"Line {line_no}: {short_msg}")
        if verbose:
            p("Rule: guidance_preference = High -> explanations shown alongside every flag.")
        else:
            p("Rule: guidance_preference = Low -> concise flags only, no unsolicited explanations.")
    p()

    p("[3] AI ASSISTANCE PANEL")
    ai_reply = ai_assistant_response(code, profile)
    if ai_reply is None:
        p("Rule: ai_usage != Yes -> AI panel disabled for this user.")
    else:
        visibility = "prominently displayed, open by default" if profile["ai_trust"] == "High" \
            else "available but collapsed until requested"
        p(f"Rule: ai_usage = Yes, ai_trust = {profile['ai_trust']} -> AI panel {visibility}.")
        p(f"    {ai_reply}")
    p()

    p("[4] ERROR MESSAGE STYLE")
    if profile["error_message_style"] == "Verbose":
        p("Rule: error_message_style = Verbose -> system will phrase runtime "
          "errors in plain language with a suggested fix (beginner-friendly).")
    else:
        p("Rule: error_message_style = Concise -> system will show the raw "
          "exception/traceback with no added explanation (fewer prompts, "
          "as preferred by experienced users).")
    p("=" * 72)
    p()


def main():
    parser = argparse.ArgumentParser(description="Adaptive Coding Assistant prototype")
    parser.add_argument("--profile", help="Profile name from user_profiles.json")
    parser.add_argument("--file", help="Path to a Python file to run through the system")
    parser.add_argument("--demo", action="store_true",
                         help="Run the bundled sample code through BOTH built-in profiles")
    args = parser.parse_args()

    profiles = load_profiles()

    if args.demo:
        with open("sample_code.py") as f:
            code = f.read()
        for name in ("beginner_learner", "experienced_professional"):
            run_session(code, profiles[name])
        return

    if not args.profile or not args.file:
        parser.print_help()
        return

    if args.profile not in profiles:
        print(f"Unknown profile '{args.profile}'. Options: {list(profiles)}")
        return

    with open(args.file) as f:
        code = f.read()
    run_session(code, profiles[args.profile])


if __name__ == "__main__":
    main()
