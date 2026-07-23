export interface Personality {
  name: string;
  description: string;
  answer_template: string;
}

export type ExperimentPreset =
  | "quick_demo"
  | "full_tournament";

export interface CreateExperimentInput {
  name: string;
  preset: ExperimentPreset;
}


export interface Agent {
  agent_id: string;
  agent_name: string;
  personality: Personality;
}


export interface Participant extends Agent {
  total_score: number;
  was_eliminated: boolean;
}


/**
 * Browser-facing answer data is intentionally anonymous. Candidate identifiers
 * only have meaning within their containing round.
 */
export interface AnonymousAnswer {
  candidate_id: string;
  content: string;
  attempt_count: number;
}


/** Browser-facing votes deliberately identify a candidate, not an answerer. */
export interface AnonymousVote {
  voter_agent_id: string;
  selected_candidate_id: string;
}


export interface CandidateScore {
  candidate_id: string;
  score: number;
}


export interface AnswerFailure {
  agent_id: string;
  error_type: string;
  message: string;
  attempt_count: number;
  retry_after_seconds: number | null;
}


export interface Round {
  round_id: number;
  round_number: number;
  question: string;
  answers: AnonymousAnswer[];
  votes: AnonymousVote[];
  scores: CandidateScore[];
  failures: AnswerFailure[];
}


export interface GenerationSeeds {
  candidate_order_seed: number | null;
  voting_seed: number | null;
  elimination_seed: number | null;
  replacement_seed: number | null;
}


export interface GenerationSummary {
  game_id: number;
  generation_number: number;
  provider_name: string;
  created_at: string;
  round_count: number;
  seeds: GenerationSeeds;
  eliminated_agent_id: string;
  replacement_agent: Agent;
}


export interface GenerationDetail extends GenerationSummary {
  starting_agents: Participant[];
  final_agents: Agent[];
  rounds: Round[];
}


export interface ExperimentSummary {
  id: number;
  name: string;
  created_at: string;
  provider_name: string | null;
}


export interface ExperimentDetail extends ExperimentSummary {
  generation_count: number;
  current_population: Agent[];
  can_run: boolean;
  run_block_reason: string | null;
}


export interface GenerationScore {
  generation_number: number;
  total_score: number;
  round_count: number;
  average_points_per_round: number | null;
  was_eliminated: boolean;
  won_generation: boolean;
}


export interface AgentPerformance {
  agent_id: string;
  agent_name: string;
  personality: Personality;
  generation_scores: GenerationScore[];
  total_points: number;
  scored_round_count: number;
  average_points_per_round: number | null;
  survival_count: number;
  elimination_generation: number | null;
  generation_win_count: number;
  generation_win_rate: number | null;
  score_slope_per_generation: number | null;
}


export interface RelationshipPeriod {
  generation_number: number;
  votes: number;
  eligible_voting_opportunities: number;
  expected_random_votes: number;
}


export interface VoteRelationship {
  voter_agent_id: string;
  target_agent_id: string;
  periods: RelationshipPeriod[];
  votes: number;
  eligible_voting_opportunities: number;
  expected_random_votes: number;
  vote_rate: number | null;
  random_baseline_rate: number | null;
  excess_votes: number;
  excess_rate: number | null;
}


export interface PersonalityPerformance {
  personality: Personality;
  agent_ids: string[];
  generation_participations: number;
  generation_survivals: number;
  total_points: number;
  scored_round_count: number;
  average_points_per_round: number | null;
  generation_win_count: number;
  replacement_observation_count: number;
  replacement_success_rate: number | null;
}


export interface PersonalityDiversity {
  generated_personality_count: number;
  distinct_name_count: number;
  distinct_instruction_count: number;
  distinct_name_rate: number | null;
  distinct_instruction_rate: number | null;
}


export interface ReplacementOutcome {
  created_in_generation: number;
  replacement_agent_id: string;
  personality: Personality;
  first_participation_generation: number | null;
  first_participation_score: number | null;
  survived_first_participation: boolean | null;
  status: string;
}


export interface ReciprocalVoteIndicator {
  first_agent_id: string;
  second_agent_id: string;
  reciprocal_rounds: number;
  eligible_co_voting_rounds: number;
  expected_random_reciprocal_rounds: number;
  distinct_generations: number;
  meets_history_threshold: boolean;
}


export interface PossibleVotingBlocIndicator {
  agent_ids: string[];
  supporting_agent_pairs: [string, string][];
  distinct_generations: number;
  caveat: string;
}


export interface EntryAdjacentRelationshipChange {
  entrant_agent_id: string;
  entry_generation: number;
  voter_agent_id: string;
  target_agent_id: string;
  previous_vote_rate: number;
  entry_vote_rate: number;
  rate_change: number;
  previous_excess_votes: number;
  entry_excess_votes: number;
}


export interface ExperimentAnalysis {
  experiment_id: number;
  experiment_name: string;
  generation_count: number;
  agent_performance: AgentPerformance[];
  vote_relationships: VoteRelationship[];
  personality_performance: PersonalityPerformance[];
  personality_diversity: PersonalityDiversity;
  replacement_outcomes: ReplacementOutcome[];
  reciprocal_vote_indicators: ReciprocalVoteIndicator[];
  possible_voting_bloc_indicators: PossibleVotingBlocIndicator[];
  entry_adjacent_changes: EntryAdjacentRelationshipChange[];
  cautions: string[];
}
