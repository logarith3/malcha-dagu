/**
 * Home Page Component
 * 
 * Features:
 * - 히어로 섹션
 * - 검색바
 * - 검색 시 결과 페이지로 이동
 */

import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import SearchBar from '../components/SearchBar';

export default function HomePage() {
    const navigate = useNavigate();

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
                        className="text-7xl mb-4"
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

                    <h1 className="text-5xl sm:text-6xl font-black mb-4 tracking-tight text-stone-800">
                        DAGU
                    </h1>

                    <p className="text-lg text-stone-600 max-w-md mx-auto">
                        악기 시세를 한눈에 비교하고, <br className="sm:hidden" />
                        <span className="text-emerald-600 font-medium">합리적인 가격</span>에 득템하세요
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
                    <span className="text-sm font-medium text-stone-400 uppercase tracking-widest text-[10px]">Popular Search</span>
                    <div className="flex flex-wrap justify-center gap-2.5">
                        {['Fender Stratocaster', 'Gibson Les Paul', 'BOSS DS-1', 'Ibanez RG'].map((term) => (
                            <motion.button
                                key={term}
                                onClick={() => handleSearch(term)}
                                className="
                                    px-4 py-2 text-sm bg-white/60 backdrop-blur-sm text-stone-600 
                                    rounded-full border border-stone-200 
                                    hover:bg-matcha-50 hover:border-matcha-200 hover:text-matcha-700 
                                    transition-all duration-300 shadow-sm
                                "
                                whileHover={{ scale: 1.05, y: -2 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                {term}
                            </motion.button>
                        ))}
                    </div>
                </motion.div>
            </main>

            {/* 푸터 */}
            <footer className="py-6 text-center text-sm text-stone-400">
                <p>© 2026 MALCHA DAGU. 악기 시세 비교 서비스</p>
            </footer>
        </div>
    );
}
