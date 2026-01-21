/**
 * Search Bar Component
 * 
 * Features:
 * - 모바일 퍼스트 디자인
 * - DB에서 악기 목록 자동완성
 * - 검색 버튼 hover 효과
 */

import { useState, useEffect, useRef, type FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchBarProps {
    onSearch: (query: string) => void;
    isLoading?: boolean;
    placeholder?: string;
    initialValue?: string;
    showSuggestions?: boolean;
    hideHint?: boolean;
}

interface Instrument {
    id: string;
    brand: string;
    name: string;  // API에서는 'name' 필드 사용
    category: string;
}

export default function SearchBar({
    onSearch,
    isLoading = false,
    placeholder = '악기 이름으로 검색 (예: 펜더 스트랫)',
    initialValue = '',
    showSuggestions = true,
    hideHint = false,
}: SearchBarProps) {
    const [query, setQuery] = useState(initialValue);
    const [isFocused, setIsFocused] = useState(false);
    const [suggestions, setSuggestions] = useState<Instrument[]>([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const wrapperRef = useRef<HTMLDivElement>(null);

    // 검색어 변경 시 서버 검색 (Debounce 적용)
    useEffect(() => {
        const trimmedQuery = query.trim();
        if (!trimmedQuery || !showSuggestions) {
            setSuggestions([]);
            setShowDropdown(false);
            return;
        }

        const timer = setTimeout(async () => {
            try {
                // 서버에서 검색 (브랜드/모델명 포함)
                // api.ts의 getInstruments는 { search: string } 파라미터를 지원함
                const { getInstruments } = await import('../services/api');
                const results = await getInstruments({ search: trimmedQuery });

                // 최대 6개만 표시
                setSuggestions(results.slice(0, 6));

                // 검색 결과가 있고 포커스 상태면 드롭다운 표시
                if (results.length > 0 && isFocused) {
                    setShowDropdown(true);
                }
            } catch (error) {
                console.error('추천 검색어 로드 실패:', error);
            }
        }, 300); // 300ms 딜레이

        return () => clearTimeout(timer);
    }, [query, showSuggestions]);

    // 포커스 상태에 따른 드롭다운 표시 제어
    useEffect(() => {
        if (isFocused && suggestions.length > 0) {
            setShowDropdown(true);
        } else if (!isFocused) {
            // blur 시에는 handleSuggestionClick 등을 위해 약간의 지연 후 닫힘 (onBlur에서 처리됨) 또는 즉시 닫힘
            // 여기서는 onBlur가 처리하므로 추가 동작 불필요, 
            // 다만 isFocused가 false로 바뀌면 드롭다운을 닫는게 안전함 (onBlur의 timeout과 별개로)
            const timer = setTimeout(() => setShowDropdown(false), 200);
            return () => clearTimeout(timer);
        }
    }, [isFocused, suggestions]);

    // 외부 클릭 시 드롭다운 닫기
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query.trim());
            setShowDropdown(false);
        }
    };

    const handleSuggestionClick = (instrument: Instrument) => {
        const searchTerm = `${instrument.brand} ${instrument.name}`;
        setQuery(searchTerm);
        onSearch(searchTerm);
        setShowDropdown(false);
    };

    // 카테고리별 이모지
    const getCategoryEmoji = (category: string) => {
        switch (category.toLowerCase()) {
            case '일렉기타': case 'guitar': return '🎸';
            case '베이스': case 'bass': return '🎸';
            case '이펙터': case 'pedal': case 'effects': return '🔊';
            case '앰프': case 'amp': return '🔈';
            case '어쿠스틱': case 'acoustic': return '🪕';
            default: return '🎵';
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
            <div ref={wrapperRef} className="relative">
                <div
                    className={`
                        relative flex items-center gap-1 sm:gap-2 p-2 sm:p-3 rounded-full transition-all duration-300
                        ${isFocused
                            ? 'bg-white shadow-[0_8px_30px_rgba(0,0,0,0.12)] ring-2 ring-matcha-500 transform -translate-y-1'
                            : 'bg-white shadow-[0_4px_20px_rgba(0,0,0,0.08)] hover:shadow-[0_8px_25px_rgba(0,0,0,0.12)] hover:-translate-y-0.5'
                        }
                    `}
                    style={{ backdropFilter: 'blur(8px)' }}
                >
                    {/* 검색 아이콘 */}
                    <div className={`pl-2 sm:pl-4 transition-colors duration-300 ${isFocused ? 'text-matcha-500' : 'text-stone-400'}`}>
                        <svg
                            className="w-4 h-4 sm:w-5 sm:h-5"
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
                        onBlur={() => setTimeout(() => setIsFocused(false), 150)}
                        placeholder={placeholder}
                        disabled={isLoading}
                        autoComplete="off"
                        className="
                            flex-1 py-2 sm:py-3 px-1 sm:px-2 bg-transparent outline-none
                            text-stone-800 placeholder-stone-400
                            text-sm sm:text-lg caret-matcha-500 min-w-0
                        "
                    />

                    {/* 검색 버튼 */}
                    <motion.button
                        type="submit"
                        disabled={isLoading}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`
                            px-4 sm:px-8 py-2.5 sm:py-4 rounded-lg sm:rounded-xl font-bold text-sm sm:text-lg text-white
                            transition-all duration-200 shrink-0
                            ${isLoading
                                ? 'bg-stone-300 cursor-not-allowed'
                                : 'bg-[#10B981] hover:bg-[#059669] shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/40 hover:scale-105 active:scale-95'
                            }
                        `}
                    >
                        {isLoading ? (
                            <motion.div
                                className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white/30 border-t-white rounded-full"
                                animate={{ rotate: 360 }}
                                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            />
                        ) : (
                            <span className="whitespace-nowrap">검색</span>
                        )}
                    </motion.button>
                </div>

                {/* 자동완성 드롭다운 (DB 악기 목록) */}
                <AnimatePresence>
                    {showDropdown && suggestions.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.15 }}
                            className="
                                absolute z-50 w-full mt-2 py-2
                                bg-white rounded-xl shadow-xl border border-stone-100
                                overflow-hidden
                            "
                        >
                            <p className="px-4 py-1 text-[10px] text-stone-400 uppercase tracking-wider">
                                등록된 악기
                            </p>
                            {suggestions.map((instrument) => (
                                <button
                                    key={instrument.id}
                                    type="button"
                                    onClick={() => handleSuggestionClick(instrument)}
                                    className="
                                        w-full px-4 py-3 text-left flex items-center gap-3
                                        hover:bg-matcha-50 transition-colors
                                        text-stone-700 hover:text-matcha-700
                                    "
                                >
                                    <span className="text-lg">{getCategoryEmoji(instrument.category)}</span>
                                    <div className="flex-1">
                                        <p className="font-medium">{instrument.brand} {instrument.name}</p>
                                        <p className="text-xs text-stone-400">{instrument.category}</p>
                                    </div>
                                </button>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* 검색 힌트 */}
            {!hideHint && (
                <motion.p
                    className="mt-3 text-center text-sm text-stone-500"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0.8 }}
                    transition={{ delay: 0.3 }}
                >
                    브랜드, 모델명, 또는 카테고리로 검색해보세요
                </motion.p>
            )}
        </motion.form>
    );
}
