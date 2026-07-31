// Common API response types
export interface ApiResponse<T = any> {
  data: T;
  status: 'success' | 'error';
  message?: string;
}

// Entity types
export interface Entity {
  id: string | number;
  name: string;
  type: 'person' | 'organization' | 'agency';
  created_at?: string;
  updated_at?: string;
}

// Report types
export interface IntelligenceReport {
  id: string | number;
  entity_name: string;
  entity_type: string;
  ticker?: string;
  sections: ReportSection[];
  created_at: string;
}

export interface ReportSection {
  title: string;
  category: string;
  claims: Claim[];
}

export interface Claim {
  text: string;
  confidence: 'DOCUMENTED' | 'REPORTED' | 'ANALYTICAL';
  source?: string;
  source_url?: string;
}

// Market data types
export interface StockData {
  ticker: string;
  currentPrice: number;
  change: number;
  changePercent: number;
  volume: number;
}

// User types
export interface User {
  id: string | number;
  email: string;
  name?: string;
  role?: string;
}

// Watchlist types
export interface WatchlistItem {
  ticker: string;
  entity_name: string;
  added_at: string;
  alert_threshold?: number;
  notify_email?: string;
  notify_phone?: string;
}

// Alert types
export interface Alert {
  id: string | number;
  type: 'big_trade' | 'investment' | 'news';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  ticker?: string;
  created_at: string;
  acknowledged: boolean;
}

export * from './api';
export * from './entities';
