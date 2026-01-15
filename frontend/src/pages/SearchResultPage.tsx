/**
 * Search Result Page Component
 * 
 * Features:
 * - 검색 결과 리스트 (Staggered Animation)
 * - 매물 등록 버튼 (API 연동 + 자동 소스 감지)
 * - React Query 캐싱 및 자동 갱신
 */

import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';
import SearchBar from '../components/SearchBar';
import MatchaBounceLoader from '../components/MatchaBounceLoader';
import ItemCard from '../components/ItemCard';
import { useSearch, useTrackItemClick, useCreateUserItem } from '../hooks/useSearch';
import type { NaverItem, MergedUserItem } from '../types';

// 소스 자동 감지 헬퍼
const SOURCE_LABELS: Record<string, string> = {
    mule: '뮬 (Mule)',
    joonggonara: '중고나라',
    danggn: '당근마켓',
    bunjang: '번개장터',
    other: '기타 사이트'
};

const SOURCE_COLORS: Record<string, string> = {
    mule: 'bg-blue-50 text-blue-700 border-blue-200',
    joonggonara: 'bg-green-50 text-green-700 border-green-200',
    danggn: 'bg-orange-50 text-orange-700 border-orange-200',
    bunjang: 'bg-red-50 text-red-700 border-red-200',
    other: 'bg-stone-50 text-stone-600 border-stone-200'
};

function detectSource(url: string): string {
    const lower = url.toLowerCase();
    if (lower.includes('mule.co.kr')) return 'mule';
    if (lower.includes('joonggonara') || (lower.includes('cafe.naver.com') && lower.includes('joon'))) return 'joonggonara';
    if (lower.includes('daangn.com') || lower.includes('danggn')) return 'danggn';
    if (lower.includes('bunjang.co.kr')) return 'bunjang';
    return 'other';
}

const MIN_LOADING_TIME = 1500;

export default function SearchResultPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const query = searchParams.get('q') || '';

    const [showLoader, setShowLoader] = useState(true);
    const [minTimeElapsed, setMinTimeElapsed] = useState(false);
    const [showRegisterModal, setShowRegisterModal] = useState(false);

    // React Query로 검색
    const { data, isLoading, isError, error } = useSearch(query, {
        enabled: query.length > 0,
    });

    // 클릭 추적
    const trackClick = useTrackItemClick();

    // 최소 로딩 시간 보장
    useEffect(() => {
        if (!query) return;
        setShowLoader(true);
        setMinTimeElapsed(false);
        const timer = setTimeout(() => setMinTimeElapsed(true), MIN_LOADING_TIME);
        return () => clearTimeout(timer);
    }, [query]);

    useEffect(() => {
        if (!isLoading && minTimeElapsed) {
            setShowLoader(false);
        }
    }, [isLoading, minTimeElapsed]);

    const handleSearch = (newQuery: string) => {
        navigate(`/search?q=${encodeURIComponent(newQuery)}`);
    };

    const handleItemClick = (item: NaverItem | MergedUserItem) => {
        if ('id' in item && item.source !== 'naver') {
            trackClick.mutate(item.id);
        }
    };

    if (!query) {
        navigate('/');
        return null;
    }

    const allItems = data?.items || [];

    return (
        <div className="min-h-screen">
            <MatchaBounceLoader isVisible={showLoader} />

            {!showLoader && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4 }}
                >
                    {/* 헤더 */}
                    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-stone-200">
                        <div className="max-w-4xl mx-auto px-4 py-4">
                            <div className="flex items-center gap-4">
                                <motion.button
                                    onClick={() => navigate('/')}
                                    className="text-2xl"
                                    whileHover={{ scale: 1.1, rotate: 10 }}
                                    whileTap={{ scale: 0.9 }}
                                >
                                    🍵
                                </motion.button>
                                <div className="flex-1">
                                    <SearchBar
                                        onSearch={handleSearch}
                                        isLoading={isLoading}
                                        initialValue={query}
                                        placeholder="다른 악기 검색"
                                    />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* 메인 */}
                    <main className="max-w-4xl mx-auto px-4 py-8">
                        {/* 헤더 + 등록 버튼 */}
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h1 className="text-2xl font-bold text-stone-800">
                                    "<span className="text-matcha-600">{query}</span>" 검색 결과
                                </h1>
                                {data && (
                                    <p className="text-stone-500 mt-1">
                                        {data.total_count}개 매물
                                    </p>
                                )}
                            </div>

                            <motion.button
                                onClick={() => setShowRegisterModal(true)}
                                className="px-4 py-2.5 bg-matcha-500 text-white rounded-xl font-medium
                                         hover:bg-matcha-600 transition-colors shadow-md flex items-center gap-2"
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                            >
                                <span>+</span>
                                <span>매물 등록</span>
                            </motion.button>
                        </div>

                        {/* 에러 */}
                        {isError && (
                            <div className="text-center py-12 bg-red-50 rounded-2xl border border-red-100">
                                <p className="text-4xl mb-4">😵</p>
                                <p className="text-red-700 font-medium">검색 중 오류가 발생했습니다</p>
                                <p className="text-red-500 text-sm mt-2">
                                    {error instanceof Error ? error.message : '잠시 후 다시 시도해주세요'}
                                </p>
                            </div>
                        )}

                        {/* 결과 없음 */}
                        {data && data.total_count === 0 && (
                            <div className="text-center py-16 bg-stone-50 rounded-2xl border border-dashed border-stone-300">
                                <p className="text-4xl mb-4 opacity-50">🎸</p>
                                <p className="text-stone-600 font-medium">검색 결과가 없습니다</p>
                                <p className="text-stone-400 text-sm mt-2">다른 검색어로 시도해보세요</p>
                            </div>
                        )}

                        {/* 결과 리스트 */}
                        {allItems.length > 0 && (
                            <motion.div
                                className="space-y-4"
                                variants={{
                                    hidden: { opacity: 0 },
                                    show: {
                                        opacity: 1,
                                        transition: {
                                            staggerChildren: 0.1
                                        }
                                    }
                                }}
                                initial="hidden"
                                animate="show"
                            >
                                {allItems.map((item, index) => (
                                    <motion.div
                                        key={`item-${index}-${'id' in item ? item.id : item.productId}`}
                                        variants={{
                                            hidden: { opacity: 0, y: 20 },
                                            show: { opacity: 1, y: 0 }
                                        }}
                                    >
                                        <ItemCard
                                            item={item}
                                            rank={index + 1}
                                            onClick={() => handleItemClick(item)}
                                        />
                                    </motion.div>
                                ))}
                            </motion.div>
                        )}
                    </main>
                </motion.div>
            )}

            {/* 매물 등록 모달 */}
            <AnimatePresence>
                {showRegisterModal && (
                    <RegisterModal
                        query={query}
                        onClose={() => setShowRegisterModal(false)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

// 매물 등록 모달
function RegisterModal({ query, onClose }: { query: string; onClose: () => void }) {
    const [price, setPrice] = useState('');
    const [link, setLink] = useState('');
    const [detectedSource, setDetectedSource] = useState('other');

    // 링크 입력 시 소스 감지
    useEffect(() => {
        setDetectedSource(detectSource(link));
    }, [link]);

    // API Hook
    const createUserItem = useCreateUserItem();
    const queryClient = useQueryClient();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // 1. 링크 URL 보정 (http/https 없으면 추가)
        let finalLink = link.trim();
        if (finalLink && !finalLink.match(/^https?:\/\//)) {
            finalLink = `https://${finalLink}`;
        }

        // 2. 최종 소스 결정
        const finalSource = detectSource(finalLink);

        createUserItem.mutate({
            title: query,
            price: Number(price),
            link: finalLink,
            source: finalSource
        }, {
            onSuccess: () => {
                // 검색 결과 캐시 즉시 만료 및 갱신 요청
                queryClient.invalidateQueries({ queryKey: ['search'] });

                const sourceName = SOURCE_LABELS[finalSource] || '등록된 매물';
                alert(`${sourceName} 매물이 성공적으로 등록되었습니다! 🎸`);
                onClose();
            },
            onError: (error: any) => {
                console.error('Failed to register item:', error);

                let errorMsg = '등록에 실패했습니다.';
                if (error.response?.data) {
                    const data = error.response.data;
                    if (typeof data === 'object') {
                        const messages = Object.entries(data)
                            .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' ') : value}`)
                            .join('\n');
                        errorMsg = `입력값을 확인해주세요:\n${messages}`;
                    } else {
                        errorMsg = `오류: ${JSON.stringify(data)}`;
                    }
                }
                alert(errorMsg);
            }
        });
    };

    return (
        <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
        >
            <motion.div
                className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6"
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-stone-800">매물 등록</h2>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center text-stone-500 hover:bg-stone-200"
                    >
                        ✕
                    </button>
                </div>

                {/* 악기명 표시 (자동) */}
                <div className="mb-4 p-3 bg-matcha-50 rounded-xl border border-matcha-100">
                    <p className="text-xs text-matcha-600 font-medium mb-1">악기명</p>
                    <p className="text-lg font-bold text-matcha-800">{query}</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* 가격 */}
                    <div>
                        <label className="block text-sm font-medium text-stone-700 mb-1.5">
                            가격 (원)
                        </label>
                        <input
                            type="number"
                            value={price}
                            onChange={(e) => setPrice(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl border border-stone-200 focus:border-matcha-400 focus:ring-2 focus:ring-matcha-100 outline-none transition-all"
                            placeholder="예: 850000"
                            required
                        />
                    </div>

                    {/* 링크 */}
                    <div>
                        <label className="block text-sm font-medium text-stone-700 mb-1.5">
                            매물 링크
                        </label>
                        <input
                            type="text"
                            value={link}
                            onChange={(e) => setLink(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl border border-stone-200 focus:border-matcha-400 focus:ring-2 focus:ring-matcha-100 outline-none transition-all"
                            placeholder="예: mule.co.kr/..."
                            required
                        />

                        {/* URL 감지 결과 표시 */}
                        {link.length > 5 && (
                            <motion.div
                                initial={{ opacity: 0, y: -5 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`mt-2 flex items-center gap-2 text-sm p-3 rounded-xl border ${SOURCE_COLORS[detectedSource]}`}
                            >
                                <span className="text-lg">
                                    {detectedSource === 'other' ? '🔗' : '✅'}
                                </span>
                                <span className="font-bold">
                                    {detectedSource === 'other'
                                        ? '출처를 감지할 수 없습니다 (기타로 등록됩니다)'
                                        : `${SOURCE_LABELS[detectedSource]} 감지되었습니다!`}
                                </span>
                            </motion.div>
                        )}
                    </div>

                    {/* 버튼 */}
                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 py-3 rounded-xl border border-stone-200 text-stone-600 font-medium hover:bg-stone-50 transition-colors"
                        >
                            취소
                        </button>
                        <button
                            type="submit"
                            disabled={createUserItem.isPending}
                            className={`flex-1 py-3 rounded-xl text-white font-bold transition-all shadow-md active:scale-95 disabled:opacity-50 ${detectedSource !== 'other'
                                    ? 'bg-matcha-600 hover:bg-matcha-700 hover:shadow-lg'
                                    : 'bg-stone-500 hover:bg-stone-600'
                                }`}
                        >
                            {createUserItem.isPending ? '등록 중...' : '등록하기'}
                        </button>
                    </div>
                </form>
            </motion.div>
        </motion.div>
    );
}
