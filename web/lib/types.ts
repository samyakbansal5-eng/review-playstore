export type ThemeRow = {
  theme: string; name: string; pain: boolean; n: number; share: number;
  share_of_low_rating: number; share_of_one_star: number;
  avg_rating: number | null; rating_gap: number | null; pct_negative_sentiment: number | null;
};
export type AppData = {
  id: string; name: string; package: string; reviews_analysed: number; reviews_in_window: number;
  avg_rating: number; pct_one_star: number; themes: ThemeRow[]; pain_ranking: string[];
};
export type TrendRow = {
  app: string; month: string; n: number; avg_rating: number | null; reviews_total: number | null;
  share: Record<string, number>;
};
export type FeatureCell = {
  app: string; feature: string; name: string; mentions: number; mention_rate: number;
  avg_rating: number | null; pct_negative: number | null;
};
export type Quote = { text: string; rating: number; date: string; thumbs_up: number };
export type Domain = {
  domain: string; title: string; description: string;
  themes: { id: string; name: string; definition: string; pain: boolean }[];
  headline: {
    reviews_analysed: number; reviews_in_window: number; apps: number;
    top_pain_theme: string | null; top_pain_share_of_one_star: number | null; months: [string, string];
  };
  apps: AppData[]; trend: TrendRow[]; feature_matrix: FeatureCell[];
  quotes: Record<string, Quote[]>;
  explorer: { app: string; theme: string; rating: number; date: string; sentiment: string; text: string }[];
};
export type Evaluation = {
  domain: string; n_labelled: number; agreement: number; kappa: number; model: string;
  per_theme: { theme: string; name: string; support: number; precision: number | null; recall: number | null; f1: number | null }[];
  confusion: { labels: string[]; matrix: number[][] };
  notes?: string;
};
export type Recommendation = {
  title: string; problem: string; evidence: string[]; quotes?: { app: string; text: string }[];
  metric: string; impact: "High" | "Medium" | "Low"; effort: "High" | "Medium" | "Low"; apps?: string;
};
export type DomainIndex = { domains: { id: string; title: string; description: string }[] };
