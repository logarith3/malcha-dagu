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
    click_count: number;
    discount_rate: number;
    is_expired: boolean;
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
    total_count: number;
    reference: {
        name: string;
        price: number;
        image_url: string;
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
}

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
}

export interface LoaderProps {
    isVisible: boolean;
    onComplete?: () => void;
}
