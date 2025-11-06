/**
 * Shared TypeScript types for TrendChecker monorepo
 * Used by both frontend (Next.js) and backend (FastAPI)
 */

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
  is_verified: boolean;
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

export interface Product {
  id: string;
  store_id: string;
  title: string;
  description?: string;
  price: number;
  compare_at_price?: number;
  currency: string;
  image_url?: string;
  vendor?: string;
  product_type?: string;
  handle?: string;
  is_available: boolean;
  tags?: string[];
  first_seen: string;
  last_seen: string;
  variant_count: number;
  created_at: string;
  updated_at: string;
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
  alert_type: 'new_store' | 'price_drop' | 'trending';
  criteria?: {
    category?: string;
    min_products?: number;
    min_trending_score?: number;
    keywords?: string[];
    min_drop_percentage?: number;
    min_score_increase?: number;
  };
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

export interface Activity {
  activity_type: 'search' | 'view' | 'save' | 'analyze';
  description: string;
  store_domain?: string;
  timestamp: string;
}

export type SubscriptionTier = 'free' | 'basic' | 'pro' | 'enterprise';
export type SubscriptionStatus = 'active' | 'inactive' | 'trialing' | 'canceled' | 'past_due';
export type StoreCategory = 'fashion' | 'beauty' | 'electronics' | 'home' | 'health' | 'sports' | 'other';
