import type { PersonalityTheme } from '../types/game.js';

export const THEME_POOL: PersonalityTheme[] = [
  { avatar: 'bg-purple-500', border: 'border-purple-400', text: 'text-purple-300', glow: 'shadow-purple-500/20' },
  { avatar: 'bg-blue-500', border: 'border-blue-400', text: 'text-blue-300', glow: 'shadow-blue-500/20' },
  { avatar: 'bg-yellow-500', border: 'border-yellow-400', text: 'text-yellow-300', glow: 'shadow-yellow-500/20' },
  { avatar: 'bg-cyan-500', border: 'border-cyan-400', text: 'text-cyan-300', glow: 'shadow-cyan-500/20' },
  { avatar: 'bg-pink-500', border: 'border-pink-400', text: 'text-pink-300', glow: 'shadow-pink-500/20' },
  { avatar: 'bg-orange-500', border: 'border-orange-400', text: 'text-orange-300', glow: 'shadow-orange-500/20' },
  { avatar: 'bg-emerald-500', border: 'border-emerald-400', text: 'text-emerald-300', glow: 'shadow-emerald-500/20' },
  { avatar: 'bg-indigo-500', border: 'border-indigo-400', text: 'text-indigo-300', glow: 'shadow-indigo-500/20' },
  { avatar: 'bg-violet-500', border: 'border-violet-400', text: 'text-violet-300', glow: 'shadow-violet-500/20' },
  { avatar: 'bg-rose-500', border: 'border-rose-400', text: 'text-rose-300', glow: 'shadow-rose-500/20' },
  { avatar: 'bg-teal-500', border: 'border-teal-400', text: 'text-teal-300', glow: 'shadow-teal-500/20' },
  { avatar: 'bg-lime-500', border: 'border-lime-400', text: 'text-lime-300', glow: 'shadow-lime-500/20' },
];

export function pickTheme(usedAvatars: string[]): PersonalityTheme {
  const available = THEME_POOL.filter((t) => !usedAvatars.includes(t.avatar));
  if (available.length > 0) {
    return available[Math.floor(Math.random() * available.length)]!;
  }
  return THEME_POOL[Math.floor(Math.random() * THEME_POOL.length)]!;
}
