/**
 * VS Comparison Layout Component
 * 
 * Features:
 * - 좌: 신품 기준가 (Gray tone)
 * - 우: 중고 최저가 리스트 (Accent color)
 * - 반응형 레이아웃
 */

import { motion } from 'framer-motion';
import ItemCard from './ItemCard';
import type { NaverItem, MergedUserItem } from '../types';

interface VSComparisonLayoutProps {
    reference: {
        name: string;
        price: number;
        image_url: string;
    } | null;
    items: (NaverItem | MergedUserItem)[];
    onItemClick?: (item: NaverItem | MergedUserItem) => void;
}

function formatPrice(price: number): string {
    return new Intl.NumberFormat('ko-KR').format(price);
}

export default function VSComparisonLayout({
    reference,
    items,
    onItemClick,
}: VSComparisonLayoutProps) {
    // 상위 5개만 표시
    const topItems = items.slice(0, 5);
    const lowestPrice = topItems[0]?.lprice || 0;
    const savings = reference ? reference.price - lowestPrice : 0;
    const savingsPercent = reference && reference.price > 0
        ? Math.round((savings / reference.price) * 100)
        : 0;

    return (
        <div className="w-full max-w-5xl mx-auto">
            {/* VS 헤더 */}
            <motion.div
                className="flex items-center justify-center gap-4 mb-8"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <span className="text-stone-400 font-medium">신품</span>
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-stone-300 to-matcha-400 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                    VS
                </div>
                <span className="text-matcha-600 font-medium">중고</span>
            </motion.div>

            {/* 메인 컨텐츠 */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
                {/* 좌측: 신품 기준가 */}
                <motion.div
                    className="lg:col-span-4"
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                >
                    <div className="sticky top-4 p-6 bg-white/50 backdrop-blur-sm rounded-2xl border border-stone-200 shadow-sm">
                        <h3 className="text-sm font-medium text-stone-500 mb-4 uppercase tracking-wider">
                            Reference Price
                        </h3>

                        {reference ? (
                            <>
                                {/* 이미지 */}
                                {reference.image_url && (
                                    <div className="w-full aspect-square rounded-xl overflow-hidden bg-white mb-6 border border-stone-100 shadow-inner">
                                        <img
                                            src={reference.image_url}
                                            alt={reference.name}
                                            className="w-full h-full object-contain p-4 mix-blend-multiply"
                                        />
                                    </div>
                                )}

                                {/* 악기 이름 */}
                                <p className="text-lg font-bold text-stone-800 mb-2 leading-tight">
                                    {reference.name}
                                </p>

                                {/* 가격 */}
                                <p className="text-2xl font-bold text-stone-400 line-through decoration-2 decoration-stone-300/50">
                                    ₩{formatPrice(reference.price)}
                                </p>
                                <p className="text-sm text-stone-400 mt-1">신품 평균가</p>

                                {/* 절약 금액 */}
                                {savings > 0 && (
                                    <motion.div
                                        className="mt-6 p-4 bg-matcha-50 rounded-xl border border-matcha-100 relative overflow-hidden"
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: 0.3 }}
                                    >
                                        <div className="absolute top-0 right-0 -mr-4 -mt-4 w-12 h-12 bg-matcha-200 rounded-full blur-xl opacity-50"></div>

                                        <p className="text-sm font-medium text-matcha-800 mb-1">
                                            중고로 구매 시
                                        </p>
                                        <div className="flex items-baseline gap-2">
                                            <p className="text-2xl font-bold text-matcha-600">
                                                {savingsPercent}%
                                            </p>
                                            <span className="text-matcha-600 font-medium">Save</span>
                                        </div>
                                        <p className="text-sm text-matcha-600 mt-0.5 opacity-80">
                                            약 ₩{formatPrice(savings)} 절약
                                        </p>
                                    </motion.div>
                                )}
                            </>
                        ) : (
                            <div className="text-center py-8 text-stone-400">
                                <p className="text-4xl mb-2 opacity-50">📊</p>
                                <p>기준가 정보 없음</p>
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* 우측: 중고 최저가 리스트 */}
                <motion.div
                    className="lg:col-span-8"
                    initial={{ opacity: 0, x: 30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <div className="flex items-center justify-between mb-4 px-1">
                        <h3 className="text-lg font-bold text-stone-800 flex items-center gap-2">
                            <span className="text-2xl">🔥</span> 최저가 TOP {Math.min(topItems.length, 5)}
                        </h3>
                        <span className="text-xs font-medium px-2 py-1 bg-stone-100 rounded-full text-stone-500">
                            총 {items.length}개 매물
                        </span>
                    </div>

                    {topItems.length > 0 ? (
                        <div className="space-y-4">
                            {topItems.map((item, index) => (
                                <ItemCard
                                    key={`item-${index}-${'id' in item ? item.id : item.productId}`}
                                    item={item}
                                    rank={index + 1}
                                    referencePrice={reference?.price}
                                    onClick={() => onItemClick?.(item)}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-16 bg-white/50 border border-dashed border-stone-300 rounded-2xl">
                            <p className="text-4xl mb-4 opacity-50">🎸</p>
                            <p className="text-stone-500 font-medium">검색 결과가 없습니다</p>
                            <p className="text-sm text-stone-400 mt-1">다른 검색어로 시도해보세요</p>
                        </div>
                    )}

                    {/* 더보기 (5개 이상일 때) */}
                    {items.length > 5 && (
                        <motion.button
                            className="w-full mt-6 py-4 text-matcha-700 font-bold bg-white border border-matcha-200 rounded-xl hover:bg-matcha-50 hover:border-matcha-300 transition-all shadow-sm"
                            whileHover={{ scale: 1.01, y: -1 }}
                            whileTap={{ scale: 0.99 }}
                        >
                            + {items.length - 5}개 더보기
                        </motion.button>
                    )}
                </motion.div>
            </div>
        </div>
    );
}
