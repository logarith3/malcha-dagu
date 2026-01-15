/**
 * Search Bar Component
 * 
 * Features:
 * - 모바일 퍼스트 디자인
 * - 입력 시 애니메이션
 * - 검색 버튼 hover 효과
 */

import { useState, type FormEvent } from 'react';
import { motion } from 'framer-motion';

interface SearchBarProps {
    onSearch: (query: string) => void;
    isLoading?: boolean;
    placeholder?: string;
    initialValue?: string;
}

export default function SearchBar({
    onSearch,
    isLoading = false,
    placeholder = '악기 이름으로 검색 (예: Fender Stratocaster)',
    initialValue = '',
}: SearchBarProps) {
    const [query, setQuery] = useState(initialValue);
    const [isFocused, setIsFocused] = useState(false);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query.trim());
        }
    };

    return (
        <motion.form
            onSubmit={handleSubmit}
            className="w-full max-w-2xl mx-auto"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
        >
            <div
                className={`
          relative flex items-center gap-2 p-2 rounded-2xl transition-all duration-300
          ${isFocused
                        ? 'bg-white shadow-lg shadow-matcha-500/20 ring-2 ring-matcha-400'
                        : 'bg-white/80 shadow-md hover:shadow-lg border border-stone-100'
                    }
        `}
                style={{ backdropFilter: 'blur(8px)' }}
            >
                {/* 검색 아이콘 */}
                <div className={`pl-4 transition-colors duration-300 ${isFocused ? 'text-matcha-500' : 'text-stone-400'}`}>
                    <svg
                        className="w-5 h-5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                    </svg>
                </div>

                {/* 입력 필드 */}
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder={placeholder}
                    disabled={isLoading}
                    className="
            flex-1 py-3 px-2 bg-transparent outline-none
            text-stone-800 placeholder-stone-400
            text-base sm:text-lg caret-matcha-500
          "
                />

                {/* 검색 버튼 */}
                <motion.button
                    type="submit"
                    disabled={isLoading || !query.trim()}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`
            px-6 py-3 rounded-xl font-medium text-white
            transition-all duration-200
            ${isLoading || !query.trim()
                            ? 'bg-stone-300 cursor-not-allowed'
                            : 'bg-gradient-to-r from-matcha-500 to-matcha-600 hover:from-matcha-600 hover:to-matcha-700 shadow-md hover:shadow-lg hover:shadow-matcha-500/30'
                        }
          `}
                >
                    {isLoading ? (
                        <motion.div
                            className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        />
                    ) : (
                        <span className="whitespace-nowrap">검색</span>
                    )}
                </motion.button>
            </div>

            {/* 검색 힌트 */}
            <motion.p
                className="mt-3 text-center text-sm text-stone-500"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.8 }}
                transition={{ delay: 0.3 }}
            >
                브랜드, 모델명, 또는 카테고리로 검색해보세요
            </motion.p>
        </motion.form>
    );
}
