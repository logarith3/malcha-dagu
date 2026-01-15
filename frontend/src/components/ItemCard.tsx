/**
 * Item Card Component
 * 
 * Features:
 * - 가격 및 할인율 표시
 * - 출처 뱃지
 * - Layout 애니메이션 (순위 변경 시)
 * - 클릭 시 링크 이동
 */

import { motion } from 'framer-motion';
import type { NaverItem, MergedUserItem } from '../types';

interface ItemCardProps {
    item: NaverItem | MergedUserItem;
    rank?: number;
    referencePrice?: number;
    onClick?: () => void;
}

// 출처별 스타일
const SOURCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
    naver: { bg: 'bg-green-100', text: 'text-green-700', label: '네이버' },
    mule: { bg: 'bg-blue-100', text: 'text-blue-700', label: '뮬' },
    bunjang: { bg: 'bg-red-100', text: 'text-red-700', label: '번개장터' },
    joonggonara: { bg: 'bg-green-100', text: 'text-green-700', label: '중고나라' },
    danggn: { bg: 'bg-orange-100', text: 'text-orange-700', label: '당근' },
    other: { bg: 'bg-stone-100', text: 'text-stone-700', label: '기타' },
};

function formatPrice(price: number): string {
    return new Intl.NumberFormat('ko-KR').format(price);
}

function calculateDiscount(price: number, referencePrice: number): number {
    if (referencePrice <= 0) return 0;
    return Math.round((1 - price / referencePrice) * 100);
}

export default function ItemCard({
    item,
    rank,
    referencePrice,
    onClick,
}: ItemCardProps) {
    const source = item.source || 'other';
    const sourceStyle = SOURCE_STYLES[source] || SOURCE_STYLES.other;

    // 할인율 계산
    const discount = 'discount_rate' in item
        ? item.discount_rate
        : referencePrice
            ? calculateDiscount(item.lprice, referencePrice)
            : 0;

    // 이미지 URL
    const imageUrl = 'image' in item ? item.image : '';

    const handleClick = () => {
        // 외부 링크 열기
        window.open(item.link, '_blank', 'noopener,noreferrer');
        onClick?.();
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            whileHover={{ scale: 1.02, y: -4 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleClick}
            className="
                relative flex gap-4 p-4 bg-white rounded-2xl shadow-sm
                cursor-pointer transition-all duration-300
                border border-stone-100 hover:border-matcha-200
                hover:shadow-[0_8px_30px_rgb(0,0,0,0.04)]
                group
            "
        >
            {/* 순위 뱃지 */}
            {rank && rank <= 3 && (
                <div
                    className={`
                        absolute -top-2 -left-2 w-8 h-8 rounded-full
                        flex items-center justify-center text-sm font-bold text-white shadow-md
                        ${rank === 1 ? 'bg-matcha-500' : rank === 2 ? 'bg-stone-400' : 'bg-stone-500'}
                    `}
                >
                    {rank}
                </div>
            )}

            {/* 이미지 */}
            <div className="flex-shrink-0 w-20 h-20 sm:w-24 sm:h-24 rounded-xl overflow-hidden bg-stone-50 border border-stone-100 group-hover:border-matcha-100 transition-colors">
                {imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={item.title}
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                        loading="lazy"
                        onError={(e) => {
                            (e.target as HTMLImageElement).src = 'https://via.placeholder.com/96?text=No+Image';
                        }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl opacity-50">
                        🎸
                    </div>
                )}
            </div>

            {/* 정보 */}
            <div className="flex-1 min-w-0 flex flex-col justify-between py-1">
                {/* 상단: 제목 + 출처 */}
                <div>
                    <div className="flex items-start gap-2 mb-1.5">
                        <span
                            className={`
                                flex-shrink-0 px-2.5 py-0.5 rounded-full text-[10px] sm:text-xs font-semibold tracking-wide
                                ${sourceStyle.bg} ${sourceStyle.text}
                            `}
                        >
                            {sourceStyle.label}
                        </span>
                    </div>
                    <h3 className="text-sm sm:text-base font-medium text-stone-800 line-clamp-2 leading-snug group-hover:text-matcha-800 transition-colors">
                        {item.title}
                    </h3>
                </div>

                {/* 하단: 가격 + 할인율 */}
                <div className="flex items-end justify-between mt-2">
                    <div>
                        <div className="flex items-baseline gap-1.5">
                            <p className="text-lg sm:text-xl font-bold text-stone-900">
                                {formatPrice(item.lprice)}<span className="text-xs sm:text-sm font-normal text-stone-500 ml-0.5">원</span>
                            </p>
                        </div>

                        {discount > 0 && (
                            <p className="text-xs text-stone-500 mt-0.5">
                                신품 대비 <span className="text-matcha-600 font-bold">{discount}%</span> 저렴
                            </p>
                        )}
                    </div>

                    {/* 화살표 아이콘 */}
                    <div className="w-8 h-8 rounded-full bg-stone-50 flex items-center justify-center text-stone-400 group-hover:bg-matcha-50 group-hover:text-matcha-600 transition-colors">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                        </svg>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
