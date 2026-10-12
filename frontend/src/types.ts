export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "teacher" | "admin";
  active: boolean;
  must_change_password: boolean;
  version: number;
}

export interface Subject {
  id: string;
  code: string;
  title: string;
}

export interface Topic {
  id: string;
  subject_id: string;
  title: string;
  description: string;
  suggested_grade: number;
  sequence: number;
  planning_note: string;
  prerequisite_ids: string[];
  archived: boolean;
  version: number;
}

export interface Curriculum {
  id: string;
  subject_id: string;
  official_grade_band: string;
  section_code: string;
  section_title: string;
  paraphrased_goal: string;
  source_url: string;
  source_version: string;
  retrieved_on: string | null;
  verification_status: "unverified" | "verified";
  reviewed_at: string | null;
  archived: boolean;
  version: number;
}

export interface SchoolYear {
  id: string;
  label: string;
  starts_on: string;
  ends_on: string;
  version: number;
}

export interface Option {
  value: string;
  label: string;
}

export interface Reference {
  subjects: Subject[];
  topics: Topic[];
  curriculum: Curriculum[];
  school_years: SchoolYear[];
  material_types: Option[];
  levels: Option[];
  templates: { id: string; name: string; subject_id: string; units: number }[];
}

export interface MaterialSummary {
  id: string;
  title: string;
  description: string;
  topic_id: string;
  topic_title: string | null;
  subject_id: string | null;
  type: string;
  type_label: string;
  level: string;
  level_label: string;
  duration_minutes: number;
  status: string;
  status_label: string;
  is_demo: boolean;
  has_main_file: boolean;
  has_solution: boolean;
  curriculum_ids: string[];
  is_favorite: boolean | null;
  version: number;
}

export interface MaterialFile {
  id: string;
  purpose: "main" | "solution";
  original_name: string;
  size_bytes: number;
  sha256: string;
  url: string;
}

export interface MaterialDetail extends MaterialSummary {
  learning_goal: string;
  keywords: string[];
  author: string;
  license_text: string;
  reviewer_id: string | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  review_note: string;
  curriculum: Curriculum[];
  files: MaterialFile[];
  subject_title: string | null;
  updated_at: string;
  release_check?: string[];
}

export interface SchoolClass {
  id: string;
  name: string;
  grade: number;
  state: string;
  school_type: string;
  school_year_id: string;
  school_year_label: string | null;
  weekdays: number[];
  subject_hours: { subject_id: string; weekly_hours: number }[];
  version: number;
}

export interface UnitMaterial {
  id: string;
  title: string;
  type: string;
  type_label: string;
  status: string;
  is_demo: boolean;
  has_main_file: boolean;
  has_solution: boolean;
  available: boolean;
}

export interface Unit {
  id: string;
  class_id: string;
  subject_id: string;
  subject_title: string | null;
  topic_id: string;
  topic_title: string | null;
  week_start_date: string;
  planned_lessons: number;
  status: "planned" | "started" | "completed";
  notes: string;
  sequence: number;
  materials: UnitMaterial[];
  curriculum: { id: string; section_code: string; paraphrased_goal: string; verification_status: string }[];
  version: number;
  updated_at: string;
}

export interface Week {
  week_start: string;
  week_end: string;
  iso_year: number;
  iso_week: number;
  in_school_year: boolean;
  teaching_week: number | null;
  teaching_days: string[];
  regular_days: number;
  shortened: boolean;
  fully_free: boolean;
  closures: { title: string; kind: string; starts_on: string; ends_on: string; approved: boolean }[];
  capacity: Record<string, number>;
}

export interface CalendarStatus {
  total: number;
  unreviewed: number;
  approved: number;
  demo_only: boolean;
}

export interface Recommendation {
  score: number;
  reason: string;
  material: MaterialSummary;
}

export interface SubjectRecommendations {
  subject_id: string;
  subject_title: string;
  mode: "planned" | "next_open_topic" | "empty";
  topics: { id: string; title: string; planned_week?: string }[];
  items: Recommendation[];
  empty_reason?: string;
}

export interface Warning {
  code: string;
  message: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
