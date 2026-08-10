// Additional API-specific types can be added here
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  status_code: number;
}
