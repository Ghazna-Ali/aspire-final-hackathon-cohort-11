"""
Additional CareerOps AI features.

Each feature reuses an EXISTING agent from agents.py and adds a new Task.
Nothing in agents.py or tasks.py is modified. app.py merges the registries
below into its own AGENTS / TASKS / AGENT_DESCRIPTIONS dictionaries.

    Feature                   Agent used
    ------------------------  -----------------
    Job Match Score           CV Analyst
    Skill Gap Detector        CV Analyst
    Cover Letter Generation   Application Agent
    Career Roadmap            Manager Agent
"""
from agents import research_agent  # already imported if present; keep single import at top

import re

from crewai import Task

from agents import (
    manager_agent,
    cv_agent,
    application_agent,
)


# ============================================================
# 1. JOB MATCH SCORE  (CV Analyst)
# ============================================================

job_match_score_task = Task(
    description="""
Calculate how well the candidate matches the target job.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

Score each category from 0 to 100 using this rubric:
- Technical Skills (weight 40%): share of the required and preferred
  technical skills and tools that the CV actually demonstrates.
- Experience and Projects (weight 30%): relevance and level of the
  candidate's work experience and projects compared with the role.
- Education and Certifications (weight 10%): fit of degree, field,
  and certifications.
- Keywords and Soft Skills (weight 20%): coverage of the job's
  important keywords and soft skills.

Be strict and consistent. Missing evidence lowers the score.
Never assume a skill that is not written in the CV.

Calculate the overall score as:
0.40 x Technical + 0.30 x Experience + 0.10 x Education + 0.20 x Keywords
and round it to a whole number.

Write the answer in Markdown using EXACTLY this structure:

## Overall Match Score: <number>%

**Verdict:** one sentence summarizing the fit.

## Score Breakdown

- **Technical Skills:** <number>/100 (weight 40%) - reason
- **Experience and Projects:** <number>/100 (weight 30%) - reason
- **Education and Certifications:** <number>/100 (weight 10%) - reason
- **Keywords and Soft Skills:** <number>/100 (weight 20%) - reason

## Why You Match
Bullet points. Each one names a job requirement and the CV evidence for it.

## Why the Score Is Not Higher
Bullet points. Each one names a job requirement and what the CV lacks.

## Fastest Ways to Raise Your Score
3 to 5 specific, truthful actions.

Do not invent qualifications, experience, projects, or achievements.
If something is absent, write: Not found in the provided documents.
""",
    expected_output="""
A Markdown report that starts with the overall match score as a
percentage, followed by a four-category score breakdown, reasons for
the match, reasons for missing points, and ways to improve the score.
""",
    agent=cv_agent,
)


# ============================================================
# 2. SKILL GAP DETECTOR  (CV Analyst)
# ============================================================

skill_gap_task = Task(
    description="""
Identify the skills the job requires that are missing or weak in the CV.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

Go through every skill, tool, technology, qualification, and experience
requirement in the job description and check it against the CV.

Classify each gap as:
- Missing: not found anywhere in the CV.
- Weak: mentioned only briefly, or listed without a project or
  experience that proves it.

Rate each gap's importance:
- Critical: stated as required or central to the role.
- Important: stated as preferred or used often in the responsibilities.
- Nice-to-have: minor or optional.

Write the answer in Markdown using this structure:

## Skill Gap Summary
One short paragraph, plus the counts: critical gaps, important gaps,
nice-to-have gaps.

## Skill Gaps

| Skill | Status | Importance | What the job asks | What the CV shows |
| ----- | ------ | ---------- | ----------------- | ----------------- |

List Critical gaps first, then Important, then Nice-to-have.
For "What the CV shows" write: Not found in the provided documents.
when the skill is completely absent.

## Skills You Already Demonstrate
Required skills the CV clearly supports, each with a short piece of
evidence from the CV.

## Quick Wins
Gaps the candidate could close or show evidence for within a few days,
using only experience they already have (for example by rewording or
adding a detail they can truthfully claim).

Do not invent skills, experience, or requirements.
""",
    expected_output="""
A Markdown skill gap report with a summary, a table of missing and weak
skills ranked by importance, skills the candidate already demonstrates,
and quick wins.
""",
    agent=cv_agent,
)


# ============================================================
# 3. COVER LETTER GENERATION  (Application Agent)
# ============================================================

cover_letter_task = Task(
    description="""
Write a customized cover letter for this candidate and job.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

Instructions:
- Use the company name, hiring manager name, and preferred tone if they
  appear in the career request or the job description. If they are not
  given, use the greeting "Dear Hiring Team" and a professional, warm tone.
- Use the candidate's real name from the CV for the sign-off. If the
  name is not in the CV, sign off with [Your Name].
- Length: 280 to 350 words in 3 to 4 short paragraphs.
- Start with a specific opening tied to the role, not "I am writing to apply".
- Include 2 or 3 real examples from the CV (projects, experience,
  achievements) that match the job's main requirements.
- If the candidate lacks a required skill, do NOT claim it. You may
  briefly express motivation to learn it.
- Do not invent experience, skills, achievements, employers, or numbers.

Write the answer in Markdown using this structure:

## Cover Letter

(the complete letter, ready to copy and paste)

## What This Letter Emphasizes
3 to 5 bullets naming the job requirements the letter addresses and the
CV evidence used.

## Before You Send
2 or 3 bullets for details the candidate should check or personalize
(for example company name or a missing detail).
""",
    expected_output="""
A complete, truthful, ready-to-send cover letter of about 300 words,
followed by a short list of what it emphasizes and what to check
before sending.
""",
    agent=application_agent,
)


# ============================================================
# 4. CAREER ROADMAP  (Manager Agent)
# ============================================================

career_roadmap_task = Task(
    description="""
Create a practical learning and career roadmap for the candidate.

CANDIDATE CV:
{cv_text}

TARGET JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

First work out, from the CV and the job description only:
- the candidate's current skills,
- the candidate's weaknesses and skill gaps for this target job,
- the target job title and its key requirements.

Then build the roadmap.

Timeframe and study time: use the timeframe and weekly hours stated in
the career request. If they are not stated, assume 90 days and 8 hours
per week.

Write the answer in Markdown using this structure:

## Where You Stand
Two or three sentences about the current position against the target job.

## Your Strengths
Skills from the CV that already match the job.

## Priority Skills to Build
A ranked table: Skill | Why it matters for this job | Priority.
Critical gaps first. Only include skills the job really needs.

## Phase-by-Phase Plan
Split the timeframe into 3 phases. For each phase give:
- Focus skills
- Weekly actions (realistic for the stated weekly hours)
- One hands-on mini-project
- A milestone that proves progress

## Portfolio Projects
One or two projects that would directly demonstrate the missing skills
for this role.

## Learning Resources
Suggest types of resources and well-known official documentation or
courses by name. Do NOT invent URLs.

## Application Strategy
When to start applying, and what to emphasize in the meantime.

## Interview Preparation
5 likely interview questions based on the job and the gaps.

Never invent facts about the candidate. If something is absent from the
CV, write: Not found in the provided documents.
""",
    expected_output="""
A Markdown career roadmap with the candidate's current standing,
prioritized skills to build, a three-phase plan with projects and
milestones, portfolio ideas, learning resources, application strategy,
and interview preparation.
""",
    agent=manager_agent,
)


# ============================================================
# REGISTRIES (merged into app.py's AGENTS / TASKS / DESCRIPTIONS)
# ============================================================

FEATURE_AGENTS = {
    "Job Match Score": cv_agent,
    "Skill Gap Detector": cv_agent,
    "Cover Letter Generation": application_agent,
    "Career Roadmap": manager_agent,
}

FEATURE_TASKS = {
    "Job Match Score": job_match_score_task,
    "Skill Gap Detector": skill_gap_task,
    "Cover Letter Generation": cover_letter_task,
    "Career Roadmap": career_roadmap_task,
}

FEATURE_DESCRIPTIONS = {
    "Job Match Score": (
        "(CV Analyst) Get a match percentage between your CV and the "
        "job, with a category breakdown and reasons."
    ),
    "Skill Gap Detector": (
        "(CV Analyst) Find required job skills that are missing or "
        "weak in your CV, ranked by importance."
    ),
    "Cover Letter Generation": (
        "(Application Agent) Generate a customized cover letter based "
        "on your CV and the job description."
    ),
    "Career Roadmap": (
        "(Manager Agent) Get a learning and career roadmap built from "
        "your skills, weaknesses, and target job. You can state a "
        "timeframe and weekly study hours in the career request."
    ),
}


# ============================================================
# MATCH SCORE PARSING (used by app.py to show a score meter)
# ============================================================

_SCORE_WEIGHTS = {
    "Technical Skills": 0.40,
    "Experience and Projects": 0.30,
    "Education and Certifications": 0.10,
    "Keywords and Soft Skills": 0.20,
}


def _clamp(value, low=0, high=100):
    return max(low, min(high, int(value)))


def parse_match_score(text):
    """
    Read the score lines from a Job Match Score result.

    Returns {"overall": int, "breakdown": {category: int}} or None if
    nothing could be parsed. When all four category scores are present
    the overall score is recalculated from them, so the number shown in
    the UI always matches the stated weights.
    """

    if not text:
        return None

    breakdown = {}

    for category in _SCORE_WEIGHTS:
        match = re.search(
            re.escape(category) + r"\W+(\d{1,3})\s*/\s*100",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            breakdown[category] = _clamp(match.group(1))

    if len(breakdown) == len(_SCORE_WEIGHTS):
        overall = round(
            sum(breakdown[c] * w for c, w in _SCORE_WEIGHTS.items())
        )
        return {"overall": _clamp(overall), "breakdown": breakdown}

    match = re.search(
        r"Overall Match Score\W+(\d{1,3})",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return {"overall": _clamp(match.group(1)), "breakdown": breakdown}

    return None

# ============================================================
# MARKET CHECK FEATURES (Research / Manager agents)
# ============================================================


job_legitimacy_task = Task(
    description="""
Assess whether this job posting looks legitimate or risky.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST (optional context):
{career_request}

Evaluate red flags and green flags for scam or low-quality postings:
- Vague salary, urgency pressure, unpaid "training", crypto/payment requests
- Grammar quality, company contactability, role clarity
- Requirements that don't match the title
- Remote/work-from-home scam patterns

Write Markdown with EXACTLY this structure:

## Legitimacy Score: <0-100>
**Verdict:** one sentence (Likely legitimate / Mixed / High risk)

## Green Flags
- bullet list

## Red Flags
- bullet list

## What To Verify Before Applying
- 3 to 5 concrete checks (company domain, LinkedIn, official careers page)

## Recommendation
One short paragraph: apply / apply with caution / avoid.

Do not invent company facts. If unknown, write: Not verifiable from the provided text.
""",
    expected_output="Markdown legitimacy report with score, flags, checks, recommendation.",
    agent=research_agent,
)

company_check_task = Task(
    description="""
Analyze the employer using only the job description and any company names in the request.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

Structure:

## Company Snapshot
What can be inferred (industry, size signals, location, product). Mark unknowns clearly.

## Reputation Signals
Positive and negative signals from the text only (not invented news).

## Role Fit For This Company
How the role typically sits in such an organization.

## Questions To Ask Recruiters
5 sharp questions.

## Risk Notes
Anything unclear or inconsistent.

Never invent funding, ratings, or scandals. Say when evidence is missing.
""",
    expected_output="Markdown company analysis from provided text only.",
    agent=research_agent,
)

similar_roles_task = Task(
    description="""
Suggest similar job directions based on this CV and target job.

CANDIDATE CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CAREER REQUEST:
{career_request}

Structure:

## Target Role Summary
One short paragraph.

## Similar Role Titles
Table: Role title | Why similar | Typical seniority

List 6 to 10 realistic alternative titles (not fantasy jobs).

## Adjacent Career Paths
3 paths with a one-line reason each.

## Skills That Transfer
Bullet list.

## Where To Search
Job boards / query keywords (no fake URLs required).

Stay realistic and tied to the CV and job text.
""",
    expected_output="Markdown list of similar roles and transferable paths.",
    agent=manager_agent,
)

# Merge into existing registries (add these lines next to FEATURE_* updates)
FEATURE_AGENTS.update({
    "Job Legitimacy Check": research_agent,
    "Company Check": research_agent,
    "Similar Roles": manager_agent,
})
FEATURE_TASKS.update({
    "Job Legitimacy Check": job_legitimacy_task,
    "Company Check": company_check_task,
    "Similar Roles": similar_roles_task,
})
FEATURE_DESCRIPTIONS.update({
    "Job Legitimacy Check": (
        "(Research) Score how legitimate the posting looks and list red/green flags."
    ),
    "Company Check": (
        "(Research) Company snapshot and questions from the job text only."
    ),
    "Similar Roles": (
        "(Manager) Alternative titles and adjacent paths from your CV and target job."
    ),
})



