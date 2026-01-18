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
import { AxiosError } from 'axios';
import SearchBar from '../components/SearchBar';
import MatchaBounceLoader from '../components/MatchaBounceLoader';
import ItemCard from '../components/ItemCard';
import { useSearch, useTrackItemClick, useCreateUserItem, useExtendUserItem, useReportItem, useUpdateItemPrice } from '../hooks/useSearch';
import { useAuth } from '../hooks/useAuth';
import type { NaverItem, MergedUserItem, ReportReason } from '../types';

// API 에러 응답 타입
interface ApiErrorResponse {
    [key: string]: string | string[];
}

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

const MIN_LOADING_TIME = 3400;

export default function SearchResultPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const query = searchParams.get('q') || '';

    const [showLoader, setShowLoader] = useState(true);
    const [minTimeElapsed, setMinTimeElapsed] = useState(false);
    const [showRegisterModal, setShowRegisterModal] = useState(false);

    // SSO 인증 상태 확인
    const { isLoggedIn } = useAuth();

    // React Query로 검색
    const { data, isLoading, isError, error } = useSearch(query, {
        enabled: query.length > 0,
    });

    // 클릭 추적
    const trackClick = useTrackItemClick();

    // 연장 기능
    const extendItem = useExtendUserItem();

    // 신고 기능
    const reportItem = useReportItem();

    // 가격 업데이트 기능
    const updatePrice = useUpdateItemPrice();

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

    // 정규화된 검색어는 외부 링크용으로만 사용 (URL 업데이트 시 재검색 발생하므로 제거)
    const externalSearchQuery = data?.search_query || query;

    const handleSearch = (newQuery: string) => {
        navigate(`/search?q=${encodeURIComponent(newQuery)}`);
    };

    const handleItemClick = (item: NaverItem | MergedUserItem) => {
        if ('id' in item && item.source !== 'naver') {
            trackClick.mutate(item.id);
        }
    };

    const handleExtendItem = (itemId: string) => {
        extendItem.mutate(itemId, {
            onSuccess: () => {
                alert('매물이 72시간 연장되었습니다!');
            },
            onError: (err: unknown) => {
                const axiosErr = err as AxiosError<{ error?: string }>;
                const statusCode = axiosErr.response?.status;
                const serverMsg = axiosErr.response?.data?.error;

                if (statusCode === 401) {
                    alert('로그인이 필요합니다.\n연장은 로그인 후 이용해주세요.');
                } else if (statusCode === 403) {
                    alert('본인 매물만 연장할 수 있습니다.');
                } else if (statusCode === 404) {
                    alert('매물을 찾을 수 없습니다.\n이미 삭제되었거나 존재하지 않는 매물입니다.');
                } else if (statusCode === 500) {
                    alert('서버 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.');
                } else if (!axiosErr.response) {
                    alert('네트워크 오류가 발생했습니다.\n인터넷 연결을 확인해주세요.');
                } else {
                    alert(serverMsg || '연장 처리 중 오류가 발생했습니다.');
                }
            },
        });
    };

    const handleReportItem = (itemId: string, reason: ReportReason) => {
        reportItem.mutate({ id: itemId, reason }, {
            onSuccess: (data) => {
                if (data.is_deleted) {
                    alert('신고가 접수되었습니다.\n가격 오류 신고가 누적되어 해당 매물이 삭제되었습니다.');
                } else if (data.is_under_review) {
                    alert('신고가 접수되었습니다.\n해당 매물은 검토 대기 중으로 전환되었습니다.');
                } else {
                    alert('신고가 접수되었습니다.\n감사합니다!');
                }
            },
            onError: (err: unknown) => {
                const axiosErr = err as AxiosError<{ error?: string }>;
                const statusCode = axiosErr.response?.status;
                const serverMsg = axiosErr.response?.data?.error;

                // 상태 코드별 상세 메시지
                if (statusCode === 400) {
                    if (serverMsg?.includes('이미 신고')) {
                        alert('이미 신고한 매물입니다.\n같은 매물은 한 번만 신고할 수 있습니다.');
                    } else if (serverMsg?.includes('본인 매물')) {
                        alert('본인 매물은 신고할 수 없습니다.');
                    } else {
                        alert(serverMsg || '잘못된 요청입니다.');
                    }
                } else if (statusCode === 404) {
                    alert('매물을 찾을 수 없습니다.\n이미 삭제되었거나 존재하지 않는 매물입니다.');
                } else if (statusCode === 500) {
                    alert('서버 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.');
                } else if (!axiosErr.response) {
                    alert('네트워크 오류가 발생했습니다.\n인터넷 연결을 확인해주세요.');
                } else {
                    alert(serverMsg || '신고 처리 중 오류가 발생했습니다.');
                }
            },
        });
    };

    const handleUpdatePrice = (itemId: string, newPrice: number) => {
        updatePrice.mutate({ id: itemId, price: newPrice }, {
            onSuccess: () => {
                alert('가격이 업데이트되었습니다.\n감사합니다!');
            },
            onError: (err: unknown) => {
                const axiosErr = err as AxiosError<{ error?: string }>;
                const statusCode = axiosErr.response?.status;
                const serverMsg = axiosErr.response?.data?.error;

                // 상태 코드별 상세 메시지
                if (statusCode === 400) {
                    if (serverMsg?.includes('유효한 가격')) {
                        alert('유효한 가격을 입력해주세요.\n0보다 큰 숫자를 입력해야 합니다.');
                    } else if (serverMsg?.includes('너무 높')) {
                        alert('가격이 너무 높습니다.\n1억원 이하로 입력해주세요.');
                    } else {
                        alert(serverMsg || '잘못된 요청입니다.');
                    }
                } else if (statusCode === 401) {
                    alert('로그인이 필요합니다.\n가격 업데이트는 로그인 후 이용해주세요.');
                } else if (statusCode === 404) {
                    alert('매물을 찾을 수 없습니다.\n이미 삭제되었거나 존재하지 않는 매물입니다.');
                } else if (statusCode === 500) {
                    alert('서버 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.');
                } else if (!axiosErr.response) {
                    alert('네트워크 오류가 발생했습니다.\n인터넷 연결을 확인해주세요.');
                } else {
                    alert(serverMsg || '가격 업데이트 중 오류가 발생했습니다.');
                }
            },
        });
    };

    // 소유자 여부 확인 (is_owner 필드가 있으면 사용, 없으면 false)
    const isItemOwner = (item: NaverItem | MergedUserItem): boolean => {
        if (!isLoggedIn) return false;
        // UserItemSerializer에서 is_owner 필드 제공 시 사용
        if ('is_owner' in item) return (item as { is_owner: boolean }).is_owner;
        return false;
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
                    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-stone-200 shadow-sm">
                        <div className="max-w-7xl mx-auto px-4 py-4">
                            <div className="flex items-center gap-4">
                                <motion.button
                                    onClick={() => navigate('/')}
                                    className="text-2xl font-black text-matcha-600 tracking-tight"
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                >
                                    DAGU
                                </motion.button>
                                <div className="flex-1 max-w-2xl">
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

                    {/* 메인 Container (Grid Layout) */}
                    <main className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_280px] gap-8 items-start">

                        {/* Left Column: Results */}
                        <div className="min-w-0">
                            {/* Title & Count */}
                            <div className="mb-6">
                                <h1 className="text-3xl font-bold text-stone-800 tracking-tight">
                                    "<span className="text-matcha-600">{query}</span>" 검색 결과
                                </h1>
                                {data && (
                                    <p className="text-stone-500 mt-2 font-medium">
                                        총 {data.total_count}개의 매물을 찾았습니다
                                    </p>
                                )}
                            </div>

                            {/* Mobile External Search Buttons (Visible only on < lg) */}
                            <div className="lg:hidden mb-8">
                                <ExternalSearchButtons query={externalSearchQuery} vertical={false} />
                            </div>

                            {/* 에러 */}
                            {isError && (
                                <div className="text-center py-12 bg-red-50 rounded-2xl border border-red-100 mb-8">
                                    <p className="text-4xl mb-4">😵</p>
                                    <p className="text-red-700 font-medium">검색 중 오류가 발생했습니다</p>
                                    <p className="text-red-500 text-sm mt-2">
                                        {error instanceof Error ? error.message : '잠시 후 다시 시도해주세요'}
                                    </p>
                                </div>
                            )}

                            {/* 결과 없음 */}
                            {data && data.total_count === 0 && (
                                <div className="text-center py-16 bg-stone-50 rounded-2xl border border-dashed border-stone-300 mb-8">
                                    <p className="text-4xl mb-4 opacity-50">🎸</p>
                                    <p className="text-stone-600 font-medium">검색 결과가 없습니다</p>
                                    <p className="text-stone-400 text-sm mt-2">다른 검색어로 시도해보세요</p>
                                </div>
                            )}

                            {/* 결과 리스트 */}
                            {allItems.length > 0 && (
                                <motion.div
                                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
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
                                                referencePrice={data?.reference?.price}
                                                onClick={() => handleItemClick(item)}
                                                isOwner={isItemOwner(item)}
                                                isLoggedIn={isLoggedIn}
                                                onExtend={'id' in item ? () => handleExtendItem(item.id) : undefined}
                                                onReport={'id' in item && item.source !== 'naver' ? (reason) => handleReportItem(item.id, reason) : undefined}
                                                onUpdatePrice={'id' in item && item.source !== 'naver' ? (price) => handleUpdatePrice(item.id, price) : undefined}
                                            />
                                        </motion.div>
                                    ))}
                                </motion.div>
                            )}
                        </div>

                        {/* Right Column: Sticky Sidebar (Visible only on >= lg) */}
                        <aside className="hidden lg:block h-full">
                            <div className="sticky top-24 space-y-4">
                                <div className="p-4 bg-stone-50 rounded-2xl border border-stone-100">
                                    <h3 className="text-sm font-bold text-stone-500 mb-3 uppercase tracking-wider">다른 사이트에서 찾기</h3>
                                    <ExternalSearchButtons query={externalSearchQuery} vertical={true} />
                                </div>
                                {/* PC용 매물등록 버튼 */}
                                <button
                                    onClick={() => {
                                        if (!isLoggedIn) {
                                            window.location.href = '/login';
                                            return;
                                        }
                                        setShowRegisterModal(true);
                                    }}
                                    className="
                                        flex items-center justify-between px-5 py-4
                                        rounded-xl bg-matcha-100 text-matcha-700
                                        hover:bg-matcha-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-matcha-200/50
                                        transition-all duration-200 group w-full
                                    "
                                >
                                    <span className="font-bold text-base">매물등록</span>
                                    <svg className="w-4 h-4 opacity-70 group-hover:translate-x-0.5 group-hover:opacity-100 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4.5v15m7.5-7.5h-15" />
                                    </svg>
                                </button>
                            </div>
                        </aside>

                    </main>

                    {/* FAB (매물 등록) - 모바일에서만 표시 (PC는 사이드바에 있음) */}
                    <motion.button
                        onClick={() => {
                            if (!isLoggedIn) {
                                window.location.href = '/login';
                                return;
                            }
                            setShowRegisterModal(true);
                        }}
                        className="
                            lg:hidden
                            fixed bottom-8 right-8 z-50
                            px-5 py-3 rounded-full
                            bg-matcha-500 text-white
                            shadow-[0_4px_0_0_#16a34a]
                            flex items-center justify-center gap-2
                            hover:bg-matcha-600 active:shadow-[0_2px_0_0_#16a34a] active:translate-y-[2px]
                            transition-all duration-150
                        "
                        initial={{ scale: 0, rotate: 90 }}
                        animate={{ scale: 1, rotate: 0 }}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                        <span className="font-bold text-sm">매물등록</span>
                    </motion.button>
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

            {/* 푸터 */}
            <footer className="mt-12 py-6 text-center text-xs text-stone-400 border-t border-stone-100">
                <p>* 네이버쇼핑 가격 정보는 실시간 조회 결과이며, 실제 판매가와 다를 수 있습니다.</p>
            </footer>
        </div>
    );
}

// 외부 검색 버튼 컴포넌트
const ExternalSearchButtons = ({ query, vertical }: { query: string, vertical: boolean }) => (
    <div className={`flex ${vertical ? 'flex-col gap-3' : 'flex-wrap gap-2'}`}>
        {/* Mule */}
        <a
            href={`https://www.mule.co.kr/bbs/market/sell?qf=title&qs=${encodeURIComponent(query.slice(0, 20))}&sb=wdate&sd=desc`}
            target="_blank"
            rel="noopener noreferrer"
            className={`
                flex items-center ${vertical ? 'justify-between px-5 py-4' : 'justify-center gap-2 px-6 py-3'} 
                rounded-xl bg-blue-100 text-blue-700
                hover:bg-blue-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-blue-200/50
                transition-all duration-200 group
            `}
        >
            <span className={`font-bold ${vertical ? 'text-base' : ''}`}>Mule</span>
            <svg className="w-4 h-4 opacity-70 group-hover:translate-x-0.5 group-hover:opacity-100 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
        </a>

        {/* Reverb */}
        <a
            href={`https://reverb.com/marketplace?query=${encodeURIComponent(query)}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`
                flex items-center ${vertical ? 'justify-between px-5 py-4' : 'justify-center gap-2 px-6 py-3'} 
                rounded-xl bg-yellow-100 text-yellow-700
                hover:bg-yellow-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-yellow-200/50
                transition-all duration-200 group
            `}
        >
            <span className={`font-bold ${vertical ? 'text-base' : ''}`}>Reverb</span>
            <svg className="w-4 h-4 opacity-70 group-hover:translate-x-0.5 group-hover:opacity-100 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
        </a>

        {/* Digimart */}
        <a
            href={`https://www.digimart.net/search?keywordAnd=${query.replace(/ /g, '+')}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`
                flex items-center ${vertical ? 'justify-between px-5 py-4' : 'justify-center gap-2 px-6 py-3'} 
                rounded-xl bg-red-100 text-red-700
                hover:bg-red-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-red-200/50
                transition-all duration-200 group
            `}
        >
            <span className={`font-bold ${vertical ? 'text-base' : ''}`}>Digimart</span>
            <svg className="w-4 h-4 opacity-70 group-hover:translate-x-0.5 group-hover:opacity-100 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
        </a>
    </div>
);

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
                // 검색 결과 즉시 다시 가져오기
                queryClient.refetchQueries({ queryKey: ['search'] });

                const sourceName = SOURCE_LABELS[finalSource] || '등록된 매물';
                alert(`${sourceName} 매물이 성공적으로 등록되었습니다! 🎸`);
                onClose();
            },
            onError: (err: Error) => {
                const error = err as AxiosError<ApiErrorResponse>;
                console.error('Failed to register item:', error);

                let errorMsg = '등록에 실패했습니다.';
                try {
                    const data = error.response?.data;
                    if (data) {
                        // JSON 문자열로 변환 후 파싱
                        const jsonStr = JSON.stringify(data);
                        if (jsonStr.includes('이미 등록된')) {
                            errorMsg = '이미 등록된 매물입니다.';
                        } else if (jsonStr.includes('허용되지 않은')) {
                            errorMsg = '허용되지 않은 사이트입니다.\n(뮬, 번개장터, 당근마켓, 중고나라만 등록 가능)';
                        } else {
                            // 모든 에러 메시지 추출
                            const messages: string[] = [];
                            Object.values(data).forEach(value => {
                                if (Array.isArray(value)) {
                                    messages.push(...value.map(v => String(v)));
                                } else if (typeof value === 'string') {
                                    messages.push(value);
                                }
                            });
                            errorMsg = messages.join('\n') || '입력값을 확인해주세요.';
                        }
                    }
                } catch {
                    errorMsg = error.message || '등록에 실패했습니다.';
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
