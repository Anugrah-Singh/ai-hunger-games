import type { Personality } from '../types/game.js';

export const INITIAL_PERSONALITIES: Personality[] = [
  {
    id: 1,
    name: 'The Philosopher',
    trait: 'Deep thinker who questions assumptions',
    alive: true,
    theme: {
      avatar: 'bg-purple-500',
      border: 'border-purple-400',
      text: 'text-purple-300',
      glow: 'shadow-purple-500/20',
    },
  },
  {
    id: 2,
    name: 'The Pragmatist',
    trait: 'Practical and solution-oriented',
    alive: true,
    theme: {
      avatar: 'bg-blue-500',
      border: 'border-blue-400',
      text: 'text-blue-300',
      glow: 'shadow-blue-500/20',
    },
  },
  {
    id: 3,
    name: 'The Optimist',
    trait: 'Positive and opportunity-focused',
    alive: true,
    theme: {
      avatar: 'bg-yellow-500',
      border: 'border-yellow-400',
      text: 'text-yellow-300',
      glow: 'shadow-yellow-500/20',
    },
  },
  {
    id: 4,
    name: 'The Skeptic',
    trait: 'Evidence-driven and difficult to convince',
    alive: true,
    theme: {
      avatar: 'bg-cyan-500',
      border: 'border-cyan-400',
      text: 'text-cyan-300',
      glow: 'shadow-cyan-500/20',
    },
  },
  {
    id: 5,
    name: 'The Empath',
    trait: 'Emotionally aware and understanding',
    alive: true,
    theme: {
      avatar: 'bg-pink-500',
      border: 'border-pink-400',
      text: 'text-pink-300',
      glow: 'shadow-pink-500/20',
    },
  },
  {
    id: 6,
    name: 'The Rebel',
    trait: 'Contrarian who challenges defaults',
    alive: true,
    theme: {
      avatar: 'bg-orange-500',
      border: 'border-orange-400',
      text: 'text-orange-300',
      glow: 'shadow-orange-500/20',
    },
  },
  {
    id: 7,
    name: 'The Analyst',
    trait: 'Logical, systematic, and data-driven',
    alive: true,
    theme: {
      avatar: 'bg-emerald-500',
      border: 'border-emerald-400',
      text: 'text-emerald-300',
      glow: 'shadow-emerald-500/20',
    },
  },
  {
    id: 8,
    name: 'The Visionary',
    trait: 'Future-focused and imaginative',
    alive: true,
    theme: {
      avatar: 'bg-indigo-500',
      border: 'border-indigo-400',
      text: 'text-indigo-300',
      glow: 'shadow-indigo-500/20',
    },
  },
];
