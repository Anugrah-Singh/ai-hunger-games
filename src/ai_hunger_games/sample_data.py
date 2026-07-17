from ai_hunger_games.models import Agent, Personality

from ai_hunger_games.models import (
    Agent,
    AnswerGenerationPolicy,
    Personality,
    VoteGenerationPolicy,
    PersonalityGenerationPolicy,
)

QUESTIONS = [
    "What quality makes a leader effective?",
    "Should difficult decisions prioritize fairness or results?",
    "What is the greatest strength of a successful team?",
]

CANDIDATE_ORDER_SEED = 42
VOTING_SEED = 7
ELIMINATION_SEED = 99
REPLACEMENT_SEED = 123
REPLACEMENT_AGENT_ID = "agent_5"
ANSWER_POLICY = AnswerGenerationPolicy(
    timeout_seconds=30.0,
    minimum_successful_answers=2,
    maximum_attempts=4,
    initial_retry_delay_seconds=3.0,
    maximum_retry_delay_seconds=20.0,
)
VOTE_POLICY = VoteGenerationPolicy(
    timeout_seconds=30.0,
    maximum_attempts=4,
    initial_retry_delay_seconds=3.0,
    maximum_retry_delay_seconds=20.0,
)
PERSONALITY_POLICY = PersonalityGenerationPolicy(
    timeout_seconds=30.0,
    maximum_attempts=4,
    initial_retry_delay_seconds=3.0,
    maximum_retry_delay_seconds=20.0,
)

AGENTS = [
    Agent(
        id="agent_1",
        name="Philosopher",
        personality=Personality(
            name="Reflective Philosopher",
            answer_template=(
                "A reflective answer to '{question}' is that "
                "effective leadership begins with wisdom, "
                "careful listening, and ethical judgment."
            ),
        ),
    ),
    Agent(
        id="agent_2",
        name="Scientist",
        personality=Personality(
            name="Evidence-Driven Scientist",
            answer_template=(
                "An evidence-based answer to '{question}' is "
                "that effective leaders test assumptions, "
                "study results, and adapt to new information."
            ),
        ),
    ),
    Agent(
        id="agent_3",
        name="Strategist",
        personality=Personality(
            name="Long-Term Strategist",
            answer_template=(
                "From a strategic perspective on '{question}', "
                "an effective leader establishes a clear goal, "
                "anticipates risks, and coordinates execution."
            ),
        ),
    ),
    Agent(
        id="agent_4",
        name="Comedian",
        personality=Personality(
            name="Optimistic Comedian",
            answer_template=(
                "My lighthearted answer to '{question}' is that "
                "a leader needs humility, accountability, and "
                "enough humor to keep the team moving."
            ),
        ),
    ),
]