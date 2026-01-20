/**
 * API client for MALCHA-DAGU backend
 */

import axios from 'axios';
import type { SearchResult, Instrument, UserItem, AIDescription } from '../types';

const api = axios.create({
    baseURL: '/api',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,  // SSO 쿠키 전송 필수
});

// =============================================================================
// Search API
// =============================================================================

export async function search(query: string, display = 20): Promise<SearchResult> {
    const response = await api.get<SearchResult>('/search/', {
        params: { q: query, display },
    });
    return response.data;
}

export async function getPopularSearches(limit = 4): Promise<string[]> {
    const response = await api.get<{ terms: string[] }>('/popular-searches/', {
        params: { limit },
    });
    return response.data.terms;
}

// =============================================================================
// Instrument API
// =============================================================================

export async function getInstruments(params?: {
    brand?: string;
    category?: string;
    search?: string;
}): Promise<Instrument[]> {
    const response = await api.get<{ results: Instrument[] }>('/instruments/', { params });
    return response.data.results || response.data as unknown as Instrument[];
}

export async function getInstrument(id: string): Promise<Instrument> {
    const response = await api.get<Instrument>(`/instruments/${id}/`);
    return response.data;
}

// =============================================================================
// UserItem API
// =============================================================================

export async function getUserItems(params?: {
    instrument?: string;
    source?: string;
    min_price?: number;
    max_price?: number;
}): Promise<UserItem[]> {
    const response = await api.get<{ results: UserItem[] }>('/items/', { params });
    return response.data.results || response.data as unknown as UserItem[];
}

export async function createUserItem(data: {
    instrument?: string;
    price: number;
    link: string;
    source: string;
    title?: string;
}): Promise<UserItem> {
    // instrument가 있으면 그대로 전송, 없으면 제거 (백엔드 매칭 유도)
    const payload = { ...data };
    if (!payload.instrument) {
        delete payload.instrument;
    }
    const response = await api.post<UserItem>('/items/', payload);
    return response.data;
}

export async function trackItemClick(id: string): Promise<UserItem> {
    const response = await api.post<UserItem>(`/items/${id}/click/`);
    return response.data;
}

export async function extendUserItem(id: string): Promise<UserItem> {
    const response = await api.post<UserItem>(`/items/${id}/extend/`);
    return response.data;
}

export async function reportUserItem(id: string, data: {
    reason: string;
    detail?: string;
}): Promise<{ message: string; report_count: number; is_under_review: boolean; is_deleted: boolean }> {
    const response = await api.post(`/items/${id}/report/`, data);
    return response.data;
}

export async function updateItemPrice(id: string, price: number): Promise<UserItem> {
    const response = await api.post<UserItem>(`/items/${id}/update_price/`, { price });
    return response.data;
}

// =============================================================================
// AI Description API
// =============================================================================

export async function getAIDescription(data: {
    model_name: string;
    brand: string;
    category: string;
}): Promise<AIDescription> {
    const response = await api.post<AIDescription>('/ai/describe/', data);
    return response.data;
}

export default api;
