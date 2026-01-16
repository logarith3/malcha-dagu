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
    placeholder = '악기 이름으로 검색 (예: Fender Stratocaster)',
    initialValue = '',
    showSuggestions = true,
}: SearchBarProps) {
    const [query, setQuery] = useState(initialValue);
    const [isFocused, setIsFocused] = useState(false);
    const [instruments, setInstruments] = useState<Instrument[]>([]);
    const [suggestions, setSuggestions] = useState<Instrument[]>([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const wrapperRef = useRef<HTMLDivElement>(null);

    // DB에서 악기 목록 로드 (최초 1회)
    useEffect(() => {
        async function fetchInstruments() {
            try {
                const res = await fetch('/api/instruments/');
                if (res.ok) {
                    const data = await res.json();
                    // DRF 페이지네이션 응답 처리 (results 배열)
                    const results = data.results || data;
                    setInstruments(Array.isArray(results) ? results : []);
                }
            } catch (error) {
                console.error('악기 목록 로드 실패:', error);
            }
        }
        fetchInstruments();
    }, []);

    // 입력에 따른 추천 필터링
    useEffect(() => {
        if (query.trim().length > 0 && showSuggestions && instruments.length > 0) {
            const queryLower = query.toLowerCase();
            const filtered = instruments.filter(item => {
                const brand = item.brand || '';
                const modelName = item.name || '';
                const fullName = `${brand} ${modelName}`.toLowerCase();
                return fullName.includes(queryLower) ||
                    brand.toLowerCase().includes(queryLower) ||
                    modelName.toLowerCase().includes(queryLower);
            }).slice(0, 6); // 최대 6개
            setSuggestions(filtered);
            setShowDropdown(filtered.length > 0 && isFocused);
        } else {
            setSuggestions([]);
            setShowDropdown(false);
        }
    }, [query, isFocused, showSuggestions, instruments]);

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
                        onBlur={() => setTimeout(() => setIsFocused(false), 150)}
                        placeholder={placeholder}
                        disabled={isLoading}
                        autoComplete="off"
                        className="
                            flex-1 py-3 px-2 bg-transparent outline-none
                            text-stone-800 placeholder-stone-400
                            text-base sm:text-lg caret-matcha-500
                        "
                    />

                    {/* 검색 버튼 */}
                    <motion.button
                        type="submit"
                        disabled={isLoading}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`
                            px-6 py-3 rounded-xl font-medium text-white
                            transition-all duration-200
                            ${isLoading
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
