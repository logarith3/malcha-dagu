/**
 * React Query hooks for MALCHA-DAGU
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../services/api';
import type { SearchResult } from '../types';

// =============================================================================
// Search Hook
// =============================================================================

export function useSearch(query: string, options?: { enabled?: boolean }) {
    return useQuery<SearchResult>({
        queryKey: ['search', query],
        queryFn: () => api.search(query),
        enabled: options?.enabled ?? query.length > 0,
        staleTime: 5 * 60 * 1000, // 5분간 캐시 유지
        gcTime: 10 * 60 * 1000, // 10분간 가비지 컬렉션 방지
    });
}

// =============================================================================
// Instruments Hook
// =============================================================================

export function useInstruments(params?: {
    brand?: string;
    category?: string;
    search?: string;
}) {
    return useQuery({
        queryKey: ['instruments', params],
        queryFn: () => api.getInstruments(params),
    });
}

export function useInstrument(id: string) {
    return useQuery({
        queryKey: ['instrument', id],
        queryFn: () => api.getInstrument(id),
        enabled: !!id,
    });
}

// =============================================================================
// User Items Hook
// =============================================================================

export function useUserItems(params?: {
    instrument?: string;
    source?: string;
    min_price?: number;
    max_price?: number;
}) {
    return useQuery({
        queryKey: ['userItems', params],
        queryFn: () => api.getUserItems(params),
    });
}

export function useCreateUserItem() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: api.createUserItem,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['userItems'] });
            queryClient.invalidateQueries({ queryKey: ['search'] });
        },
    });
}

export function useTrackItemClick() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: api.trackItemClick,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['userItems'] });
        },
    });
}

export function useExtendUserItem() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: api.extendUserItem,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['search'] });
            queryClient.invalidateQueries({ queryKey: ['userItems'] });
        },
    });
}

export function useReportItem() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, reason, detail }: { id: string; reason: string; detail?: string }) =>
            api.reportUserItem(id, { reason, detail }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['search'] });
            queryClient.invalidateQueries({ queryKey: ['userItems'] });
        },
    });
}

export function useUpdateItemPrice() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, price }: { id: string; price: number }) =>
            api.updateItemPrice(id, price),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['search'] });
            queryClient.invalidateQueries({ queryKey: ['userItems'] });
        },
    });
}

// =============================================================================
// AI Description Hook
// =============================================================================

export function useAIDescription() {
    return useMutation({
        mutationFn: api.getAIDescription,
    });
}
