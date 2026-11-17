// TypeScript mirror of the API contract in app/schemas/ (owner UPS-002).
// Keep in sync with the Pydantic models; ask the owner for changes (uak msg UPS-002 --kind request).

export type Role = "superadmin" | "academy_admin" | "member";
export type ResourceType = "document" | "link" | "video" | "other";
export type ProjectStatus = "draft" | "published";
export type ChannelType = "feed" | "general" | "academy";

/** ISO 8601 datetime string with timezone. */
export type DateTime = string;

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

export interface ApiError {
  error: { code: string; message: string; details: unknown };
}

// ── Users & auth ─────────────────────────────────────────────
export interface PublicUser {
  id: number;
  nickname: string;
  avatar_url: string | null;
}

export interface UserMe {
  id: number;
  role: Role;
  email: string;
  full_name: string;
  nickname: string;
  boleta: string | null;
  avatar_url: string | null;
  academy_id: number | null;
  academy_slug: string | null;
  must_change_password: boolean;
}

export interface UserAdminOut {
  id: number;
  role: Role;
  email: string;
  full_name: string;
  nickname: string;
  boleta: string | null;
  academy_id: number | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: DateTime;
}

export interface RegisterIn {
  full_name: string;
  boleta: string; // 10 digits
  email: string;
  password: string; // >= 8
  accept_privacy: true;
  nickname?: string | null;
}

export interface LoginIn {
  /** A 10-digit boleta or an email (UPS-044). */
  identifier: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: UserMe;
}

export interface ProfileUpdateIn {
  nickname?: string | null;
  full_name?: string | null;
}

export interface EmailChangeIn {
  new_email: string;
  current_password: string;
}

export interface PasswordChangeIn {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface AdminUserCreateIn {
  role: "academy_admin" | "member";
  email: string;
  full_name: string;
  nickname?: string | null;
  boleta?: string | null;
  academy_id?: number | null;
  password: string;
}

export interface AdminUserUpdateIn {
  full_name?: string | null;
  nickname?: string | null;
  academy_id?: number | null;
  is_active?: boolean | null;
}

export interface PasswordResetOut {
  temporary_password: string;
}

// ── Academies & home ────────────────────────────────────────
export interface AcademyBranding {
  slug: string;
  name: string;
  logo_url: string | null;
  mascot_url: string | null;
  color_primary: string;
  color_secondary: string;
  color_accent: string;
  color_accent_2: string | null;
}

export interface AcademyCardOut extends AcademyBranding {
  id: number;
  short_description: string;
  position: number;
  is_enrolled: boolean;
}

export interface AcademyOut extends AcademyCardOut {
  welcome_text: string;
  is_active: boolean;
  created_at: DateTime;
}

export interface AcademyCreateIn {
  slug: string;
  name: string;
  short_description?: string;
  welcome_text?: string;
  color_primary?: string;
  color_secondary?: string;
  color_accent?: string;
  color_accent_2?: string | null;
  position?: number;
}

export type AcademyUpdateIn = Partial<Omit<AcademyCreateIn, "slug">> & { is_active?: boolean };

export interface BrandingUpdateIn {
  short_description?: string | null;
  welcome_text?: string | null;
  color_primary?: string | null;
  color_secondary?: string | null;
  color_accent?: string | null;
  color_accent_2?: string | null;
}

export interface ContinueOut {
  route_id: number;
  lesson_id: number;
  lesson_title: string;
  lesson_number: number;
  percent: number;
}

export interface HomeContentIn {
  hero_title: string;
  hero_text?: string;
  highlighted_academy_ids?: number[];
  featured_project_ids?: number[];
}

export interface HomeContentOut {
  hero_title: string;
  hero_text: string;
  highlighted_academy_ids: number[];
  featured_project_ids: number[];
}

// ── Learning ────────────────────────────────────────────────
export interface LessonLinkIn {
  label: string;
  url: string;
}

export interface LessonLinkOut extends LessonLinkIn {
  id: number;
}

export interface LessonSummaryOut {
  id: number;
  title: string;
  duration_min: number | null;
  position: number;
  is_published: boolean;
  completed: boolean;
}

export interface ModuleOut {
  id: number;
  title: string;
  position: number;
  completed: number;
  total: number;
  lessons: LessonSummaryOut[];
}

export interface RouteProgressOut {
  completed: number;
  total: number;
  percent: number;
  next_lesson_id: number | null;
}

export interface RouteCardOut {
  id: number;
  academy_id: number;
  title: string;
  description: string;
  cover_url: string | null;
  position: number;
  is_published: boolean;
  progress: RouteProgressOut | null;
}

export interface RouteDetailOut extends RouteCardOut {
  modules: ModuleOut[];
}

export interface LessonOut {
  id: number;
  module_id: number;
  route_id: number;
  academy_slug: string;
  title: string;
  youtube_video_id: string;
  embed_url: string;
  thumbnail_url: string;
  description: string;
  duration_min: number | null;
  start_s: number | null;
  end_s: number | null;
  is_published: boolean;
  links: LessonLinkOut[];
  completed: boolean;
  completed_at: DateTime | null;
  prev_lesson_id: number | null;
  next_lesson_id: number | null;
}

export interface RouteIn {
  title: string;
  description?: string;
  is_published?: boolean;
}

export type RouteUpdateIn = Partial<RouteIn>;

export interface ModuleIn {
  title: string;
}

export interface LessonIn {
  title: string;
  youtube_url: string;
  description?: string;
  duration_min?: number | null;
  start_s?: number | null;
  end_s?: number | null;
  is_published?: boolean;
  links?: LessonLinkIn[];
}

export type LessonUpdateIn = Partial<LessonIn>;

export interface ReorderIn {
  ids: number[];
}

// ── Resources, events, gallery, blog ────────────────────────
export interface ResourceIn {
  type: ResourceType;
  title: string;
  description?: string;
  url?: string | null;
}

export interface ResourceOut {
  id: number;
  academy_id: number;
  type: ResourceType;
  title: string;
  description: string;
  url: string | null;
  file_url: string | null;
  thumbnail_url: string | null;
  created_at: DateTime;
}

export interface EventIn {
  academy_id?: number | null; // null = global (superadmin only)
  title: string;
  description?: string;
  location?: string | null;
  link?: string | null;
  starts_at: DateTime;
  ends_at: DateTime;
}

export interface EventOut {
  id: number;
  academy_id: number | null;
  academy_slug: string | null;
  title: string;
  description: string;
  location: string | null;
  link: string | null;
  starts_at: DateTime;
  ends_at: DateTime;
  cover_url: string | null;
}

export interface ProjectIn {
  title: string;
  slug: string;
  summary?: string;
  body?: string;
  authors?: string;
  academy_id?: number | null;
  tags?: string[];
  status?: ProjectStatus;
}

export interface ProjectOut {
  id: number;
  title: string;
  slug: string;
  summary: string;
  body: string;
  cover_url: string | null;
  authors: string;
  academy_id: number | null;
  tags: string[];
  status: ProjectStatus;
  published_at: DateTime | null;
}

export interface BlogPostIn {
  title: string;
  slug: string;
  body?: string;
  published?: boolean;
}

export interface BlogPostOut {
  id: number;
  title: string;
  slug: string;
  body: string;
  cover_url: string | null;
  author: PublicUser | null;
  published_at: DateTime | null;
}

// ── Community ───────────────────────────────────────────────
export interface ChannelOut {
  id: number;
  type: ChannelType;
  academy_id: number | null;
  name: string;
  slug: string;
}

export interface PostIn {
  body: string;
  link_url?: string | null;
}

export interface PostOut {
  id: number;
  channel_id: number;
  channel_slug: string | null;
  author: PublicUser;
  body: string;
  image_url: string | null;
  link_url: string | null;
  created_at: DateTime;
  comment_count: number;
  reactions: Record<string, number>;
  is_hidden: boolean;
}

export interface CommentIn {
  body: string;
}

export interface CommentOut {
  id: number;
  post_id: number;
  author: PublicUser;
  body: string; // "" when hidden (redacted by the API)
  created_at: DateTime;
  is_hidden: boolean;
}

// ── Email channel (spec 003, /api/mail) ──────────────────────
export type Audience =
  | { kind: "all" }
  | { kind: "academy"; academy_id: number }
  | { kind: "role"; role: Role }
  | { kind: "individual"; user_ids: number[]; emails: string[] }; // ≤ 50 entries in total, ≤ 20 emails

export type CampaignStatus = "draft" | "sending" | "sent" | "partial" | "failed";
export type MailRecipientStatus =
  | "pending"
  | "accepted"
  | "delivered"
  | "failed"
  | "bounced"
  | "complained";

export interface CampaignIn {
  subject: string;
  body: string;
  audience: Audience;
}

export interface Campaign {
  id: number;
  subject: string;
  audience: Audience;
  sender: PublicUser | null;
  status: CampaignStatus;
  recipient_count: number;
  counts_by_status: Partial<Record<MailRecipientStatus, number>>;
  created_at: DateTime;
  sent_at: DateTime | null;
}

/** GET /api/mail/status */
export interface MailStatus {
  enabled: boolean;
  daily_limit: number;
  sent_today: number;
  remaining: number;
}

/** GET/PUT /api/mail/preferences */
export interface MailPreferences {
  receive_club_email: boolean;
}

/** POST /api/mail/audience/preview */
export interface AudiencePreview {
  count: number;
  excluded: { inactive: number; suppressed: number; blocked_domain: number };
}
