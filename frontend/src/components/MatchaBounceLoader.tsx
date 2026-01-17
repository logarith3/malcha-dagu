/**
 * Matcha-Bounce Loader Component
 * 
 * Features:
 * - GIF 이미지만 크게 표시
 * - 완료 시 슬라이드 아웃
 */

import { motion, AnimatePresence } from 'framer-motion';
import daguLoadingGif from '../assets/daguLoading.gif';

interface MatchaBounceLoaderProps {
    isVisible: boolean;
    onComplete?: () => void;
}

export default function MatchaBounceLoader({
    isVisible,
    onComplete
}: MatchaBounceLoaderProps) {
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
                    className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white"
                >
                    {/* 메인 GIF 이미지 */}
                    <img
                        src={daguLoadingGif}
                        alt="다구 로딩"
                        className="max-w-md max-h-md"
                    />
                    {/* 로딩 텍스트 */}
                    <p className="mt-4 text-lg text-stone-600 font-medium">
                        다구가 악기를 낚는중...
                    </p>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
