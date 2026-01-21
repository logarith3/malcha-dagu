/**
 * Item Card Component
 *
 * Features:
 * - 가격 및 할인율 표시
 * - 출처 뱃지
 * - Layout 애니메이션 (순위 변경 시)
 * - 클릭 시 링크 이동
 * - 신고하기 / 가격 업데이트 버튼 (유저 매물만)
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { NaverItem, MergedUserItem, ReportReason } from '../types';
import { REPORT_REASON_LABELS } from '../types';

interface ItemCardProps {
    item: NaverItem | MergedUserItem;
    rank?: number;
    referencePrice?: number;
    onClick?: () => void;
    isOwner?: boolean;
    isLoggedIn?: boolean;
    onExtend?: () => void;
    onReport?: (reason: ReportReason, detail?: string) => void;
    onUpdatePrice?: (newPrice: number) => void;
    onClickDelete?: () => void;
}

// 출처별 스타일 및 허용 도메인
const SOURCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
    naver: { bg: 'bg-green-100', text: 'text-green-700', label: '네이버' },
    mule: { bg: 'bg-blue-100', text: 'text-blue-700', label: '뮬' },
    bunjang: { bg: 'bg-red-100', text: 'text-red-700', label: '번개장터' },
    joonggonara: { bg: 'bg-green-100', text: 'text-green-700', label: '중고나라' },
    danggn: { bg: 'bg-orange-100', text: 'text-orange-700', label: '당근' },
    other: { bg: 'bg-stone-100', text: 'text-stone-700', label: '기타' },
};

const ALLOWED_DOMAINS = [
    'mule.co.kr', 'bunjang.co.kr', 'daangn.com', 'danggeun.com',
    'cafe.naver.com', 'joongna.com', 'secondhand.co.kr',
    'naver.com' // 네이버 쇼핑 링크 포괄 허용
];

function formatPrice(price: number): string {
    return new Intl.NumberFormat('ko-KR').format(price);
}

function calculateDiscount(price: number, referencePrice: number): number {
    if (referencePrice <= 0) return 0;
    return Math.round((1 - price / referencePrice) * 100);
}

function isValidUrl(url: string): boolean {
    if (!url) return false;
    try {
        const parsed = new URL(url);
        // 1. 프로토콜 검증 (XSS 방지)
        if (!['http:', 'https:'].includes(parsed.protocol)) return false;

        // 2. 도메인 화이트리스트 검증 (Open Redirect 방지)
        // 네이버 아이템 등 신뢰할 수 있는 도메인만 이동 허용
        return ALLOWED_DOMAINS.some(domain => parsed.hostname.includes(domain));
    } catch {
        return false;
    }
}


// 기타 피크 순위 아이콘
function PickIcon({ rank }: { rank: number }) {
    const colors = {
        1: { fill: '#FFD700', stroke: '#B8860B', text: '#8B4513' }, // 골드
        2: { fill: '#C0C0C0', stroke: '#808080', text: '#404040' }, // 실버
        3: { fill: '#CD7F32', stroke: '#8B4513', text: '#FFFFFF' }, // 브론즈
    };
    const color = colors[rank as 1 | 2 | 3] || colors[3];

    return (
        <svg viewBox="0 0 100 100" className="w-8 h-8 drop-shadow-md">
            {/* 피크 몸통 */}
            <path
                d="M 50 98 C 85 80, 95 30, 85 15 C 75 5, 25 5, 15 15 C 5 30, 15 80, 50 98 Z"
                fill={color.fill}
                stroke={color.stroke}
                strokeWidth="3"
            />
            {/* 순위 숫자 */}
            <text
                x="50"
                y="55"
                textAnchor="middle"
                fill={color.text}
                fontSize="32"
                fontWeight="bold"
                fontFamily="system-ui, sans-serif"
            >
                {rank}
            </text>
        </svg>
    );
}

export default function ItemCard({
    item,
    rank,
    referencePrice,
    onClick,
    isOwner,
    isLoggedIn,
    onExtend,
    onReport,
    onUpdatePrice,
    onClickDelete,
}: ItemCardProps) {
    const [showReportModal, setShowReportModal] = useState(false);
    const [showPriceModal, setShowPriceModal] = useState(false);
    const [reportReason, setReportReason] = useState<ReportReason>('wrong_price');
    const [newPrice, setNewPrice] = useState(item.lprice.toString());

    const source = item.source || 'other';
    const sourceStyle = SOURCE_STYLES[source] || SOURCE_STYLES.other;
    const mallName = 'mallName' in item ? item.mallName : ('source_display' in item ? item.source_display : '');

    // 유저 매물인지 확인 (id 필드 존재 여부로 판단)
    const isUserItem = 'id' in item && source !== 'naver';

    // 할인율 계산
    const discount = 'discount_rate' in item
        ? item.discount_rate
        : referencePrice
            ? calculateDiscount(item.lprice, referencePrice)
            : 0;

    // 이미지 URL
    const imageUrl = 'image' in item ? item.image : '';

    const handleExtend = (e: React.MouseEvent) => {
        e.stopPropagation();
        onExtend?.();
    };

    const handleReportClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        // 로그인 없이도 신고 가능 (세션 기반)
        setShowReportModal(true);
    };

    const handleReportSubmit = () => {
        onReport?.(reportReason);
        setShowReportModal(false);
    };

    const handlePriceClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (!isLoggedIn) {
            alert('로그인이 필요합니다.');
            return;
        }
        setNewPrice(item.lprice.toString());
        setShowPriceModal(true);
    };

    const handlePriceSubmit = () => {
        const price = parseInt(newPrice.replace(/,/g, ''), 10);
        if (isNaN(price) || price <= 0) {
            alert('유효한 가격을 입력해주세요.');
            return;
        }
        onUpdatePrice?.(price);
        setShowPriceModal(false);
    };

    return (
        <>
            <motion.div
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                whileHover={{ scale: 1.02, y: -4 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => { }} // Remove handler, use Link overlay
                className="
                    relative flex flex-col p-0 bg-white rounded-2xl sm:rounded-[32px]
                    transition-all duration-300
                    hover:-translate-y-2
                    shadow-[0_10px_40px_-10px_rgba(0,0,0,0.08)]
                    hover:shadow-[0_20px_50px_-12px_rgba(0,0,0,0.12)]
                    group h-full
                "
            >
                {/* 
                  [SEO & Security] 
                  직접적인 <a> 태그 사용 (네이버 보안 정책/모바일 이슈 해결)
                  referrerPolicy="no-referrer-when-downgrade" 추가
                  XSS 방지: http/https 프로토콜만 허용
                */}
                {isValidUrl(item.link) ? (
                    <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        referrerPolicy="no-referrer-when-downgrade"
                        className="absolute inset-0 z-10 rounded-2xl sm:rounded-[32px]"
                        aria-label="상품 페이지로 이동"
                        onClick={onClick}
                    />
                ) : (
                    <div
                        className="absolute inset-0 z-10 rounded-2xl sm:rounded-[32px] cursor-not-allowed"
                        title="잘못된 링크입니다"
                    />
                )}

                {/* 이미지 (Top Half Cover) */}
                <div className="w-full h-36 sm:h-56 relative overflow-hidden bg-stone-50 rounded-t-2xl sm:rounded-t-[32px]">
                    {imageUrl ? (
                        <img
                            src={imageUrl}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                            loading="lazy"
                            onError={(e) => {
                                (e.target as HTMLImageElement).src = 'https://via.placeholder.com/300x200?text=No+Image';
                            }}
                        />
                    ) : (
                        <div className={`
                            w-full h-full flex flex-col items-center justify-center relative overflow-hidden 
                            transition-colors duration-300
                            ${source === 'mule' ? 'bg-blue-50 group-hover:bg-blue-100' :
                                source === 'bunjang' ? 'bg-red-50 group-hover:bg-red-100' :
                                    source === 'danggn' ? 'bg-orange-50 group-hover:bg-orange-100' :
                                        source === 'joonggonara' ? 'bg-green-50 group-hover:bg-green-100' :
                                            'bg-stone-50 group-hover:bg-stone-100'}
                        `}>
                            {/* 배경 데코레이션 */}
                            <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_50%_120%,currentColor_0%,transparent_50%)]" />

                            {/* 텍스트 (소스별 영어 이름) */}
                            <div className={`
                                text-4xl sm:text-5xl font-black tracking-tighter z-10 select-none
                                ${source === 'mule' ? 'text-blue-200' :
                                    source === 'bunjang' ? 'text-red-200' :
                                        source === 'danggn' ? 'text-orange-200' :
                                            source === 'joonggonara' ? 'text-green-200' :
                                                'text-stone-200'}
                            `}>
                                {source === 'mule' ? 'MULE' :
                                    source === 'bunjang' ? 'BUNJANG' :
                                        source === 'danggn' ? 'DAANGN' :
                                            source === 'joonggonara' ? 'NAVER' :
                                                'GUITAR'}
                            </div>
                        </div>
                    )}
                    {/* 출처 뱃지 (Overlay) */}
                    <span
                        className={`
                            absolute top-4 left-4 px-3 py-1.5 rounded-full text-xs font-bold tracking-wide shadow-sm
                            backdrop-blur-md bg-white/90 ${sourceStyle.text}
                        `}
                    >
                        {sourceStyle.label}
                    </span>

                    {/* 순위 (Overlay) */}
                    {rank && rank <= 3 && (
                        <div className="absolute top-4 right-4 z-10 drop-shadow-md">
                            <PickIcon rank={rank} />
                        </div>
                    )}
                </div>

                {/* 정보 (Padding) */}
                <div className="flex-1 flex flex-col p-3 sm:p-6">
                    {/* 상단: 제목 */}
                    <div className="mb-2 sm:mb-4">
                        <h3 className="text-sm sm:text-lg font-bold text-stone-800 line-clamp-2 leading-snug group-hover:text-matcha-700 transition-colors">
                            {item.title}
                        </h3>
                    </div>

                    {/* 하단: 가격 + 할인율 */}
                    <div className="flex items-end justify-between mt-auto">
                        <div>
                            <div className="flex items-baseline gap-0.5 flex-wrap">
                                <p className="text-lg sm:text-3xl font-black text-stone-900 tracking-tight leading-none">
                                    {formatPrice(item.lprice)}
                                </p>
                                <span className="text-xs sm:text-sm font-bold text-stone-400">원</span>
                            </div>

                            {discount > 0 && (
                                <p className="text-xs text-stone-500 mt-0.5">
                                    신품 대비 <span className="text-matcha-600 font-bold">{discount}%</span> 저렴
                                </p>
                            )}
                            {/* 출처 & 판매처 & 배송정보 */}
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${sourceStyle.bg} ${sourceStyle.text}`}>
                                    {sourceStyle.label}
                                </span>
                                {/* 판매처 (네이버만 표시) */}
                                {source === 'naver' && mallName && (
                                    <span className="text-xs text-stone-500 font-medium">
                                        {mallName}
                                    </span>
                                )}
                                {/* 무료배송 배지 (네이버 아이템에 임의 적용 or 조건부) */}
                                {source === 'naver' && (
                                    <span className="px-1.5 py-0.5 rounded bg-stone-100 text-stone-500 text-[10px]">
                                        무료배송
                                    </span>
                                )}
                            </div>

                            {/* 가격 disclaimer (네이버 아이템만) */}
                            {source === 'naver' && (
                                <p className="text-[10px] text-stone-400 mt-0.5">
                                    * 가격이 변동될 수 있습니다
                                </p>
                            )}
                        </div>

                        {/* 버튼들 - z-20으로 링크 위에 배치 */}
                        <div className="relative z-20 flex items-center gap-2">
                            {/* 연장 버튼 (본인 매물만) */}
                            {/* 연장 버튼 (본인 매물만) - 초록색 */}
                            {isOwner && (
                                <button
                                    onClick={handleExtend}
                                    className="w-8 h-8 rounded-full bg-matcha-100 text-matcha-600 flex items-center justify-center hover:bg-matcha-200 transition-colors"
                                    title="기간 연장"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </button>
                            )}

                            {/* 유저 매물: 가격 업데이트 버튼 (파란색) - 본인도 가능 */}
                            {isUserItem && onUpdatePrice && (
                                <button
                                    onClick={handlePriceClick}
                                    className="w-8 h-8 rounded-full bg-blue-100 text-blue-500 flex items-center justify-center hover:bg-blue-200 transition-colors"
                                    title="가격 업데이트/수정"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    </svg>
                                </button>
                            )}

                            {/* 유저 매물: 신고 버튼 (주황색) */}
                            {isUserItem && !isOwner && onReport && (
                                <button
                                    onClick={handleReportClick}
                                    className="w-8 h-8 rounded-full bg-orange-100 text-orange-500 flex items-center justify-center hover:bg-orange-200 transition-colors"
                                    title="신고하기"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                </button>
                            )}

                            {/* 본인 매물: 삭제 버튼 (빨간색) */}
                            {isOwner && onClickDelete && (
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onClickDelete();
                                    }}
                                    className="w-8 h-8 rounded-full bg-red-100 text-red-500 flex items-center justify-center hover:bg-red-200 transition-colors"
                                    title="삭제하기"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            )}

                        </div>
                    </div>
                </div>
            </motion.div>

            {/* 신고 모달 */}
            <AnimatePresence>
                {showReportModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowReportModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h3 className="text-lg font-bold text-stone-800 mb-4">🚨 신고하기</h3>
                            <div className="space-y-2 mb-4">
                                {(Object.keys(REPORT_REASON_LABELS) as ReportReason[]).map((reason) => (
                                    <label
                                        key={reason}
                                        className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${reportReason === reason ? 'bg-red-50 border-red-200 border' : 'bg-stone-50 hover:bg-stone-100'
                                            }`}
                                    >
                                        <input
                                            type="radio"
                                            name="report-reason"
                                            value={reason}
                                            checked={reportReason === reason}
                                            onChange={() => setReportReason(reason)}
                                            className="accent-red-500"
                                        />
                                        <span className="text-sm text-stone-700">{REPORT_REASON_LABELS[reason]}</span>
                                    </label>
                                ))}
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowReportModal(false)}
                                    className="flex-1 py-2 rounded-lg bg-stone-100 text-stone-600 font-medium hover:bg-stone-200 transition-colors"
                                >
                                    취소
                                </button>
                                <button
                                    onClick={handleReportSubmit}
                                    className="flex-1 py-2 rounded-lg bg-red-500 text-white font-medium hover:bg-red-600 transition-colors"
                                >
                                    신고
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 가격 업데이트 모달 */}
            <AnimatePresence>
                {showPriceModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowPriceModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <h3 className="text-lg font-bold text-stone-800 mb-4">💰 가격 업데이트</h3>
                            <p className="text-sm text-stone-500 mb-4">
                                가격이 변동되었나요? 새 가격을 입력해주세요.
                            </p>
                            <div className="relative mb-4">
                                <input
                                    type="text"
                                    value={newPrice}
                                    onChange={(e) => setNewPrice(e.target.value.replace(/[^0-9]/g, ''))}
                                    className="w-full px-4 py-3 rounded-lg border border-stone-200 focus:border-matcha-400 focus:ring-2 focus:ring-matcha-100 outline-none text-lg"
                                    placeholder="가격 입력"
                                />
                                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-stone-400">원</span>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowPriceModal(false)}
                                    className="flex-1 py-2 rounded-lg bg-stone-100 text-stone-600 font-medium hover:bg-stone-200 transition-colors"
                                >
                                    취소
                                </button>
                                <button
                                    onClick={handlePriceSubmit}
                                    className="flex-1 py-2 rounded-lg bg-matcha-500 text-white font-medium hover:bg-matcha-600 transition-colors"
                                >
                                    업데이트
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
