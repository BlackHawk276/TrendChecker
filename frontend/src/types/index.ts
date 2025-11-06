export interface Store {
  id: string;
  domain: string;
  name: string;
  description?: string;
  category: string;
  country_code?: string;
  logo_url?: string;
  product_count: number;
  avg_product_price?: number;
  estimated_monthly_revenue?: number;
  estimated_monthly_visitors?: number;
  trending_score: number;
  growth_rate?: number;
  is_active: boolean;
  theme_name?: string;
  social_links?: Record<string, string>;
  created_at: string;
  updated_at: string;
  last_scraped_at?: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  subscription_tier: string;
  subscription_status: string;
  searches_used_this_month: number;
  searches_limit: number;
  searches_remaining: number;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface StoreListResponse {
  data: Store[];
  pagination: PaginationMeta;
}

export interface SavedStore {
  store: Store;
  saved_at: string;
  notes?: string;
}

export interface Alert {
  id: string;
  user_id: string;
  alert_type: string;
  criteria?: Record<string, any>;
  store_id?: string;
  is_active: boolean;
  created_at: string;
}

export interface UsageStats {
  searches_used_this_month: number;
  searches_remaining: number;
  searches_limit: number;
  reset_date: string;
  usage_percentage: number;
  history: Array<{
    month: string;
    searches_used: number;
    searches_limit: number;
  }>;
  category_breakdown: Array<{
    category: string;
    search_count: number;
    percentage: number;
  }>;
}
