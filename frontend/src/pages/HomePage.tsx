/**
 * Home Page Component
 *
 * Features:
 * - 히어로 섹션
 * - 검색바
 * - 실시간 인기 검색어
 * - 검색 시 결과 페이지로 이동
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import SearchBar from '../components/SearchBar';
import { getPopularSearches } from '../services/api';

const DEFAULT_TERMS = ['펜더 스트랫', '깁슨 레스폴', '테일러 어쿠스틱', 'SM58'];

export default function HomePage() {
    const navigate = useNavigate();
    const [popularTerms, setPopularTerms] = useState<string[]>(DEFAULT_TERMS);

    // 인기 검색어 로드
    useEffect(() => {
        async function fetchPopularSearches() {
            try {
                const terms = await getPopularSearches(4);
                if (terms && terms.length > 0) {
                    setPopularTerms(terms);
                }
            } catch (error) {
                console.warn('Failed to fetch popular searches:', error);
                // 실패 시 기본값 유지
            }
        }
        fetchPopularSearches();
    }, []);

    const handleSearch = (query: string) => {
        navigate(`/search?q=${encodeURIComponent(query)}`);
    };

    return (
        <div className="min-h-screen flex flex-col">
            {/* 히어로 섹션 */}
            <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
                {/* 로고 / 타이틀 */}
                <motion.div
                    className="text-center mb-12"
                    initial={{ opacity: 0, y: -30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <motion.div
                        className="text-8xl sm:text-9xl mb-6"
                        animate={{
                            y: [0, -10, 0],
                            rotate: [0, -5, 5, 0],
                        }}
                        transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: 'easeInOut',
                        }}
                    >
                        🍵
                    </motion.div>

                    <h1 className="text-7xl sm:text-8xl font-black mb-8 tracking-tighter text-stone-800">
                        DAGU
                    </h1>

                    <p className="text-2xl sm:text-3xl text-stone-600 max-w-2xl mx-auto leading-relaxed">
                        악기 시세를 한눈에 비교하고 <br className="sm:hidden" />
                        <span className="block sm:inline mt-2 sm:mt-0"><span className="text-matcha-600 font-black">다구</span>에서 <span className="font-bold text-stone-800">다구</span>해보세요</span>
                    </p>
                </motion.div>

                {/* 검색바 */}
                <div className="w-full max-w-xl px-4 relative z-10">
                    <SearchBar onSearch={handleSearch} />
                </div>

                {/* 인기 검색어 / 빠른 검색 */}
                <motion.div
                    className="mt-12 flex flex-col items-center gap-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                >
                    <span className="text-sm font-medium text-stone-400 uppercase tracking-widest text-[11px] mb-2">인기 매물</span>
                    <div className="flex flex-wrap justify-center gap-2.5">
                        {popularTerms.map((term, i) => (
                            <motion.button
                                key={`${term}-${i}`}
                                onClick={() => handleSearch(term)}
                                className="
                                    pl-3 pr-5 py-2.5 text-base bg-white text-stone-600
                                    rounded-full shadow-sm shadow-stone-200
                                    hover:bg-matcha-50 hover:text-matcha-800 hover:shadow-md hover:-translate-y-0.5
                                    transition-all duration-300
                                    flex items-center gap-2.5 group
                                "
                                whileHover={{ scale: 1.05, y: -2 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <span className={`
                                    w-5 h-5 flex items-center justify-center rounded-full text-[10px] font-black
                                    ${i < 3 ? 'bg-matcha-100 text-matcha-600' : 'bg-stone-100 text-stone-400'}
                                    group-hover:bg-white group-hover:text-matcha-600 transition-colors
                                `}>
                                    {i + 1}
                                </span>
                                <span className="font-medium">{term}</span>
                            </motion.button>
                        ))}
                    </div>
                </motion.div>
            </main>

            {/* 푸터 */}
            <footer className="py-8 text-center text-sm text-stone-400 mt-auto space-y-1">
                <p>© 2026 DAGU. 비영리로 운영되는 악기 시세 비교 서비스</p>
                <p className="text-xs text-stone-300">* 네이버쇼핑 가격 정보는 실시간 조회 결과이며, 실제 판매가와 다를 수 있습니다.</p>
            </footer>
        </div>
    );
}
