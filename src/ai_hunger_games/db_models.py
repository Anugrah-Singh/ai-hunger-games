from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ExperimentRecord(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_experiments_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=utc_now,
    )

    # A legacy imported history has no reliable provider configuration. New
    # experiments set this at creation and cannot later mix provider data.
    provider_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    games: Mapped[list[GameRecord]] = relationship(
        back_populates="experiment",
    )

    initial_agents: Mapped[list[ExperimentInitialAgentRecord]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
    )

    configuration: Mapped[ExperimentConfigurationRecord | None] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ExperimentConfigurationRecord(Base):
    __tablename__ = "experiment_configurations"

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        primary_key=True,
    )

    questions_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    candidate_order_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    voting_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    elimination_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    replacement_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    seed_stride: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    answer_timeout_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    answer_minimum_successful_answers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    answer_maximum_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    answer_initial_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    answer_maximum_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    answer_maximum_concurrent_requests: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vote_timeout_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vote_maximum_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    vote_initial_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    vote_maximum_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    personality_timeout_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    personality_maximum_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    personality_initial_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    personality_maximum_retry_delay_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    experiment: Mapped[ExperimentRecord] = relationship(
        back_populates="configuration",
    )


class ExperimentInitialAgentRecord(Base):
    __tablename__ = "experiment_initial_agents"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "position",
            name="uq_experiment_initial_agents_position",
        ),
        UniqueConstraint(
            "experiment_id",
            "agent_id",
            name="uq_experiment_initial_agents_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    experiment: Mapped[ExperimentRecord] = relationship(
        back_populates="initial_agents",
    )


class GameRecord(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index(
            "uq_games_experiment_generation_number",
            "experiment_id",
            "generation_number",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    generation_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Migration 0006 backfills historical games and migration 0008 rebuilds
    # SQLite's table so this boundary is enforced as physically non-null.
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id"),
        nullable=False,
        index=True,
    )

    provider_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    candidate_order_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    voting_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    elimination_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    replacement_seed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    eliminated_agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    replacement_agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    replacement_personality_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    replacement_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    replacement_answer_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=utc_now,
    )

    experiment: Mapped[ExperimentRecord] = relationship(
        back_populates="games",
    )

    agents: Mapped[list[GameAgentRecord]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )

    final_agents: Mapped[list[GameFinalAgentRecord]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )

    rounds: Mapped[list[RoundRecord]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )


class GameAgentRecord(Base):
    __tablename__ = "game_agents"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "agent_id",
            name="uq_game_agents_game_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    answer_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    was_eliminated: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    game: Mapped[GameRecord] = relationship(
        back_populates="agents",
    )


class GameFinalAgentRecord(Base):
    __tablename__ = "game_final_agents"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "position",
            name="uq_game_final_agents_game_position",
        ),
        UniqueConstraint(
            "game_id",
            "agent_id",
            name="uq_game_final_agents_game_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    agent_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    personality_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    answer_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    game: Mapped[GameRecord] = relationship(
        back_populates="final_agents",
    )


class RoundRecord(Base):
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "round_number",
            name="uq_rounds_game_round_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    game: Mapped[GameRecord] = relationship(
        back_populates="rounds",
    )

    answers: Mapped[list[AnswerRecord]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )

    votes: Mapped[list[VoteRecord]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )

    failures: Mapped[list[AnswerFailureRecord]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )

    scores: Mapped[list[RoundScoreRecord]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan",
    )


class AnswerRecord(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_answers_round_agent",
        ),
        UniqueConstraint(
            "round_id",
            "candidate_id",
            name="uq_answers_round_candidate",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    round_id: Mapped[int] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    candidate_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    round: Mapped[RoundRecord] = relationship(
        back_populates="answers",
    )


class AnswerFailureRecord(Base):
    __tablename__ = "answer_failures"
    __table_args__ = (
        UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_answer_failures_round_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    round_id: Mapped[int] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    error_type: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    retry_after_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    round: Mapped[RoundRecord] = relationship(
        back_populates="failures",
    )


class VoteRecord(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "round_id",
            "voter_agent_id",
            name="uq_votes_round_voter",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    round_id: Mapped[int] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    voter_agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    selected_candidate_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    selected_agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    round: Mapped[RoundRecord] = relationship(
        back_populates="votes",
    )


class RoundScoreRecord(Base):
    __tablename__ = "round_scores"
    __table_args__ = (
        UniqueConstraint(
            "round_id",
            "agent_id",
            name="uq_round_scores_round_agent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    round_id: Mapped[int] = mapped_column(
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    round: Mapped[RoundRecord] = relationship(
        back_populates="scores",
    )
