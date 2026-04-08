export interface Alternative {
  id: number;
  question_id: string;
  letter: string;
  body: string;
  correct: boolean;
  answer_pct: number;
}

export interface TopicEntry {
  n: string;
  p: string;
}

export interface Question {
  id: string;
  statement: string;
  answer_type: string;
  year: number | null;
  institution: string;
  banca: string;
  finalidade: string;
  region: string;
  labels: string[];
  topics: TopicEntry[];
  correct_letter: string;
  solution: string;
  has_video: boolean;
  video_url: string;
  alternatives: Alternative[];
}

export interface FilterValues {
  specialties: string[];
  topicsTree?: TopicNode[];
  institutions: string[];
  years: number[];
  finalidades: string[];
  bancas: string[];
  regions: string[];
}

export interface TopicNode {
  name: string;
  path: string;
  children: TopicNode[];
}

export interface Filters {
  search?: string;
  specialties?: string[];
  institutions?: string[];
  years?: number[];
  finalidades?: string[];
  bancas?: string[];
  regions?: string[];
  types?: string[];
  showOutdated?: boolean;
  showCanceled?: boolean;
  page?: number;
}

export interface SavedAnswer {
  s: string; // selected letter
  c: boolean; // correct
}
