from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
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


class GameRecord(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    generation_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    provider_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
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

    agents: Mapped[list[GameAgentRecord]] = relationship(
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

    round: Mapped[RoundRecord] = relationship(
        back_populates="answers",
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