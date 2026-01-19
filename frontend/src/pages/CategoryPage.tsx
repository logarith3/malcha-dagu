/**
 * Category/Brand Page Component
 * 
 * Handles hierarchical URLs:
 * - /brand/fender
 * - /category/guitar/fender ...
 */

import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useSearch } from '../hooks/useSearch';
import SearchBar from '../components/SearchBar';
import ItemCard from '../components/ItemCard';
import MatchaBounceLoader from '../components/MatchaBounceLoader';
import CategoryHeader from '../components/CategoryHeader';
import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';

const MIN_LOADING_TIME = 2500;

export default function CategoryPage() {
    const { brand, model, submodel } = useParams<{ brand: string; model?: string; submodel?: string }>();
    const navigate = useNavigate();
    const { isLoggedIn } = useAuth();

    // Construct search query
    const rawQuery = [brand, model, submodel].filter(Boolean).join(' ');

    // Loader state
    const [showLoader, setShowLoader] = useState(true);
    const [minTimeElapsed, setMinTimeElapsed] = useState(false);

    // Search API call
    const { data, isLoading, isError, error } = useSearch(rawQuery, {
        enabled: rawQuery.length > 0,
    });

    // Minimum load time
    useEffect(() => {
        if (!rawQuery) return;
        setShowLoader(true);
        setMinTimeElapsed(false);
        const timer = setTimeout(() => setMinTimeElapsed(true), MIN_LOADING_TIME);
        return () => clearTimeout(timer);
    }, [rawQuery]);

    useEffect(() => {
        if (!isLoading && minTimeElapsed) {
            setShowLoader(false);
        }
    }, [isLoading, minTimeElapsed]);

    const handleSearch = (newQuery: string) => {
        navigate(`/search?q=${encodeURIComponent(newQuery)}`);
    };

    const allItems = data?.items || [];

    // If backend returns taxonomy, use it. Otherwise fallback to simple header.
    const taxonomy = data?.taxonomy;

    return (
        <div className="min-h-screen">
            <MatchaBounceLoader isVisible={showLoader} />

            {!showLoader && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4 }}
                >
                    {/* Header */}
                    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-stone-200 shadow-sm">
                        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-2 sm:py-4">
                            <div className="flex items-center gap-2 sm:gap-4">
                                <motion.button
                                    onClick={() => navigate('/')}
                                    className="text-lg sm:text-2xl font-black text-matcha-600 tracking-tight shrink-0"
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                >
                                    DAGU
                                </motion.button>
                                <div className="flex-1 min-w-0">
                                    <SearchBar
                                        onSearch={handleSearch}
                                        isLoading={isLoading}
                                        initialValue={rawQuery}
                                        placeholder="다른 악기 검색"
                                    />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Main Content */}
                    <main className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-8">

                        {/* Breadcrumbs fallback (if no taxonomy) */}
                        {!taxonomy && (
                            <nav className="flex items-center gap-2 text-xs font-medium text-stone-400 mb-4 overflow-x-auto whitespace-nowrap scrollbar-hide">
                                <Link to="/" className="hover:text-stone-600 transition-colors">Home</Link>
                                <span className="text-stone-300">›</span>
                                <span className="text-matcha-600 font-bold capitalize">{rawQuery}</span>
                            </nav>
                        )}

                        {/* Category Header (Taxonomy or Fallback) */}
                        <div className="mb-8">
                            {taxonomy ? (
                                <CategoryHeader taxonomy={taxonomy} />
                            ) : (
                                <>
                                    <h1 className="text-3xl sm:text-4xl font-black text-stone-800 tracking-tight capitalize mb-2">
                                        {rawQuery}
                                    </h1>
                                    <p className="text-stone-500 font-medium leading-relaxed max-w-2xl">
                                        {rawQuery} 관련 매물 검색 결과입니다.
                                    </p>
                                </>
                            )}

                            {data && (
                                <p className="text-sm text-stone-400 mt-2 text-right border-t border-dashed pt-2">
                                    총 {data.total_count}개의 매물 발견
                                </p>
                            )}
                        </div>

                        {/* Divider */}
                        {!taxonomy && <div className="h-px w-full bg-gradient-to-r from-stone-200 via-stone-100 to-transparent mb-8" />}

                        {/* Error */}
                        {isError && (
                            <div className="text-center py-12 bg-red-50 rounded-2xl border border-red-100 mb-8">
                                <p className="text-4xl mb-4">😵</p>
                                <p className="text-red-700 font-medium">검색 중 오류가 발생했습니다</p>
                                <p className="text-red-500 text-sm mt-2">
                                    {error instanceof Error ? error.message : '잠시 후 다시 시도해주세요'}
                                </p>
                            </div>
                        )}

                        {/* Results Grid */}
                        {allItems.length > 0 ? (
                            <motion.div
                                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-6"
                                variants={{
                                    hidden: { opacity: 0 },
                                    show: {
                                        opacity: 1,
                                        transition: { staggerChildren: 0.08 }
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
                                            isLoggedIn={isLoggedIn}
                                        />
                                    </motion.div>
                                ))}
                            </motion.div>
                        ) : (
                            !isLoading && (
                                <div className="text-center py-16 bg-stone-50 rounded-2xl border border-dashed border-stone-300 mb-8">
                                    <p className="text-4xl mb-4 opacity-50">🎸</p>
                                    <p className="text-stone-600 font-medium">'{rawQuery}' 관련 매물이 없습니다</p>
                                </div>
                            )
                        )}
                    </main>

                    {/* Footer */}
                    <footer className="mt-12 py-6 text-center text-xs text-stone-400 border-t border-stone-100">
                        <p>* 네이버쇼핑 가격 정보는 실시간 조회 결과이며, 실제 판매가와 다를 수 있습니다.</p>
                    </footer>
                </motion.div>
            )}
        </div>
    );
}
