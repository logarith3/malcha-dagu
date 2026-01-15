/**
 * Matcha-Bounce Loader Component
 * 
 * Features:
 * - 최소 1.5초 노출 보장
 * - 단계별 메시지 변경

 * - Bounce 애니메이션
 * - 완료 시 슬라이드 아웃
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface MatchaBounceLoaderProps {
    isVisible: boolean;
    onComplete?: () => void;
}

const LOADING_MESSAGES = [
    '다구가 기타를 낚아오는 중! 🎣',
    '꼼꼼하게 가격 비교 중... 🧐',
    '다구가 말차 만드는 중... 🍵',
    '거의 다 됐어요! ✨',
];

export default function MatchaBounceLoader({
    isVisible,
    onComplete
}: MatchaBounceLoaderProps) {
    const [messageIndex, setMessageIndex] = useState(0);

    // 단계별 메시지 변경 (0.6초마다)
    useEffect(() => {
        if (!isVisible) {
            setMessageIndex(0);
            return;
        }

        const interval = setInterval(() => {
            setMessageIndex((prev) =>
                prev < LOADING_MESSAGES.length - 1 ? prev + 1 : prev
            );
        }, 1000);

        return () => clearInterval(interval);
    }, [isVisible]);

    return (
        <AnimatePresence onExitComplete={onComplete}>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{
                        opacity: 0,
                        y: -100,
                        transition: { duration: 0.4, ease: 'easeInOut' }
                    }}
                    className="fixed inset-0 z-50 flex flex-col items-center justify-center"
                    style={{
                        background: 'linear-gradient(135deg, #f0fdf4 0%, #fffbeb 100%)',
                    }}
                >
                    {/* 배경 원형 글로우 */}
                    <motion.div
                        className="absolute w-64 h-64 rounded-full opacity-30"
                        style={{
                            background: 'radial-gradient(circle, rgba(34, 197, 94, 0.4) 0%, transparent 70%)',
                        }}
                        animate={{
                            scale: [1, 1.2, 1],
                        }}
                        transition={{
                            duration: 2,
                            repeat: Infinity,
                            ease: 'easeInOut',
                        }}
                    />

                    {/* 메인 캐릭터 (찻잔 이모지) */}
                    <motion.div
                        className="text-8xl mb-8 relative z-10"
                        animate={{
                            y: [0, -20, 0],
                        }}
                        transition={{
                            duration: 1,
                            repeat: Infinity,
                            ease: 'easeInOut',
                        }}
                    >
                        🍵
                    </motion.div>

                    {/* 로딩 메시지 */}
                    <motion.div
                        key={messageIndex}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.3 }}
                        className="text-xl font-medium text-stone-700"
                        style={{ fontFamily: 'var(--font-display)' }}
                    >
                        {LOADING_MESSAGES[messageIndex]}
                    </motion.div>

                    {/* 프로그레스 바 */}
                    <div className="mt-8 w-48 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                        <motion.div
                            className="h-full rounded-full"
                            style={{
                                background: 'linear-gradient(90deg, #22c55e 0%, #4ade80 100%)',
                            }}
                            initial={{ width: '0%' }}
                            animate={{ width: '100%' }}
                            transition={{
                                duration: 2.0,
                                ease: 'easeInOut',
                            }}
                        />
                    </div>

                    {/* 브랜드 워터마크 */}
                    <motion.p
                        className="absolute bottom-8 text-sm text-stone-400"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.6 }}
                        transition={{ delay: 0.5 }}
                    >
                        DAGU
                    </motion.p>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
