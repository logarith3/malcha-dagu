/**
 * Type definitions for MALCHA-DAGU
 */

// =============================================================================
// API Response Types
// =============================================================================

export interface Instrument {
    id: string;
    name: string;
    brand: string;
    category: string;
    category_display: string;
    image_url: string;
    reference_price: number;
    description: string;
    created_at: string;
    updated_at: string;
}

export interface UserItem {
    id: string;
    instrument: string;
    instrument_detail: {
        id: string;
        name: string;
        brand: string;
        image_url: string;
        reference_price: number;
    };
    price: number;
    link: string;
    source: string;
    source_display: string;
    title: string;
    is_active: boolean;
    expired_at: string;
    extended_at: string | null;
    click_count: number;
    discount_rate: number;
    is_expired: boolean;
    is_owner: boolean;
    owner_id: number | null;
    created_at: string;
    updated_at: string;
}

export interface NaverItem {
    title: string;
    link: string;
    image: string;
    lprice: number;
    hprice: number;
    mallName: string;
    productId: string;
    productType: number;
    source: 'naver';
}

export interface SearchResult {
    query: string;
    search_query: string;  // 정규화된 검색어 (외부 링크용)
    total_count: number;
    reference: {
        name: string;
        price: number;
        image_url: string;
    } | null;
    taxonomy: {
        title: string;
        type: string; // 'brand' | 'model'
        brand: string;
        breadcrumbs: string[];
        description: string;
        logo_url?: string;
    } | null;
    matched_instrument: {
        id: string;
        name: string;
        brand: string;
        category: string;
    } | null;
    items: (NaverItem | MergedUserItem)[];
    naver_items: NaverItem[];
    user_items: MergedUserItem[];
}

export interface MergedUserItem {
    id: string;
    title: string;
    link: string;
    image: string;
    lprice: number;
    source: string;
    source_display: string;
    discount_rate: number;
    instrument_id: string;
    instrument_name: string;
    instrument_brand: string;
    extended_at: string | null;
    report_count: number;
}

// 신고 사유 타입
export type ReportReason = 'wrong_price' | 'sold_out' | 'fake' | 'inappropriate' | 'other';

export const REPORT_REASON_LABELS: Record<ReportReason, string> = {
    wrong_price: '가격이 다릅니다',
    sold_out: '이미 판매완료된 매물입니다',
    fake: '허위/사기 매물입니다',
    inappropriate: '부적절한 내용입니다',
    other: '기타',
};

export interface AIDescription {
    summary: string;
    check_point: string;
}

// =============================================================================
// Component Props Types
// =============================================================================

export interface SearchBarProps {
    onSearch: (query: string) => void;
    isLoading?: boolean;
    placeholder?: string;
}

export interface ItemCardProps {
    item: NaverItem | MergedUserItem;
    rank?: number;
    referencePrice?: number;
    onClick?: () => void;
    isOwner?: boolean;
    isLoggedIn?: boolean;
    onExtend?: () => void;
    onReport?: (reason: ReportReason, detail?: string) => void;
    onUpdatePrice?: (newPrice: number) => void;
}

export interface LoaderProps {
    isVisible: boolean;
    onComplete?: () => void;
}
